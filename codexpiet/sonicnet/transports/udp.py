"""
UDP Multicast transport for Wi-Fi based mesh networking.
"""

import asyncio
import socket
import struct
import logging

from typing import TYPE_CHECKING

from .base import BaseTransport
from packet import SOSPacket
from config import UDP_MULTICAST_GROUP, UDP_PORT

if TYPE_CHECKING:
    from packet_manager import PacketManager

logger = logging.getLogger(__name__)

class UDPMeshTransport(BaseTransport):
    """Handles sending and receiving SOS packets over UDP multicast."""

    def __init__(self, message_queue: asyncio.Queue, packet_manager: 'PacketManager'):
        super().__init__(message_queue, packet_manager)
        self.sock = None
        self.running = False

        # Add statistics tracking
        self.stats = {
            'packets_sent': 0,
            'packets_received': 0,
            'send_errors': 0,
            'receive_errors': 0
        }

    async def start(self):
        """Initializes and starts the UDP multicast listener."""
        try:
            self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
            self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.sock.bind(('', UDP_PORT))

            mreq = struct.pack("4sl", socket.inet_aton(UDP_MULTICAST_GROUP), socket.INADDR_ANY)
            self.sock.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)
            self.sock.setblocking(False)

            self.running = True
            asyncio.create_task(self._receive_loop())
            logger.info(f"UDP transport started on {UDP_MULTICAST_GROUP}:{UDP_PORT}")
        except Exception as e:
            logger.error(f"Failed to start UDP transport: {e}")
            self.running = False

    async def stop(self):
        """Stops the UDP transport."""
        self.running = False
        if self.sock:
            self.sock.close()
        logger.info("UDP transport stopped")

    async def send(self, packet: SOSPacket):
        """Sends a packet via UDP multicast."""
        if not self.running or not self.sock:
            return
        try:
            self.sock.sendto(packet.to_json().encode('utf-8'), (UDP_MULTICAST_GROUP, UDP_PORT))
            self.stats['packets_sent'] += 1  # Increment packets sent
        except Exception as e:
            logger.error(f"Failed to send UDP message: {e}")
            self.stats['send_errors'] += 1  # Increment send error count

    async def _receive_loop(self):
        """Continuously listens for incoming UDP packets."""
        logger.info("UDP receive loop started")
        while self.running:
            try:
                loop = asyncio.get_event_loop()
                data, addr = await loop.sock_recvfrom(self.sock, 4096)
                try:
                    packet = SOSPacket.from_json(data.decode('utf-8'))
                    logger.info(f"UDP received packet from {addr}: {packet.packet_id[:8]}...")

                    # Put packet into the message queue for processing
                    await self.message_queue.put(packet)
                    self.stats['packets_received'] += 1

                except (ValueError, KeyError) as e:
                    logger.warning(f"Received invalid packet from {addr}: {e}")
                except Exception as e:
                    logger.error(f"Error processing received packet from {addr}: {e}")

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error in UDP receive loop: {e}")
                self.stats['receive_errors'] += 1
                await asyncio.sleep(1)

        logger.info("UDP receive loop stopped")

    def get_transport_stats(self):
        """Get UDP transport statistics."""
        return {
            **self.stats,
            'running': self.running,
            'multicast_group': UDP_MULTICAST_GROUP,
            'port': UDP_PORT
        }
