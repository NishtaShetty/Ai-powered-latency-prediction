import os
import time
from src.simulate_latency import run_simulation
from src.train_bootstrap import train_model
from src.live_predictor import run_live_monitoring

def main():
    print("🚀 Starting Latency Prediction Pipeline")
    
    # Step 1: Generate simulation data
    print("\n📊 Step 1: Generating simulation data...")
    run_simulation(duration_hours=24)
    print("✅ Simulation data generated")
    
    # Step 2: Train initial model
    print("\n🎯 Step 2: Training initial model...")
    train_model()
    print("✅ Model trained and saved")
    
    # Step 3: Start live monitoring
    print("\n📡 Step 3: Starting live monitoring...")
    print("Press Ctrl+C to stop monitoring")
    
    all_servers = [
        "8.8.8.8",      # Google DNS
        "1.1.1.1",      # Cloudflare DNS
        "9.9.9.9",      # Quad9 DNS
        "208.67.222.222", # OpenDNS
        "64.6.64.6"     # Verisign DNS
    ]
    
    try:
        run_live_monitoring(
            server=all_servers[0],
            all_servers=all_servers,
            log_path="logs/latency_log.csv"
        )
    except KeyboardInterrupt:
        print("\n👋 Monitoring stopped by user")

if __name__ == "__main__":
    main() 