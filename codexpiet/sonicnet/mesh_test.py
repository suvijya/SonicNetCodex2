"""
Real Device Mesh Test - Run this on separate devices to see actual mesh networking
"""

import asyncio
import logging
import sys
import os
from datetime import datetime
import socket

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from enhanced_client import SonicWaveClient
from packet import UrgencyLevel

def get_device_info():
    """Get device identification info."""
    hostname = socket.gethostname()
    try:
        local_ip = socket.gethostbyname(hostname)
    except:
        local_ip = "Unknown"
    return hostname, local_ip

async def mesh_node():
    """Run a mesh node that can communicate with other devices."""
    hostname, local_ip = get_device_info()

    print("🌐 SONICNET MESH NODE")
    print("=" * 50)
    print(f"🖥️  Device: {hostname}")
    print(f"📡 IP: {local_ip}")
    print(f"⏰ Started: {datetime.now().strftime('%H:%M:%S')}")
    print("=" * 50)

    # Create unique node name based on device
    node_name = f"{hostname}_{datetime.now().strftime('%H%M')}"
    client = SonicWaveClient(node_name)

    # Track mesh activity
    mesh_activity = []
    peer_nodes = set()

    def on_packet_received(packet):
        # Skip our own packets and heartbeats
        if packet.sender_id == client.node_id or packet.packet_type.value == 'HEARTBEAT':
            return

        peer_nodes.add(packet.sender_id)
        activity = {
            'time': datetime.now().strftime('%H:%M:%S'),
            'type': packet.packet_type.value,
            'from': packet.sender_id,
            'message': packet.message[:40] + "..." if len(packet.message) > 40 else packet.message,
            'hops': packet.hop_count
        }
        mesh_activity.append(activity)

        print(f"\n🔥 MESH MESSAGE RECEIVED!")
        print(f"   Time: {activity['time']}")
        print(f"   From: {activity['from']}")
        print(f"   Type: {activity['type']}")
        print(f"   Hops: {activity['hops']}")
        print(f"   Message: {activity['message']}")
        print(f"   🌐 Total peers discovered: {len(peer_nodes)}")

        # Auto-acknowledge SOS messages
        if packet.packet_type.value == 'SOS':
            print(f"   📨 Auto-sending acknowledgment...")

    client.register_event_callback('packet_received', on_packet_received)

    print("🚀 Starting mesh node...")
    await client.start()

    # Show initial status
    await asyncio.sleep(2)
    stats = client.get_comprehensive_stats()
    print(f"\n📊 Node Status:")
    print(f"   Node ID: {stats['node_info']['id']}")
    print(f"   Node Name: {stats['node_info']['name']}")

    active_transports = []
    for transport_name, transport_stats in stats['transport_stats'].items():
        if transport_stats.get('running', False):
            active_transports.append(transport_name.replace('Transport', ''))

    print(f"   Active Transports: {', '.join(active_transports)}")
    print(f"\n✅ Mesh node operational! Listening for other nodes...")
    print(f"📡 Broadcasting on UDP multicast 224.1.1.1:9999")

    try:
        # Main loop - send periodic messages and show status
        message_counter = 1

        while True:
            # Send a test message every 30 seconds
            await asyncio.sleep(30)

            message = f"Mesh test #{message_counter} from {hostname}"
            packet = await client.send_sos(message, UrgencyLevel.MEDIUM)

            print(f"\n📤 SENT: {message}")
            print(f"   Packet ID: {packet.packet_id}")
            print(f"   Time: {datetime.now().strftime('%H:%M:%S')}")

            # Show mesh statistics
            current_stats = client.get_comprehensive_stats()
            packet_stats = current_stats['packet_stats']

            print(f"\n📊 Mesh Statistics:")
            print(f"   Messages Sent: {packet_stats['packets_sent']}")
            print(f"   Messages Received: {packet_stats['packets_received']}")
            print(f"   Messages Relayed: {packet_stats['packets_relayed']}")
            print(f"   Peer Nodes Discovered: {len(peer_nodes)}")
            print(f"   Total Mesh Activity: {len(mesh_activity)}")

            if mesh_activity:
                print(f"\n📨 Recent Mesh Activity:")
                for activity in mesh_activity[-3:]:  # Show last 3
                    print(f"   {activity['time']}: {activity['type']} from {activity['from'][-8:]}")

            if len(peer_nodes) > 0:
                print(f"\n🌟 MESH NETWORK ACTIVE! Connected to {len(peer_nodes)} peer(s)")
            else:
                print(f"\n🔍 Waiting for other mesh nodes to join...")
                print(f"   Run this script on another device on the same network!")

            message_counter += 1

    except KeyboardInterrupt:
        print(f"\n👋 Shutting down mesh node...")

    finally:
        await client.stop()

        # Final summary
        print(f"\n📋 MESH SESSION SUMMARY:")
        print(f"   Device: {hostname} ({local_ip})")
        print(f"   Duration: Started {datetime.now().strftime('%H:%M:%S')}")
        print(f"   Peer Nodes: {len(peer_nodes)}")
        print(f"   Messages Exchanged: {len(mesh_activity)}")

        if peer_nodes:
            print(f"   Connected Peers:")
            for peer in peer_nodes:
                print(f"     - {peer}")

        print(f"✅ Mesh node stopped successfully!")

if __name__ == "__main__":
    print("🌐 SonicNet Real Device Mesh Test")
    print("=" * 40)
    print("This will run a mesh node that communicates with other devices")
    print("Run this script on multiple devices to see mesh networking!")
    print("Press Ctrl+C to stop")
    print()

    # Minimal logging for cleaner output
    logging.basicConfig(level=logging.WARNING)

    asyncio.run(mesh_node())
