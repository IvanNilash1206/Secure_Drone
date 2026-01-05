import asyncio
from mavsdk import System

async def run():
    drone = System()
    await drone.connect(system_address="udpin://0.0.0.0:14550")

    print("Connecting to ArduPilot...")

    try:
        async for state in drone.core.connection_state():
            if state.is_connected:
                print("✅ Connected to ArduPilot SITL")
                break
            elif not state.is_connecting:
                print("❌ Connection failed")
                return
    except asyncio.TimeoutError:
        print("❌ Connection timeout")
        return

    try:
        async for health in drone.telemetry.health():
            if health.is_global_position_ok:
                print("✅ Global position OK")
                break
    except Exception as e:
        print(f"❌ Health check failed: {e}")

if __name__ == "__main__":
    asyncio.run(run())
