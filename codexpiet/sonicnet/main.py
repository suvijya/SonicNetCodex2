"""
Main entry point for the SonicWave client application.
"""

import asyncio
import logging

from client import SonicWaveClient

def setup_logging():
    """Configures logging for the application."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(levelname)s - %(name)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

async def main():
    """Initializes and runs the SonicWave client."""
    setup_logging()
    client = SonicWaveClient()
    shutdown_event = asyncio.Event()

    try:
        await client.start()

        # Demonstrate sending an SOS after a short delay
        await asyncio.sleep(5)
        await client.send_sos("This is a test SOS message!", location="12.345, 67.890")

        # Wait indefinitely until a shutdown signal is received
        await shutdown_event.wait()

    except (asyncio.CancelledError, KeyboardInterrupt):
        print("\nShutdown signal received.")
    finally:
        await client.stop()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        # This is handled in the main function's finally block
        pass
