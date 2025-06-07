from river import linear_model, preprocessing
import datetime
import time
import pickle
import os
import csv
import json
from src.ping_utils import ping_latency
from src.reroute_selector import get_best_server
import pandas as pd
import numpy as np
from sklearn.ensemble import RandomForestRegressor
from sklearn.preprocessing import StandardScaler
import joblib
import threading
import warnings
warnings.filterwarnings('ignore')

def extract_features(timestamp, server_id):
    dt = datetime.datetime.fromtimestamp(timestamp)
    return {
        "hour": dt.hour,
        "minute": dt.minute,
        "day_of_week": dt.weekday(),
        "is_weekend": int(dt.weekday() >= 5),
        "is_business_hours": int(9 <= dt.hour <= 17),
        "server_id": hash(server_id) % 10,
        "time_of_day": dt.hour + dt.minute/60,  # Continuous time feature
        "is_night": int(22 <= dt.hour or dt.hour <= 6),  # Night hours
        "is_morning": int(6 < dt.hour <= 12),  # Morning hours
        "is_afternoon": int(12 < dt.hour <= 18),  # Afternoon hours
        "is_evening": int(18 < dt.hour < 22),  # Evening hours
        "is_weekday_morning": int(dt.weekday() < 5 and 6 < dt.hour <= 12),  # Weekday morning
        "is_weekday_evening": int(dt.weekday() < 5 and 18 < dt.hour < 22),  # Weekday evening
        "is_weekend_day": int(dt.weekday() >= 5 and 6 < dt.hour <= 18),  # Weekend day
        "is_weekend_night": int(dt.weekday() >= 5 and (dt.hour > 18 or dt.hour <= 6))  # Weekend night
    }

def detect_spike(actual, predicted, threshold_ms=15, min_latency_ms=100):
    """Detect if current latency is a significant spike"""
    if actual is None or predicted is None:
        return False, 0
    
    # Calculate the percentage difference
    percent_diff = abs(actual - predicted) / predicted if predicted > 0 else 0
    
    # Check if latency is above minimum threshold and significantly different from prediction
    if actual > min_latency_ms and percent_diff > 0.2:  # 20% difference threshold
        # Calculate spike severity (0-1) based on percentage difference
        severity = min(1.0, percent_diff)
        return True, severity
    return False, 0

class LatencyPredictor:
    def __init__(self, max_history=100, spike_threshold=2.0, min_samples=5, retrain_interval=20):
        self.model = RandomForestRegressor(n_estimators=100, random_state=42)
        self.scaler = StandardScaler()
        self.max_history = max_history
        self.spike_threshold = spike_threshold
        self.min_samples = min_samples
        self.retrain_interval = retrain_interval
        self.history = []
        self.last_retrain = 0
        self.is_trained = False
        self.training_data = []  # Store all historical data for training
        
    def prepare_features(self, history):
        if len(history) < 2:
            return None
            
        df = pd.DataFrame(history)
        df['timestamp'] = pd.to_datetime(df['timestamp'])
        
        # Time-based features
        df['hour'] = df['timestamp'].dt.hour
        df['minute'] = df['timestamp'].dt.minute
        df['second'] = df['timestamp'].dt.second
        df['day_of_week'] = df['timestamp'].dt.dayofweek
        df['is_weekend'] = df['day_of_week'].isin([5, 6]).astype(int)
        
        # Rolling statistics
        df['rolling_mean'] = df['latency'].rolling(window=5, min_periods=1).mean()
        df['rolling_std'] = df['latency'].rolling(window=5, min_periods=1).std()
        df['rolling_std'] = df['rolling_std'].replace(0, 1)  # Handle zero standard deviation
        
        # Rate of change
        df['latency_diff'] = df['latency'].diff()
        df['latency_diff_abs'] = df['latency_diff'].abs()
        
        # Moving averages
        df['ma_5'] = df['latency'].rolling(window=5, min_periods=1).mean()
        df['ma_10'] = df['latency'].rolling(window=10, min_periods=1).mean()
        
        # Volatility
        df['volatility'] = df['latency'].rolling(window=10, min_periods=1).std()
        
        # Drop NaN values
        df = df.dropna()
        
        if len(df) == 0:
            return None
            
        features = [
            'hour', 'minute', 'second', 'day_of_week', 'is_weekend',
            'rolling_mean', 'rolling_std', 'latency_diff', 'latency_diff_abs',
            'ma_5', 'ma_10', 'volatility'
        ]
        return df[features].values
        
    def predict(self, current_latency):
        try:
            if len(self.history) < self.min_samples:
                return current_latency, False, 0
                
            features = self.prepare_features(self.history)
            if features is None:
                return current_latency, False, 0
                
            if not self.is_trained or len(self.history) % self.retrain_interval == 0:
                self.retrain()
                
            # Scale features
            features_scaled = self.scaler.transform(features[-1:])
            
            # Make prediction
            predicted = self.model.predict(features_scaled)[0]
            
            # Calculate spike severity
            if current_latency > predicted * self.spike_threshold:
                severity = (current_latency - predicted) / predicted
                return predicted, True, severity
                
            return predicted, False, 0
            
        except Exception as e:
            print(f"Error in prediction: {str(e)}")
            return current_latency, False, 0
            
    def update(self, latency, timestamp):
        try:
            # Add to history
            self.history.append({
                'timestamp': timestamp,
                'latency': latency
            })
            
            # Add to training data
            self.training_data.append({
                'timestamp': timestamp,
                'latency': latency
            })
            
            # Keep history size limited
            if len(self.history) > self.max_history:
                self.history.pop(0)
                
            # Retrain periodically
            if len(self.history) >= self.retrain_interval and len(self.history) % self.retrain_interval == 0:
                self.retrain()
                
        except Exception as e:
            print(f"Error updating history: {str(e)}")
            
    def retrain(self):
        try:
            if len(self.training_data) < self.min_samples:
                return
                
            # Prepare features from all training data
            features = self.prepare_features(self.training_data)
            if features is None:
                return
                
            # Get targets
            targets = [d['latency'] for d in self.training_data[-len(features):]]
            
            # Scale features
            self.scaler.fit(features)
            features_scaled = self.scaler.transform(features)
            
            # Train model
            self.model.fit(features_scaled, targets)
            self.is_trained = True
            self.last_retrain = len(self.history)
            
            print(f"Model retrained with {len(self.training_data)} samples")
            
        except Exception as e:
            print(f"Error retraining model: {str(e)}")

def run_live_monitoring(server, servers, log_file, callback):
    """Run live monitoring for a server."""
    try:
        print(f"Starting live monitoring for {server}")
        predictor = LatencyPredictor()
        
        # Create log directory if it doesn't exist
        os.makedirs(os.path.dirname(log_file), exist_ok=True)
        
        while True:
            try:
                # Get actual latency using ping
                latency = ping_latency(server)
                if latency is None:
                    print(f"Failed to get latency for {server}")
                    time.sleep(1)
                    continue
                    
                timestamp = pd.Timestamp.now()
                
                # Update predictor
                predictor.update(latency, timestamp)
                
                # Get prediction
                predicted, is_spike, severity = predictor.predict(latency)
                
                print(f"Server: {server}, Latency: {latency:.2f}ms, Predicted: {predicted:.2f}ms, Spike: {is_spike}")
                
                # Get best alternate server if there's a spike
                suggested_server = None
                improvement = None
                if is_spike:
                    best_server = get_best_server(server)
                    if best_server != server:
                        suggested_server = best_server
                        # Test latency to best server
                        best_latency = ping_latency(best_server)
                        if best_latency:
                            improvement = latency - best_latency
                
                # Call callback with results
                callback(server, latency, predicted, is_spike, severity, suggested_server, improvement)
                
                # Log data
                with open(log_file, 'a') as f:
                    f.write(f"{timestamp},{latency},{predicted},{is_spike},{severity},{suggested_server},{improvement}\n")
                    
                # Wait before next measurement
                time.sleep(1)
                
            except Exception as e:
                print(f"Error in monitoring loop: {str(e)}")
                time.sleep(1)
                
    except Exception as e:
        print(f"Fatal error in live monitoring: {str(e)}")
