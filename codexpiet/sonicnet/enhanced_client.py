"""
Enhanced SonicWave client that coordinates all components with advanced features.
"""

import asyncio
import logging
import uuid
import time
import psutil
from typing import Optional, List, Dict, Any

from packet import SOSPacket, PacketType, UrgencyLevel, GPSLocation
from packet_manager import PacketManager
from server_uploader import ServerUploader
from location_service import LocationService
from transports.udp import UDPMeshTransport
from transports.ble_transport import BLEMeshTransport
from transports.ggwave import GGWaveTransport

logger = logging.getLogger(__name__)

class SonicWaveClient:
    """The enhanced main client class, orchestrating all parts of the application."""

    def __init__(self, node_name: Optional[str] = None):
        self.node_id = f"node_{uuid.uuid4().hex[:8]}"
        self.node_name = node_name or f"SonicNet_{self.node_id[-4:]}"

        # Core components
        self.packet_manager = PacketManager()
        self.server_uploader = ServerUploader(self.packet_manager)
        self.location_service = LocationService()

        # Communication
        self.message_queue = asyncio.Queue()
        self.transports = []
        self.running = False

        # User profile and emergency info
        self.user_profile = {
            'name': '',
            'emergency_contacts': [],
            'medical_info': '',
            'location_sharing': True
        }

        # Performance and resource monitoring
        self.performance_monitor = None
        self.last_heartbeat = time.time()

        # Event callbacks for UI
        self.event_callbacks = {
            'packet_received': [],
            'packet_sent': [],
            'peer_discovered': [],
            'connection_status_changed': [],
            'sos_received': []
        }

    async def start(self):
        """Starts the enhanced client and all its components."""
        logger.info(f"Starting SonicWave client - Node: {self.node_name} (ID: {self.node_id})")
        self.running = True

        # Initialize location services
        await self.location_service.start()

        # Initialize transports
        self._initialize_transports()

        # Start components
        await self.server_uploader.start()
        for transport in self.transports:
            await transport.start()

        # Start core processing loops
        asyncio.create_task(self._process_messages())
        asyncio.create_task(self._heartbeat_loop())
        asyncio.create_task(self._performance_monitor_loop())
        asyncio.create_task(self._network_maintenance_loop())

        logger.info(f"SonicWave client fully operational with {len(self.transports)} transports")

    async def stop(self):
        """Stops the client and all components gracefully."""
        logger.info("Shutting down SonicWave client...")
        self.running = False

        # Stop components in reverse order
        for transport in self.transports:
            await transport.stop()
        await self.server_uploader.stop()

        logger.info("SonicWave client stopped.")

    def _initialize_transports(self):
        """Initializes all available communication transports."""
        available_transports = [
            UDPMeshTransport,
            BLEMeshTransport,
            GGWaveTransport
        ]

        for transport_class in available_transports:
            try:
                transport = transport_class(self.message_queue, self.packet_manager)
                self.transports.append(transport)
                logger.info(f"Successfully initialized {transport_class.__name__}")
            except Exception as e:
                logger.error(f"Failed to initialize {transport_class.__name__}: {e}")

    async def send_sos(self, message: str, urgency: UrgencyLevel = UrgencyLevel.HIGH,
                      location: Optional[GPSLocation] = None,
                      media_attachments: Optional[List] = None) -> SOSPacket:
        """Creates and broadcasts an enhanced SOS packet."""

        # Get current location if not provided
        if location is None and self.user_profile.get('location_sharing', True):
            location = await self.location_service.get_current_location()

        # Create SOS packet
        packet = SOSPacket(
            sender_id=self.node_id,
            message=message,
            location=location,
            urgency=urgency,
            packet_type=PacketType.SOS
        )

        # Add battery level
        packet.battery_level = self._get_battery_level()

        # Add media attachments if provided
        if media_attachments:
            for media_data, media_type, filename in media_attachments:
                packet.add_media_attachment(media_data, media_type, filename)

        # Add to packet manager and broadcast
        self.packet_manager.add_packet(packet)
        await self._broadcast(packet)

        # Trigger event callbacks
        await self._trigger_event('packet_sent', packet)

        logger.critical(f"SOS SENT: {message} (Urgency: {urgency.value}, ID: {packet.packet_id})")
        return packet

    async def send_status_update(self, message: str, thread_id: str) -> SOSPacket:
        """Send a status update for an ongoing emergency."""
        location = await self.location_service.get_current_location()

        packet = SOSPacket(
            sender_id=self.node_id,
            message=message,
            location=location,
            urgency=UrgencyLevel.MEDIUM,
            packet_type=PacketType.STATUS_UPDATE,
            thread_id=thread_id
        )

        packet.battery_level = self._get_battery_level()
        self.packet_manager.add_packet(packet)
        await self._broadcast(packet)

        return packet

    async def send_all_clear(self, thread_id: str) -> SOSPacket:
        """Send an all-clear message to indicate emergency is resolved."""
        packet = SOSPacket(
            sender_id=self.node_id,
            message="All clear - emergency resolved",
            urgency=UrgencyLevel.LOW,
            packet_type=PacketType.ALL_CLEAR,
            thread_id=thread_id
        )

        self.packet_manager.add_packet(packet)
        await self._broadcast(packet)

        logger.info(f"All clear sent for thread {thread_id}")
        return packet

    async def _broadcast(self, packet: SOSPacket):
        """Broadcasts a packet to all active transports with retry logic."""
        broadcast_tasks = []

        for transport in self.transports:
            broadcast_tasks.append(asyncio.create_task(transport.send(packet)))

        # Wait for all broadcasts to complete
        if broadcast_tasks:
            await asyncio.gather(*broadcast_tasks, return_exceptions=True)

        self.packet_manager.stats['packets_sent'] += 1

    async def _process_messages(self):
        """Enhanced message processing loop with priority handling."""
        while self.running:
            try:
                # Process high-priority packets first
                packet = self.packet_manager.get_next_packet_to_process()

                if packet is None:
                    # No priority packets, check regular queue
                    try:
                        packet = await asyncio.wait_for(self.message_queue.get(), timeout=1.0)
                    except asyncio.TimeoutError:
                        continue

                # Skip our own packets
                if packet.sender_id == self.node_id:
                    logger.debug(f"Ignoring our own packet {packet.packet_id}")
                    continue

                # Process the packet
                await self._handle_incoming_packet(packet)

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error processing message: {e}")

    async def _handle_incoming_packet(self, packet: SOSPacket):
        """Handle an incoming packet with intelligent processing."""

        # Add packet to manager (includes duplicate detection and rate limiting)
        if not self.packet_manager.add_packet(packet):
            return  # Duplicate or rate limited

        # Trigger event callbacks
        await self._trigger_event('packet_received', packet)

        # Special handling for SOS packets
        if packet.packet_type == PacketType.SOS:
            await self._trigger_event('sos_received', packet)
            logger.warning(f"SOS RECEIVED: {packet.message} from {packet.sender_id}")

            # Send acknowledgment if required
            if packet.requires_ack:
                ack_packet = self.packet_manager.create_ack_for_packet(packet, self.node_id)
                await self._broadcast(ack_packet)

        # Decide whether to relay
        if self.packet_manager.should_relay_packet(packet, self.node_id):
            packet.increment_hop(self.node_id)
            await self._broadcast(packet)
            self.packet_manager.stats['packets_relayed'] += 1
            logger.info(f"Relayed packet {packet.packet_id} (hop {packet.hop_count})")

    async def _heartbeat_loop(self):
        """Send periodic heartbeats to maintain network presence."""
        while self.running:
            try:
                heartbeat_packet = SOSPacket(
                    sender_id=self.node_id,
                    message=f"Heartbeat from {self.node_name}",
                    packet_type=PacketType.HEARTBEAT,
                    urgency=UrgencyLevel.LOW
                )

                heartbeat_packet.battery_level = self._get_battery_level()
                heartbeat_packet.requires_ack = False

                # Don't cache heartbeats, just broadcast
                await self._broadcast(heartbeat_packet)
                self.last_heartbeat = time.time()

                await asyncio.sleep(60)  # Heartbeat every minute

            except Exception as e:
                logger.error(f"Heartbeat error: {e}")
                await asyncio.sleep(60)

    async def _performance_monitor_loop(self):
        """Monitor system performance and resource usage."""
        while self.running:
            try:
                # Clean up old data periodically
                self.packet_manager.cleanup_old_data()

                # Log performance stats
                stats = self.get_comprehensive_stats()
                logger.debug(f"Performance stats: {stats}")

                await asyncio.sleep(300)  # Every 5 minutes

            except Exception as e:
                logger.error(f"Performance monitor error: {e}")
                await asyncio.sleep(300)

    async def _network_maintenance_loop(self):
        """Maintain network connections and topology."""
        while self.running:
            try:
                # Update transport statistics
                for transport in self.transports:
                    if hasattr(transport, 'get_transport_stats'):
                        stats = transport.get_transport_stats()
                        logger.debug(f"{transport.__class__.__name__} stats: {stats}")

                await asyncio.sleep(120)  # Every 2 minutes

            except Exception as e:
                logger.error(f"Network maintenance error: {e}")
                await asyncio.sleep(120)

    def _get_battery_level(self) -> Optional[float]:
        """Get current battery level as percentage."""
        try:
            battery = psutil.sensors_battery()
            if battery:
                return battery.percent
        except Exception:
            pass
        return None

    async def _trigger_event(self, event_type: str, data: Any):
        """Trigger event callbacks for UI updates."""
        callbacks = self.event_callbacks.get(event_type, [])
        for callback in callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(data)
                else:
                    callback(data)
            except Exception as e:
                logger.error(f"Event callback error ({event_type}): {e}")

    def register_event_callback(self, event_type: str, callback):
        """Register a callback for specific events."""
        if event_type in self.event_callbacks:
            self.event_callbacks[event_type].append(callback)

    def set_user_profile(self, profile: Dict[str, Any]):
        """Update user profile information."""
        self.user_profile.update(profile)
        logger.info("User profile updated")

    def get_comprehensive_stats(self) -> Dict[str, Any]:
        """Get comprehensive system statistics."""
        stats = {
            'node_info': {
                'id': self.node_id,
                'name': self.node_name,
                'uptime': time.time() - self.last_heartbeat if self.running else 0
            },
            'packet_stats': self.packet_manager.get_network_stats(),
            'transport_stats': {},
            'system_stats': {
                'battery_level': self._get_battery_level(),
                'memory_usage': psutil.virtual_memory().percent,
                'cpu_usage': psutil.cpu_percent()
            }
        }

        # Add transport-specific stats
        for transport in self.transports:
            transport_name = transport.__class__.__name__
            if hasattr(transport, 'get_transport_stats'):
                stats['transport_stats'][transport_name] = transport.get_transport_stats()

        return stats

    def get_active_conversations(self) -> List[Dict]:
        """Get all active emergency conversations."""
        conversations = []
        thread_packets = {}

        for packet in self.packet_manager.get_all_packets():
            thread_id = packet.thread_id
            if thread_id not in thread_packets:
                thread_packets[thread_id] = []
            thread_packets[thread_id].append(packet)

        for thread_id, packets in thread_packets.items():
            # Sort by timestamp
            packets.sort(key=lambda p: p.timestamp)
            latest_packet = packets[-1]

            conversations.append({
                'thread_id': thread_id,
                'original_sender': packets[0].sender_id,
                'latest_message': latest_packet.message,
                'urgency': latest_packet.urgency.value,
                'packet_count': len(packets),
                'last_update': latest_packet.timestamp,
                'status': latest_packet.packet_type.value
            })

        return conversations

    async def get_location_info(self) -> Dict[str, Any]:
        """Get current location information."""
        current_location = await self.location_service.get_current_location()

        info = {
            'has_gps': current_location is not None,
            'location': None,
            'description': 'Location unavailable'
        }

        if current_location:
            info['location'] = {
                'latitude': current_location.latitude,
                'longitude': current_location.longitude,
                'altitude': current_location.altitude,
                'accuracy': current_location.accuracy,
                'timestamp': current_location.timestamp
            }

            description = await self.location_service.get_location_description(current_location)
            info['description'] = description

        return info
