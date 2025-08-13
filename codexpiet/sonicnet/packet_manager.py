"""
Manages the caching and lifecycle of SOS packets with enhanced features.
"""

import time
import asyncio
import heapq
from typing import Dict, Optional, List, Set
from collections import defaultdict
import logging

from packet import SOSPacket, PacketType, UrgencyLevel
from config import PACKET_CACHE_LIMIT, PACKET_EXPIRATION

logger = logging.getLogger(__name__)

class PacketPriorityQueue:
    """Priority queue for packet processing."""
    def __init__(self):
        self._queue = []
        self._index = 0

    def put(self, packet: SOSPacket):
        # Use negative priority for max-heap behavior (higher priority first)
        priority = -packet.get_priority_score()
        heapq.heappush(self._queue, (priority, self._index, packet))
        self._index += 1

    def get(self) -> Optional[SOSPacket]:
        if self._queue:
            _, _, packet = heapq.heappop(self._queue)
            return packet
        return None

    def empty(self) -> bool:
        return len(self._queue) == 0

class NetworkTopology:
    """Tracks network topology and node relationships."""
    def __init__(self):
        self.neighbors: Dict[str, Set[str]] = defaultdict(set)
        self.node_last_seen: Dict[str, float] = {}
        self.node_reliability: Dict[str, float] = defaultdict(lambda: 1.0)
        self.transport_availability: Dict[str, Set[str]] = defaultdict(set)

    def add_neighbor(self, node_id: str, transport: str):
        """Add a neighbor discovered via a transport."""
        self.neighbors[node_id].add(transport)
        self.node_last_seen[node_id] = time.time()
        self.transport_availability[transport].add(node_id)

    def remove_neighbor(self, node_id: str, transport: str = None):
        """Remove a neighbor."""
        if transport:
            self.neighbors[node_id].discard(transport)
            self.transport_availability[transport].discard(node_id)
        else:
            # Remove from all transports
            for t in list(self.neighbors[node_id]):
                self.neighbors[node_id].discard(t)
                self.transport_availability[t].discard(node_id)

    def get_active_neighbors(self, max_age: float = 300) -> Set[str]:
        """Get neighbors seen within max_age seconds."""
        current_time = time.time()
        active = set()
        for node_id, last_seen in self.node_last_seen.items():
            if current_time - last_seen <= max_age:
                active.add(node_id)
        return active

    def update_reliability(self, node_id: str, success: bool):
        """Update node reliability based on successful packet delivery."""
        current = self.node_reliability[node_id]
        if success:
            self.node_reliability[node_id] = min(1.0, current + 0.1)
        else:
            self.node_reliability[node_id] = max(0.1, current - 0.1)

class PacketManager:
    """Enhanced packet manager with intelligent routing and caching."""

    def __init__(self):
        self.packet_cache: Dict[str, SOSPacket] = {}
        self.seen_packet_ids: Set[str] = set()
        self.thread_packets: Dict[str, List[str]] = defaultdict(list)
        self.pending_acks: Dict[str, SOSPacket] = {}

        # Priority queues for different packet types
        self.priority_queue = PacketPriorityQueue()
        self.outbound_queue = PacketPriorityQueue()

        # Network topology tracking
        self.topology = NetworkTopology()

        # Anti-flooding measures
        self.node_packet_count: Dict[str, int] = defaultdict(int)
        self.node_last_packet: Dict[str, float] = {}
        self.rate_limit_violations: Dict[str, int] = defaultdict(int)

        # Statistics
        self.stats = {
            'packets_received': 0,
            'packets_sent': 0,
            'packets_relayed': 0,
            'duplicates_filtered': 0,
            'rate_limited': 0,
            'acks_sent': 0,
            'acks_received': 0
        }

    def add_packet(self, packet: SOSPacket, from_transport: str = None,
                   signal_strength: float = None) -> bool:
        """
        Adds a packet to the cache if it's new. Returns True if added, False otherwise.
        Enhanced with anti-flooding and intelligent routing.
        """
        # Check for duplicates
        if packet.packet_id in self.seen_packet_ids:
            self.stats['duplicates_filtered'] += 1
            logger.debug(f"Duplicate packet filtered: {packet.packet_id}")
            return False

        # Anti-flooding: Check rate limits
        if not self._check_rate_limit(packet.sender_id):
            self.stats['rate_limited'] += 1
            logger.warning(f"Rate limit exceeded for node {packet.sender_id}")
            return False

        # Check TTL
        if not packet.can_relay():
            logger.debug(f"Packet {packet.packet_id} TTL expired, not relaying")
            return False

        # Add transport and signal strength info
        if from_transport:
            packet.received_via.append(from_transport)
            self.topology.add_neighbor(packet.sender_id, from_transport)

        if signal_strength is not None:
            packet.signal_strength[packet.sender_id] = signal_strength

        # Add to cache and seen set
        self.packet_cache[packet.packet_id] = packet
        self.seen_packet_ids.add(packet.packet_id)
        self.thread_packets[packet.thread_id].append(packet.packet_id)

        # Update statistics
        self.stats['packets_received'] += 1

        # Handle different packet types
        if packet.packet_type == PacketType.ACK:
            self._handle_ack_packet(packet)
        elif packet.requires_ack:
            self.pending_acks[packet.packet_id] = packet

        # Add to priority queue for processing
        self.priority_queue.put(packet)

        # Enforce cache limit
        if len(self.packet_cache) > PACKET_CACHE_LIMIT:
            self._prune_cache()

        logger.info(f"Added packet {packet.packet_id} from {packet.sender_id} "
                   f"(type: {packet.packet_type.value}, urgency: {packet.urgency.value})")
        return True

    def _check_rate_limit(self, node_id: str, max_packets_per_minute: int = 10) -> bool:
        """Check if node is within rate limits."""
        current_time = time.time()

        # Reset counter if more than a minute has passed
        if node_id in self.node_last_packet:
            if current_time - self.node_last_packet[node_id] > 60:
                self.node_packet_count[node_id] = 0

        # Update counters
        self.node_packet_count[node_id] += 1
        self.node_last_packet[node_id] = current_time

        # Check limit
        if self.node_packet_count[node_id] > max_packets_per_minute:
            self.rate_limit_violations[node_id] += 1
            return False

        return True

    def _handle_ack_packet(self, ack_packet: SOSPacket):
        """Handle acknowledgment packets."""
        # Extract original packet ID from ACK message
        if "ACK for " in ack_packet.message:
            original_packet_id = ack_packet.message.replace("ACK for ", "")
            if original_packet_id in self.pending_acks:
                original_packet = self.pending_acks[original_packet_id]
                original_packet.add_acknowledgment(ack_packet.sender_id)
                self.stats['acks_received'] += 1
                logger.info(f"Received ACK for packet {original_packet_id}")

    def should_relay_packet(self, packet: SOSPacket, node_id: str) -> bool:
        """
        Intelligent decision on whether to relay a packet based on various factors.
        """
        # Don't relay our own packets
        if packet.sender_id == node_id:
            return False

        # Don't relay if we're already in the relay path (loop prevention)
        if node_id in packet.relay_path:
            return False

        # Don't relay if TTL expired
        if not packet.can_relay():
            return False

        # Always relay critical packets
        if packet.urgency == UrgencyLevel.CRITICAL:
            return True

        # For other packets, consider network density and reliability
        active_neighbors = self.topology.get_active_neighbors()
        if len(active_neighbors) < 3:  # Sparse network, relay more aggressively
            return True

        # In dense networks, be more selective
        if packet.hop_count > 5 and packet.urgency == UrgencyLevel.LOW:
            return False

        return True

    def get_next_packet_to_process(self) -> Optional[SOSPacket]:
        """Get the next highest priority packet for processing."""
        return self.priority_queue.get()

    def get_packets_for_relay(self, max_count: int = 5) -> List[SOSPacket]:
        """Get packets that should be relayed, prioritized by urgency."""
        relay_packets = []
        for packet in sorted(self.packet_cache.values(),
                           key=lambda p: p.get_priority_score(), reverse=True):
            if len(relay_packets) >= max_count:
                break
            if packet.can_relay():
                relay_packets.append(packet)
        return relay_packets

    def create_ack_for_packet(self, packet: SOSPacket, ack_sender_id: str) -> SOSPacket:
        """Create and track an acknowledgment packet."""
        ack_packet = packet.create_ack_packet(ack_sender_id)
        self.stats['acks_sent'] += 1
        return ack_packet

    def get_packet(self, packet_id: str) -> Optional[SOSPacket]:
        """Retrieves a packet from the cache."""
        return self.packet_cache.get(packet_id)

    def get_thread_packets(self, thread_id: str) -> List[SOSPacket]:
        """Get all packets in a conversation thread."""
        packet_ids = self.thread_packets.get(thread_id, [])
        return [self.packet_cache[pid] for pid in packet_ids if pid in self.packet_cache]

    def get_all_packets(self) -> List[SOSPacket]:
        """Returns all packets currently in the cache."""
        return list(self.packet_cache.values())

    def get_pending_acks(self) -> List[SOSPacket]:
        """Get packets that are waiting for acknowledgment."""
        return list(self.pending_acks.values())

    def remove_packet(self, packet_id: str):
        """Removes a packet from the cache, e.g., after successful upload."""
        if packet_id in self.packet_cache:
            packet = self.packet_cache[packet_id]
            del self.packet_cache[packet_id]

            # Clean up thread tracking
            if packet.thread_id in self.thread_packets:
                if packet_id in self.thread_packets[packet.thread_id]:
                    self.thread_packets[packet.thread_id].remove(packet_id)

            # Clean up pending ACKs
            if packet_id in self.pending_acks:
                del self.pending_acks[packet_id]

    def update_topology(self, node_id: str, transport: str, active: bool = True):
        """Update network topology information."""
        if active:
            self.topology.add_neighbor(node_id, transport)
        else:
            self.topology.remove_neighbor(node_id, transport)

    def get_network_stats(self) -> Dict:
        """Get comprehensive network statistics."""
        active_neighbors = self.topology.get_active_neighbors()

        return {
            **self.stats,
            'cache_size': len(self.packet_cache),
            'active_neighbors': len(active_neighbors),
            'pending_acks': len(self.pending_acks),
            'thread_count': len(self.thread_packets),
            'rate_violations': sum(self.rate_limit_violations.values()),
            'avg_node_reliability': sum(self.topology.node_reliability.values()) /
                                  max(1, len(self.topology.node_reliability))
        }

    def _prune_cache(self):
        """Enhanced cache pruning with priority-based removal."""
        current_time = time.time()

        # First, remove expired packets
        expired_ids = [
            pid for pid, p in self.packet_cache.items()
            if current_time - p.timestamp > PACKET_EXPIRATION
        ]

        for pid in expired_ids:
            self.remove_packet(pid)
            self.seen_packet_ids.discard(pid)

        # If still over limit, remove lowest priority packets
        while len(self.packet_cache) > PACKET_CACHE_LIMIT:
            # Find packet with lowest priority score
            lowest_priority_id = min(
                self.packet_cache.keys(),
                key=lambda pid: self.packet_cache[pid].get_priority_score()
            )
            self.remove_packet(lowest_priority_id)
            self.seen_packet_ids.discard(lowest_priority_id)

    def cleanup_old_data(self, max_age: float = 3600):
        """Clean up old tracking data to prevent memory leaks."""
        current_time = time.time()

        # Clean up node tracking data
        old_nodes = [
            node_id for node_id, last_seen in self.topology.node_last_seen.items()
            if current_time - last_seen > max_age
        ]

        for node_id in old_nodes:
            if node_id in self.topology.node_last_seen:
                del self.topology.node_last_seen[node_id]
            if node_id in self.topology.node_reliability:
                del self.topology.node_reliability[node_id]
            if node_id in self.node_packet_count:
                del self.node_packet_count[node_id]
            if node_id in self.node_last_packet:
                del self.node_last_packet[node_id]
