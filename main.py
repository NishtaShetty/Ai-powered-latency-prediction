from src.live_predictor import run_live_monitoring

if __name__ == "__main__":
    all_servers = ["8.8.8.8", "1.1.1.1", "9.9.9.9"]
    run_live_monitoring(server="8.8.8.8", all_servers=all_servers)
