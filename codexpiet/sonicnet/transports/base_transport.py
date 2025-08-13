"""
Defines the base interfaces for all communication transports with separate sender and receiver components.
"""

import asyncio
from abc import ABC, abstractmethod
from typing import Optional, Dict, Any

from packet import SOSPacket

class BaseTransportSender(ABC):
    """Abstract base class for all communication transport senders."""

    def __init__(self, node_id: str):
        self.node_id = node_id
        self.running = False
        self.stats = {
            'packets_sent': 0,
            'send_errors': 0
        }

    @abstractmethod
    async def start(self):
        """Starts the transport sender."""
        pass

    @abstractmethod
    async def stop(self):
        """Stops the transport sender."""
        pass

    @abstractmethod
    async def send(self, packet: SOSPacket):
        """Sends an SOS packet."""
        pass

    def get_stats(self) -> Dict[str, Any]:
        """Get transport sender statistics."""
        return self.stats


class BaseTransportReceiver(ABC):
    """Abstract base class for all communication transport receivers."""

    def __init__(self, message_queue: asyncio.Queue, node_id: str):
        self.message_queue = message_queue
        self.node_id = node_id
        self.running = False
        self.stats = {
            'packets_received': 0,
            'receive_errors': 0
        }

    @abstractmethod
    async def start(self):
        """Starts the transport receiver."""
        pass

    @abstractmethod
    async def stop(self):
        """Stops the transport receiver."""
        pass

    def get_stats(self) -> Dict[str, Any]:
        """Get transport receiver statistics."""
        return self.stats


class BaseTransportManager:
    """Manages a specific transport's sender and receiver."""

    def __init__(self, sender: BaseTransportSender, receiver: BaseTransportReceiver):
        self.sender = sender
        self.receiver = receiver
        self.running = False

    async def start(self):
        """Start both sender and receiver components."""
        await self.sender.start()
        await self.receiver.start()
        self.running = True

    async def stop(self):
        """Stop both sender and receiver components."""
        await self.sender.stop()
        await self.receiver.stop()
        self.running = False

    async def send(self, packet: SOSPacket):
        """Send a packet using the transport sender."""
        if self.running:
            await self.sender.send(packet)

    def get_stats(self) -> Dict[str, Dict[str, Any]]:
        """Get combined statistics from sender and receiver."""
        return {
            'sender': self.sender.get_stats(),
            'receiver': self.receiver.get_stats()
        }
