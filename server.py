from flask import Flask, jsonify, render_template, request
import threading
import time
from src.live_predictor import run_live_monitoring
import os
import json
import dns.resolver
import random
import requests
from urllib.parse import urlparse
import subprocess
import re
from datetime import datetime
from flask_cors import CORS



app = Flask(__name__)
CORS(app)
# Global variables to store monitoring state
monitoring_threads = {}  # Dictionary to store monitoring threads for each website
is_monitoring = False
current_status = {}
visited_websites = set()
cookies_store = {}  # Store cookies for each domain

def reset_monitoring_state():
    """Reset all monitoring state variables."""
    global monitoring_threads, is_monitoring, current_status
    print("Resetting monitoring state...")
    is_monitoring = False
    monitoring_threads.clear()
    current_status.clear()
    print("Monitoring state reset complete")

def ping_server(server):
    """Ping a server and return the latency in milliseconds."""
    try:
        # Use ping command with 1 packet and 1 second timeout
        result = subprocess.run(['ping', '-n', '1', '-w', '1000', server], 
                              capture_output=True, text=True)
        
        # Extract latency using regex
        match = re.search(r'Average = (\d+)ms', result.stdout)
        if match:
            return int(match.group(1))
        return None
    except:
        return None

def get_best_server(domain):
    """Get the best server for a domain by checking latency."""
    try:
        # Get A records (IPv4 addresses)
        answers = dns.resolver.resolve(domain, 'A')
        servers = [str(rdata) for rdata in answers]
        
        if not servers:
            return domain
            
        # Test latency for each server
        best_server = None
        best_latency = float('inf')
        
        for server in servers:
            latency = ping_server(server)
            if latency and latency < best_latency:
                best_latency = latency
                best_server = server
                
        return best_server if best_server else domain
    except:
        return domain

def switch_to_server(domain, new_server):
    """Switch to a new server while maintaining cookies."""
    try:
        # Get current cookies
        current_cookies = cookies_store.get(domain, {})
        
        # Make request to new server with existing cookies
        response = requests.get(
            f'http://{new_server}',
            cookies=current_cookies,
            allow_redirects=True,
            timeout=5
        )
        
        # Update cookies
        cookies_store[domain] = response.cookies.get_dict()
        
        return True
    except:
        return False

def monitoring_callback(server, latency, predicted, is_spike, severity, suggested_server=None, improvement=None):
    global current_status
    if server in current_status:
        # Always check for best server
        best_server = get_best_server(server)
        if best_server != server:
            suggested_server = best_server
            # Test latency to best server
            best_latency = ping_server(best_server)
            if best_latency:
                improvement = latency - best_latency

        current_status[server].update({
            "latency": round(latency, 2),
            "predicted": round(predicted, 2),
            "is_spike": is_spike,
            "spike_severity": round(severity, 2),
            "last_update": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "suggested_server": suggested_server,
            "improvement": round(improvement, 2) if improvement else None
        })
        print(f"Updated status for {server}: {current_status[server]}")

def start_monitoring():
    global is_monitoring, monitoring_threads, current_status
    
    if is_monitoring:
        print("Monitoring already running")
        return "Monitoring already running"
    
    is_monitoring = True
    print("Starting monitoring...")
    
    # Initialize status for all visited websites
    for website in visited_websites:
        if website not in current_status:
            current_status[website] = {
                "server": website,
                "latency": None,
                "predicted": None,
                "is_spike": False,
                "spike_severity": 0,
                "last_update": None,
                "suggested_server": None,
                "improvement": None
            }
    
    # Start monitoring for each visited website
    for website in visited_websites:
        if website not in monitoring_threads:
            print(f"Starting monitoring thread for {website}")
            thread = threading.Thread(
                target=run_live_monitoring,
                args=(website, [website], f"logs/latency_log_{website}.csv", monitoring_callback),
                daemon=True
            )
            monitoring_threads[website] = thread
            thread.start()
    
    print("Monitoring started successfully")
    return "Monitoring started"

def stop_monitoring():
    global is_monitoring, monitoring_threads, current_status
    print("Stopping monitoring...")
    is_monitoring = False
    monitoring_threads.clear()
    
    # Reset status for all websites
    for website in current_status:
        current_status[website].update({
            "latency": None,
            "predicted": None,
            "is_spike": False,
            "spike_severity": 0,
            "last_update": None,
            "suggested_server": None,
            "improvement": None
        })
    
    print("Monitoring stopped")
    return "Monitoring stopped"

@app.route('/')
def home():
    return render_template('index.html')

@app.route('/api/status')
def get_status():
    print(f"Current status: {current_status}")
    return jsonify(current_status)

@app.route('/api/start')
def start():
    result = start_monitoring()
    print(f"Start monitoring result: {result}")
    return jsonify({"message": result})

@app.route('/api/stop')
def stop():
    result = stop_monitoring()
    print(f"Stop monitoring result: {result}")
    return jsonify({"message": result})

@app.route('/api/reset')
def reset():
    """Reset the monitoring state."""
    reset_monitoring_state()
    return jsonify({"message": "Monitoring state reset"})

@app.route('/api/switch_server', methods=['POST'])
def switch_server():
    try:
        data = request.get_json()
        domain = data.get('domain')
        new_server = data.get('new_server')
        
        if not domain or not new_server:
            return jsonify({'success': False, 'error': 'Missing domain or server'})
            
        if switch_to_server(domain, new_server):
            return jsonify({'success': True})
        else:
            return jsonify({'success': False, 'error': 'Failed to switch server'})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/add_website', methods=['POST'])
def add_website():
    global visited_websites, current_status, monitoring_threads
    
    try:
        data = request.get_json()
        website = data.get('website')
        
        if not website:
            return jsonify({'success': False, 'error': 'No website specified'})
        
        print(f"Adding website: {website}")
        
        # Add to visited websites
        visited_websites.add(website)
        
        # Initialize status for the new website
        if website not in current_status:
            current_status[website] = {
                "server": website,
                "latency": None,
                "predicted": None,
                "is_spike": False,
                "spike_severity": 0,
                "last_update": None,
                "suggested_server": None,
                "improvement": None
            }
            
            # Start monitoring the new website if monitoring is active
            if is_monitoring and website not in monitoring_threads:
                print(f"Starting monitoring thread for new website: {website}")
                thread = threading.Thread(
                    target=run_live_monitoring,
                    args=(website, [website], f"logs/latency_log_{website}.csv", monitoring_callback),
                    daemon=True
                )
                monitoring_threads[website] = thread
                thread.start()
        
        return jsonify({'success': True})
    except Exception as e:
        print(f"Error adding website: {str(e)}")
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/websites')
def get_websites():
    return jsonify(list(visited_websites))

if __name__ == '__main__':
    # Create necessary directories
    os.makedirs("templates", exist_ok=True)
    os.makedirs("logs", exist_ok=True)
    os.makedirs("model", exist_ok=True)
    
    # Reset monitoring state on startup
    reset_monitoring_state()
    
    app.run(debug=True, port=5000) 