#!/usr/bin/env python3
"""
Comprehensive test for SonicNet transports.
Tests all transport mechanisms (UDP, BLE, GGWave) for proper sending and receiving.
"""

import asyncio
import logging
import time
import uuid
import sys
import argparse
from typing import List, Dict, Any

from packet import SOSPacket, GPSLocation
from transports.base_transport import BaseTransportManager
from transports.udp_transport import UDPTransport
from transports.ble_transport import BLETransport
from transports.ggwave_transport import GGWaveTransport

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class TransportTester:
    """Tests all SonicNet transport mechanisms."""

    def __init__(self, transports_to_test: List[str] = None):
        """
        Initialize transport tester.

        Args:
            transports_to_test: List of transports to test (udp, ble, ggwave)
                                If None, test all available transports
        """
        # Generate a unique node ID for this test instance
        self.node_id = f"test_{uuid.uuid4().hex[:8]}"

        # Create a message queue for receiving packets
        self.message_queue = asyncio.Queue()

        # Track running state
        self.running = False

        # Store transports by name
        self.transports: Dict[str, BaseTransportManager] = {}

        # Track received messages by transport type
        self.received_messages: Dict[str, List[SOSPacket]] = {
            'udp': [],
            'ble': [],
            'ggwave': []
        }

        # Track sent messages by transport type
        self.sent_messages: Dict[str, List[SOSPacket]] = {
            'udp': [],
            'ble': [],
            'ggwave': []
        }

        # Determine which transports to test
        self.transports_to_test = transports_to_test or ['udp', 'ble', 'ggwave']
        logger.info(f"Transport tester initialized with node ID: {self.node_id}")
        logger.info(f"Testing transports: {', '.join(self.transports_to_test)}")

    async def setup(self):
        """Set up all transport mechanisms for testing."""
        # Set Windows-specific event loop policy if needed
        if sys.platform == 'win32':
            try:
                loop = asyncio.get_event_loop()
                if not isinstance(loop, asyncio.ProactorEventLoop):
                    logger.info("Setting Windows ProactorEventLoop for better compatibility")
                    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
            except Exception as e:
                logger.warning(f"Could not set ProactorEventLoop: {e}")

        # Initialize requested transports
        if 'udp' in self.transports_to_test:
            try:
                self.transports['udp'] = UDPTransport(self.message_queue, self.node_id)
                logger.info("UDP transport initialized")
            except Exception as e:
                logger.error(f"Failed to initialize UDP transport: {e}")

        if 'ble' in self.transports_to_test:
            try:
                self.transports['ble'] = BLETransport(self.message_queue, self.node_id)
                logger.info("BLE transport initialized")
            except Exception as e:
                logger.error(f"Failed to initialize BLE transport: {e}")

        if 'ggwave' in self.transports_to_test:
            try:
                self.transports['ggwave'] = GGWaveTransport(self.message_queue, self.node_id)
                logger.info("GGWave transport initialized")
            except Exception as e:
                logger.error(f"Failed to initialize GGWave transport: {e}")

        # Start message processing
        self.running = True
        asyncio.create_task(self._process_received_messages())

        # Start all transports
        for name, transport in self.transports.items():
            try:
                await transport.start()
                logger.info(f"Started {name} transport")
            except Exception as e:
                logger.error(f"Failed to start {name} transport: {e}")

    async def shutdown(self):
        """Shut down all transport mechanisms."""
        self.running = False

        # Stop all transports
        for name, transport in self.transports.items():
            try:
                await transport.stop()
                logger.info(f"Stopped {name} transport")
            except Exception as e:
                logger.error(f"Error stopping {name} transport: {e}")

    async def _process_received_messages(self):
        """Process incoming messages from all transports."""
        logger.info("Starting message processor")

        while self.running:
            try:
                # Get message with timeout to allow checking running state
                try:
                    packet = await asyncio.wait_for(self.message_queue.get(), timeout=1.0)
                except asyncio.TimeoutError:
                    continue

                # Skip packets from self
                if packet.sender_id == self.node_id:
                    continue

                # Determine which transport received this message
                # This is a best guess based on metadata or transport-specific attributes
                if hasattr(packet, '_transport_type') and packet._transport_type in self.received_messages:
                    self.received_messages[packet._transport_type].append(packet)
                    logger.info(f"Received message via {packet._transport_type}: {packet.message}")
                else:
                    # If transport type not specified, try to determine from packet properties
                    if packet.message.startswith("UDP:"):
                        self.received_messages['udp'].append(packet)
                        logger.info(f"Received UDP message: {packet.message}")
                    elif packet.message.startswith("BLE:"):
                        self.received_messages['ble'].append(packet)
                        logger.info(f"Received BLE message: {packet.message}")
                    elif packet.message.startswith("GGW:"):
                        self.received_messages['ggwave'].append(packet)
                        logger.info(f"Received GGWave message: {packet.message}")
                    else:
                        # Unknown transport, log it anyway
                        logger.info(f"Received message from unknown transport: {packet.message}")

                # Mark task as done
                self.message_queue.task_done()

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Error processing message: {e}")
                await asyncio.sleep(1)

        logger.info("Message processor stopped")

    async def send_test_message(self, transport_name: str):
        """
        Send a test message via the specified transport.

        Args:
            transport_name: Name of the transport to use ('udp', 'ble', or 'ggwave')

        Returns:
            The sent packet or None if sending failed
        """
        if transport_name not in self.transports:
            logger.error(f"Transport {transport_name} not available")
            return None

        transport = self.transports[transport_name]

        try:
            # Create a test packet
            timestamp = int(time.time())
            message = f"{transport_name.upper()}: Test message {timestamp}"
            packet = SOSPacket(
                message=message,
                sender_id=self.node_id
            )

            # Add transport type as metadata
            packet._transport_type = transport_name

            # Send the packet
            await transport.send(packet)

            # Add to sent messages
            self.sent_messages[transport_name].append(packet)

            logger.info(f"Sent test message via {transport_name}: {message}")
            return packet

        except Exception as e:
            logger.error(f"Error sending test message via {transport_name}: {e}")
            return None

    def get_stats(self):
        """Get statistics on sent and received messages."""
        stats = {
            'sent': {t: len(msgs) for t, msgs in self.sent_messages.items()},
            'received': {t: len(msgs) for t, msgs in self.received_messages.items()},
            'transport_stats': {}
        }

        # Add transport-specific stats
        for name, transport in self.transports.items():
            if hasattr(transport, 'get_stats'):
                stats['transport_stats'][name] = transport.get_stats()

        return stats

async def run_transport_test(args):
    """Run the transport test."""
    # Create tester with specified transports
    tester = TransportTester(args.transports)

    try:
        # Set up transports
        await tester.setup()

        # Send test messages
        for transport in tester.transports:
            for _ in range(args.count):
                await tester.send_test_message(transport)
                # Wait between sends
                await asyncio.sleep(1)

        # Wait for responses
        logger.info(f"Waiting {args.wait} seconds for responses...")
        await asyncio.sleep(args.wait)

        # Print results
        stats = tester.get_stats()
        logger.info("Transport Test Results:")
        logger.info(f"Sent messages: {stats['sent']}")
        logger.info(f"Received messages: {stats['received']}")

        # Print detailed transport stats
        for transport_name, transport_stats in stats['transport_stats'].items():
            logger.info(f"\n{transport_name.upper()} Transport Statistics:")
            for component, comp_stats in transport_stats.items():
                logger.info(f"  {component}: {comp_stats}")

    finally:
        # Shutdown all transports
        await tester.shutdown()

def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Test SonicNet transport mechanisms.")
    parser.add_argument("--transports", nargs="+", choices=["udp", "ble", "ggwave"],
                        default=["udp", "ble", "ggwave"],
                        help="Transports to test")
    parser.add_argument("--count", type=int, default=3,
                        help="Number of test messages to send per transport")
    parser.add_argument("--wait", type=int, default=10,
                        help="Time to wait for responses (in seconds)")

    args = parser.parse_args()

    # Run the transport test
    asyncio.run(run_transport_test(args))

if __name__ == "__main__":
    main()
