"""
Defines the SOSPacket data structure for the SonicWave network.
"""

import time
import hashlib
import json
import base64
from typing import Optional, List, Dict, Union
from enum import Enum
import uuid

class PacketType(Enum):
    SOS = "SOS"
    STATUS_UPDATE = "STATUS_UPDATE"
    ALL_CLEAR = "ALL_CLEAR"
    HEARTBEAT = "HEARTBEAT"
    ACK = "ACK"

class UrgencyLevel(Enum):
    CRITICAL = "CRITICAL"  # Life-threatening emergency
    HIGH = "HIGH"         # Urgent assistance needed
    MEDIUM = "MEDIUM"     # Non-urgent help needed
    LOW = "LOW"           # Information only

class GPSLocation:
    """GPS location data structure."""
    def __init__(self, latitude: float, longitude: float, altitude: Optional[float] = None, accuracy: Optional[float] = None):
        self.latitude = latitude
        self.longitude = longitude
        self.altitude = altitude
        self.accuracy = accuracy
        self.timestamp = time.time()

    def to_dict(self) -> dict:
        return {
            'latitude': self.latitude,
            'longitude': self.longitude,
            'altitude': self.altitude,
            'accuracy': self.accuracy,
            'timestamp': self.timestamp
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'GPSLocation':
        location = cls(data['latitude'], data['longitude'], data.get('altitude'), data.get('accuracy'))
        location.timestamp = data.get('timestamp', time.time())
        return location

class MediaAttachment:
    """Media attachment for packets (images, audio, etc.)."""
    def __init__(self, data: bytes, media_type: str, filename: Optional[str] = None):
        self.data = data
        self.media_type = media_type  # MIME type
        self.filename = filename or f"attachment_{uuid.uuid4().hex[:8]}"
        self.size = len(data)
        self.checksum = hashlib.md5(data).hexdigest()

    def to_dict(self) -> dict:
        return {
            'data': base64.b64encode(self.data).decode('utf-8'),
            'media_type': self.media_type,
            'filename': self.filename,
            'size': self.size,
            'checksum': self.checksum
        }

    @classmethod
    def from_dict(cls, data: dict) -> 'MediaAttachment':
        attachment = cls(
            base64.b64decode(data['data']),
            data['media_type'],
            data.get('filename')
        )
        return attachment

class SOSPacket:
    """Represents an emergency SOS packet with metadata for routing and identification."""

    def __init__(self, sender_id: str, message: str,
                 location: Optional[Union[str, GPSLocation]] = None,
                 urgency: Union[str, UrgencyLevel] = UrgencyLevel.HIGH,
                 packet_type: Union[str, PacketType] = PacketType.SOS,
                 thread_id: Optional[str] = None):
        self.sender_id = sender_id
        self.message = message
        self.packet_type = PacketType(packet_type) if isinstance(packet_type, str) else packet_type
        self.urgency = UrgencyLevel(urgency) if isinstance(urgency, str) else urgency
        self.timestamp = time.time()
        self.thread_id = thread_id or str(uuid.uuid4())

        # Location handling
        if isinstance(location, str):
            self.location_text = location
            self.gps_location = None
        elif isinstance(location, GPSLocation):
            self.location_text = f"{location.latitude:.6f}, {location.longitude:.6f}"
            self.gps_location = location
        else:
            self.location_text = "Unknown"
            self.gps_location = None

        self.packet_id = self._generate_packet_id()
        self.hop_count = 0
        self.relay_path = [sender_id]
        self.ttl = self._calculate_ttl()

        # Media and acknowledgment
        self.media_attachments: List[MediaAttachment] = []
        self.requires_ack = self.packet_type == PacketType.SOS
        self.ack_received = False
        self.ack_nodes: List[str] = []

        # Network metadata
        self.received_via = []  # Track which transports received this packet
        self.signal_strength = {}  # Track signal strength from different nodes
        self.battery_level = None  # Sender's battery level

    def _calculate_ttl(self) -> int:
        """Calculate TTL based on urgency level."""
        ttl_map = {
            UrgencyLevel.CRITICAL: 20,
            UrgencyLevel.HIGH: 15,
            UrgencyLevel.MEDIUM: 10,
            UrgencyLevel.LOW: 5
        }
        return ttl_map.get(self.urgency, 10)

    def _generate_packet_id(self) -> str:
        """Generates a unique ID for the packet based on its content and timestamp."""
        data = f"{self.sender_id}:{self.message}:{self.timestamp}:{self.thread_id}"
        return hashlib.sha256(data.encode()).hexdigest()[:16]

    def add_media_attachment(self, data: bytes, media_type: str, filename: Optional[str] = None):
        """Add a media attachment to the packet."""
        attachment = MediaAttachment(data, media_type, filename)
        self.media_attachments.append(attachment)

    def add_acknowledgment(self, node_id: str):
        """Add an acknowledgment from a node."""
        if node_id not in self.ack_nodes:
            self.ack_nodes.append(node_id)
        if self.requires_ack and len(self.ack_nodes) > 0:
            self.ack_received = True

    def can_relay(self) -> bool:
        """Check if packet can still be relayed based on TTL."""
        return self.ttl > 0 and self.hop_count < self.ttl

    def to_json(self) -> str:
        """Serializes the packet to a JSON string."""
        return json.dumps(self.to_dict())

    def to_dict(self) -> dict:
        """Converts the packet to a dictionary."""
        data = {
            'packet_id': self.packet_id,
            'sender_id': self.sender_id,
            'message': self.message,
            'packet_type': self.packet_type.value,
            'urgency': self.urgency.value,
            'location_text': self.location_text,
            'timestamp': self.timestamp,
            'hop_count': self.hop_count,
            'relay_path': self.relay_path,
            'ttl': self.ttl,
            'thread_id': self.thread_id,
            'requires_ack': self.requires_ack,
            'ack_received': self.ack_received,
            'ack_nodes': self.ack_nodes,
            'received_via': self.received_via,
            'signal_strength': self.signal_strength,
            'battery_level': self.battery_level,
            'media_attachments': [att.to_dict() for att in self.media_attachments]
        }

        if self.gps_location:
            data['gps_location'] = self.gps_location.to_dict()

        return data

    @classmethod
    def from_dict(cls, data: dict) -> 'SOSPacket':
        """Creates an SOSPacket from a dictionary."""
        # Handle GPS location
        gps_location = None
        if 'gps_location' in data:
            gps_location = GPSLocation.from_dict(data['gps_location'])

        packet = cls(
            sender_id=data['sender_id'],
            message=data['message'],
            location=gps_location or data.get('location_text', 'Unknown'),
            urgency=UrgencyLevel(data.get('urgency', 'HIGH')),
            packet_type=PacketType(data.get('packet_type', 'SOS')),
            thread_id=data.get('thread_id')
        )

        # Restore packet metadata
        packet.packet_id = data['packet_id']
        packet.timestamp = data['timestamp']
        packet.hop_count = data.get('hop_count', 0)
        packet.relay_path = data.get('relay_path', [data['sender_id']])
        packet.ttl = data.get('ttl', packet._calculate_ttl())
        packet.requires_ack = data.get('requires_ack', False)
        packet.ack_received = data.get('ack_received', False)
        packet.ack_nodes = data.get('ack_nodes', [])
        packet.received_via = data.get('received_via', [])
        packet.signal_strength = data.get('signal_strength', {})
        packet.battery_level = data.get('battery_level')

        # Restore media attachments
        for att_data in data.get('media_attachments', []):
            attachment = MediaAttachment.from_dict(att_data)
            packet.media_attachments.append(attachment)

        return packet

    @classmethod
    def from_json(cls, json_str: str) -> 'SOSPacket':
        """Creates an SOSPacket from a JSON string."""
        return cls.from_dict(json.loads(json_str))

    def increment_hop(self, node_id: str, transport_type: str = None, signal_strength: float = None):
        """Increments the hop count and adds the current node to the relay path."""
        self.hop_count += 1
        self.ttl -= 1
        if node_id not in self.relay_path:
            self.relay_path.append(node_id)

        if transport_type and transport_type not in self.received_via:
            self.received_via.append(transport_type)

        if signal_strength is not None:
            self.signal_strength[node_id] = signal_strength

    def create_ack_packet(self, ack_sender_id: str) -> 'SOSPacket':
        """Create an acknowledgment packet for this SOS."""
        ack_packet = SOSPacket(
            sender_id=ack_sender_id,
            message=f"ACK for {self.packet_id}",
            packet_type=PacketType.ACK,
            urgency=UrgencyLevel.LOW,
            thread_id=self.thread_id
        )
        ack_packet.requires_ack = False
        return ack_packet

    def get_priority_score(self) -> int:
        """Calculate priority score for packet processing order."""
        urgency_scores = {
            UrgencyLevel.CRITICAL: 1000,
            UrgencyLevel.HIGH: 100,
            UrgencyLevel.MEDIUM: 10,
            UrgencyLevel.LOW: 1
        }

        base_score = urgency_scores.get(self.urgency, 10)

        # Boost score for packets with fewer hops (fresher packets)
        freshness_bonus = max(0, 20 - self.hop_count)

        # Boost score for packets requiring acknowledgment
        ack_bonus = 50 if self.requires_ack and not self.ack_received else 0

        return base_score + freshness_bonus + ack_bonus

    def __str__(self) -> str:
        return f"SOSPacket({self.packet_id[:8]}, {self.urgency.value}, hops:{self.hop_count}, ttl:{self.ttl})"
