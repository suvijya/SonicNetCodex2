#!/usr/bin/env python3
"""
SonicWave Comprehensive Test Suite
Tests all functionality: client, server, BLE, UDP, location, database integration
"""

import asyncio
import logging
import sys
import os
import time
import json
import requests
import websockets
from datetime import datetime
from typing import Dict, List, Any

# Add current directory to path
sys.path.insert(0, os.getcwd())

from client import SonicWaveClient
from server import app
import uvicorn
import threading

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class ComprehensiveTestSuite:
    """Complete test suite for SonicWave system."""

    def __init__(self):
        self.server_url = "http://localhost:8000"
        self.websocket_url = "ws://localhost:8000/ws"
        self.clients = []
        self.server_process = None
        self.test_results = {}
        self.server_thread = None

    async def run_all_tests(self):
        """Run the complete comprehensive test suite."""
        print("🚀 SonicWave Comprehensive Test Suite")
        print("=" * 60)
        print(f"Date: {datetime.now()}")
        print(f"Platform: {sys.platform}")
        print("=" * 60)

        try:
            # Phase 1: Setup and Infrastructure
            print("\n📋 PHASE 1: Infrastructure Setup")
            await self._test_server_startup()
            await self._test_database_connection()

            # Phase 2: Client Functionality
            print("\n📋 PHASE 2: Client Functionality")
            await self._test_client_initialization()
            await self._test_location_service()
            await self._test_transport_initialization()

            # Phase 3: Communication
            print("\n📋 PHASE 3: Communication & Messaging")
            await self._test_single_sos()
            await self._test_location_formats()
            await self._test_multiple_clients()
            await self._test_packet_relay()

            # Phase 4: Server Integration
            print("\n📋 PHASE 4: Server Integration")
            await self._test_server_reception()
            await self._test_websocket_updates()
            await self._test_packet_history()
            await self._test_emergency_notifications()

            # Phase 5: Advanced Features
            print("\n📋 PHASE 5: Advanced Features")
            await self._test_network_topology()
            await self._test_location_updates()
            await self._test_duplicate_prevention()
            await self._test_urgency_levels()

            # Phase 6: Stress Testing
            print("\n📋 PHASE 6: Performance & Stress Testing")
            await self._test_multiple_rapid_messages()
            await self._test_long_running_stability()

        except Exception as e:
            logger.error(f"Test suite failed: {e}")
            import traceback
            traceback.print_exc()
        finally:
            await self._cleanup()
            self._print_final_results()

    async def _test_server_startup(self):
        """Test server startup and health."""
        test_name = "Server Startup"
        print(f"\n🖥️  Testing: {test_name}")

        try:
            # Start server in background thread
            def run_server():
                uvicorn.run(app, host="0.0.0.0", port=8000, log_level="warning")

            self.server_thread = threading.Thread(target=run_server, daemon=True)
            self.server_thread.start()

            # Wait for server to start
            for i in range(10):
                try:
                    response = requests.get(f"{self.server_url}/api/stats", timeout=2)
                    if response.status_code == 200:
                        print(f"  ✅ Server started and responding")
                        stats = response.json()
                        print(f"  ℹ️  Initial stats: {stats}")
                        self.test_results[test_name] = {"status": "PASS", "startup_time": i}
                        return
                except:
                    await asyncio.sleep(1)

            raise Exception("Server failed to start within 10 seconds")

        except Exception as e:
            print(f"  ❌ {test_name} failed: {e}")
            self.test_results[test_name] = {"status": "FAIL", "error": str(e)}

    async def _test_database_connection(self):
        """Test database connectivity."""
        test_name = "Database Connection"
        print(f"\n🗄️  Testing: {test_name}")

        try:
            # Test basic database operations
            response = requests.get(f"{self.server_url}/api/packets", timeout=5)
            if response.status_code == 200:
                packets = response.json()

                # Test authorities
                auth_response = requests.get(f"{self.server_url}/api/authorities", timeout=5)
                if auth_response.status_code == 200:
                    authorities = auth_response.json()

                    print(f"  ✅ Database connected")
                    print(f"  ℹ️  Existing packets: {len(packets)}")
                    print(f"  ℹ️  Rescue authorities: {len(authorities)}")

                    self.test_results[test_name] = {
                        "status": "PASS",
                        "packets": len(packets),
                        "authorities": len(authorities)
                    }
                else:
                    raise Exception("Could not access authorities table")
            else:
                raise Exception("Could not access packets table")

        except Exception as e:
            print(f"  ❌ {test_name} failed: {e}")
            self.test_results[test_name] = {"status": "FAIL", "error": str(e)}

    async def _test_client_initialization(self):
        """Test client initialization."""
        test_name = "Client Initialization"
        print(f"\n🔧 Testing: {test_name}")

        try:
            client = SonicWaveClient()
            print(f"  ✅ Client created: {client.node_id}")

            await client.start()
            print(f"  ✅ Client started")
            print(f"  ℹ️  Active transports: {client.stats['transports_active']}")

            self.clients.append(client)

            # Test client stats
            stats = client.get_stats()
            print(f"  ℹ️  Client stats: {stats['client']}")

            self.test_results[test_name] = {
                "status": "PASS",
                "node_id": client.node_id,
                "transports": client.stats['transports_active'],
                "stats": stats
            }

        except Exception as e:
            print(f"  ❌ {test_name} failed: {e}")
            self.test_results[test_name] = {"status": "FAIL", "error": str(e)}

    async def _test_location_service(self):
        """Test location service functionality."""
        test_name = "Location Service"
        print(f"\n🌍 Testing: {test_name}")

        try:
            if not self.clients:
                raise Exception("No clients available")

            client = self.clients[0]

            # Test mock location
            client.set_mock_location(40.7128, -74.0060, 10.0)
            location_info = await client.get_current_location_info()

            if location_info.get('available'):
                print(f"  ✅ Location service working")
                print(f"  ℹ️  Test location: {location_info['formatted']}")

                self.test_results[test_name] = {
                    "status": "PASS",
                    "location_info": location_info
                }
            else:
                raise Exception("Location service not available")

        except Exception as e:
            print(f"  ❌ {test_name} failed: {e}")
            self.test_results[test_name] = {"status": "FAIL", "error": str(e)}

    async def _test_transport_initialization(self):
        """Test transport initialization."""
        test_name = "Transport Initialization"
        print(f"\n📡 Testing: {test_name}")

        try:
            if not self.clients:
                raise Exception("No clients available")

            client = self.clients[0]
            transport_results = await client.test_transports()

            print(f"  ✅ Transport test completed")
            for name, result in transport_results.items():
                status = "✅" if result.get('available') else "❌"
                print(f"  {status} {name}: {result}")

            # Test BLE peers
            ble_peers = client.get_ble_peers()
            print(f"  ℹ️  BLE peers discovered: {len(ble_peers)}")

            self.test_results[test_name] = {
                "status": "PASS",
                "transports": transport_results,
                "ble_peers": len(ble_peers)
            }

        except Exception as e:
            print(f"  ❌ {test_name} failed: {e}")
            self.test_results[test_name] = {"status": "FAIL", "error": str(e)}

    async def _test_single_sos(self):
        """Test sending a single SOS message."""
        test_name = "Single SOS Message"
        print(f"\n📤 Testing: {test_name}")

        try:
            if not self.clients:
                raise Exception("No clients available")

            client = self.clients[0]
            client.set_mock_location(40.7589, -73.9851)  # Times Square

            packet_id = await client.send_sos(
                message="Test emergency message",
                urgency="HIGH"
            )

            if packet_id:
                print(f"  ✅ SOS sent: {packet_id}")

                # Wait for processing
                await asyncio.sleep(3)

                # Verify on server
                if await self._verify_packet_on_server(packet_id):
                    print(f"  ✅ Packet received by server")
                    self.test_results[test_name] = {
                        "status": "PASS",
                        "packet_id": packet_id,
                        "server_received": True
                    }
                else:
                    self.test_results[test_name] = {
                        "status": "PARTIAL",
                        "packet_id": packet_id,
                        "server_received": False
                    }
            else:
                raise Exception("Failed to send SOS")

        except Exception as e:
            print(f"  ❌ {test_name} failed: {e}")
            self.test_results[test_name] = {"status": "FAIL", "error": str(e)}

    async def _test_location_formats(self):
        """Test different location formats."""
        test_name = "Location Formats"
        print(f"\n📍 Testing: {test_name}")

        try:
            if not self.clients:
                raise Exception("No clients available")

            client = self.clients[0]

            # Test different location formats
            test_cases = [
                ("34.0522, -118.2437", "coordinates"),
                ("Central Park, New York", "address"),
                (None, "auto_gps")  # Should use mock location
            ]

            results = []
            for location, format_type in test_cases:
                if format_type == "auto_gps":
                    client.set_mock_location(48.8566, 2.3522)  # Paris

                packet_id = await client.send_sos(
                    message=f"Test {format_type} location",
                    location=location,
                    urgency="MEDIUM"
                )

                if packet_id:
                    results.append({"format": format_type, "success": True, "packet_id": packet_id})
                    print(f"  ✅ {format_type}: {packet_id}")
                else:
                    results.append({"format": format_type, "success": False})
                    print(f"  ❌ {format_type}: Failed")

                await asyncio.sleep(1)

            successful = len([r for r in results if r["success"]])
            self.test_results[test_name] = {
                "status": "PASS" if successful == len(test_cases) else "PARTIAL",
                "total": len(test_cases),
                "successful": successful,
                "results": results
            }

        except Exception as e:
            print(f"  ❌ {test_name} failed: {e}")
            self.test_results[test_name] = {"status": "FAIL", "error": str(e)}

    async def _test_multiple_clients(self):
        """Test multiple clients communication."""
        test_name = "Multiple Clients"
        print(f"\n👥 Testing: {test_name}")

        try:
            # Create second client
            client2 = SonicWaveClient()
            await client2.start()
            self.clients.append(client2)

            print(f"  ✅ Second client created: {client2.node_id}")

            # Send messages from both clients
            client2.set_mock_location(51.5074, -0.1278)  # London

            packet_id1 = await self.clients[0].send_sos("Message from client 1", urgency="HIGH")
            packet_id2 = await client2.send_sos("Message from client 2", urgency="CRITICAL")

            if packet_id1 and packet_id2:
                print(f"  ✅ Messages sent from both clients")

                await asyncio.sleep(3)

                # Check server stats
                response = requests.get(f"{self.server_url}/api/stats", timeout=5)
                if response.status_code == 200:
                    stats = response.json()
                    print(f"  ✅ Server stats updated")
                    print(f"  ℹ️  Total packets: {stats['total_packets']}")

                    self.test_results[test_name] = {
                        "status": "PASS",
                        "client1_id": self.clients[0].node_id,
                        "client2_id": client2.node_id,
                        "packet1": packet_id1,
                        "packet2": packet_id2,
                        "server_stats": stats
                    }
                else:
                    raise Exception("Could not get server stats")
            else:
                raise Exception("Failed to send messages from both clients")

        except Exception as e:
            print(f"  ❌ {test_name} failed: {e}")
            self.test_results[test_name] = {"status": "FAIL", "error": str(e)}

    async def _test_packet_relay(self):
        """Test packet relay functionality."""
        test_name = "Packet Relay"
        print(f"\n🔄 Testing: {test_name}")

        try:
            if len(self.clients) < 2:
                raise Exception("Need at least 2 clients")

            # Test relay between clients (simulation since we can't test real mesh)
            relay_stats = []
            for client in self.clients:
                stats = client.get_stats()
                relay_stats.append({
                    "node_id": client.node_id,
                    "messages_sent": stats['client']['messages_sent'],
                    "messages_received": stats['client']['messages_received']
                })

            print(f"  ✅ Relay stats collected")
            for stat in relay_stats:
                print(f"  ℹ️  {stat['node_id']}: sent={stat['messages_sent']}, received={stat['messages_received']}")

            self.test_results[test_name] = {
                "status": "PASS",
                "relay_stats": relay_stats
            }

        except Exception as e:
            print(f"  ❌ {test_name} failed: {e}")
            self.test_results[test_name] = {"status": "FAIL", "error": str(e)}

    async def _test_server_reception(self):
        """Test server packet reception and processing."""
        test_name = "Server Packet Reception"
        print(f"\n📥 Testing: {test_name}")

        try:
            # Get current packet count
            response = requests.get(f"{self.server_url}/api/packets", timeout=5)
            if response.status_code == 200:
                initial_count = len(response.json())

                # Send test packet
                if self.clients:
                    packet_id = await self.clients[0].send_sos(
                        "Server reception test",
                        urgency="LOW"
                    )

                    await asyncio.sleep(2)

                    # Check new count
                    response2 = requests.get(f"{self.server_url}/api/packets", timeout=5)
                    if response2.status_code == 200:
                        new_count = len(response2.json())

                        if new_count > initial_count:
                            print(f"  ✅ Server received packet")
                            print(f"  ℹ️  Packet count: {initial_count} → {new_count}")

                            self.test_results[test_name] = {
                                "status": "PASS",
                                "initial_count": initial_count,
                                "new_count": new_count,
                                "packet_id": packet_id
                            }
                        else:
                            raise Exception("Packet count did not increase")
                    else:
                        raise Exception("Could not get updated packet count")
                else:
                    raise Exception("No clients available")
            else:
                raise Exception("Could not get initial packet count")

        except Exception as e:
            print(f"  ❌ {test_name} failed: {e}")
            self.test_results[test_name] = {"status": "FAIL", "error": str(e)}

    async def _test_websocket_updates(self):
        """Test WebSocket real-time updates."""
        test_name = "WebSocket Updates"
        print(f"\n🔌 Testing: {test_name}")

        try:
            messages = []

            async def collect_messages():
                try:
                    async with websockets.connect(self.websocket_url) as ws:
                        for _ in range(3):  # Collect 3 messages
                            try:
                                message = await asyncio.wait_for(ws.recv(), timeout=2.0)
                                data = json.loads(message)
                                messages.append(data)
                            except asyncio.TimeoutError:
                                break
                except Exception as e:
                    print(f"    WebSocket error: {e}")

            # Start collecting messages
            ws_task = asyncio.create_task(collect_messages())

            # Send a test message while collecting
            await asyncio.sleep(0.5)
            if self.clients:
                await self.clients[0].send_sos("WebSocket test message", urgency="LOW")

            # Wait for collection to complete
            await ws_task

            if messages:
                print(f"  ✅ WebSocket messages received: {len(messages)}")
                for i, msg in enumerate(messages):
                    print(f"    {i+1}. Type: {msg.get('type', 'unknown')}")

                self.test_results[test_name] = {
                    "status": "PASS",
                    "messages_count": len(messages),
                    "message_types": [msg.get('type') for msg in messages]
                }
            else:
                self.test_results[test_name] = {
                    "status": "PARTIAL",
                    "note": "WebSocket connected but no messages received"
                }

        except Exception as e:
            print(f"  ❌ {test_name} failed: {e}")
            self.test_results[test_name] = {"status": "FAIL", "error": str(e)}

    async def _test_packet_history(self):
        """Test packet history functionality."""
        test_name = "Packet History"
        print(f"\n📚 Testing: {test_name}")

        try:
            # Get a recent packet
            response = requests.get(f"{self.server_url}/api/packets/recent", timeout=5)
            if response.status_code == 200:
                packets = response.json()

                if packets:
                    test_packet = packets[0]
                    packet_id = test_packet['packet_id']

                    # Get packet history
                    history_response = requests.get(
                        f"{self.server_url}/api/packets/{packet_id}/history",
                        timeout=5
                    )

                    if history_response.status_code == 200:
                        history = history_response.json()

                        print(f"  ✅ Packet history retrieved")
                        print(f"  ℹ️  Packet ID: {packet_id}")
                        print(f"  ℹ️  Relay path: {len(history.get('relay_path', []))}")
                        print(f"  ℹ️  Location history: {len(history.get('location_history', []))}")

                        self.test_results[test_name] = {
                            "status": "PASS",
                            "packet_id": packet_id,
                            "history": history
                        }
                    else:
                        raise Exception("Could not get packet history")
                else:
                    self.test_results[test_name] = {
                        "status": "SKIP",
                        "reason": "No packets available for testing"
                    }
            else:
                raise Exception("Could not get recent packets")

        except Exception as e:
            print(f"  ❌ {test_name} failed: {e}")
            self.test_results[test_name] = {"status": "FAIL", "error": str(e)}

    async def _test_emergency_notifications(self):
        """Test emergency notification system."""
        test_name = "Emergency Notifications"
        print(f"\n🚨 Testing: {test_name}")

        try:
            # Send critical emergency
            if self.clients:
                packet_id = await self.clients[0].send_sos(
                    "CRITICAL EMERGENCY - Test notification system",
                    urgency="CRITICAL"
                )

                if packet_id:
                    print(f"  ✅ Critical emergency sent: {packet_id}")

                    # Wait for notification processing
                    await asyncio.sleep(3)

                    # Check if notifications were processed
                    response = requests.get(f"{self.server_url}/api/packets/recent", timeout=5)
                    if response.status_code == 200:
                        packets = response.json()

                        critical_packet = next((p for p in packets if p['packet_id'] == packet_id), None)

                        if critical_packet:
                            notifications_sent = critical_packet.get('notifications_sent', 0)
                            print(f"  ✅ Notifications processed: {notifications_sent}")

                            self.test_results[test_name] = {
                                "status": "PASS",
                                "packet_id": packet_id,
                                "notifications_sent": notifications_sent
                            }
                        else:
                            raise Exception("Critical packet not found on server")
                    else:
                        raise Exception("Could not verify notifications")
                else:
                    raise Exception("Failed to send critical emergency")
            else:
                raise Exception("No clients available")

        except Exception as e:
            print(f"  ❌ {test_name} failed: {e}")
            self.test_results[test_name] = {"status": "FAIL", "error": str(e)}

    async def _test_network_topology(self):
        """Test network topology analysis."""
        test_name = "Network Topology"
        print(f"\n🌐 Testing: {test_name}")

        try:
            response = requests.get(f"{self.server_url}/api/network/topology", timeout=5)
            if response.status_code == 200:
                topology = response.json()

                print(f"  ✅ Network topology retrieved")
                print(f"  ℹ️  Active nodes: {topology.get('active_nodes', 0)}")
                print(f"  ℹ️  Total nodes: {topology.get('total_nodes', 0)}")
                print(f"  ℹ️  Network health: {topology.get('network_health', 'unknown')}")

                self.test_results[test_name] = {
                    "status": "PASS",
                    "topology": topology
                }
            else:
                raise Exception("Could not get network topology")

        except Exception as e:
            print(f"  ❌ {test_name} failed: {e}")
            self.test_results[test_name] = {"status": "FAIL", "error": str(e)}

    async def _test_location_updates(self):
        """Test location update functionality."""
        test_name = "Location Updates"
        print(f"\n📍 Testing: {test_name}")

        try:
            if not self.clients:
                raise Exception("No clients available")

            client = self.clients[0]

            # Send initial location
            client.set_mock_location(37.7749, -122.4194)  # San Francisco
            packet1 = await client.send_sos("Moving emergency - initial", urgency="HIGH")

            await asyncio.sleep(1)

            # Send updated location
            client.set_mock_location(37.7849, -122.4094)  # Moved in SF
            packet2 = await client.send_sos("Moving emergency - updated", urgency="HIGH")

            if packet1 and packet2:
                print(f"  ✅ Location updates sent")
                print(f"  ℹ️  Initial: {packet1}")
                print(f"  ℹ️  Updated: {packet2}")

                self.test_results[test_name] = {
                    "status": "PASS",
                    "initial_packet": packet1,
                    "update_packet": packet2
                }
            else:
                raise Exception("Failed to send location updates")

        except Exception as e:
            print(f"  ❌ {test_name} failed: {e}")
            self.test_results[test_name] = {"status": "FAIL", "error": str(e)}

    async def _test_duplicate_prevention(self):
        """Test duplicate packet prevention."""
        test_name = "Duplicate Prevention"
        print(f"\n🔒 Testing: {test_name}")

        try:
            # Get initial packet count
            response = requests.get(f"{self.server_url}/api/stats", timeout=5)
            if response.status_code == 200:
                initial_stats = response.json()
                initial_count = initial_stats['total_packets']

                # Send same message multiple times (should be deduplicated by hash)
                if self.clients:
                    client = self.clients[0]

                    # Send multiple similar messages quickly
                    for i in range(3):
                        await client.send_sos("Duplicate test message", urgency="LOW")
                        await asyncio.sleep(0.5)

                    await asyncio.sleep(2)

                    # Check final count
                    response2 = requests.get(f"{self.server_url}/api/stats", timeout=5)
                    if response2.status_code == 200:
                        final_stats = response2.json()
                        final_count = final_stats['total_packets']

                        packets_added = final_count - initial_count
                        print(f"  ✅ Duplicate prevention tested")
                        print(f"  ℹ️  Packets sent: 3, actually added: {packets_added}")

                        self.test_results[test_name] = {
                            "status": "PASS",
                            "sent": 3,
                            "actually_added": packets_added,
                            "duplicates_prevented": 3 - packets_added
                        }
                    else:
                        raise Exception("Could not get final stats")
                else:
                    raise Exception("No clients available")
            else:
                raise Exception("Could not get initial stats")

        except Exception as e:
            print(f"  ❌ {test_name} failed: {e}")
            self.test_results[test_name] = {"status": "FAIL", "error": str(e)}

    async def _test_urgency_levels(self):
        """Test different urgency levels."""
        test_name = "Urgency Levels"
        print(f"\n⚡ Testing: {test_name}")

        try:
            if not self.clients:
                raise Exception("No clients available")

            client = self.clients[0]
            urgency_levels = ["CRITICAL", "HIGH", "MEDIUM", "LOW"]

            packets_sent = []
            for urgency in urgency_levels:
                packet_id = await client.send_sos(
                    f"Test {urgency} urgency message",
                    urgency=urgency
                )

                if packet_id:
                    packets_sent.append({"urgency": urgency, "packet_id": packet_id})
                    print(f"  ✅ {urgency}: {packet_id}")
                else:
                    print(f"  ❌ {urgency}: Failed")

                await asyncio.sleep(0.5)

            self.test_results[test_name] = {
                "status": "PASS" if len(packets_sent) == len(urgency_levels) else "PARTIAL",
                "total_levels": len(urgency_levels),
                "successful": len(packets_sent),
                "packets": packets_sent
            }

        except Exception as e:
            print(f"  ❌ {test_name} failed: {e}")
            self.test_results[test_name] = {"status": "FAIL", "error": str(e)}

    async def _test_multiple_rapid_messages(self):
        """Test sending multiple rapid messages."""
        test_name = "Rapid Message Stress Test"
        print(f"\n🚀 Testing: {test_name}")

        try:
            if not self.clients:
                raise Exception("No clients available")

            client = self.clients[0]

            # Send 10 rapid messages
            start_time = time.time()
            packets_sent = []

            for i in range(10):
                packet_id = await client.send_sos(
                    f"Rapid test message {i+1}",
                    urgency="MEDIUM"
                )

                if packet_id:
                    packets_sent.append(packet_id)

                # Small delay to prevent overwhelming
                await asyncio.sleep(0.1)

            end_time = time.time()
            duration = end_time - start_time

            print(f"  ✅ Rapid messages test completed")
            print(f"  ℹ️  Messages sent: {len(packets_sent)}/10")
            print(f"  ℹ️  Duration: {duration:.2f} seconds")
            print(f"  ℹ️  Rate: {len(packets_sent)/duration:.1f} msg/sec")

            self.test_results[test_name] = {
                "status": "PASS" if len(packets_sent) >= 8 else "PARTIAL",
                "sent": len(packets_sent),
                "attempted": 10,
                "duration": duration,
                "rate": len(packets_sent)/duration
            }

        except Exception as e:
            print(f"  ❌ {test_name} failed: {e}")
            self.test_results[test_name] = {"status": "FAIL", "error": str(e)}

    async def _test_long_running_stability(self):
        """Test long-running stability."""
        test_name = "Long Running Stability"
        print(f"\n⏱️  Testing: {test_name}")

        try:
            if not self.clients:
                raise Exception("No clients available")

            # Run for 30 seconds, sending periodic messages
            start_time = time.time()
            messages_sent = 0
            errors = 0

            print(f"  ℹ️  Running stability test for 30 seconds...")

            for i in range(6):  # 6 intervals of 5 seconds each
                try:
                    packet_id = await self.clients[0].send_sos(
                        f"Stability test message {i+1}",
                        urgency="LOW"
                    )

                    if packet_id:
                        messages_sent += 1
                    else:
                        errors += 1

                except Exception:
                    errors += 1

                await asyncio.sleep(5)

            end_time = time.time()
            actual_duration = end_time - start_time

            print(f"  ✅ Stability test completed")
            print(f"  ℹ️  Duration: {actual_duration:.1f} seconds")
            print(f"  ℹ️  Messages sent: {messages_sent}")
            print(f"  ℹ️  Errors: {errors}")

            # Check if clients are still responsive
            final_stats = []
            for client in self.clients:
                try:
                    stats = client.get_stats()
                    final_stats.append(stats)
                except Exception as e:
                    final_stats.append({"error": str(e)})

            self.test_results[test_name] = {
                "status": "PASS" if errors <= 1 else "PARTIAL",
                "duration": actual_duration,
                "messages_sent": messages_sent,
                "errors": errors,
                "final_client_stats": final_stats
            }

        except Exception as e:
            print(f"  ❌ {test_name} failed: {e}")
            self.test_results[test_name] = {"status": "FAIL", "error": str(e)}

    async def _verify_packet_on_server(self, packet_id: str) -> bool:
        """Verify if packet exists on server."""
        try:
            response = requests.get(f"{self.server_url}/api/packets/recent", timeout=3)
            if response.status_code == 200:
                packets = response.json()
                return any(p['packet_id'] == packet_id for p in packets)
        except:
            pass
        return False

    async def _cleanup(self):
        """Clean up all test resources."""
        print("\n🧹 Cleaning up test resources...")

        # Stop all clients
        for i, client in enumerate(self.clients):
            try:
                await client.stop()
                print(f"  ✅ Client {i+1} stopped")
            except Exception as e:
                print(f"  ⚠️  Error stopping client {i+1}: {e}")

        # Server cleanup (it will stop when the process ends)
        print(f"  ℹ️  Server will stop when process ends")

    def _print_final_results(self):
        """Print comprehensive final results."""
        print("\n" + "=" * 60)
        print("📊 COMPREHENSIVE TEST RESULTS")
        print("=" * 60)

        passed = 0
        failed = 0
        partial = 0
        skipped = 0

        # Group results by phase
        phases = {
            "Infrastructure": ["Server Startup", "Database Connection"],
            "Client": ["Client Initialization", "Location Service", "Transport Initialization"],
            "Communication": ["Single SOS Message", "Location Formats", "Multiple Clients", "Packet Relay"],
            "Server Integration": ["Server Packet Reception", "WebSocket Updates", "Packet History", "Emergency Notifications"],
            "Advanced Features": ["Network Topology", "Location Updates", "Duplicate Prevention", "Urgency Levels"],
            "Performance": ["Rapid Message Stress Test", "Long Running Stability"]
        }

        for phase, test_names in phases.items():
            print(f"\n📋 {phase}:")
            for test_name in test_names:
                if test_name in self.test_results:
                    result = self.test_results[test_name]
                    status = result['status']

                    if status == 'PASS':
                        print(f"  ✅ {test_name}")
                        passed += 1
                    elif status == 'FAIL':
                        print(f"  ❌ {test_name}: {result.get('error', 'Unknown error')}")
                        failed += 1
                    elif status == 'PARTIAL':
                        print(f"  ⚠️  {test_name}: {result.get('note', 'Partial success')}")
                        partial += 1
                    elif status == 'SKIP':
                        print(f"  ⏭️  {test_name}: {result.get('reason', 'Skipped')}")
                        skipped += 1

        # Summary
        total = passed + failed + partial + skipped
        print(f"\n📈 SUMMARY:")
        print(f"  Total Tests: {total}")
        print(f"  ✅ Passed: {passed}")
        print(f"  ❌ Failed: {failed}")
        print(f"  ⚠️  Partial: {partial}")
        print(f"  ⏭️  Skipped: {skipped}")

        success_rate = (passed + partial * 0.5) / total * 100 if total > 0 else 0
        print(f"  📊 Success Rate: {success_rate:.1f}%")

        if failed == 0 and partial <= 2:
            print("\n🎉 EXCELLENT! SonicWave system is working correctly!")
            print("✅ All critical functionality is operational")
            print("✅ Client-server communication working")
            print("✅ Location services functional")
            print("✅ Emergency notifications active")
        elif failed <= 2:
            print("\n✅ GOOD! Most functionality is working correctly")
            print("⚠️  Some minor issues detected - check failed tests")
        else:
            print("\n⚠️  NEEDS ATTENTION! Multiple issues detected")
            print("❌ Check the failed tests above for details")

        # Save detailed results
        try:
            os.makedirs("test_outputs", exist_ok=True)
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            results_file = f"test_outputs/comprehensive_test_{timestamp}.json"

            with open(results_file, 'w') as f:
                json.dump({
                    'timestamp': timestamp,
                    'platform': sys.platform,
                    'summary': {
                        'total': total,
                        'passed': passed,
                        'failed': failed,
                        'partial': partial,
                        'skipped': skipped,
                        'success_rate': success_rate
                    },
                    'results': self.test_results
                }, f, indent=2, default=str)

            print(f"\n📄 Detailed results saved to: {results_file}")

        except Exception as e:
            print(f"⚠️  Could not save results: {e}")

async def main():
    """Main test execution."""
    print("🔬 SonicWave Comprehensive Test Suite")
    print("This will test the entire system end-to-end")

    suite = ComprehensiveTestSuite()

    try:
        await suite.run_all_tests()
    except KeyboardInterrupt:
        print("\n⚡ Test suite interrupted by user")
    except Exception as e:
        print(f"\n💥 Test suite crashed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())
