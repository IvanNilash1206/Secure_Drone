# 🟥 Attacker Component

## What This Component Represents

This represents a **malicious actor** attempting to compromise the UAV system from the network perimeter.

## Real-World UAV System Role

**Location**: Attacker's laptop (separate from GCS and companion computer)  
**Network Access**: Same WiFi/network as the GCS  
**Trust Level**: **ZERO TRUST** - Hostile entity  

## Responsibilities

### What the Attacker DOES:
- ✅ Sends valid MAVLink messages (properly formatted)
- ✅ Attempts GPS spoofing attacks
- ✅ Attempts waypoint injection
- ✅ Attempts dangerous command injection (RTL, DISARM, LAND)
- ✅ Performs DoS flooding attacks
- ✅ Demonstrates what happens WITHOUT security enforcement

### What the Attacker DOES NOT DO:
- ❌ No security logic
- ❌ No assumptions about success
- ❌ No cryptographic capabilities
- ❌ No direct access to flight controller (enforced by firewall/topology)

## Why This Component is Separated

1. **Real-world isolation**: In actual UAV deployments, attackers operate from separate systems
2. **Network boundary demonstration**: Shows that attackers can join the network but cannot reach FC directly
3. **Attack surface clarity**: Makes it obvious what threats the system faces
4. **Demo effectiveness**: Judges can run attacker on separate laptop to see live attacks

## Architecture Position

```
┌────────────────────────────────────────────────────────┐
│                    NETWORK LAYER                       │
│                                                        │
│  ┌──────────────┐                                     │
│  │   ATTACKER   │  ──────────┐                        │
│  │  (Laptop 1)  │             │                        │
│  │  UDP:14560   │             ▼                        │
│  └──────────────┘      ┌──────────────┐               │
│                        │ AEGIS PROXY  │               │
│  ┌──────────────┐      │ (Companion)  │               │
│  │     GCS      │ ───▶ │  UDP:14560   │ ──▶ FC SITL  │
│  │  (Laptop 2)  │      │     ▼        │     UDP:14550│
│  │  UDP:14560   │      │  Security    │               │
│  └──────────────┘      │   Layers     │               │
│                        └──────────────┘               │
└────────────────────────────────────────────────────────┘
```

## How to Run

### 1. Basic Attack (with AEGIS protection)
```bash
cd attacker
python attacker.py --target <AEGIS_IP> --port 14560 --attack combined
```

### 2. Direct Attack (bypassing AEGIS - for comparison)
```bash
python attacker.py --target <SITL_IP> --port 14550 --attack combined
```

### 3. Specific Attack Types
```bash
# GPS Spoofing
python attacker.py --target <AEGIS_IP> --port 14560 --attack gps-spoof

# Waypoint Injection
python attacker.py --target <AEGIS_IP> --port 14560 --attack waypoint-inject

# Force RTL
python attacker.py --target <AEGIS_IP> --port 14560 --attack rtl

# DoS Flooding
python attacker.py --target <AEGIS_IP> --port 14560 --attack dos --duration 10
```

## Expected Results

### WITH AEGIS (Port 14560):
- ✅ Attacks are **BLOCKED** by crypto + AI layers
- ✅ Malicious commands never reach flight controller
- ✅ Audit logs show blocked attempts
- ✅ System remains secure

### WITHOUT AEGIS (Port 14550 - Direct to SITL):
- ❌ Attacks **SUCCEED** 
- ❌ GPS spoofed
- ❌ Waypoints injected
- ❌ Dangerous commands executed
- ❌ System compromised

## Attack Types Implemented

1. **GPS Spoofing**: Send fake GPS coordinates to mislead navigation
2. **Waypoint Injection**: Inject unauthorized mission waypoints
3. **Command Injection**: Send dangerous commands (RTL, DISARM, LAND)
4. **DoS Flooding**: Overwhelm system with message bursts
5. **Combined Scenario**: Multi-vector attack sequence

## Dependencies

```bash
pip install pymavlink
```

## Logs

Attack logs are written to: `logs/attacker.log`

## Security Model Visibility

This code structure makes the security model immediately obvious:
- **attacker/** = untrusted, hostile, network-accessible
- **GCS/** = trusted, legitimate, network-accessible  
- **companion_comp/** = security gateway, decision enforcer

If the attacker could talk directly to the flight controller, the entire security model would collapse. The firewall and AEGIS proxy enforce this boundary.

## Educational Value

For judges evaluating this system:
1. The attacker code is intentionally simple and realistic
2. It uses proper MAVLink protocol (not magic)
3. It demonstrates real attack vectors against UAVs
4. It proves that security enforcement is necessary
5. It shows the difference between protected vs unprotected systems
