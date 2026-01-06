# AEGIS 3-Machine Deployment Guide

## 🎯 System Architecture

```
┌─────────────────────┐
│  Attacker (Laptop 2)│ ❌ UNTRUSTED
│  192.168.1.200      │
└──────────┬──────────┘
           │ MAVLink packets
           │ to PI_IP:14560
           ↓
┌─────────────────────┐
│  GCS (Laptop 1)     │ ⚠️ SEMI-TRUSTED
│  192.168.1.50       │
│  Runs SITL :14550   │
└──────────┬──────────┘
           │ MAVLink packets
           │ to PI_IP:14560
           ↓
┌─────────────────────┐  ═══════════════════════════════════════════
│  AEGIS (Raspberry Pi│  ✅ TRUSTED SECURITY GATEWAY
│  192.168.1.100      │  ═══════════════════════════════════════════
│  :14560 (in)        │      Trust boundary enforced by firewall
│  :14550 (out)       │      Decision governance enforced by AEGIS
└──────────┬──────────┘
           │ Validated traffic only
           ↓
┌─────────────────────┐
│  ArduPilot SITL     │
│  :14550 (protected) │
└─────────────────────┘
```

---

## 📋 Prerequisites

### Hardware Required
- **Laptop 1 (GCS)**: Any OS (Windows/Linux/Mac), 4GB+ RAM
- **Laptop 2 (Attacker)**: Any OS, 2GB+ RAM
- **Raspberry Pi 4** (or Pi 3): 2GB+ RAM, Raspbian OS
- **Network**: All devices on same Wi-Fi/LAN

### Software Requirements
All machines need:
```bash
# Python 3.8+
python3 --version

# pymavlink
pip install pymavlink pyyaml

# (GCS only) ArduPilot SITL
# Follow: https://ardupilot.org/dev/docs/building-setup-linux.html
```

---

## 🔧 Configuration

### Step 1: Get IP Addresses

On each machine, find its IP:
```bash
# Linux/Mac
ifconfig | grep inet

# Windows
ipconfig | findstr IPv4

# Raspberry Pi
hostname -I
```

**Example IPs used in this guide:**
- Laptop 1 (GCS): `192.168.1.50`
- Laptop 2 (Attacker): `192.168.1.200`
- Raspberry Pi (AEGIS): `192.168.1.100`

---

### Step 2: Configure AEGIS (Raspberry Pi)

Edit `companion_comp/config.yaml`:
```yaml
network:
  listen_host: "0.0.0.0"      # DO NOT CHANGE
  listen_port: 14560          # DO NOT CHANGE
  fc_ip: "192.168.1.50"       # ⚠️ SET THIS to Laptop 1 IP
  fc_port: 14550              # DO NOT CHANGE
```

---

### Step 3: Configure GCS (Laptop 1)

Edit `GCS/config.yaml`:
```yaml
connection:
  aegis_ip: "192.168.1.100"   # ⚠️ SET THIS to Raspberry Pi IP
  aegis_port: 14560           # DO NOT CHANGE
  sitl_host: "127.0.0.1"      # DO NOT CHANGE (localhost)
  sitl_port: 14550            # DO NOT CHANGE
```

---

### Step 4: Configure Attacker (Laptop 2)

Edit `attacker/config.yaml`:
```yaml
connection:
  target_host: "192.168.1.100"  # ⚠️ SET THIS to Raspberry Pi IP
  target_port: 14560             # DO NOT CHANGE
```

---

## 🔥 Trust Boundary Enforcement (CRITICAL)

### On Laptop 1 (GCS), set up firewall:

**Linux (UFW):**
```bash
# Block all access to SITL port
sudo ufw deny 14550/udp

# Allow ONLY Raspberry Pi to access SITL
sudo ufw allow from 192.168.1.100 to any port 14550 proto udp

# Allow AEGIS port for sending commands
sudo ufw allow 14560/udp

# Enable firewall
sudo ufw enable

# Verify rules
sudo ufw status
```

**Windows (PowerShell as Administrator):**
```powershell
# Block all inbound to port 14550
New-NetFirewallRule -DisplayName "Block SITL" -Direction Inbound -Protocol UDP -LocalPort 14550 -Action Block

# Allow ONLY Raspberry Pi
New-NetFirewallRule -DisplayName "Allow AEGIS to SITL" -Direction Inbound -Protocol UDP -LocalPort 14550 -RemoteAddress 192.168.1.100 -Action Allow

# Allow outbound to AEGIS
New-NetFirewallRule -DisplayName "Allow to AEGIS" -Direction Outbound -Protocol UDP -RemotePort 14560 -Action Allow
```

**Mac (pf firewall):**
```bash
# Edit /etc/pf.conf
sudo nano /etc/pf.conf

# Add these rules:
block in proto udp from any to any port 14550
pass in proto udp from 192.168.1.100 to any port 14550
pass out proto udp from any to any port 14560

# Load rules
sudo pfctl -f /etc/pf.conf
sudo pfctl -e
```

---

## 🚀 Running the Demo

### Terminal 1 (Laptop 1 - GCS): Start SITL
```bash
cd ~/ardupilot/ArduCopter
sim_vehicle.py -v ArduCopter --console --map --out=udp:127.0.0.1:14550
```

Wait for: `APM: EKF2 IMU0 is using GPS`

---

### Terminal 2 (Raspberry Pi): Start AEGIS
```bash
cd companion_comp
python3 aegis_proxy.py
```

Expected output:
```
======================================================================
    AEGIS MAVLink Security Proxy
    Companion Computer Security Gateway
======================================================================
Listening on: 0.0.0.0:14560
Forwarding to: 192.168.1.50:14550
Security: ENABLED
======================================================================

⚠️  TRUST BOUNDARY ENFORCEMENT:
   - OS firewall MUST block direct access to :14550
   - Only AEGIS can communicate with flight controller
   - AEGIS enforces decision governance (ALLOW/BLOCK)
======================================================================
```

---

### Terminal 3 (Laptop 1 - GCS): Run GCS Client
```bash
cd GCS
python3 gcs_client.py --interactive
```

You'll see:
```
========================================
   GCS – Ground Control Station
   MAVLink Command Interface
========================================
Connected to AEGIS Gateway

Select an operation:

[1] Arm Vehicle
[2] Takeoff
[3] Send Waypoint
[4] Change Flight Mode
[5] Return to Launch (RTL)
[6] Land
[7] Request Telemetry
[0] Exit GCS
```

Try legitimate commands:
1. Change to GUIDED mode (option 4)
2. Arm vehicle (option 1)
3. Takeoff (option 2)
4. All should be **ALLOWED** by AEGIS

---

### Terminal 4 (Laptop 2 - Attacker): Launch Attacks
```bash
cd attacker
python3 attacker.py --interactive
```

You'll see:
```
========================================
   ATTACKER CONSOLE
   MAVLink Injection Interface
========================================
Target: AEGIS Gateway

Select an attack to launch:

[1] Inject Fake Waypoint
[2] Force Return-to-Launch (RTL)
[3] GPS Spoofing Attack
[4] Command Flood (DoS-style)
[5] Mode Flapping Attack
[0] Exit Attacker Console
```

Try malicious attacks:
1. GPS Spoofing (option 3)
2. Waypoint Injection (option 1)
3. All should be **BLOCKED** by AEGIS

---

## 📊 Observing Results

### Check AEGIS Logs (Raspberry Pi)
```bash
tail -f logs/aegis_proxy.log
```

Look for:
- `✅ ALLOW` - Legitimate GCS commands
- `❌ BLOCK` - Attacker commands rejected
- Source IP tracking
- Decision reasoning

### Check Audit Log
```bash
tail -f logs/aegis_audit.log
```

Shows detailed decision explanations:
- Risk scores
- AI model verdicts
- Crypto validation results

---

## 🧪 Testing Without AEGIS

### Demonstrate Firewall Protection

**On Attacker Laptop, try direct attack:**
```bash
cd attacker
python3 attacker.py --target 192.168.1.50 --port 14550 --attack rtl
```

**Result:** Should **FAIL** due to firewall blocking port 14550

**Explanation:**
- Firewall enforces trust boundary (WHO can connect)
- AEGIS enforces decision governance (WHAT commands are allowed)

---

## 🐛 Troubleshooting

### Issue: "Connection refused" on AEGIS
**Solution:** Check firewall rules on Laptop 1
```bash
sudo ufw status  # Linux
```

### Issue: AEGIS can't reach SITL
**Solution:** Verify `fc_ip` in `companion_comp/config.yaml` matches Laptop 1 IP

### Issue: GCS commands blocked by AEGIS
**Solution:** Check crypto layer - ensure GCS has valid keys
```bash
# On Raspberry Pi
ls crypto_layer/key_metadata.json
```

### Issue: Attacker sees no response
**Solution:** This is correct! AEGIS silently drops malicious traffic

### Issue: SITL not receiving commands
**Solution:** 
1. Verify SITL is listening on all interfaces
2. Check AEGIS logs for forwarding errors
3. Ensure no VPN/double NAT issues

---

## 📸 Demo Script for Judges

**Setup (5 min):**
1. Show 3 machines with their roles
2. Explain network topology diagram
3. Show firewall rules on Laptop 1

**Demo Phase 1 - Legitimate GCS (3 min):**
1. Start GCS interactive mode
2. Execute: Mode change → Arm → Takeoff
3. Show AEGIS logs: all `✅ ALLOW`

**Demo Phase 2 - Attacker Blocked (3 min):**
1. Start Attacker interactive mode
2. Execute: GPS spoof → Waypoint inject → RTL
3. Show AEGIS logs: all `❌ BLOCK`

**Demo Phase 3 - Firewall Bypass Attempt (2 min):**
1. Attacker tries direct SITL connection (port 14550)
2. Show firewall blocking the connection
3. Explain: "Firewall enforces WHO, AEGIS enforces WHAT"

**Wrap-up (2 min):**
1. Show audit logs with decision reasoning
2. Highlight: Same network, different treatment
3. Q&A

---

## 🎓 Key Talking Points

1. **Trust Boundary Enforcement**
   - OS firewall enforces network-level access control
   - AEGIS enforces application-level decision governance
   - Defense-in-depth strategy

2. **Content-Based Security**
   - System ID alone is insufficient (attacker can spoof)
   - AEGIS analyzes command content, intent, and behavior
   - AI/ML models detect anomalies

3. **Real-World Deployment**
   - Companion computer = Raspberry Pi on drone
   - GCS = Ground station operator laptop
   - Attacker = Hostile actor on same network

4. **Scalability**
   - Works with any MAVLink-compatible flight controller
   - Extensible security layers (crypto, AI, decision engine)
   - Production-ready architecture

---

## 🔒 Security Notes

⚠️ **This is a demonstration system**

Production deployments should add:
- Encrypted MAVLink (MAVLink 2.0 signing)
- Certificate-based authentication
- Rate limiting per source IP
- Intrusion detection system integration
- Secure key distribution mechanism

---

## 📚 Additional Resources

- ArduPilot SITL Setup: https://ardupilot.org/dev/docs/sitl-simulator-software-in-the-loop.html
- MAVLink Protocol: https://mavlink.io/
- Raspberry Pi Network Setup: https://www.raspberrypi.org/documentation/
- UFW Firewall Guide: https://help.ubuntu.com/community/UFW

---

## ✅ Deployment Checklist

Before demo:
- [ ] All 3 machines have correct IPs configured
- [ ] Firewall rules active on Laptop 1
- [ ] SITL running and stable
- [ ] AEGIS proxy running on Raspberry Pi
- [ ] GCS can send heartbeat successfully
- [ ] Attacker can connect (but attacks blocked)
- [ ] Log files are being written
- [ ] Network connectivity stable

---

**Status:** 🎉 **READY FOR 3-MACHINE DEMO**
