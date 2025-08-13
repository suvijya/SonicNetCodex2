"""
UDP Multicast transport for Wi-Fi based mesh networking.
Refactored with separate sender and receiver components.
"""

import asyncio
import socket
import struct
import logging
import json
from typing import Optional

from .base_transport import BaseTransportSender, BaseTransportReceiver, BaseTransportManager
from packet import SOSPacket
from config import UDP_MULTICAST_GROUP, UDP_PORT

logger = logging.getLogger(__name__)

class UDPSender(BaseTransportSender):
    """Handles sending SOS packets over UDP multicast."""

    def __init__(self, node_id: str):
        super().__init__(node_id)
        self.sock = None

    async def start(self):
        """Initialize the UDP multicast sender."""
        try:
            # Create a UDP socket for sending
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
            self.sock.setsockopt(socket.IPPROTO_IP, socket.IP_MULTICAST_TTL, 2)
            self.running = True
            logger.info(f"UDP sender started for node {self.node_id}")
            return True
        except Exception as e:
            logger.error(f"Failed to start UDP sender: {e}")
            self.stats['send_errors'] += 1
            return False

    async def stop(self):
        """Stop the UDP sender."""
        self.running = False
        if self.sock:
            try:
                self.sock.close()
            except Exception as e:
                logger.error(f"Error closing UDP sender socket: {e}")
        logger.info("UDP sender stopped")

    async def send(self, packet: SOSPacket):
        """Send a packet via UDP multicast."""
        if not self.running or not self.sock:
            return False

        try:
            # Ensure sender ID is set to this node's ID
            if not packet.sender_id:
                packet.sender_id = self.node_id

            # Send the packet
            self.sock.sendto(packet.to_json().encode('utf-8'), (UDP_MULTICAST_GROUP, UDP_PORT))
            self.stats['packets_sent'] += 1
            logger.debug(f"UDP sent packet {packet.packet_id[:8]}...")
            return True
        except Exception as e:
            logger.error(f"Failed to send UDP message: {e}")
            self.stats['send_errors'] += 1
            return False


class UDPReceiver(BaseTransportReceiver):
    """Handles receiving SOS packets over UDP multicast."""

    def __init__(self, message_queue: asyncio.Queue, node_id: str):
        super().__init__(message_queue, node_id)
        self.sock = None
        self.receive_task = None

    async def start(self):
        """Initialize and start the UDP multicast receiver."""
        try:
            # Create a UDP socket for receiving
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
            self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

            # Bind to the multicast port
            self.sock.bind(('', UDP_PORT))

            # Join the multicast group
            mreq = struct.pack("4sl", socket.inet_aton(UDP_MULTICAST_GROUP), socket.INADDR_ANY)
            self.sock.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)

            # Set non-blocking mode for asyncio compatibility
            self.sock.setblocking(False)

            self.running = True

            # Start the receive loop as a background task
            self.receive_task = asyncio.create_task(self._receive_loop())
            logger.info(f"UDP receiver started for node {self.node_id} on {UDP_MULTICAST_GROUP}:{UDP_PORT}")
            return True
        except Exception as e:
            logger.error(f"Failed to start UDP receiver: {e}")
            self.stats['receive_errors'] += 1
            return False

    async def stop(self):
        """Stop the UDP receiver."""
        self.running = False

        # Cancel the receive loop task
        if self.receive_task and not self.receive_task.done():
            self.receive_task.cancel()
            try:
                await self.receive_task
            except asyncio.CancelledError:
                pass

        # Close the socket
        if self.sock:
            try:
                self.sock.close()
            except Exception as e:
                logger.error(f"Error closing UDP receiver socket: {e}")

        logger.info("UDP receiver stopped")

    async def _receive_loop(self):
        """Background task that continuously listens for incoming UDP packets."""
        logger.info("UDP receive loop started")

        while self.running:
            try:
                # Use asyncio to receive data from the socket
                loop = asyncio.get_event_loop()
                data, addr = await loop.sock_recvfrom(self.sock, 4096)

                try:
                    # Parse the received data into an SOS packet
                    packet_json = data.decode('utf-8')
                    packet = SOSPacket.from_json(packet_json)

                    # Skip packets sent by ourselves
                    if packet.sender_id == self.node_id:
                        continue

                    logger.info(f"UDP received packet from {addr}: {packet.packet_id[:8]}...")

                    # Put the packet into the message queue for processing
                    await self.message_queue.put(packet)
                    self.stats['packets_received'] += 1

                except json.JSONDecodeError:
                    logger.warning(f"Received invalid JSON from {addr}")
                    self.stats['receive_errors'] += 1
                except (ValueError, KeyError) as e:
                    logger.warning(f"Received invalid packet format from {addr}: {e}")
                    self.stats['receive_errors'] += 1
                except Exception as e:
                    logger.error(f"Error processing received packet from {addr}: {e}")
                    self.stats['receive_errors'] += 1

            except asyncio.CancelledError:
                # Handle task cancellation
                break
            except ConnectionError as e:
                logger.error(f"UDP connection error: {e}")
                self.stats['receive_errors'] += 1
                await asyncio.sleep(1)
            except Exception as e:
                logger.error(f"Error in UDP receive loop: {e}")
                self.stats['receive_errors'] += 1
                await asyncio.sleep(1)

        logger.info("UDP receive loop stopped")


class UDPTransport(BaseTransportManager):
    """Combined UDP transport with both sending and receiving capabilities."""

    def __init__(self, message_queue: asyncio.Queue, node_id: str):
        # Create the sender and receiver components
        sender = UDPSender(node_id)
        receiver = UDPReceiver(message_queue, node_id)

        # Initialize the transport manager with the components
        super().__init__(sender, receiver)

    async def start(self):
        """Start both UDP sender and receiver components."""
        await super().start()
        logger.info("UDP transport started (sender and receiver)")

    async def stop(self):
        """Stop both UDP sender and receiver components."""
        await super().stop()
        logger.info("UDP transport stopped (sender and receiver)")
