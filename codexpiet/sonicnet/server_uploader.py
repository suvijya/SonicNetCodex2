"""
Handles uploading SOS packets to the central server.
"""

import asyncio
import logging
import requests

from packet_manager import PacketManager
from config import SERVER_API_URL, SERVER_UPLOAD_INTERVAL

logger = logging.getLogger(__name__)

class ServerUploader:
    """Continuously tries to upload packets from the cache to the server."""

    def __init__(self, packet_manager: PacketManager):
        self.packet_manager = packet_manager
        self.running = False

    async def start(self):
        """Starts the background task for uploading packets."""
        self.running = True
        asyncio.create_task(self._upload_loop())
        logger.info("Server uploader started.")

    async def stop(self):
        """Stops the uploader."""
        self.running = False
        logger.info("Server uploader stopped.")

    async def _upload_loop(self):
        """The main loop that periodically uploads packets."""
        while self.running:
            packets_to_upload = self.packet_manager.get_all_packets()
            if not packets_to_upload:
                await asyncio.sleep(SERVER_UPLOAD_INTERVAL)
                continue

            logger.info(f"Attempting to upload {len(packets_to_upload)} packets to the server...")
            for packet in packets_to_upload:
                await self._upload_packet(packet)
            
            await asyncio.sleep(SERVER_UPLOAD_INTERVAL)

    async def _upload_packet(self, packet):
        """Uploads a single packet to the server."""
        try:
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None, 
                lambda: requests.post(SERVER_API_URL, json=packet.to_dict(), timeout=10)
            )

            if response.status_code == 200:
                logger.info(f"Successfully uploaded packet {packet.packet_id}")
                self.packet_manager.remove_packet(packet.packet_id)
            else:
                logger.warning(f"Failed to upload packet {packet.packet_id}. Server responded with {response.status_code}")
        except requests.exceptions.RequestException as e:
            logger.error(f"Could not connect to the server: {e}")
        except Exception as e:
            logger.error(f"An unexpected error occurred during upload: {e}")
