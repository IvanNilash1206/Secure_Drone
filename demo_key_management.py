#!/usr/bin/env python3
"""
Secure Drone - Key Management System Demonstration
"""

from src.crypto_layer.key_manager import key_manager

def main():
    print('🔐 SECURE DRONE - HIERARCHICAL KEY MANAGEMENT SYSTEM')
    print('=' * 60)

    # Display key status
    status = key_manager.get_key_status()
    print('📊 Key Hierarchy Status:')
    for key_type, info in status.items():
        print(f'  {key_type.upper()} KEY:')
        print(f'    State: {info["state"]}')
        print(f'    Session ID: {info["session_id"]}')
        print(f'    Expires in: {info["time_to_expiry"]:.0f} seconds')
        print(f'    Command count: {info["command_count"]}')
        print(f'    Risk level: {info["risk_level"]}')
        print()

    print('✅ Key Hierarchy Validation:', key_manager.validate_key_hierarchy())
    print()

    # Demonstrate key rotation
    print('🔄 Demonstrating Key Rotation:')
    initial_session = status['session']['session_id']
    key_manager.rotate_session_key('demo_rotation')
    new_status = key_manager.get_key_status()
    new_session = new_status['session']['session_id']
    print(f'  Before: {initial_session}')
    print(f'  After:  {new_session}')
    print(f'  Rotated: {initial_session != new_session}')
    print()

    print('🛡️  Security Features Implemented:')
    print('  ✓ Root Key (KR) - Long-term trust anchor')
    print('  ✓ Session Key (KS) - Short-lived working key')
    print('  ✓ Automatic key rotation (time/command/risk-based)')
    print('  ✓ Emergency key revocation')
    print('  ✓ Replay attack protection')
    print('  ✓ Tamper detection')
    print('  ✓ Timestamp validation')
    print('  ✓ Risk escalation')
    print('  ✓ Secure key destruction')
    print('  ✓ Comprehensive logging')

if __name__ == '__main__':
    main()