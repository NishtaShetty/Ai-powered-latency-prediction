from src.ping_utils import ping_latency

def get_best_server(servers):
    latencies = [(s, ping_latency(s)) for s in servers]
    latencies = [(s, l) for s, l in latencies if l is not None]
    if not latencies:
        return None
    return min(latencies, key=lambda x: x[1])[0]
