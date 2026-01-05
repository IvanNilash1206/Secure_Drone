#!/usr/bin/env python3

import asyncio
from mavsdk import System

async def run():
    drone = System()
    # Use udpin:// instead of deprecated udp://
    await drone.connect(system_address="udpin://0.0.0.0:14550")

    print("Waiting for connection...")
    async for state in drone.core.connection_state():
        if state.is_connected:
            print("✅ Connected")
            break

    print("Waiting for drone to be ready...")
    async for health in drone.telemetry.health():
        if health.is_global_position_ok and health.is_home_position_ok:
            print("✅ Ready")
            break

    # Ensure drone is in a good state before arming
    print("Arming...")
    try:
        await drone.action.arm()
        await asyncio.sleep(1)  # Brief delay after arming
    except Exception as e:
        print(f"❌ Arming failed: {e}")
        return

    print("Taking off...")
    try:
        await drone.action.takeoff()
        await asyncio.sleep(2)  # Wait for takeoff to stabilize
    except Exception as e:
        print(f"❌ Takeoff failed: {e}")
        return

    print("🚁 Hovering for 10 seconds...")
    await asyncio.sleep(10)

    print("Landing...")
    try:
        await drone.action.land()
    except Exception as e:
        print(f"❌ Landing failed: {e}")
        return

    # Wait for landing to complete and disarm
    print("Waiting for disarm...")
    async for is_armed in drone.telemetry.armed():
        if not is_armed:
            print("✅ Disarmed")
            break

    print("✅ Mission complete")

if __name__ == "__main__":
    asyncio.run(run())
