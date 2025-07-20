from flask import Flask, jsonify, render_template, request
import threading
import time
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

# Import the real latency predictor modules
from src.live_predictor import run_live_monitoring, LatencyPredictor
from src.ping_utils import ping_latency
from src.reroute_selector import get_best_server

app = Flask(__name__)
CORS(app)

# Global variables to store monitoring state
monitoring_threads = {}  # Dictionary to store monitoring threads for each website
is_monitoring = False
current_status = {}
visited_websites = set()
cookies_store = {}  # Store cookies for each domain
predictors = {}  # Store LatencyPredictor instances for each website

def reset_monitoring_state():
    """Reset all monitoring state variables."""
    global monitoring_threads, is_monitoring, current_status, predictors
    print("Resetting monitoring state...")
    is_monitoring = False
    monitoring_threads.clear()
    current_status.clear()
    predictors.clear()
    print("Monitoring state reset complete")

def ping_server(server):
    """Ping a server and return the latency in milliseconds."""
    return ping_latency(server)

def get_best_server_for_domain(domain):
    """Get the best server for a domain by checking latency."""
    try:
        # Get A records (IPv4 addresses)
        answers = dns.resolver.resolve(domain, 'A')
        servers = [str(rdata) for rdata in answers]
        
        if not servers:
            return domain
            
        # Use the reroute_selector to find best server
        best_server = get_best_server(servers)
        return best_server if best_server else domain
        
    except Exception as e:
        print(f"DNS resolution error for {domain}: {e}")
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
    except Exception as e:
        print(f"Server switch error: {e}")
        return False

def real_monitoring(website):
    """Real monitoring using the live predictor."""
    try:
        print(f"Starting real monitoring for {website}")
        
        # Create log file path
        log_file = f"logs/{website}_monitoring.csv"
        
        # Get available servers for this domain
        try:
            answers = dns.resolver.resolve(website, 'A')
            servers = [str(rdata) for rdata in answers]
        except:
            servers = [website]  # Fallback to original domain
        
        # Start live monitoring
        run_live_monitoring(website, servers, log_file, monitoring_callback)
        
    except Exception as e:
        print(f"Error in real monitoring for {website}: {e}")
        # Fallback to simulation if real monitoring fails
        simulate_monitoring(website)

def simulate_monitoring(website):
    """Fallback simulation for monitoring when real predictor fails."""
    print(f"Falling back to simulation for {website}")
    
    # Initialize predictor for this website if not exists
    if website not in predictors:
        predictors[website] = LatencyPredictor()
    
    predictor = predictors[website]
    
    while is_monitoring and website in monitoring_threads:
        try:
            # Get real latency using ping
            current_latency = ping_latency(website)
            
            if current_latency is None:
                # If ping fails, use simulated data
                base_latency = random.uniform(20, 100)
                spike_factor = random.uniform(0.8, 2.5) if random.random() < 0.2 else 1.0
                current_latency = base_latency * spike_factor
            
            # Update predictor with real data
            timestamp = datetime.now()
            predictor.update(current_latency, timestamp)
            
            # Get prediction
            predicted_latency, is_spike, severity = predictor.predict(current_latency)
            
            # Get best server suggestion if there's a spike
            suggested_server = None
            improvement = None
            if is_spike:
                best_server = get_best_server_for_domain(website)
                if best_server != website:
                    suggested_server = best_server
                    best_latency = ping_latency(best_server)
                    if best_latency:
                        improvement = current_latency - best_latency
            
            # Call monitoring callback
            monitoring_callback(website, current_latency, predicted_latency, is_spike, severity, suggested_server, improvement)
            
            time.sleep(2)  # Update every 2 seconds
            
        except Exception as e:
            print(f"Monitoring error for {website}: {e}")
            break

def monitoring_callback(server, latency, predicted, is_spike, severity, suggested_server=None, improvement=None):
    """Callback function for monitoring updates."""
    global current_status
    
    if server in current_status:
        # Update status with real prediction data
        current_status[server].update({
            "latency": round(latency, 2),
            "predicted": round(predicted, 2),
            "is_spike": is_spike,
            "spike_severity": round(severity * 100, 2) if severity else 0,  # Convert to percentage
            "last_update": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "suggested_server": suggested_server,
            "improvement": round(improvement, 2) if improvement else None
        })
        print(f"Updated status for {server}: {current_status[server]}")

def start_monitoring():
    """Start monitoring for all visited websites."""
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
                target=real_monitoring,  # Use real monitoring instead of simulation
                args=(website,),
                daemon=True
            )
            monitoring_threads[website] = thread
            thread.start()
    
    print("Monitoring started successfully")
    return "Monitoring started"

def stop_monitoring():
    """Stop monitoring for all websites."""
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
    """Get current monitoring status for all websites."""
    print(f"Current status: {current_status}")
    return jsonify(current_status)

@app.route('/api/start')
def start():
    """Start monitoring endpoint."""
    result = start_monitoring()
    print(f"Start monitoring result: {result}")
    return jsonify({"message": result})

@app.route('/api/stop')
def stop():
    """Stop monitoring endpoint."""
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
    """Switch to a different server for a domain."""
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
    """Add a new website to monitor."""
    global visited_websites, current_status, monitoring_threads
    
    try:
        data = request.get_json()
        website = data.get('website')
        
        if not website:
            return jsonify({'success': False, 'error': 'No website specified'})
        
        # Clean up the website URL
        website = website.replace('http://', '').replace('https://', '').replace('www.', '')
        
        print(f"Adding website: {website}")
        
        # Add to visited websites
        visited_websites.add(website)
        
        # Initialize predictor for this website
        if website not in predictors:
            predictors[website] = LatencyPredictor()
        
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
                    target=real_monitoring,
                    args=(website,),
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
    """Get list of all monitored websites."""
    return jsonify(list(visited_websites))

@app.route('/api/predictor_stats/<website>')
def get_predictor_stats(website):
    """Get statistics about the predictor for a specific website."""
    try:
        if website in predictors:
            predictor = predictors[website]
            stats = {
                "is_trained": predictor.is_trained,
                "history_length": len(predictor.history),
                "training_samples": len(predictor.training_data),
                "last_retrain": predictor.last_retrain,
                "spike_threshold": predictor.spike_threshold
            }
            return jsonify(stats)
        else:
            return jsonify({"error": "Website not found"})
    except Exception as e:
        return jsonify({"error": str(e)})

@app.route('/api/retrain/<website>', methods=['POST'])
def retrain_predictor(website):
    """Manually retrain the predictor for a specific website."""
    try:
        if website in predictors:
            predictors[website].retrain()
            return jsonify({"success": True, "message": f"Predictor for {website} retrained"})
        else:
            return jsonify({"success": False, "error": "Website not found"})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

if __name__ == '__main__':
    # Create necessary directories
    os.makedirs("templates", exist_ok=True)
    os.makedirs("logs", exist_ok=True)
    os.makedirs("static", exist_ok=True)
    os.makedirs("src", exist_ok=True)
    os.makedirs("model", exist_ok=True)
    
    # Reset monitoring state on startup
    reset_monitoring_state()
    
    print("Starting Flask Network Monitoring Server with Real Latency Prediction...")
    print("Dashboard will be available at: http://localhost:5000")
    
    app.run(debug=True, port=5000, host='0.0.0.0')