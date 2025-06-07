import subprocess
import re
import platform

def ping_latency(host):
    """Ping a host and return the latency in milliseconds."""
    try:
        # Use different ping commands based on OS
        if platform.system().lower() == "windows":
            # Windows ping command
            result = subprocess.run(['ping', '-n', '1', '-w', '1000', host], 
                                  capture_output=True, text=True)
            # Extract latency using regex for Windows output
            match = re.search(r'Average = (\d+)ms', result.stdout)
        else:
            # Unix/Linux ping command
            result = subprocess.run(['ping', '-c', '1', '-W', '1', host], 
                                  capture_output=True, text=True)
            # Extract latency using regex for Unix output
            match = re.search(r'time=(\d+\.?\d*) ms', result.stdout)

        if match:
            latency = float(match.group(1))
            print(f"Ping to {host}: {latency}ms")  # Debug print
            return latency
        else:
            print(f"No latency found in ping output for {host}")  # Debug print
            print(f"Ping output: {result.stdout}")  # Debug print
            return None
    except Exception as e:
        print(f"Error pinging {host}: {str(e)}")  # Debug print
        return None
