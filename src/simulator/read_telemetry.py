import asyncio
from mavsdk import System

async def run():
    drone = System()
    await drone.connect(system_address="udpin://0.0.0.0:14550")

    async for position in drone.telemetry.position():
        print(
            f"Lat: {position.latitude_deg}, "
            f"Lon: {position.longitude_deg}, "
            f"Alt: {position.relative_altitude_m}"
        )

if __name__ == "__main__":
    asyncio.run(run())
import asyncio
from mavsdk import System

async def run():
    drone = System()
    await drone.connect(system_address="udpin://:14550")

    async for position in drone.telemetry.position():
        print(
            f"Lat: {position.latitude_deg}, "
            f"Lon: {position.longitude_deg}, "
            f"Alt: {position.relative_altitude_m}"
        )

if __name__ == "__main__":
    asyncio.run(run())
