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
        
        // Add to visited websites
        visitedWebsites.add(domain);
        
        // Update popup
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
    fetch('http://localhost:5000/api/status')
        .then(response => response.json())
        .then(data => {
            if (data[domain]) {
                if (data[domain].latency !== undefined && data[domain].latency !== null) {
                    chrome.runtime.sendMessage({ action: 'updateLatency', latency: data[domain].latency });
                }
                if (data[domain].predicted !== undefined && data[domain].predicted !== null) {
                    chrome.runtime.sendMessage({ action: 'updatePrediction', prediction: data[domain].predicted });
                }
            }
        })
        .catch(error => {
            console.error('Failed to fetch status from server:', error);
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