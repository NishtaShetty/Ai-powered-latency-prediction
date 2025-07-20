# Latency Predictor

A Flask-based network monitoring and latency prediction tool. This project monitors the latency of specified websites, predicts latency spikes, and suggests better servers when available. It also includes a Chrome extension for browser integration.

## Features
- Real-time latency monitoring for multiple websites
- Latency prediction using machine learning
- Spike detection and severity reporting
- Server rerouting suggestions
- REST API for status, control, and stats
- Chrome extension for browser integration

## Project Structure
```
latency_predictor/
├── main.py
├── requirements.txt
├── run_pipeline.py
├── server.py           # Main Flask server (real prediction)
├── chrome_extension/   # Chrome extension files
├── data/               # Data files (CSV, logs)
├── logs/               # Monitoring logs
├── model/              # Trained model files
├── src/                # Core modules (predictor, utils, etc.)
├── static/             # Static files for web UI
└── templates/          # HTML templates
```

## Getting Started

### Prerequisites
- Python 3.8+
- pip

### Installation
1. Clone the repository:
   ```sh
   git clone https://github.com/<your-username>/<repo-name>.git
   cd <repo-name>
   ```
2. Install dependencies:
   ```sh
   pip install -r requirements.txt
   ```

### Running the Server
- For real prediction (requires model and src modules):
  ```sh
  python server.py
  ```
- For simulation/demo only:
  ```sh
  python server1.py
  ```

The dashboard will be available at [http://localhost:5000](http://localhost:5000).

### API Endpoints
- `/api/status` — Get current monitoring status
- `/api/start` — Start monitoring
- `/api/stop` — Stop monitoring
- `/api/reset` — Reset monitoring state
- `/api/add_website` — Add a website to monitor (POST JSON: `{ "website": "example.com" }`)
- `/api/websites` — List monitored websites
- `/api/switch_server` — Switch to a different server (POST JSON)
- `/api/predictor_stats/<website>` — Get predictor stats (real mode)
- `/api/retrain/<website>` — Retrain predictor (real mode)

### Chrome Extension
- See `chrome_extension/` for browser integration. Follow the instructions in the folder to load the extension in Chrome.

## How to Use This Project

This project is designed for:

- **Network administrators and IT professionals** who want to monitor website latency, detect spikes, and optimize routing for better performance.
- **Developers and researchers** interested in real-time network analytics, latency prediction, and server rerouting using machine learning.
- **Anyone needing a dashboard** to visualize and track latency for a set of websites or web services.

### Typical Use Cases
- **Monitor multiple websites** for latency and spikes in real time.
- **Receive server suggestions** when a latency spike is detected, allowing you to reroute traffic for improved performance.
- **Integrate with browsers** using the included Chrome extension for seamless website tracking.
- **Analyze historical data** by reviewing logs and model predictions.
- **Extend or customize** the prediction logic by modifying the `src/` modules or retraining the model.

### Getting Started
1. **Add websites** to monitor using the dashboard or API.
2. **Start monitoring** to begin collecting latency data and predictions.
3. **View the dashboard** at [http://localhost:5000](http://localhost:5000) to see real-time stats and server suggestions.
4. **Use the API** for automation or integration with other tools.
5. **(Optional) Load the Chrome extension** for browser-based monitoring.

For more details, see the sections above on installation, running the server, and available API endpoints.

## Implementation Steps

Follow these steps to implement and use the Latency Predictor project:

1. **Clone the Repository**
   - Download the project from GitHub:
     ```sh
     git clone https://github.com/<your-username>/<repo-name>.git
     cd <repo-name>
     ```

2. **Install Dependencies**
   - Install all required Python packages:
     ```sh
     pip install -r requirements.txt
     ```

3. **(Optional) Prepare Model Files**
   - If using real prediction, ensure the `model/` directory contains the necessary model files (e.g., `latency_model.joblib`).

4. **Start the Server**
   - For real prediction:
     ```sh
     python server.py
     ```
   - For simulation/demo only:
     ```sh
     python server1.py
     ```

5. **Access the Dashboard**
   - Open your browser and go to [http://localhost:5000](http://localhost:5000).

6. **Add Websites to Monitor**
   - Use the dashboard or send a POST request to `/api/add_website` with the website domain.

7. **Start Monitoring**
   - Click the start button on the dashboard or call the `/api/start` endpoint.

8. **View Real-Time Stats**
   - Monitor latency, predictions, and server suggestions on the dashboard.

9. **(Optional) Use the Chrome Extension**
   - Load the extension from the `chrome_extension/` folder in your browser for seamless integration.

10. **(Optional) Use the API**
    - Integrate with other tools or automate monitoring using the provided REST API endpoints.

11. **Stop or Reset Monitoring**
    - Use the dashboard or API endpoints to stop or reset monitoring as needed.

## License
MIT License