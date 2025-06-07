import random
import time
import csv
import os
import datetime
import math

def simulate_latency(timestamp):
    dt = datetime.datetime.fromtimestamp(timestamp)
    hour = dt.hour
    
    # Base latency varies by time of day
    if 9 <= hour <= 17:  # Business hours
        base = random.randint(60, 90)
    elif 18 <= hour <= 22:  # Evening peak
        base = random.randint(70, 100)
    else:  # Off hours
        base = random.randint(40, 70)
    
    # Random spikes with different probabilities
    spike = random.choices([0, 20, 50, 100], weights=[85, 10, 4, 1])[0]
    
    # Add some periodic variation
    periodic = 10 * abs(math.sin(timestamp / 3600))  # Hourly cycle
    
    return base + spike + periodic

def run_simulation(path="data/bootstrapped_latency.csv", duration_hours=24):
    os.makedirs("data", exist_ok=True)
    
    servers = [
        "8.8.8.8",      # Google DNS
        "1.1.1.1",      # Cloudflare DNS
        "9.9.9.9",      # Quad9 DNS
        "208.67.222.222", # OpenDNS
        "64.6.64.6"     # Verisign DNS
    ]
    
    start_time = time.time() - (duration_hours * 3600)  # Start from duration_hours ago
    
    with open(path, "w", newline="") as f:
        writer = csv.writer(f)
        writer.writerow(["timestamp", "server_id", "latency"])
        
        current_time = start_time
        while current_time < time.time():
            for server in servers:
                latency = simulate_latency(current_time)
                writer.writerow([current_time, server, latency])
            current_time += 60  # One reading per minute per server
