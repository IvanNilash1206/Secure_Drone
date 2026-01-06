# UAV Security Threat Model

## System Overview

This document describes the threat model for a MAVLink-based UAV system with the AEGIS security gateway.

## Trust Boundaries

```
┌─────────────────────────────────────────────────────────┐
│                    UNTRUSTED ZONE                       │
│  ┌──────────────┐          ┌──────────────┐            │
│  │   Attacker   │          │     GCS      │            │
│  │   Network    │          │   Operator   │            │
│  └──────┬───────┘          └──────┬───────┘            │
│         │                         │                     │
│         └─────────────┬───────────┘                     │
│                       │                                 │
└───────────────────────┼─────────────────────────────────┘
                        │ UDP:14560
                        ▼
┌─────────────────────────────────────────────────────────┐
│                    TRUST BOUNDARY                       │
│                  ┌──────────────┐                       │
│                  │    AEGIS     │                       │
│                  │    Proxy     │                       │
│                  └──────┬───────┘                       │
└─────────────────────────┼─────────────────────────────────┘
                        │ UDP:14550
                        ▼
┌─────────────────────────────────────────────────────────┐
│                    TRUSTED ZONE                         │
│                  ┌──────────────┐                       │
│                  │    Flight    │                       │
│                  │  Controller  │                       │
│                  └──────────────┘                       │
└─────────────────────────────────────────────────────────┘
```

## Threat Actors

### 1. Network Attacker
- **Access Level**: Network-level access (same WiFi/LAN)
- **Capabilities**: 
  - Send MAVLink packets to AEGIS proxy (port 14560)
  - Observe network traffic (passive sniffing)
  - DoS attacks
- **Constraints**:
  - Cannot directly reach flight controller (firewall blocked)
  - Cannot decrypt encrypted messages (without keys)
  - Cannot bypass AEGIS proxy

### 2. Insider Threat (Compromised GCS)
- **Access Level**: Legitimate operator credentials
- **Capabilities**:
  - Send properly formatted commands
  - Access to encryption keys (if implemented)
  - Knowledge of mission plans
- **Constraints**:
  - Still must go through AEGIS validation
  - Behavioral anomalies can be detected

## Attack Vectors

### 1. GPS Spoofing
**Description**: Send fake GPS coordinates to mislead navigation

**Attack Flow**:
```
Attacker → GPS_RAW_INT(fake_coords) → AEGIS → [BLOCKED] → FC
```

**Mitigation**:
- Intent classification detects GPS spoofing intent
- Shadow execution validates GPS data against physics
- Decision engine blocks suspicious GPS data

**Risk Level**: 🔴 HIGH (could redirect drone)

---

### 2. Waypoint Injection
**Description**: Inject unauthorized waypoints into mission plan

**Attack Flow**:
```
Attacker → MISSION_ITEM(malicious_wp) → AEGIS → [BLOCKED] → FC
```

**Mitigation**:
- Intent firewall detects unauthorized waypoint patterns
- Behavioral IDS flags unusual waypoint frequencies
- Decision engine validates waypoint authority

**Risk Level**: 🔴 HIGH (could redirect drone)

---

### 3. Command Injection
**Description**: Send dangerous commands (RTL, DISARM, LAND)

**Attack Flow**:
```
Attacker → COMMAND_LONG(DISARM) → AEGIS → [BLOCKED] → FC
```

**Mitigation**:
- Intent classification identifies dangerous commands
- Decision engine validates command authority
- Safe mode prevents catastrophic commands

**Risk Level**: 🔴 CRITICAL (could crash drone)

---

### 4. Denial of Service (DoS)
**Description**: Flood system with rapid message bursts

**Attack Flow**:
```
Attacker → HEARTBEAT x 1000 → AEGIS → [BLOCKED] → FC
```

**Mitigation**:
- Behavioral IDS detects abnormal message rates
- Rate limiting prevents resource exhaustion
- Decision engine triggers DoS protection

**Risk Level**: 🟡 MEDIUM (disrupts operations)

---

### 5. Man-in-the-Middle (MITM)
**Description**: Intercept and modify messages

**Attack Flow**:
```
GCS → MSG → [Attacker Intercepts/Modifies] → MSG' → AEGIS
```

**Mitigation**:
- Cryptographic authentication (MAC/signatures)
- Nonce-based replay protection
- Message integrity validation

**Risk Level**: 🟡 MEDIUM (requires network position)

---

### 6. Replay Attack
**Description**: Record and replay legitimate commands

**Attack Flow**:
```
Attacker → [Recorded Command] → AEGIS → [BLOCKED] → FC
```

**Mitigation**:
- Nonce validation (timestamp/counter)
- Temporal analysis detects replay patterns
- Cryptographic freshness guarantees

**Risk Level**: 🟢 LOW (with crypto enabled)

---

## Assets to Protect

1. **Flight Controller**
   - **Value**: CRITICAL
   - **Impact if compromised**: Loss of vehicle control, crash

2. **Mission Data**
   - **Value**: HIGH
   - **Impact if compromised**: Unauthorized access to flight plans

3. **Communication Channel**
   - **Value**: HIGH
   - **Impact if compromised**: Command injection, data manipulation

4. **Telemetry Data**
   - **Value**: MEDIUM
   - **Impact if compromised**: Privacy breach, reconnaissance

## Security Assumptions

### What We ASSUME:
✅ Attacker can join the network (same WiFi)  
✅ Attacker knows MAVLink protocol  
✅ Attacker can send properly formatted packets  
✅ AEGIS proxy hardware is trusted (not compromised)  
✅ Firewall rules are correctly configured  

### What We DO NOT ASSUME:
❌ Attacker cannot bypass network layer (firewall enforced)  
❌ Attacker does not have encryption keys  
❌ Attacker cannot compromise AEGIS proxy itself  
❌ Flight controller firmware is not modified  

## Defense-in-Depth Strategy

### Layer 1: Network (Firewall)
**Purpose**: Topology enforcement  
**Blocks**: Direct access to FC  
**Limitation**: Cannot inspect content  

### Layer 2: Cryptography
**Purpose**: Authentication & integrity  
**Blocks**: Unauthorized senders, tampering  
**Limitation**: Cannot detect legitimate-but-malicious commands  

### Layer 3: Intent Firewall
**Purpose**: Command intent validation  
**Blocks**: Malicious command patterns  
**Limitation**: May not detect novel attacks  

### Layer 4: Behavioral IDS
**Purpose**: Anomaly detection  
**Blocks**: Unusual behavior patterns  
**Limitation**: Requires training data  

### Layer 5: Shadow Execution
**Purpose**: Outcome prediction  
**Blocks**: Physics-violating commands  
**Limitation**: Computational overhead  

### Layer 6: Decision Engine
**Purpose**: Risk-based decision making  
**Blocks**: High-risk actions  
**Limitation**: False positives possible  

## Attack Scenarios

### Scenario 1: External Attacker (No Credentials)
```
[Attacker] --GPS_SPOOF--> [AEGIS]
                            ↓
                    [Intent Firewall: BLOCK]
                            ↓
                    [Audit Log: Recorded]
                            ↓
                         [X] FC Never Reached
```
**Result**: ✅ Attack blocked

---

### Scenario 2: Compromised GCS (With Credentials)
```
[Compromised GCS] --VALID_COMMAND(malicious)--> [AEGIS]
                                                  ↓
                                          [Crypto: PASS]
                                                  ↓
                                       [Behavioral IDS: ANOMALY]
                                                  ↓
                                       [Decision Engine: BLOCK]
                                                  ↓
                                              [X] FC Protected
```
**Result**: ✅ Attack blocked (behavioral detection)

---

### Scenario 3: Legitimate GCS (Normal Operation)
```
[GCS] --ARM_COMMAND--> [AEGIS]
                        ↓
                 [Crypto: PASS]
                        ↓
               [Intent: PASS]
                        ↓
             [Behavioral: PASS]
                        ↓
            [Decision: ALLOW]
                        ↓
                     [FC] ✅ Executed
```
**Result**: ✅ Command allowed

## Risk Matrix

| Attack Vector | Likelihood | Impact | Risk Level |
|---------------|------------|--------|------------|
| GPS Spoofing | HIGH | HIGH | 🔴 CRITICAL |
| Waypoint Injection | HIGH | HIGH | 🔴 CRITICAL |
| Command Injection | HIGH | CRITICAL | 🔴 CRITICAL |
| DoS Flooding | MEDIUM | MEDIUM | 🟡 MEDIUM |
| MITM | LOW | HIGH | 🟡 MEDIUM |
| Replay Attack | LOW | MEDIUM | 🟢 LOW |

## Residual Risks

After implementing AEGIS, the following residual risks remain:

1. **Zero-day attacks in AEGIS**: Novel attack patterns not in training data
2. **Physical access**: Attacker with physical access to companion computer
3. **Side-channel attacks**: Timing attacks, power analysis (out of scope)
4. **Firmware vulnerabilities**: Bugs in ArduPilot itself (out of scope)

## Compliance & Validation

### How to Validate Security:
1. **Attack Simulation**: Run attacker scripts, verify blocks
2. **Audit Log Review**: Check decision explanations
3. **Penetration Testing**: Professional security assessment
4. **Monitoring**: Real-time threat detection during operations

### Metrics:
- **Attack Block Rate**: % of attacks successfully blocked
- **False Positive Rate**: % of legitimate commands incorrectly blocked
- **Detection Latency**: Time from attack to detection
- **Audit Coverage**: % of decisions logged and explained

## Conclusion

This threat model demonstrates that the AEGIS security architecture provides defense-in-depth protection against known UAV attack vectors. The combination of firewall (topology enforcement), cryptography (authentication), and AI-based validation (content analysis) creates multiple barriers that attackers must bypass.

Key insight: **Firewall alone is insufficient** - it only controls "who can talk to whom", not "what content is dangerous". AEGIS provides the critical content analysis layer.
