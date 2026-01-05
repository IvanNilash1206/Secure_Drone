import math

def extract_features(prev, curr):
    if prev is None:
        return None

    p_cmd = prev["command"]
    c_cmd = curr["command"]

    # Position deltas
    d_lat = c_cmd["lat"] - p_cmd["lat"]
    d_lon = c_cmd["lon"] - p_cmd["lon"]
    d_alt = c_cmd["alt"] - p_cmd["alt"]

    # Time delta
    dt = curr["timestamp"] - prev["timestamp"]

    # Velocity (simple approximation)
    distance = math.sqrt(d_lat**2 + d_lon**2 + d_alt**2)
    velocity = distance / dt if dt > 0 else 0.0

    # Mode transition (0 = same, 1 = changed)
    mode_change = 1 if c_cmd["mode"] != p_cmd["mode"] else 0

    return [
        d_lat,
        d_lon,
        d_alt,
        dt,
        velocity,
        mode_change
    ]
