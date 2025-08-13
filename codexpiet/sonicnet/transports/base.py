"""
Defines the base interface for all communication transports.
"""

import asyncio
from abc import ABC, abstractmethod
from typing import Optional, TYPE_CHECKING

from packet import SOSPacket

if TYPE_CHECKING:
    from packet_manager import PacketManager

class BaseTransport(ABC):
    """Abstract base class for all communication transports."""

    def __init__(self, message_queue: asyncio.Queue, packet_manager: 'PacketManager'):
        self.message_queue = message_queue
        self.packet_manager = packet_manager

    @abstractmethod
    async def start(self):
        """Starts the transport."""
        pass

    @abstractmethod
    async def stop(self):
        """Stops the transport."""
        pass

    @abstractmethod
    async def send(self, packet: SOSPacket):
        """Sends an SOS packet."""
        pass
