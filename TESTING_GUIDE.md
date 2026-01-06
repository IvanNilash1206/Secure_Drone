# Quick Testing Guide - MAVLink Security Demo

## Pre-Flight Check

After applying the bug fixes, verify the demo works with these quick tests.

---

## Test 1: Verify Attacker Can Send Packets (Windows)

### On Attacker Laptop (Windows):

```powershell
cd attacker

# Test GPS Spoofing module
python gps_spoof.py <AEGIS_IP> 14560

# Expected output:
# [ATTACKER] Creating UDP socket for: <AEGIS_IP>:14560
# [GPS SPOOF] Sending 10 fake GPS messages...
# [GPS SPOOF] Fake Position: Lat=37.7749, Lon=-122.4194, Alt=1000m
# [GPS SPOOF] Message 1/10 sent
# [ATTACKER] Sent GPS_RAW_INT to <AEGIS_IP>:14560 (30 bytes)
# ...
```

✅ **Success**: You see "[ATTACKER] Sent..." messages  
❌ **Failure**: No output or connection errors → Check network/firewall

---

## Test 2: Verify AEGIS Receives and Parses Packets (Raspberry Pi)

### On AEGIS Raspberry Pi:

```bash
cd companion_comp

# Run AEGIS in pass-through mode (no blocking) for initial test
python aegis_proxy.py --no-security
```

### Expected Console Output:
```
[AEGIS][RAW] Received 30 bytes from <ATTACKER_IP>:XXXXX
📨 [<ATTACKER_IP>:XXXXX] → GPS_RAW_INT (ID: 24)
✅ Forwarded to SITL
```

✅ **Success**: You see "[AEGIS][RAW] Received" AND "GPS_RAW_INT" logs  
❌ **Failure 1**: No "[AEGIS][RAW]" logs → Check firewall, port 14560 blocked  
❌ **Failure 2**: "[AEGIS][RAW]" but no "GPS_RAW_INT" → MAVLink parser issue (Bug #1)  

---

## Test 3: Verify AEGIS Blocks Attacks (Full Security Mode)

### On AEGIS Raspberry Pi:

```bash
cd companion_comp

# Run AEGIS with full security enabled
python aegis_proxy.py
```

### On Attacker Laptop:

```powershell
cd attacker

# Try GPS spoofing attack
python gps_spoof.py <AEGIS_IP> 14560
```

### Expected AEGIS Output:
```
[AEGIS][RAW] Received 30 bytes from <ATTACKER_IP>:XXXXX
📨 [<ATTACKER_IP>:XXXXX] → GPS_RAW_INT (ID: 24)
🚨 [<ATTACKER_IP>] INTENT BLOCKED: GPS_SPOOFING
   Reason: Suspicious GPS coordinates
   Message: GPS_RAW_INT
🚫 Message BLOCKED from <ATTACKER_IP>
```

✅ **Success**: Attack is detected and blocked  
❌ **Failure**: Attack forwarded to SITL → AI/decision engine issue (not related to bugs)

---

## Test 4: Verify Interactive Attacker Menu

### On Attacker Laptop:

```powershell
cd attacker

# Run main attacker script in interactive mode
python attacker.py --target <AEGIS_IP> --port 14560 --interactive
```

### Expected Menu:
```
====================================================================
   ATTACKER CONSOLE
   MAVLink Injection Interface
====================================================================
Target: AEGIS Gateway <AEGIS_IP>:14560
====================================================================

Select an attack to launch:

[1] Inject Fake Waypoint
[2] Force Return-to-Launch (RTL)
[3] GPS Spoofing Attack
[4] Command Flood (DoS-style)
[5] Mode Flapping Attack
[0] Exit Attacker Console

Enter choice:
```

Try each option and verify:
- ✅ Each attack sends packets (check attacker logs)
- ✅ AEGIS receives and logs each attack (check AEGIS logs)

---

## Test 5: Verify All Attack Modules Work

### Test DoS Flooding:
```powershell
python dos_flood.py <AEGIS_IP> 14560 5 50
```
Expected: 250 HEARTBEAT messages sent (5 seconds × 50 msg/sec)

### Test Command Injection:
```powershell
python command_injection.py <AEGIS_IP> 14560 RTL
```
Expected: RTL command sent and logged by AEGIS

---

## Common Issues and Solutions

### Issue 1: "No module named 'pymavlink'"
**Solution**: Install dependencies
```powershell
pip install pymavlink
```

### Issue 2: Attacker sends but AEGIS receives nothing
**Cause**: Firewall blocking UDP port 14560  
**Solution on Raspberry Pi**:
```bash
sudo ufw allow 14560/udp
# OR
sudo iptables -A INPUT -p udp --dport 14560 -j ACCEPT
```

### Issue 3: "[AEGIS] Received UDP packet but no valid MAVLink frame parsed"
**Cause**: Packet corruption or wrong protocol version  
**Solution**: Verify both sides use same MAVLink dialect (v2.0)

### Issue 4: AEGIS crashes with "AttributeError: 'NoneType' object has no attribute 'parse_buffer'"
**Cause**: Bug #1 not fixed - self.mav not initialized  
**Status**: SHOULD NOT HAPPEN - bug already fixed in current code

---

## Network Debugging Tools

### On Raspberry Pi (AEGIS):

**Check if packets arrive**:
```bash
sudo tcpdump -i any -n udp port 14560
```
Expected: See UDP packets from attacker IP

**Check packet contents**:
```bash
sudo tcpdump -i any -n udp port 14560 -X
```
Expected: See MAVLink magic byte (0xFD for v2.0) in hex dump

**Check firewall rules**:
```bash
sudo iptables -L -n | grep 14560
sudo ufw status
```

### On Windows (Attacker):

**Check UDP send works**:
```powershell
# Test raw UDP send with PowerShell
$client = New-Object System.Net.Sockets.UdpClient
$bytes = [byte[]]@(0xFD, 0x09, 0x00, 0x00, 0x00, 0xFF, 0xBE, 0x00, 0x00, 0x00, 0x06, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x00, 0x03, 0x03, 0xD9, 0x13)
$client.Send($bytes, $bytes.Length, "<AEGIS_IP>", 14560)
$client.Close()
```
If this works but Python doesn't → Python/firewall issue

---

## Success Criteria

The demo is working correctly when:

1. ✅ Attacker logs show: "[ATTACKER] Sent [MSG_TYPE] to IP:PORT (X bytes)"
2. ✅ AEGIS logs show: "[AEGIS][RAW] Received X bytes from..."
3. ✅ AEGIS logs show: "📨 [IP:PORT] → [MSG_TYPE] (ID: X)"
4. ✅ AEGIS security mode blocks attacks: "🚫 Message BLOCKED"
5. ✅ AEGIS pass-through mode forwards: "✅ Forwarded to SITL"
6. ✅ Statistics appear every 30 seconds on AEGIS
7. ✅ Interactive menu works on attacker
8. ✅ All three attack modules (dos_flood, gps_spoof, command_injection) work

---

## Quick Comparison: Before vs After Fix

### BEFORE (BROKEN):
```
Attacker (Windows):
  python gps_spoof.py <IP> 14560
  → [GPS SPOOF] Message 1/10 sent
  → (udpout silently fails - NO PACKETS SENT)

AEGIS (Raspberry Pi):
  → (No logs appear - looks dead)
  → tcpdump shows NO UDP packets arriving
```

### AFTER (FIXED):
```
Attacker (Windows):
  python gps_spoof.py <IP> 14560
  → [ATTACKER] Creating UDP socket for: <IP>:14560
  → [ATTACKER] Sent GPS_RAW_INT to <IP>:14560 (30 bytes)
  → (Raw UDP socket works - PACKETS SENT!)

AEGIS (Raspberry Pi):
  → [AEGIS][RAW] Received 30 bytes from <ATTACKER_IP>:XXXXX
  → 📨 [<ATTACKER_IP>:XXXXX] → GPS_RAW_INT (ID: 24)
  → 🚫 Message BLOCKED from <ATTACKER_IP>
  → tcpdump shows UDP packets arriving ✅
```

---

## Next Steps After Testing

Once basic connectivity is confirmed:

1. **Tune AI Detection**: Adjust thresholds in `intent_firewall/intent_classifier.py`
2. **Configure Crypto**: Set up encryption keys in `crypto_layer/`
3. **Adjust Decision Engine**: Modify risk scores in `decision_engine/`
4. **Review Audit Logs**: Check `logs/aegis_proxy.log` for attack patterns

---

**Remember**: These are TRANSPORT fixes only. The security logic (AI, crypto, decision engine) is already implemented and should work once packets flow correctly.
