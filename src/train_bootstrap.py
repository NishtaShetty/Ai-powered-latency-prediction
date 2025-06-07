from river import linear_model, preprocessing, metrics
import csv
import datetime
import pickle
import os
import numpy as np
import random

def extract_features(timestamp, server_id):
    dt = datetime.datetime.fromtimestamp(float(timestamp))
    return {
        "hour": dt.hour,
        "minute": dt.minute,
        "day_of_week": dt.weekday(),
        "is_weekend": int(dt.weekday() >= 5),
        "is_business_hours": int(9 <= dt.hour <= 17),
        "server_id": hash(server_id) % 10
    }

def train_model(path="data/bootstrapped_latency.csv"):
    # Initialize model with standard preprocessing
    model = (
        preprocessing.StandardScaler() |
        linear_model.LinearRegression()
    )
    
    # Initialize metrics
    mae = metrics.MAE()
    rmse = metrics.RMSE()
    
    # Load and process data
    data = []
    with open(path) as f:
        reader = csv.DictReader(f)
        for row in reader:
            data.append(row)
    
    # Shuffle data
    random.shuffle(data)
    
    # Split into train/test (80/20)
    split_idx = int(len(data) * 0.8)
    train_data = data[:split_idx]
    test_data = data[split_idx:]
    
    # Train model
    print("Training model...")
    for row in train_data:
        x = extract_features(row["timestamp"], row["server_id"])
        y = float(row["latency"])
        pred = model.predict_one(x) or 0
        model.learn_one(x, y)
        mae.update(y, pred)
        rmse.update(y, pred)
    
    print(f"Training metrics - MAE: {mae.get():.2f}ms, RMSE: {rmse.get():.2f}ms")
    
    # Evaluate on test set
    mae = metrics.MAE()
    rmse = metrics.RMSE()
    for row in test_data:
        x = extract_features(row["timestamp"], row["server_id"])
        y = float(row["latency"])
        pred = model.predict_one(x) or 0
        mae.update(y, pred)
        rmse.update(y, pred)
    
    print(f"Test metrics - MAE: {mae.get():.2f}ms, RMSE: {rmse.get():.2f}ms")
    
    # Save model
    os.makedirs("model", exist_ok=True)
    with open("model/model_state.pkl", "wb") as f:
        pickle.dump(model, f)
    
    return model

if __name__ == "__main__":
    train_model()
