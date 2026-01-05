# Secure Drone Testing Log

## Overview
This document logs the testing processes for the Secure Drone project, focusing on MAVLink communication with and without crypto layer integration, attacker simulation, and latency checks.

**Note:** Logging has been added to all source and test files for better debugging and monitoring. Logs are written to `secure_drone.log` and console output.

## Test Structure
- `test_no_crypto.py`: Tests MAVLink command parsing without encryption
- `test_crypto.py`: Tests crypto layer functionality including encryption/decryption, attack resistance, and latency

## Test Descriptions

### test_no_crypto.py

#### test_non_command_messages_are_ignored
- **Purpose**: Ensures non-command MAVLink messages (e.g., HEARTBEAT) are filtered out
- **Process**: Creates a fake HEARTBEAT message and verifies `parse_command` returns None
- **Expected**: Pass - no command object created for telemetry

#### test_command_long_classification_and_params
- **Purpose**: Tests classification of COMMAND_LONG messages and parameter extraction
- **Process**: Simulates a RETURN_TO_LAUNCH command, checks classification as "RETURN", source as "gcs", and parameter extraction
- **Expected**: Pass - correct command type, source, and params

#### test_navigation_command_is_parsed
- **Purpose**: Verifies parsing of navigation commands like SET_POSITION_TARGET_LOCAL_NED
- **Process**: Creates a position target message, checks classification as "NAVIGATION", source as "companion", and coordinate extraction
- **Expected**: Pass - accurate parsing of navigation data

#### test_parse_latency_under_budget
- **Purpose**: Measures command parsing performance
- **Process**: Parses 50 COMMAND_LONG messages and calculates average latency
- **Expected**: Pass - average < 0.01 seconds per message

### test_crypto.py

#### test_encrypt_decrypt_round_trip
- **Purpose**: Validates end-to-end encryption/decryption
- **Process**: Encrypts a payload ("ARM_AND_TAKEOFF"), decrypts it, checks integrity
- **Expected**: Pass - decrypted payload matches original

#### test_replay_attack_is_rejected
- **Purpose**: Simulates replay attack by reusing nonce/ciphertext
- **Process**: Encrypts payload, decrypts once successfully, then attempts decryption again with same data
- **Expected**: Pass - second decryption raises ValueError for replay detection

#### test_tamper_attack_fails
- **Purpose**: Tests tamper detection by modifying ciphertext
- **Process**: Encrypts payload, flips a bit in ciphertext, attempts decryption
- **Expected**: Pass - decryption raises Exception due to integrity failure

#### test_latency_encrypt_decrypt_budget
- **Purpose**: Measures crypto operation performance
- **Process**: Performs 20 encrypt/decrypt cycles, calculates average latency
- **Expected**: Pass - average < 0.05 seconds per cycle

## Running Tests
1. Ensure Python environment is configured: `.venv\Scripts\python.exe`
2. Install dependencies: `pip install pytest cryptography pymavlink`
3. Run no-crypto tests: `python -m pytest test/test_no_crypto.py -v`
4. Run crypto tests: `python -m pytest test/test_crypto.py -v`

## Attack Simulation
- **Replay Attack**: Attempted reuse of encrypted messages - detected via nonce counter
- **Tamper Attack**: Modification of ciphertext - detected via AES-GCM authentication tag
- **Latency Check**: Ensures operations complete within performance budgets

## Results Summary
- All tests designed to pass under normal conditions
- Crypto tests include attacker simulation scenarios
- Latency tests ensure real-time performance requirements

## Logging Configuration
- **Central Configuration**: `src/logging_config.py` sets up logging for all modules
- **Level**: INFO (captures important operations and errors)
- **Output**: Both file (`logs/secure_drone.log`) and console
- **Format**: `%(asctime)s - %(name)s - %(levelname)s - %(message)s`
- **Modules**: All source files and tests import logger from `src.logging_config`
- **Directory**: All logs saved in dedicated `logs/` folder