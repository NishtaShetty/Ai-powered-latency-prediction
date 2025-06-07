let isMonitoring = false;

// Initialize UI with current monitoring state
chrome.runtime.sendMessage({ action: 'getMonitoringState' }, (response) => {
    if (response) {
        isMonitoring = response.isMonitoring;
        updateUI();
        chrome.runtime.sendMessage({ action: 'getStatusForDomain', domain: document.getElementById('lastWebsite').textContent });
    }
});

document.getElementById('toggleMonitoring').addEventListener('click', () => {
    isMonitoring = !isMonitoring;
    updateUI();
    
    // Send status to background script
    chrome.runtime.sendMessage({
        action: 'toggleMonitoring',
        isMonitoring: isMonitoring
    });
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
    }
}

// Listen for updates from background script
chrome.runtime.onMessage.addListener((message) => {
    if (message.action === 'updateLastWebsite') {
        document.getElementById('lastWebsite').textContent = message.website;
        chrome.runtime.sendMessage({ action: 'getStatusForDomain', domain: message.website });
    } else if (message.action === 'updateLatency') {
        document.getElementById('currentLatencyValue').textContent = message.latency;
    } else if (message.action === 'updatePrediction') {
        document.getElementById('predictedLatencyValue').textContent = message.prediction;
    }
}); 