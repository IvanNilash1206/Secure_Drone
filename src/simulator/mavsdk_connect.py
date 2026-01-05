import asyncio
from src.logging_config import logger
from mavsdk import System

async def run():
    logger.info("Starting MAVSDK connection")
    drone = System()
    await drone.connect(system_address="udpin://0.0.0.0:14550")

    logger.info("Connecting to ArduPilot...")
    print("Connecting to ArduPilot...")

    try:
        async for state in drone.core.connection_state():
            if state.is_connected:
                logger.info("Connected to ArduPilot SITL")
                print("✅ Connected to ArduPilot SITL")
                break
            elif not state.is_connecting:
                logger.error("Connection failed")
                print("❌ Connection failed")
                return
    except asyncio.TimeoutError:
        logger.error("Connection timeout")
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
