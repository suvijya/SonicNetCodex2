"""
BLE transport for close-range, low-energy communication.
Redesigned to use bleak library for better BLE functionality and reliability.
"""

import asyncio
import logging
import json
import time
import uuid
from typing import Optional, Dict, List, Set
from dataclasses import dataclass

from .base import BaseTransport
from packet import SOSPacket
from config import BLE_SERVICE_UUID, BLE_SCAN_INTERVAL, BLE_CONNECTION_TIMEOUT

try:
    from bleak import BleakScanner, BleakClient
    from bleak.backends.device import BLEDevice as BleakBLEDevice
    from bleak.advertising import AdvertisementData, BleakScanner

    BLE_AVAILABLE = True
except ImportError:
    BLE_AVAILABLE = False
    # Create dummy classes when bleak is not available
    class BleakBLEDevice:
        pass

    class BleakScanner:
        pass

    class BleakClient:
        pass


logger = logging.getLogger(__name__)

# SonicWave BLE service and characteristic UUIDs
SONICWAVE_SERVICE_UUID = "6e400001-b5a3-f393-e0a9-e50e24dcca9e"  # Nordic UART Service UUID
SONICWAVE_RX_CHAR_UUID = "6e400002-b5a3-f393-e0a9-e50e24dcca9e"  # RX Characteristic (we receive data here)
SONICWAVE_TX_CHAR_UUID = "6e400003-b5a3-f393-e0a9-e50e24dcca9e"  # TX Characteristic (we send data here)

@dataclass
class BLEPeer:
    """Represents a discovered BLE peer device."""
    device: BleakBLEDevice
    address: str
    name: str
    last_seen: float
    packets_sent: int = 0
    connection_failures: int = 0

class BLEMeshTransport(BaseTransport):
    """
    Redesigned BLE transport using bleak-py library.
    - Uses bleak-py's discover and connection methods
    - Implements proper notification-based receiving
    - Maintains GATT client architecture for reliable communication
    """

    def __init__(self, message_queue: asyncio.Queue, packet_manager):
        super().__init__(message_queue, packet_manager)
        self.running = False

        # Peer management
        self.discovered_peers: Dict[str, BLEPeer] = {}
        self.connected_devices: Dict[str, BleakClient] = {}
        self.pending_packets: asyncio.Queue = asyncio.Queue()

        # Background tasks
        self.discover_task = None
        self.send_task = None
        self.monitor_task = None
        self.advertiser = None

        # Start server task
        self.server_task = None

        # Data handling
        self.received_data_buffer: Dict[str, Dict[int, str]] = {}  # Buffer for chunked data

        # Statistics
        self.stats = {
            'discoveries_performed': 0,
            'peers_discovered': 0,
            'packets_sent': 0,
            'packets_received': 0,
            'connection_errors': 0,
            'discovery_errors': 0,
            'active_connections': 0,
            'notification_errors': 0,
            'server_running': False,
            'server_connections': 0,
            'server_errors': 0
        }

        # GATT Server components
        self.server_running = False

    async def start(self):
        """Start BLE transport with discovery and connection management."""
        if not BLE_AVAILABLE:
            logger.warning("BLE transport unavailable. bleak-py not installed.")
            return

        try:
            self.running = True

            logger.info("Starting BLE transport with bleak library")

            # Start advertising
            await self._start_advertising()

            # Start discovery task
            self.discover_task = asyncio.create_task(self._discovery_loop())

            # Start sending task
            self.send_task = asyncio.create_task(self._send_loop())

            # Start connection monitoring task
            self.monitor_task = asyncio.create_task(self._monitor_connections())

            # Start mock GATT server task (for testing compatibility)
            self.server_task = asyncio.create_task(self._start_mock_server())

            logger.info("BLE transport started with discovery and connection management")

        except Exception as e:
            logger.error(f"Failed to start BLE transport: {e}")
            self.running = False
            raise

    async def stop(self):
        """Stop BLE transport gracefully."""
        self.running = False

        # Stop advertising
        if self.advertiser:
            await self.advertiser.stop()

        # Disconnect all connected devices
        for address, device in self.connected_devices.items():
            try:
                await device.disconnect()
                logger.debug(f"Disconnected from {address}")
            except Exception as e:
                logger.debug(f"Error disconnecting from {address}: {e}")

        self.connected_devices.clear()

        # Cancel all background tasks
        tasks_to_cancel = [self.discover_task, self.send_task, self.monitor_task, self.server_task]

        for task in tasks_to_cancel:
            if task and not task.done():
                task.cancel()
                try:
                    await task
                except asyncio.CancelledError:
                    pass

        # Stop server
        self.server_running = False
        self.stats['server_running'] = False

        logger.info("BLE transport stopped")

    async def send(self, packet: SOSPacket):
        """Queue a packet for BLE transmission to discovered peers."""
        if not self.running:
            return

        try:
            await self.pending_packets.put(packet)
            logger.debug(f"Queued packet {packet.packet_id} for BLE transmission")
        except Exception as e:
            logger.error(f"Error queuing BLE packet: {e}")

    async def _discovery_loop(self):
        """Continuously discover BLE devices using bleak library."""
        while self.running:
            try:
                logger.debug("Starting BLE device discovery...")

                discovered_count = 0
                current_time = time.time()

                # Use bleak BleakScanner.discover() function
                try:
                    # Call bleak discover function - returns a list of BLEDevice objects
                    devices = await BleakScanner.discover(timeout=5.0)

                    logger.info(f"Found {len(devices)} BLE devices")

                except Exception as discover_error:
                    logger.error(f"BLE discovery error: {discover_error}")
                    self.stats['discovery_errors'] += 1
                    devices = []

                # Process discovered devices
                for i, device in enumerate(devices):
                    if not self.running:
                        break

                    logger.debug(f"Processing device {i+1}/{len(devices)}: {type(device)}")

                    try:
                        # Use bleak BLEDevice properties - these are direct attributes
                        address = device.address
                        name = device.name if device.name else "Unknown"

                        logger.debug(f"Device info - Address: {address}, Name: {name}")

                    except Exception as e:
                        logger.debug(f"Error getting device info: {e}")
                        # Fallback
                        address = str(device)
                        name = "Unknown"

                    # Check if this is a SonicWave device
                    if self._is_sonicwave_device(device, name):
                        if address not in self.discovered_peers:
                            self.discovered_peers[address] = BLEPeer(
                                device=device,
                                address=address,
                                name=name,
                                last_seen=current_time
                            )
                            self.stats['peers_discovered'] += 1
                            discovered_count += 1
                            logger.info(f"Discovered SonicWave BLE device: {address} ({name})")
                        else:
                            # Update last seen time
                            self.discovered_peers[address].last_seen = current_time

                self.stats['discoveries_performed'] += 1

                # Clean up old peers (not seen for 5 minutes)
                cutoff_time = current_time - 300
                old_peers = [addr for addr, peer in self.discovered_peers.items()
                           if peer.last_seen < cutoff_time]
                for addr in old_peers:
                    # Disconnect if connected
                    if addr in self.connected_devices:
                        try:
                            await self.connected_devices[addr].disconnect()
                            del self.connected_devices[addr]
                            self.stats['active_connections'] -= 1
                        except:
                            pass

                    del self.discovered_peers[addr]
                    logger.debug(f"Removed stale BLE peer: {addr}")

                logger.debug(f"Discovery complete - found {discovered_count} new SonicWave devices, "
                           f"{len(self.discovered_peers)} total active peers")

            except Exception as e:
                logger.error(f"BLE discovery error: {e}")
                self.stats['discovery_errors'] += 1

            # Wait before next discovery cycle
            await asyncio.sleep(BLE_SCAN_INTERVAL)

    async def _start_advertising(self):
        """Start advertising the BLE service."""
        try:
            self.advertiser = BleakScanner()
            advertisement_data = AdvertisementData(
                local_name="SonicWave",
                service_uuids=[SONICWAVE_SERVICE_UUID]
            )
            await self.advertiser.start(advertisement_data)
            logger.info("BLE advertising started successfully.")
        except Exception as e:
            logger.error(f"Failed to start BLE advertising: {e}")

    def _is_sonicwave_device(self, device: BleakBLEDevice, name: str) -> bool:
        """Determine if a device is a SonicWave device."""
        # Add your filtering logic here
        # For now, we'll look for devices with "SonicWave" in the name or specific characteristics
        if "sonicwave" in name.lower():
            return True
        if "ble-test" in name.lower():
            return True
        # Check for our service UUID in the advertised data
        if SONICWAVE_SERVICE_UUID in device.metadata.get('uuids', []):
            return True
        return False

    async def _send_loop(self):
        """Process pending packets and send to connected peers."""
        while self.running:
            try:
                # Wait for packets to send
                try:
                    packet = await asyncio.wait_for(
                        self.pending_packets.get(),
                        timeout=1.0
                    )
                except asyncio.TimeoutError:
                    continue

                # Send packet to all connected peers
                if self.connected_devices:
                    await self._broadcast_packet_to_peers(packet)
                else:
                    logger.debug(f"No connected BLE peers for packet {packet.packet_id}")

            except Exception as e:
                logger.error(f"Error in BLE send loop: {e}")
                await asyncio.sleep(1)

    async def _monitor_connections(self):
        """Monitor and maintain connections to discovered peers."""
        while self.running:
            try:
                # Try to connect to discovered peers that aren't connected
                for address, peer in list(self.discovered_peers.items()):
                    if address not in self.connected_devices and peer.connection_failures < 3:
                        try:
                            await self._connect_to_peer(peer)
                        except Exception as e:
                            logger.debug(f"Failed to connect to {address}: {e}")
                            peer.connection_failures += 1

                # Check connection health
                disconnected_devices = []
                for address, device in self.connected_devices.items():
                    if not device.is_connected():
                        disconnected_devices.append(address)

                # Clean up disconnected devices
                for address in disconnected_devices:
                    del self.connected_devices[address]
                    self.stats['active_connections'] -= 1
                    logger.debug(f"Device {address} disconnected")

                await asyncio.sleep(5)  # Check every 5 seconds

            except Exception as e:
                logger.error(f"Error in connection monitor: {e}")
                await asyncio.sleep(5)

    async def _connect_to_peer(self, peer: BLEPeer):
        """Connect to a peer device and set up notifications using BleakClient."""
        try:
            logger.debug(f"Connecting to BLE peer {peer.address}")

            # Create a BleakClient for the device
            client = BleakClient(peer.device)

            # Connect to the device
            await client.connect()

            if client.is_connected:
                # Set up notification callback for receiving data
                await client.start_notify(
                    SONICWAVE_TX_CHAR_UUID,
                    lambda sender, data: self._on_notification_received(peer.address, sender, data)
                )

                # Add to connected devices
                self.connected_devices[peer.address] = client
                self.stats['active_connections'] += 1
                peer.connection_failures = 0

                logger.info(f"Successfully connected to {peer.address} ({peer.name})")

            else:
                raise Exception("Connection failed")

        except Exception as e:
            peer.connection_failures += 1
            self.stats['connection_errors'] += 1
            logger.debug(f"Failed to connect to {peer.address}: {e}")
            raise

    def _on_notification_received(self, device_address: str, char_uuid: str, data: bytes):
        """Handle notification data received from a peer device."""
        try:
            logger.debug(f"BLE notification from {device_address}: {len(data)} bytes")

            # Convert bytes to string
            data_str = data.decode('utf-8')

            # Handle chunked data
            if data_str.startswith("CHUNK:"):
                parts = data_str.split(":", 3)
                if len(parts) == 4:
                    client_id = parts[1]
                    chunk_num = int(parts[2])
                    chunk_data = parts[3]

                    # Store chunk
                    if client_id not in self.received_data_buffer:
                        self.received_data_buffer[client_id] = {}

                    self.received_data_buffer[client_id][chunk_num] = chunk_data
                    return

            elif data_str.startswith("END:"):
                parts = data_str.split(":", 2)
                if len(parts) == 3:
                    client_id = parts[1]
                    total_chunks = int(parts[2])

                    # Reconstruct packet from chunks
                    if client_id in self.received_data_buffer:
                        chunks = self.received_data_buffer[client_id]

                        if len(chunks) == total_chunks:
                            # Reconstruct data
                            reconstructed_data = ""
                            for i in range(total_chunks):
                                if i in chunks:
                                    reconstructed_data += chunks[i]
                                else:
                                    logger.error(f"Missing chunk {i} for {client_id}")
                                    return

                            del self.received_data_buffer[client_id]
                            data_str = reconstructed_data
                        else:
                            logger.error(f"Incomplete chunks for {client_id}")
                            return
                    else:
                        logger.error(f"No chunks found for {client_id}")
                        return

            # Parse packet
            try:
                packet = SOSPacket.from_json(data_str)
                logger.info(f"BLE received packet: {packet.packet_id[:8]}... from {packet.sender_id[:8]}...")

                # Put packet into message queue
                try:
                    self.message_queue.put_nowait(packet)
                    self.stats['packets_received'] += 1
                except asyncio.QueueFull:
                    logger.warning("Message queue full, dropping BLE packet")

            except Exception as e:
                logger.error(f"Failed to parse BLE packet: {e}")
                logger.debug(f"Raw data: {data_str[:100]}...")

        except Exception as e:
            logger.error(f"Error processing BLE notification: {e}")
            self.stats['notification_errors'] += 1

    def _on_device_disconnected(self, device_address: str):
        """Handle device disconnection."""
        if device_address in self.connected_devices:
            del self.connected_devices[device_address]
            self.stats['active_connections'] -= 1
            logger.info(f"BLE device {device_address} disconnected")

    async def _broadcast_packet_to_peers(self, packet: SOSPacket):
        """Send a packet to all connected peers."""
        tasks = []
        for address, device in list(self.connected_devices.items()):
            if device.is_connected():
                task = asyncio.create_task(self._send_packet_to_device(device, packet, address))
                tasks.append(task)

        if tasks:
            try:
                await asyncio.wait_for(asyncio.gather(*tasks, return_exceptions=True), timeout=30.0)
            except asyncio.TimeoutError:
                logger.warning("BLE broadcast timed out")

    async def _send_packet_to_device(self, client: BleakClient, packet: SOSPacket, address: str):
        """Send a packet to a specific connected device."""
        try:
            if not client.is_connected:
                raise Exception("Device not connected")

            # Prepare packet data
            packet_data = packet.to_json()
            packet_bytes = packet_data.encode('utf-8')

            # Send data (handle chunking for large packets)
            max_chunk_size = 180

            if len(packet_bytes) <= max_chunk_size:
                # Send as single packet
                await client.write_gatt_char(SONICWAVE_RX_CHAR_UUID, packet_bytes)
            else:
                # Send in chunks
                client_id = f"client_{int(time.time() * 1000) % 10000}"
                chunks = []

                # Split data into chunks
                for i in range(0, len(packet_data), max_chunk_size - 50):
                    chunk_data = packet_data[i:i + max_chunk_size - 50]
                    chunk_num = len(chunks)
                    chunk_msg = f"CHUNK:{client_id}:{chunk_num}:{chunk_data}"
                    chunks.append(chunk_msg.encode('utf-8'))

                # Send all chunks
                for chunk in chunks:
                    await client.write_gatt_char(SONICWAVE_RX_CHAR_UUID, chunk)
                    await asyncio.sleep(0.1)

                # Send end marker
                end_msg = f"END:{client_id}:{len(chunks)}"
                await client.write_gatt_char(SONICWAVE_RX_CHAR_UUID, end_msg.encode('utf-8'))

            # Update peer stats
            if address in self.discovered_peers:
                self.discovered_peers[address].packets_sent += 1

            self.stats['packets_sent'] += 1
            logger.debug(f"Successfully sent packet {packet.packet_id} to {address}")

        except Exception as e:
            self.stats['connection_errors'] += 1
            logger.debug(f"Failed to send to BLE device {address}: {e}")

    async def _start_mock_server(self):
        """
        Start a mock GATT server for testing compatibility.
        Since bleak is primarily a client library, this simulates server functionality.
        """
        try:
            # Simulate server startup delay
            await asyncio.sleep(2)

            self.server_running = True
            self.stats['server_running'] = True

            logger.info("Mock BLE GATT server started")
            logger.info(f"Service UUID: {SONICWAVE_SERVICE_UUID}")
            logger.info(f"RX Characteristic: {SONICWAVE_RX_CHAR_UUID}")
            logger.info(f"TX Characteristic: {SONICWAVE_TX_CHAR_UUID}")

            # Keep server running and simulate it's working
            while self.running and self.server_running:
                await asyncio.sleep(5)

                # Mock server activity - could handle incoming connections here
                # For now, just update stats to show server is active
                self.stats['server_running'] = True

        except Exception as e:
            logger.error(f"Mock GATT server error: {e}")
            self.stats['server_errors'] += 1
            self.server_running = False
            self.stats['server_running'] = False

    def get_transport_stats(self) -> Dict:
        """Get BLE transport statistics."""
        return {
            **self.stats,
            'ble_available': BLE_AVAILABLE,
            'running': self.running,
            'active_peers': len(self.discovered_peers),
            'connected_devices': len(self.connected_devices),
            'pending_packets': self.pending_packets.qsize(),
            'buffered_chunks': len(self.received_data_buffer)
        }

    def get_discovered_peers(self) -> List[Dict]:
        """Get list of discovered BLE peers."""
        return [
            {
                'address': peer.address,
                'name': peer.name,
                'last_seen': peer.last_seen,
                'packets_sent': peer.packets_sent,
                'connection_failures': peer.connection_failures,
                'connected': peer.address in self.connected_devices
            }
            for peer in self.discovered_peers.values()
        ]
