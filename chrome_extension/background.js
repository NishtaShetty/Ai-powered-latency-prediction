// Track visited websites and monitoring state
let visitedWebsites = new Set();
let isMonitoring = false;

// Initialize monitoring state from storage
chrome.storage.local.get(['isMonitoring'], (result) => {
    isMonitoring = result.isMonitoring || false;
    if (isMonitoring) {
        // Start monitoring all current tabs
        chrome.tabs.query({}, (tabs) => {
            tabs.forEach(tab => {
                if (tab.url) {
                    addWebsite(tab.url);
                }
            });
        });
    }
});

// Listen for messages from popup
chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
    if (message.action === 'toggleMonitoring') {
        isMonitoring = message.isMonitoring;
        // Save monitoring state to storage
        chrome.storage.local.set({ isMonitoring: isMonitoring });
        
        if (isMonitoring) {
            // Start monitoring all current tabs
            chrome.tabs.query({}, (tabs) => {
                tabs.forEach(tab => {
                    if (tab.url) {
                        addWebsite(tab.url);
                    }
                });
            });
        }
    } else if (message.action === 'getMonitoringState') {
        // Send current monitoring state to popup
        sendResponse({ isMonitoring: isMonitoring });
    } else if (message.action === 'getStatusForDomain') {
        fetchAndUpdateStatus(message.domain);
    }
});

function addWebsite(url) {
    try {
        const urlObj = new URL(url);
        const domain = urlObj.hostname;
        
        // Skip chrome:// and extension URLs
        if (urlObj.protocol === 'chrome:' || urlObj.protocol === 'chrome-extension:') {
            return;
        }
        
        // Add to visited websites
        visitedWebsites.add(domain);
        
        // Update popup with current website
        chrome.runtime.sendMessage({
            action: 'updateLastWebsite',
            website: domain
        });
        
        // Send to our monitoring server if monitoring is active
        if (isMonitoring) {
            console.log('Sending website to server:', domain);
            fetch('http://localhost:5000/api/add_website', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    website: domain
                })
            })
            .then(response => response.json())
            .then(data => {
                console.log('Server response:', data);
                fetchAndUpdateStatus(domain);
            })
            .catch(error => {
                console.error('Failed to send website to server:', error);
            });
        }
    } catch (error) {
        console.error('Error processing URL:', error);
    }
}

function fetchAndUpdateStatus(domain) {
    if (!domain || domain === 'No website detected') {
        return;
    }
    
    fetch('http://localhost:5000/api/status')
        .then(response => response.json())
        .then(data => {
            if (data[domain]) {
                // Update latency
                if (data[domain].latency !== undefined && data[domain].latency !== null) {
                    chrome.runtime.sendMessage({ 
                        action: 'updateLatency', 
                        latency: Math.round(data[domain].latency ) // Convert to ms
                    });
                }
                
                // Update prediction
                if (data[domain].predicted !== undefined && data[domain].predicted !== null) {
                    chrome.runtime.sendMessage({ 
                        action: 'updatePrediction', 
                        prediction: Math.round(data[domain].predicted ) // Convert to ms
                    });
                }
                
                // Update confidence (assuming server provides this)
                if (data[domain].confidence !== undefined && data[domain].confidence !== null) {
                    chrome.runtime.sendMessage({ 
                        action: 'updateConfidence', 
                        confidence: data[domain].confidence 
                    });
                } else {
                    // If no confidence provided, calculate a mock confidence based on prediction accuracy
                    if (data[domain].latency && data[domain].predicted) {
                        const accuracy = 1 - Math.abs(data[domain].latency - data[domain].predicted) / data[domain].latency;
                        const confidence = Math.max(0.3, Math.min(0.95, accuracy)); // Clamp between 30% and 95%
                        chrome.runtime.sendMessage({ 
                            action: 'updateConfidence', 
                            confidence: confidence 
                        });
                    }
                }
            } else {
                // No data available for this domain
                chrome.runtime.sendMessage({ action: 'updateLatency', latency: null });
                chrome.runtime.sendMessage({ action: 'updatePrediction', prediction: null });
                chrome.runtime.sendMessage({ action: 'updateConfidence', confidence: null });
            }
        })
        .catch(error => {
            console.error('Failed to fetch status from server:', error);
            // Clear values on error
            chrome.runtime.sendMessage({ action: 'updateLatency', latency: null });
            chrome.runtime.sendMessage({ action: 'updatePrediction', prediction: null });
            chrome.runtime.sendMessage({ action: 'updateConfidence', confidence: null });
        });
}

// Listen for navigation events
chrome.webNavigation.onCompleted.addListener((details) => {
    if (details.frameId === 0) {  // Main frame only
        addWebsite(details.url);
    }
});

// Listen for tab updates
chrome.tabs.onUpdated.addListener((tabId, changeInfo, tab) => {
    if (changeInfo.status === 'complete' && tab.url) {
        addWebsite(tab.url);
    }
});

// Listen for tab activation to update current website display
chrome.tabs.onActivated.addListener((activeInfo) => {
    chrome.tabs.get(activeInfo.tabId, (tab) => {
        if (tab.url) {
            addWebsite(tab.url);
        }
    });
});