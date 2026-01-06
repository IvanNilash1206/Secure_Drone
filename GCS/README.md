# 🟦 Ground Control Station (GCS) Component

## What This Component Represents

This represents the **legitimate UAV operator** - the trusted human controlling the drone for authorized missions.

## Real-World UAV System Role

**Location**: Operator's laptop (separate from companion computer and attacker)  
**Network Access**: Same WiFi/network as the companion computer  
**Trust Level**: **TRUSTED** - Authorized operator  

## Responsibilities

### What the GCS DOES:
- ✅ Sends legitimate MAVLink commands (properly formatted)
- ✅ Performs normal flight operations (ARM, TAKEOFF, NAVIGATE, RTL, LAND)
- ✅ Uploads mission plans
- ✅ Monitors telemetry (basic)
- ✅ Operates through AEGIS proxy for security validation
- ✅ Demonstrates normal operational workflow

### What the GCS DOES NOT DO:
- ❌ No attack logic
- ❌ No security enforcement (trusts AEGIS)
- ❌ No assumptions about threat detection
- ❌ No direct cryptographic operations

## Why This Component is Separated

1. **Real-world isolation**: In actual UAV deployments, GCS runs on operator's laptop, not on drone
2. **Trust boundary demonstration**: Shows that even trusted operators go through security gateway
3. **Normal operations baseline**: Provides comparison point for attack scenarios
4. **Demo effectiveness**: Judges can see legitimate vs malicious traffic side-by-side

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

### 1. Connect through AEGIS (Recommended - Secure)
```bash
cd GCS
python gcs_client.py --target <AEGIS_IP> --port 14560 --mission
```

### 2. Test Connection
```bash
python gcs_client.py --target <AEGIS_IP> --port 14560 --test
```

### 3. Direct to SITL (Bypass Security - For Comparison)
```bash
python gcs_client.py --target <SITL_IP> --port 14550 --mission
```

## Mission Scenario

The GCS runs a typical 7-step mission:

1. **Change to GUIDED mode** - Enable autonomous navigation
2. **ARM** - Activate motors
3. **TAKEOFF** - Ascend to 10m
4. **NAVIGATE** - Fly to waypoint coordinates
5. **RTL** - Return to launch point
6. **LAND** - Descend and land
7. **DISARM** - Deactivate motors

## Expected Results

### WITH AEGIS (Port 14560):
- ✅ All legitimate commands **ALLOWED**
- ✅ Commands validated by crypto + AI layers
- ✅ Normal mission completes successfully
- ✅ Telemetry flows normally
- ✅ Audit logs show authorized traffic

### WITHOUT AEGIS (Port 14550 - Direct):
- ✅ Commands reach SITL directly
- ⚠️ No security validation
- ⚠️ Vulnerable to MITM attacks
- ⚠️ No audit trail
- ⚠️ Cannot distinguish from attacker traffic

## Commands Implemented

- **ARM/DISARM**: Motor control
- **TAKEOFF**: Autonomous takeoff to altitude
- **GOTO_POSITION**: Navigate to GPS coordinates
- **CHANGE_MODE**: Switch flight modes (GUIDED, AUTO, RTL, etc.)
- **RTL**: Return to launch
- **LAND**: Autonomous landing
- **HEARTBEAT**: Keep-alive messages
- **TELEMETRY_REQUEST**: Request sensor data streams

## Dependencies

```bash
pip install pymavlink
```

## Logs

GCS logs are written to: `logs/gcs_client.log`

## Security Model Visibility

This code structure makes the security model immediately obvious:
- **GCS/** = trusted, legitimate, but still goes through security gateway
- **attacker/** = untrusted, hostile, blocked by security layers
- **companion_comp/** = security gateway, decision enforcer

Even trusted operators must go through AEGIS. This demonstrates **zero-trust architecture** where trust is never assumed, always verified.

## Comparison: GCS vs Attacker

| Aspect | GCS | Attacker |
|--------|-----|----------|
| **Intent** | Legitimate mission | Malicious compromise |
| **Commands** | Authorized operations | Dangerous attacks |
| **Behavior** | Predictable, normal | Anomalous, suspicious |
| **Frequency** | Normal rate | DoS flooding |
| **Trust Level** | Trusted | Untrusted |
| **AEGIS Response** | Allow commands | Block commands |
| **Result** | Mission succeeds | Attacks blocked |

## Educational Value

For judges evaluating this system:
1. GCS code shows normal operational workflow
2. Demonstrates that security doesn't block legitimate traffic
3. Provides baseline for comparison with attack traffic
4. Shows that security validation is transparent to operators
5. Proves the system is practical for real-world use

## Demo Script for Judges

1. **Start SITL** (flight controller simulator)
2. **Start AEGIS proxy** (security gateway)
3. **Run GCS mission** - observe normal operation ✅
4. **Run attacker** - observe attacks blocked ❌
5. **Compare logs** - see the difference

This separation makes the demo crystal clear: trusted vs untrusted, allowed vs blocked.
