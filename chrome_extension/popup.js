let isMonitoring = false;
let currentWebsite = '';

// Initialize UI with current monitoring state
chrome.runtime.sendMessage({ action: 'getMonitoringState' }, (response) => {
    if (response) {
        isMonitoring = response.isMonitoring;
        updateUI();
        // Get current active tab to display
        getCurrentTab();
    }
});

// Get current active tab information
function getCurrentTab() {
    chrome.tabs.query({ active: true, currentWindow: true }, (tabs) => {
        if (tabs[0] && tabs[0].url) {
            try {
                const urlObj = new URL(tabs[0].url);
                const domain = urlObj.hostname;
                updateCurrentWebsite(domain);
                // Request status for current domain
                chrome.runtime.sendMessage({ action: 'getStatusForDomain', domain: domain });
            } catch (error) {
                console.error('Error processing current tab URL:', error);
                updateCurrentWebsite('Invalid URL');
            }
        }
    });
}

function updateCurrentWebsite(website) {
    currentWebsite = website;
    const websiteElement = document.getElementById('currentWebsite');
    if (website && website !== 'Invalid URL') {
        websiteElement.textContent = website;
        websiteElement.className = 'website-name';
    } else {
        websiteElement.textContent = 'No website detected';
        websiteElement.className = 'website-name no-data';
    }
}

function updateConfidenceDisplay(confidence) {
    const confidenceBar = document.getElementById('confidenceBar');
    const confidenceText = document.getElementById('confidenceText');
    
    if (confidence !== undefined && confidence !== null && confidence !== '-') {
        const confidencePercent = Math.round(confidence * 100);
        confidenceBar.style.width = `${confidencePercent}%`;
        confidenceText.textContent = `${confidencePercent}%`;
        
        // Update confidence bar color based on confidence level
        if (confidencePercent >= 80) {
            confidenceBar.style.background = '#34a853'; // Green for high confidence
        } else if (confidencePercent >= 60) {
            confidenceBar.style.background = '#fbbc04'; // Yellow for medium confidence
        } else {
            confidenceBar.style.background = '#ea4335'; // Red for low confidence
        }
    } else {
        confidenceBar.style.width = '0%';
        confidenceText.textContent = '-';
    }
}

document.getElementById('toggleMonitoring').addEventListener('click', () => {
    isMonitoring = !isMonitoring;
    updateUI();
    
    // Send status to background script
    chrome.runtime.sendMessage({
        action: 'toggleMonitoring',
        isMonitoring: isMonitoring
    });
    
    // Refresh current tab info when starting monitoring
    if (isMonitoring) {
        getCurrentTab();
    }
});

function updateUI() {
    const statusEl = document.getElementById('status');
    const buttonEl = document.getElementById('toggleMonitoring');
    
    if (isMonitoring) {
        statusEl.textContent = 'Active';
        statusEl.className = 'active';
        buttonEl.textContent = 'Stop Monitoring';
    } else {
        statusEl.textContent = 'Inactive';
        statusEl.className = 'inactive';
        buttonEl.textContent = 'Start Monitoring';
        // Clear metrics when monitoring is stopped
        document.getElementById('currentLatencyValue').textContent = '-';
        document.getElementById('predictedLatencyValue').textContent = '-';
        updateConfidenceDisplay(null);
    }
}

// Listen for updates from background script
chrome.runtime.onMessage.addListener((message) => {
    if (message.action === 'updateLastWebsite') {
        updateCurrentWebsite(message.website);
        chrome.runtime.sendMessage({ action: 'getStatusForDomain', domain: message.website });
    } else if (message.action === 'updateLatency') {
        const latencyValue = message.latency;
        document.getElementById('currentLatencyValue').textContent = 
            latencyValue !== undefined && latencyValue !== null ? `${latencyValue}ms` : '-';
    } else if (message.action === 'updatePrediction') {
        const predictionValue = message.prediction;
        document.getElementById('predictedLatencyValue').textContent = 
            predictionValue !== undefined && predictionValue !== null ? `${predictionValue}ms` : '-';
    } else if (message.action === 'updateConfidence') {
        updateConfidenceDisplay(message.confidence);
    }
});

// Listen for tab changes to update current website display
chrome.tabs.onActivated.addListener(() => {
    getCurrentTab();
});

chrome.tabs.onUpdated.addListener((tabId, changeInfo, tab) => {
    if (changeInfo.status === 'complete') {
        chrome.tabs.query({ active: true, currentWindow: true }, (tabs) => {
            if (tabs[0] && tabs[0].id === tabId) {
                getCurrentTab();
            }
        });
    }
});