"""
Main SonicWave client that coordinates all components.
Enhanced with separate send/receive transport models for more reliable communication.
"""

import asyncio
import logging
import uuid
import sys
import signal

from packet import SOSPacket, GPSLocation
from packet_manager import PacketManager
from server_uploader import ServerUploader
from transports.udp_transport import UDPTransport
from transports.ble_transport import BLETransport
from transports.ggwave_transport import GGWaveTransport
from location_service import LocationService

logger = logging.getLogger(__name__)

class SonicWaveClient:
    """The main client class, orchestrating all parts of the application."""

    def __init__(self):
        self.node_id = f"node_{uuid.uuid4().hex[:8]}"
        self.packet_manager = PacketManager()
        self.server_uploader = ServerUploader(self.packet_manager)
        self.location_service = LocationService()
        self.message_queue = asyncio.Queue(maxsize=100)  # Prevent memory issues
        self.transports = []
        self.running = False
        self.stats = {
            'messages_sent': 0,
            'messages_received': 0,
            'transports_active': 0,
            'errors': 0
        }

    async def start(self):
        """Starts the client and all its components."""
        logger.info(f"Starting SonicWave client with Node ID: {self.node_id}")

        # Set Windows-specific event loop policy if needed
        if sys.platform == 'win32':
            try:
                # Use ProactorEventLoop for better Windows compatibility
                loop = asyncio.get_event_loop()
                if not isinstance(loop, asyncio.ProactorEventLoop):
                    logger.info("Setting Windows ProactorEventLoop for better BLE compatibility")
                    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
            except Exception as e:
                logger.warning(f"Could not set ProactorEventLoop: {e}")

        self.running = True

        try:
            # Initialize location service
            location_started = await self.location_service.start()
            if location_started:
                logger.info("Location service started successfully")
            else:
                logger.info("Location service using manual/text input mode")

            # Initialize transports with new models
            await self._initialize_transports()

            # Start server uploader
            await self.server_uploader.start()

            # Start transports
            for transport in self.transports:
                try:
                    await transport.start()
                    self.stats['transports_active'] += 1
                    logger.info(f"Started {type(transport).__name__}")
                except Exception as e:
                    logger.error(f"Failed to start {type(transport).__name__}: {e}")
                    self.stats['errors'] += 1

            # Start the main message processing loop
            asyncio.create_task(self._process_messages())
            logger.info(f"SonicWave client started with {self.stats['transports_active']} active transports")

        except Exception as e:
            logger.error(f"Failed to start SonicWave client: {e}")
            self.stats['errors'] += 1
            raise

    async def stop(self):
        """Stops the client and all components gracefully."""
        logger.info("Stopping SonicWave client...")
        self.running = False

        # Stop location service
        try:
            await self.location_service.stop()
        except Exception as e:
            logger.error(f"Error stopping location service: {e}")

        # Stop server uploader
        try:
            await self.server_uploader.stop()
        except Exception as e:
            logger.error(f"Error stopping server uploader: {e}")

        # Stop all transports
        for transport in self.transports:
            try:
                await transport.stop()
                logger.info(f"Stopped {type(transport).__name__}")
            except Exception as e:
                logger.error(f"Error stopping {type(transport).__name__}: {e}")
                self.stats['errors'] += 1

        logger.info("SonicWave client stopped")

    async def _initialize_transports(self):
        """Initialize all transport mechanisms with new models."""
        # Initialize transports with new models
        try:
            # Create UDP transport with separate sender/receiver
            udp_transport = UDPTransport(self.message_queue, self.node_id)
            self.transports.append(udp_transport)
            logger.info("UDP transport initialized")
        except Exception as e:
            logger.error(f"Failed to initialize UDP transport: {e}")
            self.stats['errors'] += 1

        try:
            # Create BLE transport with separate sender/receiver
            ble_transport = BLETransport(self.message_queue, self.node_id)
            self.transports.append(ble_transport)
            logger.info("BLE transport initialized")
        except Exception as e:
            logger.error(f"Failed to initialize BLE transport: {e}")
            self.stats['errors'] += 1

        try:
            # Create GGWave transport with separate sender/receiver
            ggwave_transport = GGWaveTransport(self.message_queue, self.node_id)
            self.transports.append(ggwave_transport)
            logger.info("GGWave transport initialized")
        except Exception as e:
            logger.error(f"Failed to initialize GGWave transport: {e}")
            self.stats['errors'] += 1

    async def _process_messages(self):
        """Process incoming messages from all transports."""
        logger.info("Starting message processing loop")

        while self.running:
            try:
                # Get message from queue with timeout to allow checking running state
                try:
                    packet = await asyncio.wait_for(self.message_queue.get(), timeout=1.0)
                except asyncio.TimeoutError:
                    continue

                # Process the received packet
                try:
                    # Skip packets from self
                    if packet.sender_id == self.node_id:
                        logger.debug(f"Skipping packet from self: {packet.packet_id[:8]}...")
                        continue

                    logger.info(f"Processing packet {packet.packet_id[:8]}... from {packet.sender_id[:8]}...")

                    # Add to packet manager
                    if self.packet_manager.add_packet(packet):
                        self.stats['messages_received'] += 1

                    # Mark task as done
                    self.message_queue.task_done()

                except Exception as e:
                    logger.error(f"Error processing message: {e}")
                    self.stats['errors'] += 1

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in message processing loop: {e}")
                self.stats['errors'] += 1
                await asyncio.sleep(1)

        logger.info("Message processing loop stopped")

    async def send_message(self, message: str, location: GPSLocation = None, recipient_id: str = None):
        """
        Send a message through all available transports.

        Args:
            message: Text message to send
            location: GPS location to include (optional)
            recipient_id: Target recipient ID (optional, None for broadcast)
        """
        try:
            # Create packet
            packet = SOSPacket(
                message=message,
                location=location,
                sender_id=self.node_id,
                recipient_id=recipient_id
            )

            # Add to packet manager
            self.packet_manager.add_packet(packet)

            # Send through all transports
            for transport in self.transports:
                if transport.running:
                    await transport.send(packet)

            self.stats['messages_sent'] += 1
            logger.info(f"Sent message with ID {packet.packet_id[:8]}...")
            return packet

        except Exception as e:
            logger.error(f"Error sending message: {e}")
            self.stats['errors'] += 1
            return None

    def get_status(self):
        """Get overall client status information."""
        transport_stats = {}

        for transport in self.transports:
            transport_name = type(transport).__name__
            if hasattr(transport, 'get_stats'):
                transport_stats[transport_name] = transport.get_stats()

        return {
            'node_id': self.node_id,
            'running': self.running,
            'stats': self.stats,
            'transports': transport_stats,
            'packet_manager': self.packet_manager.get_status()
        }
