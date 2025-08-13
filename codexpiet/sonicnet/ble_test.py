#!/usr/bin/env python3
"""
BLE Transport Test for Two Laptops
Tests the redesigned BLE transport with GATT server/client architecture.

This test can be run on two laptops to verify:
- BLE device discovery between laptops
- GATT server setup and advertising
- GATT client connection and data transfer
- Bidirectional packet exchange
- Chunked data transmission for large packets

Usage:
  Laptop 1: python ble_test.py --device Laptop-A
  Laptop 2: python ble_test.py --device Laptop-B
"""

import asyncio
import logging
import sys
import argparse
import time
import json
from datetime import datetime
from typing import Dict, List, Optional

# Add current directory to path
import os
sys.path.insert(0, os.getcwd())

from transports.ble import BLEMeshTransport, BLE_AVAILABLE
from packet import SOSPacket
from packet_manager import PacketManager

# Setup detailed logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class BLETransportTest:
    """Comprehensive BLE transport test for two laptops."""

    def __init__(self, device_name: str = "BLE-Test-Device"):
        self.device_name = device_name
        self.transport = None
        self.message_queue = asyncio.Queue()
        self.packet_manager = PacketManager()
        self.running = False
        self.received_packets = []
        self.sent_packets = []
        self.test_results = {}

    async def run_test(self):
        """Run comprehensive BLE transport test."""
        print(f"\n🔵 BLE Transport Test for Two Laptops")
        print(f"📱 Device: {self.device_name}")
        print(f"⏰ Started: {datetime.now().strftime('%H:%M:%S')}")
        print("=" * 60)

        # Check BLE availability first
        if not BLE_AVAILABLE:
            print(f"❌ BLE not available - bleak library not installed")
            print(f"💡 Install with: pip install bleak")
            return False

        try:
            self.running = True

            # Phase 1: Initialize BLE transport
            await self._phase_1_initialization()

            # Phase 2: Test GATT server setup
            await self._phase_2_server_setup()

            # Phase 3: Test device discovery
            await self._phase_3_device_discovery()

            # Phase 4: Test packet sending
            await self._phase_4_packet_sending()

            # Phase 5: Test packet receiving
            await self._phase_5_packet_receiving()

            # Phase 6: Bidirectional communication test
            await self._phase_6_bidirectional_test()

            # Phase 7: Stress test with multiple packets
            await self._phase_7_stress_test()

            # Final results
            await self._show_final_results()

        except KeyboardInterrupt:
            print(f"\n⚡ Test interrupted by user")
        except Exception as e:
            print(f"\n💥 Test error: {e}")
            import traceback
            traceback.print_exc()
        finally:
            await self._cleanup()

    async def _phase_1_initialization(self):
        """Phase 1: Initialize BLE transport."""
        print(f"\n📋 PHASE 1: BLE Transport Initialization")
        print("-" * 50)

        try:
            # Create BLE transport
            self.transport = BLEMeshTransport(self.message_queue, self.packet_manager)
            print(f"✅ BLE transport created successfully")

            # Start background message monitoring
            asyncio.create_task(self._monitor_messages())

            # Start the transport
            await self.transport.start()
            print(f"✅ BLE transport started")

            # Wait for initialization
            await asyncio.sleep(3)

            # Check initial stats
            stats = self.transport.get_transport_stats()
            print(f"\n📊 Initial Stats:")
            print(f"   BLE Available: {'✅' if stats['ble_available'] else '❌'}")
            print(f"   Transport Running: {'✅' if stats['running'] else '❌'}")
            print(f"   Active Peers: {stats['active_peers']}")
            print(f"   Connected Devices: {stats['connected_devices']}")

            self.test_results['initialization'] = 'SUCCESS' if stats['running'] else 'FAILED'

        except Exception as e:
            print(f"❌ Initialization failed: {e}")
            self.test_results['initialization'] = 'FAILED'
            raise

    async def _phase_2_server_setup(self):
        """Phase 2: Test GATT server setup and advertising."""
        print(f"\n📋 PHASE 2: GATT Server Setup")
        print("-" * 50)

        try:
            print(f"🔍 Checking GATT server status...")

            # Wait for server to start advertising
            await asyncio.sleep(5)

            stats = self.transport.get_transport_stats()
            server_running = stats.get('server_running', False)

            if server_running:
                print(f"✅ GATT server is running and advertising")
                print(f"📡 Service UUID: 6e400001-b5a3-f393-e0a9-e50e24dcca9e")
                print(f"📝 RX Characteristic: 6e400002-b5a3-f393-e0a9-e50e24dcca9e")
                print(f"📤 TX Characteristic: 6e400003-b5a3-f393-e0a9-e50e24dcca9e")
                print(f"💡 Other devices should now be able to discover this device!")
                self.test_results['server_setup'] = 'SUCCESS'
            else:
                print(f"❌ GATT server failed to start")
                self.test_results['server_setup'] = 'FAILED'

            # Show server stats
            print(f"\n📊 Server Stats:")
            print(f"   Server Connections: {stats.get('server_connections', 0)}")
            print(f"   Server Errors: {stats.get('server_errors', 0)}")

        except Exception as e:
            print(f"❌ Server setup failed: {e}")
            self.test_results['server_setup'] = 'FAILED'

    async def _phase_3_device_discovery(self):
        """Phase 3: Test BLE device discovery."""
        print(f"\n📋 PHASE 3: Device Discovery")
        print("-" * 50)

        try:
            print(f"🔍 Scanning for other SonicWave BLE devices...")
            print(f"💡 Make sure the other laptop is running this test!")

            initial_peers = len(self.transport.discovered_peers)
            print(f"   Initial peer count: {initial_peers}")

            # Monitor discovery for 30 seconds
            discovery_timeout = 30
            for i in range(discovery_timeout):
                await asyncio.sleep(1)

                current_peers = len(self.transport.discovered_peers)
                stats = self.transport.get_transport_stats()
                scans = stats.get('scans_performed', 0)

                if i % 5 == 0:  # Update every 5 seconds
                    print(f"   [{i:2d}s] Scans: {scans}, Peers: {current_peers}")

                # Check if we found any new peers
                if current_peers > initial_peers:
                    print(f"🎉 Device discovery successful!")
                    break

            # Show discovered peers
            final_peers = len(self.transport.discovered_peers)
            peers_list = self.transport.get_discovered_peers()

            print(f"\n👥 Discovery Results:")
            print(f"   Total peers discovered: {final_peers}")

            if peers_list:
                print(f"   📱 Discovered Devices:")
                for peer in peers_list:
                    print(f"      🟢 {peer['address']} ({peer['name']})")
                    print(f"         RSSI: {peer['rssi']}, Last seen: {time.time() - peer['last_seen']:.1f}s ago")
                self.test_results['discovery'] = 'SUCCESS'
            else:
                print(f"   📪 No SonicWave devices found")
                print(f"   💡 Make sure another laptop is running this test")
                print(f"   💡 Check that both devices have BLE enabled")
                self.test_results['discovery'] = 'NO_PEERS'

            stats = self.transport.get_transport_stats()
            print(f"\n📊 Discovery Stats:")
            print(f"   Scans performed: {stats.get('scans_performed', 0)}")
            print(f"   Peers discovered: {stats.get('peers_discovered', 0)}")
            print(f"   Scan errors: {stats.get('scan_errors', 0)}")

        except Exception as e:
            print(f"❌ Discovery failed: {e}")
            self.test_results['discovery'] = 'FAILED'

    async def _phase_4_packet_sending(self):
        """Phase 4: Test packet sending to discovered peers."""
        print(f"\n📋 PHASE 4: Packet Sending Test")
        print("-" * 50)

        try:
            # Check if we have any peers to send to
            if not self.transport.discovered_peers:
                print(f"⚠️ No peers available for sending test")
                print(f"💡 Discovery phase must find peers first")
                self.test_results['sending'] = 'NO_PEERS'
                return

            # Create test packets
            test_packets = [
                f"BLE test message #1 from {self.device_name}",
                f"BLE test message #2 - Hello from {self.device_name}!",
                f"BLE test message #3 - Testing chunked data transmission with a longer message that should be split into multiple BLE MTU-sized chunks to verify the chunking protocol works correctly.",
            ]

            print(f"📤 Sending {len(test_packets)} test packets...")

            for i, message in enumerate(test_packets, 1):
                print(f"\n📨 Sending packet {i}:")
                print(f"   Message: {message[:50]}{'...' if len(message) > 50 else ''}")
                print(f"   Length: {len(message)} chars")

                # Create SOS packet
                packet = SOSPacket(
                    sender_id=f"ble_test_{self.device_name}",
                    message=message,
                    urgency="LOW"
                )

                # Send packet
                await self.transport.send(packet)
                self.sent_packets.append({
                    'packet': packet,
                    'time': datetime.now(),
                    'length': len(message)
                })

                print(f"   ✅ Packet queued: {packet.packet_id[:8]}...")

                # Wait between sends
                await asyncio.sleep(2)

            # Wait for sends to complete
            print(f"\n⏳ Waiting for packets to be transmitted...")
            await asyncio.sleep(10)

            # Check sending stats
            stats = self.transport.get_transport_stats()
            packets_sent = stats.get('packets_sent', 0)
            connection_errors = stats.get('connection_errors', 0)

            print(f"\n📊 Sending Results:")
            print(f"   Packets sent: {packets_sent}")
            print(f"   Connection errors: {connection_errors}")
            print(f"   Pending packets: {stats.get('pending_packets', 0)}")

            if packets_sent > 0:
                print(f"✅ Packet sending successful!")
                self.test_results['sending'] = 'SUCCESS'
            else:
                print(f"❌ No packets were sent")
                self.test_results['sending'] = 'FAILED'

        except Exception as e:
            print(f"❌ Sending test failed: {e}")
            self.test_results['sending'] = 'FAILED'

    async def _phase_5_packet_receiving(self):
        """Phase 5: Test packet receiving from other devices."""
        print(f"\n📋 PHASE 5: Packet Receiving Test")
        print("-" * 50)

        try:
            print(f"📥 Monitoring for incoming BLE packets...")
            print(f"💡 Other devices should send packets to this device")

            initial_received = len(self.received_packets)

            # Monitor for 20 seconds
            monitoring_time = 20
            for i in range(monitoring_time):
                await asyncio.sleep(1)

                current_received = len(self.received_packets)
                stats = self.transport.get_transport_stats()
                server_connections = stats.get('server_connections', 0)

                if i % 5 == 0:  # Update every 5 seconds
                    print(f"   [{i:2d}s] Received: {current_received}, Server connections: {server_connections}")

                # Show real-time received packets
                if current_received > initial_received:
                    latest_packets = self.received_packets[initial_received:]
                    for packet_info in latest_packets:
                        packet = packet_info['packet']
                        print(f"   📨 Received: {packet.packet_id[:8]}... from {packet.sender_id}")

            # Show receiving results
            final_received = len(self.received_packets)
            packets_received_count = final_received - initial_received

            print(f"\n📊 Receiving Results:")
            print(f"   New packets received: {packets_received_count}")
            print(f"   Total packets received: {final_received}")

            stats = self.transport.get_transport_stats()
            print(f"   Server connections: {stats.get('server_connections', 0)}")
            print(f"   Buffered chunks: {stats.get('buffered_chunks', 0)}")

            if packets_received_count > 0:
                print(f"✅ Packet receiving successful!")
                self.test_results['receiving'] = 'SUCCESS'

                # Show received packet details
                print(f"\n📨 Received Packet Details:")
                for packet_info in self.received_packets[-packets_received_count:]:
                    packet = packet_info['packet']
                    print(f"   📦 {packet.packet_id[:8]}... from {packet.sender_id[:12]}...")
                    print(f"      Message: {packet.message[:60]}{'...' if len(packet.message) > 60 else ''}")
            else:
                print(f"⚠️ No packets received")
                print(f"💡 Make sure other device is sending packets")
                self.test_results['receiving'] = 'NO_PACKETS'

        except Exception as e:
            print(f"❌ Receiving test failed: {e}")
            self.test_results['receiving'] = 'FAILED'

    async def _phase_6_bidirectional_test(self):
        """Phase 6: Test bidirectional communication."""
        print(f"\n📋 PHASE 6: Bidirectional Communication Test")
        print("-" * 50)

        try:
            print(f"🔄 Testing bidirectional communication...")

            # Send a response packet
            response_message = f"Bidirectional response from {self.device_name} at {datetime.now().strftime('%H:%M:%S')}"

            packet = SOSPacket(
                sender_id=f"ble_bidir_{self.device_name}",
                message=response_message,
                urgency="MEDIUM"
            )

            print(f"📤 Sending bidirectional test packet...")
            await self.transport.send(packet)

            # Monitor for responses
            initial_count = len(self.received_packets)

            print(f"📥 Monitoring for bidirectional responses...")
            for i in range(15):
                await asyncio.sleep(1)

                current_count = len(self.received_packets)
                if current_count > initial_count:
                    new_packets = current_count - initial_count
                    print(f"   📨 Received {new_packets} new packet(s)!")
                    break

                if i % 5 == 0:
                    print(f"   [{i:2d}s] Waiting for responses...")

            # Evaluate bidirectional success
            sent_count = len(self.sent_packets)
            received_count = len(self.received_packets)

            print(f"\n📊 Bidirectional Results:")
            print(f"   Total sent: {sent_count}")
            print(f"   Total received: {received_count}")

            if sent_count > 0 and received_count > 0:
                print(f"🎉 Bidirectional communication working!")
                self.test_results['bidirectional'] = 'SUCCESS'
            elif sent_count > 0:
                print(f"⚠️ Can send but not receiving")
                self.test_results['bidirectional'] = 'SEND_ONLY'
            elif received_count > 0:
                print(f"⚠️ Can receive but not sending")
                self.test_results['bidirectional'] = 'RECEIVE_ONLY'
            else:
                print(f"❌ No bidirectional communication")
                self.test_results['bidirectional'] = 'FAILED'

        except Exception as e:
            print(f"❌ Bidirectional test failed: {e}")
            self.test_results['bidirectional'] = 'FAILED'

    async def _phase_7_stress_test(self):
        """Phase 7: Stress test with multiple rapid packets."""
        print(f"\n📋 PHASE 7: Stress Test")
        print("-" * 50)

        try:
            if not self.transport.discovered_peers:
                print(f"⚠️ Skipping stress test - no peers available")
                self.test_results['stress_test'] = 'SKIPPED'
                return

            print(f"🚀 Sending rapid-fire packets for stress testing...")

            stress_packets = []
            for i in range(5):
                message = f"Stress test packet #{i+1} from {self.device_name} - timestamp {datetime.now().timestamp()}"
                packet = SOSPacket(
                    sender_id=f"stress_{self.device_name}",
                    message=message,
                    urgency="LOW"
                )
                stress_packets.append(packet)

            # Send packets rapidly
            start_time = time.time()
            for i, packet in enumerate(stress_packets):
                await self.transport.send(packet)
                print(f"   📤 Sent stress packet {i+1}/5: {packet.packet_id[:8]}...")
                await asyncio.sleep(0.5)  # Rapid sending

            send_time = time.time() - start_time

            # Wait for transmission
            print(f"⏳ Waiting for stress test packets to transmit...")
            await asyncio.sleep(10)

            stats = self.transport.get_transport_stats()

            print(f"\n📊 Stress Test Results:")
            print(f"   Packets queued: {len(stress_packets)}")
            print(f"   Total sent: {stats.get('packets_sent', 0)}")
            print(f"   Send time: {send_time:.2f} seconds")
            print(f"   Connection errors: {stats.get('connection_errors', 0)}")

            if stats.get('packets_sent', 0) >= len(stress_packets):
                print(f"✅ Stress test passed!")
                self.test_results['stress_test'] = 'SUCCESS'
            else:
                print(f"⚠️ Some packets may have failed")
                self.test_results['stress_test'] = 'PARTIAL'

        except Exception as e:
            print(f"❌ Stress test failed: {e}")
            self.test_results['stress_test'] = 'FAILED'

    async def _show_final_results(self):
        """Show final test results and summary."""
        print(f"\n🎯 FINAL BLE TEST RESULTS")
        print("=" * 60)

        # Test results summary
        print(f"📊 Test Phase Results:")
        for phase, result in self.test_results.items():
            status_icon = {
                'SUCCESS': '✅',
                'FAILED': '❌',
                'NO_PEERS': '⚠️',
                'NO_PACKETS': '⚠️',
                'SEND_ONLY': '🔄',
                'RECEIVE_ONLY': '🔄',
                'PARTIAL': '🟡',
                'SKIPPED': '⏭️'
            }.get(result, '❓')

            print(f"   {status_icon} {phase.title().replace('_', ' ')}: {result}")

        # Communication summary
        print(f"\n📈 Communication Summary:")
        print(f"   📤 Packets sent: {len(self.sent_packets)}")
        print(f"   📥 Packets received: {len(self.received_packets)}")

        # Transport stats
        if self.transport:
            stats = self.transport.get_transport_stats()
            print(f"\n📊 Final Transport Stats:")
            print(f"   Scans performed: {stats.get('scans_performed', 0)}")
            print(f"   Peers discovered: {stats.get('peers_discovered', 0)}")
            print(f"   Total packets sent: {stats.get('packets_sent', 0)}")
            print(f"   Total packets received: {stats.get('packets_received', 0)}")
            print(f"   Connection errors: {stats.get('connection_errors', 0)}")
            print(f"   Server connections: {stats.get('server_connections', 0)}")

        # Overall assessment
        print(f"\n🎯 Overall Assessment:")

        success_count = sum(1 for result in self.test_results.values() if result == 'SUCCESS')
        total_tests = len(self.test_results)

        if success_count >= total_tests * 0.8:
            print(f"🎉 BLE transport is working well! ({success_count}/{total_tests} tests passed)")
        elif success_count >= total_tests * 0.5:
            print(f"🟡 BLE transport partially working ({success_count}/{total_tests} tests passed)")
        else:
            print(f"❌ BLE transport needs attention ({success_count}/{total_tests} tests passed)")

        # Save test results
        await self._save_test_results()

    async def _monitor_messages(self):
        """Background task to monitor incoming messages."""
        while self.running:
            try:
                if not self.message_queue.empty():
                    try:
                        while not self.message_queue.empty():
                            packet = await asyncio.wait_for(
                                self.message_queue.get(),
                                timeout=0.1
                            )

                            self.received_packets.append({
                                'packet': packet,
                                'time': datetime.now()
                            })

                            print(f"\n📨 RECEIVED BLE PACKET: {packet.packet_id[:8]}... from {packet.sender_id[:12]}...")

                    except asyncio.TimeoutError:
                        pass

                await asyncio.sleep(0.2)

            except Exception as e:
                logger.error(f"Error in message monitor: {e}")
                await asyncio.sleep(1)

    async def _save_test_results(self):
        """Save test results to file."""
        try:
            timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
            filename = f"test_outputs/ble_test_{timestamp}.json"

            # Ensure directory exists
            os.makedirs('test_outputs', exist_ok=True)

            results_data = {
                'test_info': {
                    'device_name': self.device_name,
                    'timestamp': timestamp,
                    'ble_available': BLE_AVAILABLE
                },
                'test_results': self.test_results,
                'communication_stats': {
                    'packets_sent': len(self.sent_packets),
                    'packets_received': len(self.received_packets)
                },
                'transport_stats': self.transport.get_transport_stats() if self.transport else {},
                'discovered_peers': self.transport.get_discovered_peers() if self.transport else []
            }

            with open(filename, 'w') as f:
                json.dump(results_data, f, indent=2, default=str)

            print(f"\n💾 Test results saved to: {filename}")

        except Exception as e:
            print(f"⚠️ Could not save test results: {e}")

    async def _cleanup(self):
        """Clean up resources."""
        print(f"\n🧹 Cleaning up...")
        self.running = False

        if self.transport:
            try:
                await self.transport.stop()
                print(f"✅ BLE transport stopped")
            except Exception as e:
                print(f"❌ Error stopping transport: {e}")

async def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description='BLE Transport Test for Two Laptops')
    parser.add_argument('--device', '-d',
                       help='Device name for identification',
                       default=f"BLE-Test-{datetime.now().strftime('%H%M%S')}")

    args = parser.parse_args()

    print(f"🔵 Starting BLE Transport Test")
    print(f"📱 Device: {args.device}")
    print(f"💡 Instructions:")
    print(f"   1. Run this on two different laptops")
    print(f"   2. Make sure both laptops have BLE enabled")
    print(f"   3. Keep laptops within 10 meters of each other")
    print(f"   4. Watch for device discovery and communication")
    print()

    test = BLETransportTest(device_name=args.device)
    await test.run_test()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print(f"\n⚡ Test interrupted by user")
    except Exception as e:
        print(f"💥 Fatal test error: {e}")
        import traceback
        traceback.print_exc()
