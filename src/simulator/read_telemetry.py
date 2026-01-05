import asyncio
from src.logging_config import logger
from mavsdk import System

async def run():
    logger.info("Starting telemetry reader")
    drone = System()
    await drone.connect(system_address="udpin://0.0.0.0:14550")

    logger.info("Reading position telemetry...")
    async for position in drone.telemetry.position():
        logger.debug(f"Position: Lat {position.latitude_deg}, Lon {position.longitude_deg}, Alt {position.relative_altitude_m}")
        print(
            f"Lat: {position.latitude_deg}, "
            f"Lon: {position.longitude_deg}, "
            f"Alt: {position.relative_altitude_m}"
        )
        break

    logger.info("Telemetry reading completed")

if __name__ == "__main__":
    logger.info("Launching telemetry reader")
    asyncio.run(run())
