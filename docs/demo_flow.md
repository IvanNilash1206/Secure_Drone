# Demo Execution Flow

## Quick Start (3-Component Setup)

This guide walks you through running the complete UAV security demonstration.

## Prerequisites

1. **ArduPilot SITL** installed
2. **Python 3.8+** installed
3. **Three terminals** (or three separate machines for full demo)

## System Topology

```
Terminal 1          Terminal 2          Terminal 3
┌──────────┐       ┌──────────┐       ┌──────────┐
│   SITL   │◀─────▶│  AEGIS   │◀─────▶│GCS/Attack│
│          │       │  Proxy   │       │          │
│UDP:14550 │       │UDP:14560 │       │   Both   │
└──────────┘       └──────────┘       └──────────┘
```

---

## Setup Phase

### Terminal 1: Start ArduPilot SITL

```bash
cd ~/ardupilot/ArduCopter
sim_vehicle.py -v ArduCopter --console --map --out=udp:127.0.0.1:14550
```

**What this does**:
- Starts simulated ArduCopter flight controller
- Listens on `127.0.0.1:14550` (localhost only - protected by firewall)
- Provides SITL console and map

**Expected output**:
```
Ready to FLY ✓
```

---

### Terminal 2: Start AEGIS Proxy

```bash
cd companion_comp
python aegis_proxy.py
```

**What this does**:
- Starts security gateway on `0.0.0.0:14560` (accepts external traffic)
- Forwards approved messages to `127.0.0.1:14550` (SITL)
- Loads all security layers (crypto, AI, decision engine)

**Expected output**:
```
[AEGIS] ✅ Security layers loaded successfully
[AEGIS] 🟢 Proxy listening on 0.0.0.0:14560
[AEGIS] 🔒 Forwarding to SITL at 127.0.0.1:14550
```

---

## Demo Phase 1: Legitimate GCS Operations

### Terminal 3: Run GCS Client

```bash
cd GCS
python gcs_client.py --target 127.0.0.1 --port 14560 --mission
```

**What this does**:
- Connects to AEGIS proxy (port 14560)
- Runs normal mission: ARM → TAKEOFF → NAVIGATE → RTL → LAND
- All commands validated by AEGIS

**Expected output**:
```
✅ All commands ALLOWED
✅ Mission completed successfully
```

**What to observe**:
- Terminal 2 (AEGIS): Green logs showing "ALLOW" decisions
- Terminal 1 (SITL): Drone executing commands normally

---

## Demo Phase 2: Attack Simulation (GPS Spoofing)

### Terminal 3: Run GPS Spoof Attack

```bash
cd attacker
python gps_spoof.py 127.0.0.1 14560 37.7749 -122.4194 1000
```

**What this does**:
- Sends fake GPS coordinates (San Francisco location)
- Attempts to mislead navigation system
- Targets AEGIS proxy (port 14560)

**Expected output**:
```
[GPS SPOOF] Attack complete!
```

**What to observe**:
- Terminal 2 (AEGIS): 🔴 Red logs showing "BLOCK" decisions
- Terminal 1 (SITL): GPS data NOT changed (attack blocked)

---

## Demo Phase 3: Attack Simulation (Command Injection)

### Terminal 3: Run Command Injection Attack

```bash
cd attacker
python command_injection.py 127.0.0.1 14560 RTL
```

**What this does**:
- Attempts to force drone to Return To Launch
- Simulates attacker taking control

**Expected output**:
```
[COMMAND INJECT] RTL command sent!
```

**What to observe**:
- Terminal 2 (AEGIS): 🔴 "BLOCK - Unauthorized command"
- Terminal 1 (SITL): Mode NOT changed (attack blocked)

---

## Demo Phase 4: Attack Simulation (DoS Flooding)

### Terminal 3: Run DoS Attack

```bash
cd attacker
python dos_flood.py 127.0.0.1 14560 10 100
```

**What this does**:
- Floods AEGIS with 100 messages/second for 10 seconds
- Attempts to overwhelm system

**Expected output**:
```
[DOS FLOOD] 1000 messages sent (100 msg/s)
```

**What to observe**:
- Terminal 2 (AEGIS): 🟡 "DoS pattern detected - rate limiting"
- Terminal 1 (SITL): Still responsive (attack mitigated)

---

## Demo Phase 5: Combined Attack

### Terminal 3: Run Full Attack Scenario

```bash
cd attacker
python attacker.py --target 127.0.0.1 --port 14560 --attack combined
```

**What this does**:
- Runs all attacks in sequence: GPS spoof → Waypoint inject → Command inject → DoS
- Demonstrates comprehensive attack surface

**What to observe**:
- Terminal 2 (AEGIS): Multiple block decisions with explanations
- Terminal 1 (SITL): Completely protected

---

## Comparison Demo: WITH vs WITHOUT AEGIS

### Scenario A: WITH AEGIS (Secure)

```bash
# Terminal 3: Attack through AEGIS
cd attacker
python attacker.py --target 127.0.0.1 --port 14560 --attack gps-spoof
```

**Result**: ✅ Attack BLOCKED

---

### Scenario B: WITHOUT AEGIS (Insecure)

⚠️ **WARNING: This demonstrates vulnerability - use with caution!**

```bash
# Terminal 3: Attack SITL directly (bypassing AEGIS)
cd attacker
python attacker.py --target 127.0.0.1 --port 14550 --attack gps-spoof
```

**Result**: ❌ Attack SUCCEEDS (GPS spoofed, drone misled)

---

## Audit Log Review

After demo, review the security decisions:

```bash
cd companion_comp
cat logs/aegis_audit.log
```

**What you'll see**:
- Timestamp of each message
- Decision (ALLOW/BLOCK/MODIFY)
- Risk scores from each security layer
- Explanation of why decision was made

Example log entry:
```json
{
  "timestamp": "2026-01-06T10:30:45",
  "source": "255.190",
  "message_type": "GPS_RAW_INT",
  "intent_score": 0.95,
  "anomaly_score": 0.85,
  "risk_score": 0.90,
  "decision": "BLOCK",
  "explanation": "GPS spoofing detected - coordinates inconsistent with physics model"
}
```

---

## Two-Laptop Setup (Full Network Demo)

For maximum realism, run components on separate machines:

### Laptop 1: SITL + AEGIS (Companion Computer)

```bash
# Terminal 1
cd ~/ardupilot/ArduCopter
sim_vehicle.py -v ArduCopter --out=udp:127.0.0.1:14550

# Terminal 2
cd companion_comp
python aegis_proxy.py
```

### Laptop 2: GCS + Attacker (Both on same network)

```bash
# Get Laptop 1 IP address
AEGIS_IP=192.168.1.100  # Replace with actual IP

# Run GCS
cd GCS
python gcs_client.py --target $AEGIS_IP --port 14560 --mission

# Run attacker
cd attacker
python attacker.py --target $AEGIS_IP --port 14560 --attack combined
```

**Demonstrates**:
- GCS and attacker on same network ✅
- AEGIS differentiates based on CONTENT, not source IP ✅
- Network-level isolation (firewall) ✅

---

## Troubleshooting

### Issue: "Connection refused" on port 14560
**Solution**: Ensure AEGIS proxy is running first

### Issue: "Connection timeout" on port 14550
**Solution**: This is expected! Port 14550 should be blocked by firewall (only localhost allowed)

### Issue: "No heartbeat received"
**Solution**: Check SITL is running and AEGIS is forwarding

### Issue: "Security layers not loaded"
**Solution**: Install dependencies: `pip install -r companion_comp/requirements.txt`

---

## Performance Metrics

After demo, check performance:

```bash
# Attack block rate
grep "BLOCK" companion_comp/logs/aegis_audit.log | wc -l

# False positive rate (legitimate commands blocked)
grep "GCS" companion_comp/logs/aegis_audit.log | grep "BLOCK" | wc -l

# Latency (decision time)
grep "latency" companion_comp/logs/aegis_proxy.log
```

---

## Demo Narrative for Judges

**1. Introduction** (1 min)
"This is a UAV security system demonstrating defense-in-depth against real-world attacks."

**2. Architecture Overview** (2 min)
"Three components: GCS (operator), AEGIS (security gateway), SITL (flight controller). Only AEGIS can reach FC."

**3. Normal Operations** (2 min)
"Watch legitimate GCS commands flow through AEGIS and get approved."

**4. Attack Demonstration** (3 min)
"Now an attacker on the same network tries GPS spoofing, command injection, and DoS. All blocked."

**5. Comparison** (2 min)
"Without AEGIS? Same attacks succeed. With AEGIS? All blocked. That's the difference."

**6. Audit Log** (1 min)
"Every decision is logged with explanation. Full transparency and auditability."

**Total: 11 minutes**

---

## Next Steps

1. Review `docs/architecture.md` for system design
2. Review `docs/threat_model.md` for security analysis
3. Explore `companion_comp/` subdirectories for implementation details
4. Read component READMEs for detailed explanations

---

## Key Takeaways

✅ **Network isolation (firewall)** enforces topology - who can talk to whom  
✅ **AEGIS (content analysis)** enforces security - what content is malicious  
✅ **Both are necessary** - defense-in-depth  
✅ **Zero-trust architecture** - even trusted GCS is validated  
✅ **Explainable decisions** - full audit trail  
