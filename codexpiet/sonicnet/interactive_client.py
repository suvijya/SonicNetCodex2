#!/usr/bin/env python3
"""
Interactive SonicWave Client Showcase
A comprehensive client that demonstrates real-time communication between devices.

Features:
- Real-time message sending and receiving
- Node discovery and peer tracking
- Interactive command interface
- Status monitoring
- Multi-transport support

Usage:
  Terminal 1: python interactive_client.py --device Device-A
  Terminal 2: python interactive_client.py --device Device-B
"""

import asyncio
import logging
import sys
import argparse
import time
import random
import json
import uuid
from datetime import datetime
from typing import Dict, List, Optional

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

class InteractiveSonicClient:
    """Interactive client for demonstrating device-to-device communication."""

    def __init__(self, device_name: str = None):
        self.device_name = device_name or f"Device-{random.randint(1000, 9999)}"
        self.client = None
        self.running = False
        self.discovered_peers = {}
        self.received_messages = []
        self.sent_messages = []
        self.last_status_time = 0

    async def start(self):
        """Start the interactive client."""
        print(f"\n🚀 Starting SonicWave Interactive Client")
        print(f"📱 Device Name: {self.device_name}")
        print(f"⏰ Started at: {datetime.now().strftime('%H:%M:%S')}")
        print("=" * 60)

        try:
            # Create and start client
            self.client = SonicWaveClient()
            await self.client.start()

            self.running = True

            # Start background tasks
            asyncio.create_task(self._monitor_messages())
            asyncio.create_task(self._periodic_discovery())
            asyncio.create_task(self._status_updater())

            print(f"✅ Client started successfully!")
            print(f"🆔 Node ID: {self.client.node_id}")
            print(f"🌐 Ready for communication...")

            await self._show_initial_status()
            await self._interactive_loop()

        except Exception as e:
            print(f"❌ Failed to start client: {e}")
            import traceback
            traceback.print_exc()
        finally:
            await self._cleanup()

    async def _show_initial_status(self):
        """Show initial system status."""
        await asyncio.sleep(2)  # Give transports time to initialize

        print(f"\n📊 Initial System Status:")
        stats = self.client.get_stats()

        # Transport status
        transport_results = await self.client.test_transports()
        print(f"🔧 Transport Status:")
        for transport_name, result in transport_results.items():
            if result.get('available'):
                status = "🟢 ACTIVE" if result.get('running') else "🟡 READY"
                print(f"   {status} {transport_name}")
            else:
                print(f"   🔴 UNAVAILABLE {transport_name}: {result.get('error', 'Unknown')}")

        print(f"📈 Stats: Sent={stats['client']['messages_sent']}, Received={stats['client']['messages_received']}")
        print(f"📡 Queue Size: {stats['queue_size']}")

    async def _interactive_loop(self):
        """Main interactive command loop."""
        print(f"\n🎮 Interactive Commands:")
        print(f"   1. Send SOS message")
        print(f"   2. Send status update")
        print(f"   3. Show discovered peers")
        print(f"   4. Show received messages")
        print(f"   5. Show system stats")
        print(f"   6. Send location emergency")
        print(f"   7. Broadcast discovery ping")
        print(f"   8. Show full status")
        print(f"   q. Quit")
        print("=" * 60)

        while self.running:
            try:
                # Show prompt with device name
                command = input(f"\n[{self.device_name}] Enter command (1-8, q): ").strip().lower()

                if command == 'q' or command == 'quit':
                    break
                elif command == '1':
                    await self._send_sos_interactive()
                elif command == '2':
                    await self._send_status_interactive()
                elif command == '3':
                    await self._show_peers()
                elif command == '4':
                    await self._show_received_messages()
                elif command == '5':
                    await self._show_stats()
                elif command == '6':
                    await self._send_location_emergency()
                elif command == '7':
                    await self._send_discovery_ping()
                elif command == '8':
                    await self._show_full_status()
                else:
                    print(f"❓ Unknown command: {command}")

            except KeyboardInterrupt:
                break
            except EOFError:
                break
            except Exception as e:
                print(f"❌ Error processing command: {e}")

    async def _send_sos_interactive(self):
        """Interactive SOS message sending."""
        print(f"\n🚨 Send SOS Message")
        try:
            message = input("Enter emergency message: ").strip()
            if not message:
                message = f"Emergency from {self.device_name} at {datetime.now().strftime('%H:%M:%S')}"

            urgency = input("Enter urgency (LOW/MEDIUM/HIGH/CRITICAL) [HIGH]: ").strip().upper()
            if urgency not in ['LOW', 'MEDIUM', 'HIGH', 'CRITICAL']:
                urgency = 'HIGH'

            packet_id = await self.client.send_sos(message=message, urgency=urgency)

            if packet_id:
                self.sent_messages.append({
                    'type': 'SOS',
                    'message': message,
                    'urgency': urgency,
                    'packet_id': packet_id,
                    'time': datetime.now()
                })
                print(f"✅ SOS sent successfully!")
                print(f"   📦 Packet ID: {packet_id}")
                print(f"   ⚠️ Urgency: {urgency}")
                print(f"   📡 Broadcasting to all transports...")
            else:
                print(f"❌ Failed to send SOS message")

        except Exception as e:
            print(f"❌ Error sending SOS: {e}")

    async def _send_status_interactive(self):
        """Send a status update message."""
        print(f"\n📊 Send Status Update")
        try:
            status_messages = [
                f"{self.device_name} is online and operational",
                f"{self.device_name} checking in - all systems normal",
                f"Status update from {self.device_name} - ready for communication",
                f"{self.device_name} mesh network test - please acknowledge"
            ]

            message = random.choice(status_messages)
            packet_id = await self.client.send_sos(message=message, urgency="LOW")

            if packet_id:
                self.sent_messages.append({
                    'type': 'STATUS',
                    'message': message,
                    'packet_id': packet_id,
                    'time': datetime.now()
                })
                print(f"✅ Status update sent!")
                print(f"   📦 Packet ID: {packet_id}")
                print(f"   💬 Message: {message}")
            else:
                print(f"❌ Failed to send status update")

        except Exception as e:
            print(f"❌ Error sending status: {e}")

    async def _send_location_emergency(self):
        """Send emergency with location data."""
        print(f"\n📍 Send Location Emergency")
        try:
            # Demo coordinates for different devices
            demo_locations = [
                (40.7128, -74.0060, "New York City Emergency"),
                (34.0522, -118.2437, "Los Angeles Incident"),
                (41.8781, -87.6298, "Chicago Emergency"),
                (29.7604, -95.3698, "Houston Crisis")
            ]

            lat, lon, location_desc = random.choice(demo_locations)
            message = f"{location_desc} - Immediate assistance required at coordinates"

            packet_id = await self.client.send_sos_with_coordinates(
                message=message,
                latitude=lat,
                longitude=lon,
                urgency="CRITICAL"
            )

            if packet_id:
                self.sent_messages.append({
                    'type': 'LOCATION_EMERGENCY',
                    'message': message,
                    'coordinates': f"{lat:.6f}, {lon:.6f}",
                    'packet_id': packet_id,
                    'time': datetime.now()
                })
                print(f"✅ Location emergency sent!")
                print(f"   📦 Packet ID: {packet_id}")
                print(f"   📍 Coordinates: {lat:.6f}, {lon:.6f}")
                print(f"   🚨 Message: {message}")
            else:
                print(f"❌ Failed to send location emergency")

        except Exception as e:
            print(f"❌ Error sending location emergency: {e}")

    async def _send_discovery_ping(self):
        """Send a discovery ping to find other devices."""
        print(f"\n🔍 Broadcasting Discovery Ping")
        try:
            message = f"Discovery ping from {self.device_name} - please respond if you receive this"
            packet_id = await self.client.send_sos(message=message, urgency="LOW")

            if packet_id:
                self.sent_messages.append({
                    'type': 'DISCOVERY',
                    'message': message,
                    'packet_id': packet_id,
                    'time': datetime.now()
                })
                print(f"✅ Discovery ping sent!")
                print(f"   📦 Packet ID: {packet_id}")
                print(f"   🔍 Waiting for responses...")

                # Wait a bit and check for new messages
                await asyncio.sleep(3)
                recent_messages = [msg for msg in self.received_messages
                                 if (datetime.now() - msg['time']).seconds < 10]
                if recent_messages:
                    print(f"   📨 Received {len(recent_messages)} recent messages!")
                else:
                    print(f"   📪 No immediate responses received")
            else:
                print(f"❌ Failed to send discovery ping")

        except Exception as e:
            print(f"❌ Error sending discovery ping: {e}")

    async def _show_peers(self):
        """Show discovered peers."""
        print(f"\n👥 Discovered Peers:")
        if not self.discovered_peers:
            print(f"   📪 No peers discovered yet")
            print(f"   💡 Try sending a discovery ping (option 7) or wait for other devices")
        else:
            for peer_id, peer_info in self.discovered_peers.items():
                last_seen = (datetime.now() - peer_info['last_seen']).seconds
                print(f"   🟢 {peer_id}")
                print(f"      └─ Last seen: {last_seen}s ago")
                print(f"      └─ Messages: {peer_info['message_count']}")

    async def _show_received_messages(self):
        """Show received messages."""
        print(f"\n📨 Received Messages:")
        if not self.received_messages:
            print(f"   📪 No messages received yet")
            print(f"   💡 Start another instance to test communication")
        else:
            # Show last 5 messages
            recent_messages = self.received_messages[-5:]
            for msg in recent_messages:
                time_str = msg['time'].strftime('%H:%M:%S')
                print(f"   📨 [{time_str}] From {msg['sender_id'][:8]}...")
                print(f"      └─ {msg['message']}")
                if 'urgency' in msg:
                    print(f"      └─ Urgency: {msg['urgency']}")

            if len(self.received_messages) > 5:
                print(f"   ... and {len(self.received_messages) - 5} more messages")

    async def _show_stats(self):
        """Show system statistics."""
        print(f"\n📊 System Statistics:")
        try:
            stats = self.client.get_stats()
            print(f"   📤 Messages Sent: {len(self.sent_messages)}")
            print(f"   📥 Messages Received: {len(self.received_messages)}")
            print(f"   👥 Peers Discovered: {len(self.discovered_peers)}")
            print(f"   📡 Queue Size: {stats['queue_size']}")
            print(f"   🔧 Active Transports: {stats['client']['transports_active']}")
            print(f"   ❌ Errors: {stats['client']['errors']}")

            # Transport-specific stats
            transport_results = await self.client.test_transports()
            print(f"   🌐 Transport Details:")
            for transport_name, result in transport_results.items():
                if result.get('available'):
                    status = "ACTIVE" if result.get('running') else "READY"
                    print(f"      └─ {transport_name}: {status}")

        except Exception as e:
            print(f"❌ Error getting stats: {e}")

    async def _show_full_status(self):
        """Show comprehensive system status."""
        print(f"\n🔍 Full System Status")
        print("=" * 50)

        # Basic info
        print(f"🆔 Device: {self.device_name}")
        print(f"🏷️  Node ID: {self.client.node_id}")
        print(f"⏰ Uptime: {datetime.now().strftime('%H:%M:%S')}")

        # Messages summary
        print(f"\n📊 Message Summary:")
        print(f"   Sent: {len(self.sent_messages)} | Received: {len(self.received_messages)}")
        print(f"   Peers: {len(self.discovered_peers)}")

        # Recent activity
        recent_sent = [msg for msg in self.sent_messages
                      if (datetime.now() - msg['time']).seconds < 60]
        recent_received = [msg for msg in self.received_messages
                          if (datetime.now() - msg['time']).seconds < 60]

        print(f"\n⏱️  Recent Activity (last 60s):")
        print(f"   Sent: {len(recent_sent)} | Received: {len(recent_received)}")

        # Transport status
        await self._show_stats()

    async def _monitor_messages(self):
        """Background task to monitor incoming messages."""
        last_check = 0

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

            # Show real-time notification
            time_str = datetime.now().strftime('%H:%M:%S')
            print(f"\n📨 [{time_str}] Message from {packet.sender_id[:8]}...: {packet.message[:50]}...")

        except Exception as e:
            logger.error(f"Error handling received packet: {e}")

    async def _periodic_discovery(self):
        """Periodically send discovery messages."""
        while self.running:
            try:
                # Send discovery every 30 seconds
                await asyncio.sleep(30)

                if self.running:  # Check if still running
                    discovery_msg = f"Auto-discovery from {self.device_name}"
                    await self.client.send_sos(message=discovery_msg, urgency="LOW")

            except Exception as e:
                logger.error(f"Error in periodic discovery: {e}")

    async def _status_updater(self):
        """Periodically update status display."""
        while self.running:
            try:
                await asyncio.sleep(10)  # Update every 10 seconds

                current_time = time.time()
                if current_time - self.last_status_time > 30:  # Show status every 30s
                    self.last_status_time = current_time
                    print(f"\n⏰ [{datetime.now().strftime('%H:%M:%S')}] Status: "
                          f"Sent={len(self.sent_messages)}, Received={len(self.received_messages)}, "
                          f"Peers={len(self.discovered_peers)}")

            except Exception as e:
                logger.error(f"Error in status updater: {e}")

    async def _cleanup(self):
        """Clean up resources."""
        self.running = False
        if self.client:
            try:
                await self.client.stop()
                print(f"\n✅ Client stopped successfully")
            except Exception as e:
                print(f"❌ Error stopping client: {e}")

async def main():
    """Main entry point."""
    parser = argparse.ArgumentParser(description='Interactive SonicWave Client')
    parser.add_argument('--device', '-d',
                       help='Device name (e.g., Device-A, Device-B)',
                       default=None)

    args = parser.parse_args()

    client = InteractiveSonicClient(device_name=args.device)
    await client.start()

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print(f"\n⚡ Shutting down...")
    except Exception as e:
        print(f"💥 Fatal error: {e}")
        import traceback
        traceback.print_exc()
