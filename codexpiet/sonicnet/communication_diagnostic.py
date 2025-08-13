#!/usr/bin/env python3
"""
SonicWave Communication Diagnostic Tool
Diagnoses why clients can't discover each other and provides real-time debugging.
"""

import asyncio
import logging
import sys
import time
import json
from datetime import datetime

# Add current directory to path
import os
sys.path.insert(0, os.getcwd())

from client import SonicWaveClient
from packet import SOSPacket

# Setup detailed logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class CommunicationDiagnostic:
    """Comprehensive diagnostic tool for SonicWave communication issues."""

    def __init__(self, device_name="DiagnosticDevice"):
        self.device_name = device_name
        self.client = None
        self.running = False
        self.received_packets = []
        self.sent_packets = []

    async def run_diagnostics(self):
        """Run comprehensive communication diagnostics."""
        print(f"\n🔍 SonicWave Communication Diagnostics")
        print(f"📱 Device: {self.device_name}")
        print(f"⏰ Started: {datetime.now().strftime('%H:%M:%S')}")
        print("=" * 60)

        try:
            # Phase 1: Basic initialization
            await self._phase_1_initialization()

            # Phase 2: Transport testing
            await self._phase_2_transport_testing()

            # Phase 3: Sending test
            await self._phase_3_sending_test()

            # Phase 4: Receiving test
            await self._phase_4_receiving_test()

            # Phase 5: Live monitoring
            await self._phase_5_live_monitoring()

        except KeyboardInterrupt:
            print(f"\n⚡ Diagnostics interrupted by user")
        except Exception as e:
            print(f"\n💥 Diagnostic error: {e}")
            import traceback
            traceback.print_exc()
        finally:
            await self._cleanup()

    async def _phase_1_initialization(self):
        """Phase 1: Initialize client and check basic setup."""
        print(f"\n📋 PHASE 1: Client Initialization")
        print("-" * 40)

        self.client = SonicWaveClient()
        print(f"✅ Client created: {self.client.node_id}")

        # Start background message monitoring
        asyncio.create_task(self._monitor_messages())

        await self.client.start()
        print(f"✅ Client started successfully")

        self.running = True
        await asyncio.sleep(2)

    async def _phase_2_transport_testing(self):
        """Phase 2: Test individual transport capabilities."""
        print(f"\n📋 PHASE 2: Transport Testing")
        print("-" * 40)

        # Test each transport individually
        for transport in self.client.transports:
            transport_name = type(transport).__name__
            print(f"\n🔧 Testing {transport_name}:")

            try:
                # Check if transport is running
                if hasattr(transport, 'running'):
                    print(f"   Running: {'✅ Yes' if transport.running else '❌ No'}")

                # Get transport stats
                if hasattr(transport, 'get_transport_stats'):
                    stats = transport.get_transport_stats()
                    print(f"   Stats: {json.dumps(stats, indent=6)}")

                # Test sending capability
                test_packet = SOSPacket(
                    sender_id=self.client.node_id,
                    message=f"Transport test from {transport_name}",
                    urgency="LOW"
                )

                print(f"   🚀 Attempting to send test packet...")
                await transport.send(test_packet)
                print(f"   ✅ Send successful")

            except Exception as e:
                print(f"   ❌ Error: {e}")

    async def _phase_3_sending_test(self):
        """Phase 3: Test sending packets through the client."""
        print(f"\n📋 PHASE 3: Client Sending Test")
        print("-" * 40)

        # Send test messages
        test_messages = [
            "Diagnostic ping #1 - Testing basic sending",
            "Diagnostic ping #2 - Testing discovery",
            "Diagnostic ping #3 - Testing reliability"
        ]

        for i, message in enumerate(test_messages, 1):
            print(f"\n📤 Sending test message {i}:")
            print(f"   Message: {message}")

            packet_id = await self.client.send_sos(message=message, urgency="LOW")

            if packet_id:
                print(f"   ✅ Sent successfully: {packet_id[:8]}...")
                self.sent_packets.append({
                    'packet_id': packet_id,
                    'message': message,
                    'time': datetime.now()
                })
            else:
                print(f"   ❌ Send failed")

            await asyncio.sleep(2)

        # Show sending stats
        stats = self.client.get_stats()
        print(f"\n📊 Sending Statistics:")
        print(f"   Messages sent by client: {stats['client']['messages_sent']}")
        print(f"   Queue size: {stats['queue_size']}")
        print(f"   Active transports: {stats['client']['transports_active']}")

    async def _phase_4_receiving_test(self):
        """Phase 4: Test receiving capabilities."""
        print(f"\n📋 PHASE 4: Receiving Test")
        print("-" * 40)

        print(f"🔍 Checking message queue and processing:")

        # Check queue status
        queue_size = self.client.message_queue.qsize()
        print(f"   Current queue size: {queue_size}")

        # Check if message processing loop is running
        print(f"   Client running status: {'✅ Running' if self.client.running else '❌ Stopped'}")

        # Check for any messages received so far
        print(f"   Messages received so far: {len(self.received_packets)}")

        if self.received_packets:
            print(f"   📨 Recent received messages:")
            for msg in self.received_packets[-3:]:
                print(f"      - From {msg['sender_id'][:8]}...: {msg['message'][:50]}...")

        # Wait and monitor for incoming messages
        print(f"\n⏳ Monitoring for incoming messages for 10 seconds...")
        for i in range(10):
            await asyncio.sleep(1)
            new_count = len(self.received_packets)
            queue_size = self.client.message_queue.qsize()
            print(f"   [{i+1:2d}s] Received: {new_count}, Queue: {queue_size}")

        # Final receiving stats
        stats = self.client.get_stats()
        print(f"\n📊 Receiving Statistics:")
        print(f"   Messages received by client: {stats['client']['messages_received']}")
        print(f"   Our messages captured: {len(self.received_packets)}")

    async def _phase_5_live_monitoring(self):
        """Phase 5: Live monitoring and interaction."""
        print(f"\n📋 PHASE 5: Live Monitoring")
        print("-" * 40)

        print(f"🔄 Starting live monitoring...")
        print(f"💡 Run another instance to test communication!")
        print(f"⚡ Press Ctrl+C to stop")

        last_stats_time = 0

        while self.running:
            try:
                current_time = time.time()

                # Show periodic status
                if current_time - last_stats_time > 5:  # Every 5 seconds
                    last_stats_time = current_time

                    stats = self.client.get_stats()
                    queue_size = self.client.message_queue.qsize()

                    print(f"\n⏰ [{datetime.now().strftime('%H:%M:%S')}] Status Update:")
                    print(f"   📤 Sent: {len(self.sent_packets)} | 📥 Received: {len(self.received_packets)}")
                    print(f"   📊 Queue: {queue_size} | 🔧 Transports: {stats['client']['transports_active']}")

                    # Show transport-specific stats
                    for transport_name, transport_stats in stats['transports'].items():
                        if isinstance(transport_stats, dict) and 'packets_sent' in transport_stats:
                            sent = transport_stats.get('packets_sent', 0)
                            received = transport_stats.get('packets_received', 0)
                            running = transport_stats.get('running', False)
                            status = '🟢' if running else '🔴'
                            print(f"   {status} {transport_name}: S={sent}, R={received}")

                # Send periodic discovery pings
                if len(self.sent_packets) % 3 == 0:  # Every few iterations
                    discovery_msg = f"Live discovery ping from {self.device_name} at {datetime.now().strftime('%H:%M:%S')}"
                    packet_id = await self.client.send_sos(message=discovery_msg, urgency="LOW")
                    if packet_id:
                        self.sent_packets.append({
                            'packet_id': packet_id,
                            'message': discovery_msg,
                            'time': datetime.now()
                        })
                        print(f"   📡 Discovery ping sent: {packet_id[:8]}...")

                await asyncio.sleep(2)

            except KeyboardInterrupt:
                break
            except Exception as e:
                print(f"   ❌ Error in live monitoring: {e}")
                await asyncio.sleep(1)

    async def _monitor_messages(self):
        """Background task to monitor incoming messages."""
        while self.running:
            try:
                # Check for new messages in the queue
                if not self.client.message_queue.empty():
                    try:
                        while not self.client.message_queue.empty():
                            packet = await asyncio.wait_for(
                                self.client.message_queue.get(),
                                timeout=0.1
                            )
                            await self._handle_received_packet(packet)
                    except asyncio.TimeoutError:
                        pass

                await asyncio.sleep(0.2)  # Check every 200ms

            except Exception as e:
                logger.error(f"Error in message monitor: {e}")
                await asyncio.sleep(1)

    async def _handle_received_packet(self, packet: SOSPacket):
        """Handle a received packet."""
        try:
            # Track all packets (including our own for debugging)
            self.received_packets.append({
                'sender_id': packet.sender_id,
                'message': packet.message,
                'urgency': packet.urgency,
                'packet_id': packet.packet_id,
                'time': datetime.now(),
                'is_own': packet.sender_id == self.client.node_id
            })

            # Show real-time notification
            time_str = datetime.now().strftime('%H:%M:%S')
            sender_short = packet.sender_id[:8]

            if packet.sender_id == self.client.node_id:
                print(f"\n📨 [{time_str}] 🔄 OWN MESSAGE: {sender_short}...: {packet.message[:40]}...")
            else:
                print(f"\n📨 [{time_str}] 🎉 EXTERNAL MESSAGE: {sender_short}...: {packet.message[:40]}...")
                print(f"   🎯 SUCCESS! Device discovery working!")

        except Exception as e:
            logger.error(f"Error handling received packet: {e}")

    async def _cleanup(self):
        """Clean up resources."""
        print(f"\n🧹 Cleaning up...")
        self.running = False

        if self.client:
            try:
                await self.client.stop()
                print(f"✅ Client stopped successfully")
            except Exception as e:
                print(f"❌ Error stopping client: {e}")

        # Final summary
        print(f"\n📊 FINAL DIAGNOSTIC SUMMARY")
        print("=" * 50)
        print(f"📤 Total messages sent: {len(self.sent_packets)}")
        print(f"📥 Total messages received: {len(self.received_packets)}")

        external_messages = [msg for msg in self.received_packets if not msg['is_own']]
        print(f"🎯 External messages received: {len(external_messages)}")

        if external_messages:
            print(f"🎉 SUCCESS: Device communication is working!")
            print(f"📋 External messages:")
            for msg in external_messages[-3:]:
                print(f"   - From {msg['sender_id'][:8]}...: {msg['message'][:50]}...")
        else:
            print(f"⚠️  No external messages received")
            print(f"💡 Possible issues:")
            print(f"   - No other devices running")
            print(f"   - Network connectivity problems")
            print(f"   - Transport configuration issues")
            print(f"   - Firewall blocking UDP multicast")

async def main():
    """Main entry point."""
    import argparse

    parser = argparse.ArgumentParser(description='SonicWave Communication Diagnostics')
    parser.add_argument('--device', '-d',
                       help='Device name for identification',
                       default=f"Diagnostic-{datetime.now().strftime('%H%M%S')}")

    args = parser.parse_args()

    diagnostic = CommunicationDiagnostic(device_name=args.device)
    await diagnostic.run_diagnostics()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print(f"\n⚡ Diagnostics stopped by user")
    except Exception as e:
        print(f"💥 Fatal diagnostic error: {e}")
        import traceback
        traceback.print_exc()
