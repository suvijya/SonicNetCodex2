#!/usr/bin/env python3
"""
SonicWave Client Showcase Script
Demonstrates emergency communication capabilities between two laptops/devices.

This script can be run on multiple devices to showcase:
- Multi-transport mesh networking (BLE, UDP, GGWave)
- Real-time emergency communication
- Device discovery and peer-to-peer messaging
- Location tracking and updates
- Server integration and dashboard updates
- Cross-device emergency relay

Usage:
  Device 1: python client_showcase.py --device Device-A
  Device 2: python client_showcase.py --device Device-B
  Or simply: python client_showcase.py (auto-detects device)
"""

import asyncio
import logging
import sys
import argparse
import time
import random
import json
import requests
from datetime import datetime
from typing import Dict, List

# Add current directory to path
import os
sys.path.insert(0, os.getcwd())

from client import SonicWaveClient
from packet import SOSPacket

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class SonicWaveShowcase:
    """Comprehensive showcase of SonicWave emergency communication capabilities."""

    def __init__(self, device_id: int = None):
        self.device_id = device_id or random.randint(1, 100)
        self.device_name = f"Device-{self.device_id}"
        self.client = None
        self.server_url = "http://localhost:8000"
        self.showcase_scenarios = []
        self.discovered_peers = {}
        self.received_messages = []
        self.sent_messages = []
        self.running = False

    async def run_showcase(self):
        """Run the complete SonicWave showcase demonstration."""
        print("🚀" + "=" * 60)
        print(f"   SonicWave Emergency Communication Showcase")
        print(f"   Device: {self.device_name}")
        print(f"   Time: {datetime.now()}")
        print("🚀" + "=" * 60)

        try:
            self.running = True

            # Phase 1: System Initialization
            await self._phase_1_initialization()

            # Phase 2: Device Discovery Demo
            await self._phase_2_device_discovery()

            # Phase 3: Basic Emergency Communication
            await self._phase_3_basic_emergency()

            # Phase 4: Location-Based Emergencies
            await self._phase_4_location_emergencies()

            # Phase 5: Multi-Device Communication Test
            await self._phase_5_multi_device()

            # Phase 6: Real-Time Communication Loop
            await self._phase_6_realtime_communication()

            # Phase 7: Server Integration Demo
            await self._phase_7_server_integration()

            # Final Summary
            await self._showcase_summary()

        except KeyboardInterrupt:
            print("\n⚡ Showcase interrupted by user")
        except Exception as e:
            print(f"\n💥 Showcase error: {e}")
            import traceback
            traceback.print_exc()
        finally:
            self.running = False
            await self._cleanup()

    async def _phase_1_initialization(self):
        """Phase 1: Initialize and test all transport systems."""
        print(f"\n📋 PHASE 1: System Initialization ({self.device_name})")
        print("-" * 50)

        # Create and start client
        self.client = SonicWaveClient()
        print(f"📱 Created SonicWave client: {self.client.node_id}")

        # Test server connectivity
        await self._test_server_connection()

        # Start the client
        await self.client.start()
        print(f"✅ Client started successfully")

        # Start message monitoring
        asyncio.create_task(self._monitor_messages())

        # Test all transports
        print(f"\n🔍 Testing Transport Systems:")
        transport_results = await self.client.test_transports()

        for transport_name, result in transport_results.items():
            if result.get('available'):
                status = "🟢 ACTIVE" if result.get('running') else "🟡 AVAILABLE"
                print(f"   {status} {transport_name}")
                if 'scans_performed' in result:
                    print(f"      └─ Scans: {result.get('scans_performed', 0)}")
                if 'peers_discovered' in result:
                    print(f"      └─ Peers: {result.get('peers_discovered', 0)}")
            else:
                print(f"   🔴 UNAVAILABLE {transport_name}: {result.get('error', 'Unknown error')}")

        # Test location services
        print(f"\n🌍 Testing Location Services:")
        location_info = await self.client.get_current_location_info()
        if location_info.get('available'):
            print(f"   ✅ GPS/Location: Available")
            print(f"      └─ {location_info.get('formatted', 'Unknown format')}")
        else:
            print(f"   ⚠️  GPS/Location: {location_info.get('reason', 'Not available')}")
            # Set mock location for demo
            demo_locations = [
                (40.7128, -74.0060, "New York City"),
                (34.0522, -118.2437, "Los Angeles"),
                (41.8781, -87.6298, "Chicago"),
                (29.7604, -95.3698, "Houston")
            ]
            lat, lon, city = demo_locations[self.device_id % len(demo_locations)]
            self.client.set_mock_location(lat, lon)
            print(f"   📍 Set demo location: {city}")

        stats = self.client.get_stats()
        print(f"\n📊 Initial Stats:")
        print(f"   Active Transports: {stats['client']['transports_active']}")
        print(f"   Node ID: {self.client.node_id}")
        print(f"   Queue Size: {stats['queue_size']}")

        await asyncio.sleep(3)

    async def _phase_2_device_discovery(self):
        """Phase 2: Demonstrate device discovery capabilities."""
        print(f"\n📋 PHASE 2: Device Discovery Demo ({self.device_name})")
        print("-" * 50)

        print(f"🔍 Broadcasting discovery signals...")
        print(f"💡 This will help other devices discover this one!")
        print(f"🎯 If you have another instance running, they should discover each other!")

        # Send multiple discovery messages
        for i in range(3):
            discovery_msg = f"Discovery beacon {i+1} from {self.device_name} - Node ID: {self.client.node_id[:8]}"
            packet_id = await self.client.send_sos(
                message=discovery_msg,
                urgency="LOW"
            )

            if packet_id:
                print(f"   📡 Discovery signal {i+1} sent: {packet_id[:8]}...")
                self.sent_messages.append({
                    'type': 'DISCOVERY',
                    'message': discovery_msg,
                    'packet_id': packet_id,
                    'time': datetime.now()
                })

            await asyncio.sleep(2)

        # Wait for responses and show discovered peers
        print(f"\n⏳ Waiting for peer discovery responses...")
        await asyncio.sleep(8)

        print(f"\n👥 Discovery Results:")
        if self.discovered_peers:
            print(f"   🎉 Discovered {len(self.discovered_peers)} peer(s)!")
            for peer_id, peer_info in self.discovered_peers.items():
                print(f"      🟢 {peer_id[:8]}... (Messages: {peer_info['message_count']})")
                print(f"         └─ Last seen: {(datetime.now() - peer_info['last_seen']).seconds}s ago")
        else:
            print(f"   📪 No peers discovered yet")
            print(f"   💡 Start another instance with: python client_showcase.py --device Device-B")
            print(f"   💡 They should automatically discover each other!")

        print(f"\n📨 Messages received so far: {len(self.received_messages)}")
        if self.received_messages:
            for msg in self.received_messages[-3:]:  # Show last 3
                print(f"   📨 From {msg['sender_id'][:8]}...: {msg['message'][:50]}...")

    async def _phase_3_basic_emergency(self):
        """Phase 3: Demonstrate basic emergency communication."""
        print(f"\n📋 PHASE 3: Basic Emergency Communication ({self.device_name})")
        print("-" * 50)

        emergency_scenarios = [
            ("🚗 Car accident on highway - need immediate assistance!", "CRITICAL"),
            ("🥾 Lost hiker in mountain trail - send help", "HIGH"),
            ("🏥 Medical emergency - person unconscious", "CRITICAL"),
            ("🔧 Vehicle breakdown in remote area", "MEDIUM"),
            ("👀 Witnessing suspicious activity", "LOW")
        ]

        scenario = emergency_scenarios[self.device_id % len(emergency_scenarios)]
        message, urgency = scenario

        print(f"🚨 Emergency Scenario: {urgency}")
        print(f"   Message: {message}")

        # Send emergency SOS
        packet_id = await self.client.send_sos(
            message=message,
            urgency=urgency
        )

        if packet_id:
            print(f"✅ Emergency transmitted successfully!")
            print(f"   📦 Packet ID: {packet_id}")
            print(f"   ⚠️ Urgency: {urgency}")
            print(f"   📡 Broadcasting via all available transports...")

            self.sent_messages.append({
                'type': 'EMERGENCY',
                'message': message,
                'urgency': urgency,
                'packet_id': packet_id,
                'time': datetime.now()
            })

            # Wait for transmission and check for responses
            await asyncio.sleep(5)

            # Check transmission status
            stats = self.client.get_stats()
            print(f"   📊 Messages sent: {stats['client']['messages_sent']}")

            # Check for peer responses
            recent_messages = [msg for msg in self.received_messages
                             if (datetime.now() - msg['time']).seconds < 10]
            if recent_messages:
                print(f"   📨 Received {len(recent_messages)} recent responses!")

            # Check server reception
            await self._check_server_reception(packet_id)
        else:
            print(f"❌ Emergency transmission failed!")

        await asyncio.sleep(2)

    async def _phase_4_location_emergencies(self):
        """Phase 4: Demonstrate location-based emergency scenarios."""
        print(f"\n📋 PHASE 4: Location-Based Emergencies ({self.device_name})")
        print("-" * 50)

        location_scenarios = [
            # Format: (message, location_type, location_data)
            ("🏢 Emergency at specific coordinates", "coordinates", (40.7589, -73.9851)),
            ("🌳 Help needed at landmark", "text", "Central Park, near Bethesda Fountain"),
            ("🚦 Accident at intersection", "text", "5th Avenue and 42nd Street"),
            ("📍 Emergency at GPS location", "gps", None)  # Will use current/mock GPS
        ]

        scenario = location_scenarios[self.device_id % len(location_scenarios)]
        message, location_type, location_data = scenario

        print(f"📍 Location Emergency Scenario:")
        print(f"   Type: {location_type.upper()}")
        print(f"   Message: {message}")

        if location_type == "coordinates":
            lat, lon = location_data
            packet_id = await self.client.send_sos_with_coordinates(
                message=message,
                latitude=lat,
                longitude=lon,
                urgency="HIGH"
            )
            print(f"   📍 Coordinates: {lat:.6f}, {lon:.6f}")

        elif location_type == "text":
            packet_id = await self.client.send_sos(
                message=message,
                location=location_data,
                urgency="HIGH"
            )
            print(f"   📍 Location: {location_data}")

        elif location_type == "gps":
            packet_id = await self.client.send_sos(
                message=message,
                urgency="HIGH"
            )
            print(f"   📍 Using GPS/Mock location")

        if packet_id:
            print(f"✅ Location-based emergency sent: {packet_id}")
            self.sent_messages.append({
                'type': 'LOCATION_EMERGENCY',
                'message': message,
                'packet_id': packet_id,
                'time': datetime.now()
            })
            await self._check_server_reception(packet_id)
        else:
            print(f"❌ Location emergency failed!")

        await asyncio.sleep(3)

    async def _phase_5_multi_device(self):
        """Phase 5: Demonstrate multi-device mesh communication."""
        print(f"\n📋 PHASE 5: Multi-Device Mesh Communication ({self.device_name})")
        print("-" * 50)

        # Send a mesh networking test message
        mesh_message = f"🌐 Mesh network test from {self.device_name} - relay this message!"

        print(f"🌐 Mesh Network Test:")
        print(f"   Sending: {mesh_message}")
        print(f"   This message should be relayed by other devices in range")

        packet_id = await self.client.send_sos(
            message=mesh_message,
            urgency="LOW"
        )

        if packet_id:
            print(f"✅ Mesh message transmitted: {packet_id}")
            self.sent_messages.append({
                'type': 'MESH_TEST',
                'message': mesh_message,
                'packet_id': packet_id,
                'time': datetime.now()
            })

            # Wait for potential relay activity
            print(f"⏳ Monitoring for relay activity...")
            await asyncio.sleep(8)

            # Check for received messages
            stats = self.client.get_stats()
            print(f"📊 Network Activity:")
            print(f"   Messages sent: {stats['client']['messages_sent']}")
            print(f"   Messages received: {stats['client']['messages_received']}")
            print(f"   Queue size: {stats['queue_size']}")

            # Show current peers
            print(f"   👥 Current peers: {len(self.discovered_peers)}")
            if self.discovered_peers:
                for peer_id, peer_info in list(self.discovered_peers.items())[:3]:
                    print(f"      └─ {peer_id[:8]}...: {peer_info['message_count']} messages")

        await asyncio.sleep(2)

    async def _phase_6_realtime_communication(self):
        """Phase 6: Real-time communication demonstration."""
        print(f"\n📋 PHASE 6: Real-Time Communication Loop ({self.device_name})")
        print("-" * 50)

        print(f"🔄 Starting real-time communication test...")
        print(f"💡 This will send periodic messages and show responses")
        print(f"🎯 Perfect for testing with multiple devices!")

        # Send status updates and monitor responses
        for round_num in range(1, 6):  # 5 rounds
            print(f"\n🔄 Round {round_num}/5:")

            # Send status message
            status_msg = f"Status update #{round_num} from {self.device_name} at {datetime.now().strftime('%H:%M:%S')}"
            packet_id = await self.client.send_sos(
                message=status_msg,
                urgency="LOW"
            )

            if packet_id:
                print(f"   📤 Sent: {status_msg}")
                self.sent_messages.append({
                    'type': 'STATUS_UPDATE',
                    'message': status_msg,
                    'packet_id': packet_id,
                    'time': datetime.now()
                })

                # Wait and check for responses
                await asyncio.sleep(4)

                # Show recent activity
                recent_received = [msg for msg in self.received_messages
                                 if (datetime.now() - msg['time']).seconds < 8]
                recent_sent = [msg for msg in self.sent_messages
                             if (datetime.now() - msg['time']).seconds < 8]

                print(f"   📊 Activity: Sent {len(recent_sent)}, Received {len(recent_received)}")

                # Show any new messages
                if recent_received:
                    latest = recent_received[-1]
                    print(f"   📨 Latest: From {latest['sender_id'][:8]}...: {latest['message'][:40]}...")

                # Show peer count
                active_peers = len([p for p in self.discovered_peers.values()
                                  if (datetime.now() - p['last_seen']).seconds < 30])
                print(f"   👥 Active peers: {active_peers}")

            await asyncio.sleep(3)

        print(f"\n✅ Real-time communication test completed!")
        print(f"📊 Final stats: Sent {len(self.sent_messages)}, Received {len(self.received_messages)}")

    async def _phase_7_server_integration(self):
        """Phase 7: Server integration demonstration."""
        print(f"\n📋 PHASE 7: Server Integration Demo ({self.device_name})")
        print("-" * 50)

        # Test server connectivity
        server_available = await self._test_server_connection()

        if server_available:
            print(f"✅ Server is available - testing integration")

            # Send a server test message
            server_msg = f"Server integration test from {self.device_name}"
            packet_id = await self.client.send_sos(
                message=server_msg,
                urgency="MEDIUM"
            )

            if packet_id:
                print(f"📤 Sent server test message: {packet_id}")
                await asyncio.sleep(3)
                await self._check_server_reception(packet_id)
        else:
            print(f"⚠️ Server not available - skipping integration test")
            print(f"💡 Start server with: python server.py")

    async def _showcase_summary(self):
        """Final summary of the showcase."""
        print(f"\n🎯 SHOWCASE SUMMARY ({self.device_name})")
        print("=" * 50)

        print(f"📊 Communication Statistics:")
        print(f"   📤 Messages Sent: {len(self.sent_messages)}")
        print(f"   📥 Messages Received: {len(self.received_messages)}")
        print(f"   👥 Peers Discovered: {len(self.discovered_peers)}")

        if self.discovered_peers:
            print(f"\n👥 Discovered Peers:")
            for peer_id, peer_info in self.discovered_peers.items():
                last_seen = (datetime.now() - peer_info['last_seen']).seconds
                print(f"   🟢 {peer_id[:8]}... - {peer_info['message_count']} messages, last seen {last_seen}s ago")

        # Message breakdown
        message_types = {}
        for msg in self.sent_messages:
            msg_type = msg.get('type', 'UNKNOWN')
            message_types[msg_type] = message_types.get(msg_type, 0) + 1

        if message_types:
            print(f"\n📋 Message Types Sent:")
            for msg_type, count in message_types.items():
                print(f"   {msg_type}: {count}")

        # Success indicators
        print(f"\n✅ Showcase Results:")
        if len(self.discovered_peers) > 0:
            print(f"   🎉 SUCCESS: Device discovery working!")
            print(f"   🎉 SUCCESS: Peer-to-peer communication established!")
        else:
            print(f"   ⚠️  No peers discovered - try running multiple instances")

        if len(self.received_messages) > 0:
            print(f"   🎉 SUCCESS: Message receiving working!")

        if len(self.sent_messages) > 0:
            print(f"   🎉 SUCCESS: Message sending working!")

        print(f"\n🚀 Showcase completed successfully!")
        print(f"💡 Keep this running to continue communication with other devices")

    async def _monitor_messages(self):
        """Background task to monitor incoming messages."""
        while self.running:
            try:
                # Check for new messages in the queue
                if not self.client.message_queue.empty():
                    try:
                        # Process messages from queue
                        while not self.client.message_queue.empty():
                            packet = await asyncio.wait_for(
                                self.client.message_queue.get(),
                                timeout=0.1
                            )
                            await self._handle_received_packet(packet)
                    except asyncio.TimeoutError:
                        pass

                await asyncio.sleep(0.5)  # Check every 500ms

            except Exception as e:
                logger.error(f"Error in message monitor: {e}")
                await asyncio.sleep(1)

    async def _handle_received_packet(self, packet: SOSPacket):
        """Handle a received packet."""
        try:
            # Don't process our own messages
            if packet.sender_id == self.client.node_id:
                return

            # Add to received messages
            self.received_messages.append({
                'sender_id': packet.sender_id,
                'message': packet.message,
                'urgency': packet.urgency,
                'packet_id': packet.packet_id,
                'time': datetime.now()
            })

            # Update peer tracking
            if packet.sender_id not in self.discovered_peers:
                self.discovered_peers[packet.sender_id] = {
                    'first_seen': datetime.now(),
                    'last_seen': datetime.now(),
                    'message_count': 1
                }
                print(f"\n🎉 NEW PEER DISCOVERED: {packet.sender_id[:8]}...")
            else:
                self.discovered_peers[packet.sender_id]['last_seen'] = datetime.now()
                self.discovered_peers[packet.sender_id]['message_count'] += 1

        except Exception as e:
            logger.error(f"Error handling received packet: {e}")

    async def _test_server_connection(self):
        """Test connection to the server."""
        try:
            response = requests.get(f"{self.server_url}/status", timeout=5)
            if response.status_code == 200:
                print(f"✅ Server connection: OK")
                return True
        except:
            pass

        print(f"⚠️ Server connection: Not available")
        return False

    async def _check_server_reception(self, packet_id: str):
        """Check if server received the packet."""
        try:
            await asyncio.sleep(2)  # Wait for server processing
            response = requests.get(f"{self.server_url}/packets/{packet_id}", timeout=5)
            if response.status_code == 200:
                print(f"   ✅ Server confirmed receipt: {packet_id}")
                return True
        except:
            pass

        print(f"   ⚠️ Server reception not confirmed")
        return False

    async def _cleanup(self):
        """Clean up resources."""
        if self.client:
            try:
                await self.client.stop()
                print(f"\n✅ Client stopped successfully")
            except Exception as e:
                print(f"❌ Error stopping client: {e}")

async def main():
    """Main entry point with enhanced argument parsing."""
    parser = argparse.ArgumentParser(description='SonicWave Client Showcase')
    parser.add_argument('--device', '-d', type=int,
                       help='Device ID (e.g., 1, 2, 3)',
                       default=None)
    parser.add_argument('--auto', '-a', action='store_true',
                       help='Run in automatic mode (no user interaction)')

    args = parser.parse_args()

    # Auto-assign device ID if not provided
    if args.device is None:
        args.device = random.randint(1, 99)

    print(f"🚀 Starting SonicWave Showcase for Device-{args.device}")
    print(f"💡 To test communication, run this on another device:")
    print(f"   python client_showcase.py --device {args.device + 1}")
    print()

    showcase = SonicWaveShowcase(device_id=args.device)
    await showcase.run_showcase()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print(f"\n⚡ Showcase interrupted by user")
    except Exception as e:
        print(f"💥 Fatal error: {e}")
        import traceback
        traceback.print_exc()
