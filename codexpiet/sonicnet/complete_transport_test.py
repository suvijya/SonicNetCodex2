"""
Complete Transport Test - Test ALL transports (UDP, BLE, GGWave) sending and receiving
"""

import asyncio
import logging
import sys
import os
from datetime import datetime

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from enhanced_client import SonicWaveClient
from packet import UrgencyLevel, PacketType

async def comprehensive_transport_test():
    """Test all transports with actual packet transmission and reception."""
    print("🚀 COMPREHENSIVE TRANSPORT TEST")
    print("=" * 60)
    print("Testing UDP, BLE, and GGWave transports")
    print("=" * 60)

    # Setup logging to see detailed transport activity
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    # Create client
    client = SonicWaveClient("TransportTest")

    # Track all received packets
    received_packets = []
    transport_activity = {}

    def on_packet_received(packet):
        received_packets.append(packet)
        transport_info = {
            'type': packet.packet_type.value,
            'sender': packet.sender_id,
            'message': packet.message[:30] + "..." if len(packet.message) > 30 else packet.message,
            'received_via': packet.received_via,
            'timestamp': datetime.now().strftime('%H:%M:%S')
        }
        transport_activity[packet.packet_id] = transport_info

        print(f"\n📨 PACKET RECEIVED!")
        print(f"   Type: {packet.packet_type.value}")
        print(f"   From: {packet.sender_id}")
        print(f"   Via: {packet.received_via}")
        print(f"   Message: {transport_info['message']}")
        print(f"   Time: {transport_info['timestamp']}")

    client.register_event_callback('packet_received', on_packet_received)

    try:
        print("🔧 Starting SonicNet client with all transports...")
        await client.start()

        # Wait for full initialization
        await asyncio.sleep(3)

        print("\n📊 INITIAL TRANSPORT STATUS:")
        stats = client.get_comprehensive_stats()

        active_transports = []
        for transport_name, transport_stats in stats['transport_stats'].items():
            status = "🟢 ACTIVE" if transport_stats.get('running', False) else "🔴 INACTIVE"
            print(f"  {transport_name}: {status}")

            if transport_stats.get('running', False):
                active_transports.append(transport_name)

            # Show specific stats for each transport
            if transport_name == "UDPMeshTransport":
                print(f"    Multicast: {transport_stats.get('multicast_group', 'N/A')}:{transport_stats.get('port', 'N/A')}")
            elif transport_name == "GGWaveTransport":
                print(f"    Audio Available: {transport_stats.get('audio_available', 'N/A')}")
                print(f"    Volume: {transport_stats.get('volume', 'N/A')}")
            elif transport_name == "BLEMeshTransport":
                print(f"    Peers Discovered: {transport_stats.get('discovered_peers', 0)}")
                print(f"    Connected Peers: {transport_stats.get('connected_peers', 0)}")

        print(f"\n✅ Active Transports: {len(active_transports)}")

        if len(active_transports) == 0:
            print("❌ NO TRANSPORTS ACTIVE - Test cannot proceed")
            return

        print(f"\n🔥 TESTING PACKET TRANSMISSION...")
        print(f"Will send test packets via all active transports")

        # Test 1: Send SOS packet
        print(f"\n1️⃣ Sending SOS packet...")
        sos_packet = await client.send_sos(
            "TRANSPORT TEST: SOS packet via all transports",
            UrgencyLevel.HIGH
        )
        print(f"   📤 SOS sent: {sos_packet.packet_id}")

        # Wait for processing
        await asyncio.sleep(5)

        # Test 2: Send status update
        print(f"\n2️⃣ Sending status update...")
        status_packet = await client.send_status_update(
            "Transport test status update",
            sos_packet.thread_id
        )
        print(f"   📤 Status update sent: {status_packet.packet_id}")

        await asyncio.sleep(3)

        # Test 3: Send all clear
        print(f"\n3️⃣ Sending all clear...")
        clear_packet = await client.send_all_clear(sos_packet.thread_id)
        print(f"   📤 All clear sent: {clear_packet.packet_id}")

        await asyncio.sleep(3)

        print(f"\n📊 FINAL TRANSPORT STATISTICS:")
        final_stats = client.get_comprehensive_stats()

        for transport_name, transport_stats in final_stats['transport_stats'].items():
            print(f"\n  🚀 {transport_name}:")
            print(f"    Status: {'🟢 ACTIVE' if transport_stats.get('running', False) else '🔴 INACTIVE'}")

            # Common stats
            if 'packets_sent' in transport_stats:
                print(f"    Packets Sent: {transport_stats['packets_sent']}")
            if 'packets_received' in transport_stats:
                print(f"    Packets Received: {transport_stats['packets_received']}")

            # Transport-specific stats
            if transport_name == "UDPMeshTransport":
                print(f"    Send Errors: {transport_stats.get('send_errors', 0)}")
                print(f"    Receive Errors: {transport_stats.get('receive_errors', 0)}")
            elif transport_name == "GGWaveTransport":
                print(f"    Messages Sent: {transport_stats.get('messages_sent', 0)}")
                print(f"    Audio Errors: {transport_stats.get('audio_errors', 0)}")
            elif transport_name == "BLEMeshTransport":
                print(f"    Connection Failures: {transport_stats.get('connection_failures', 0)}")
                print(f"    Peers Discovered: {transport_stats.get('discovered_peers', 0)}")

        # Overall network stats
        print(f"\n📈 OVERALL NETWORK STATS:")
        packet_stats = final_stats['packet_stats']
        print(f"  Total Packets Sent: {packet_stats['packets_sent']}")
        print(f"  Total Packets Received: {packet_stats['packets_received']}")
        print(f"  Packets Relayed: {packet_stats['packets_relayed']}")
        print(f"  Cache Size: {packet_stats['cache_size']}")

        # Reception analysis
        print(f"\n📨 PACKET RECEPTION ANALYSIS:")
        print(f"  Packets Received: {len(received_packets)}")

        if received_packets:
            print(f"  Reception Details:")
            for packet_id, info in transport_activity.items():
                print(f"    📦 {packet_id[:8]}: {info['type']} via {info['received_via']} at {info['timestamp']}")
        else:
            print(f"  ℹ️  No packets received (normal for single-device test)")
            print(f"      Packets are being transmitted but need another device to receive")

        await client.stop()

        # Final assessment
        print(f"\n🎯 TRANSPORT ASSESSMENT:")

        working_transports = []
        partially_working = []
        failed_transports = []

        for transport_name, transport_stats in final_stats['transport_stats'].items():
            if transport_stats.get('running', False):
                # Check if transport actually sent packets
                sent_packets = (transport_stats.get('packets_sent', 0) +
                               transport_stats.get('messages_sent', 0))
                errors = (transport_stats.get('send_errors', 0) +
                         transport_stats.get('audio_errors', 0) +
                         transport_stats.get('connection_failures', 0))

                if sent_packets > 0 and errors == 0:
                    working_transports.append(transport_name)
                elif sent_packets > 0:
                    partially_working.append(transport_name)
                else:
                    failed_transports.append(transport_name)
            else:
                failed_transports.append(transport_name)

        print(f"  ✅ Fully Working: {working_transports}")
        print(f"  ⚠️  Partially Working: {partially_working}")
        print(f"  ❌ Not Working: {failed_transports}")

        if len(working_transports) > 0:
            print(f"\n🌟 SUCCESS! {len(working_transports)} transport(s) are fully functional!")
            print(f"🚀 Your SonicNet client can communicate via: {', '.join(working_transports)}")

        if len(working_transports) >= 2:
            print(f"🎉 MESH NETWORKING READY! Multiple transports working for redundancy!")

        return working_transports, partially_working, failed_transports

    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return [], [], ["ALL"]

if __name__ == "__main__":
    print("🧪 This will test ALL transports and show actual packet transmission")
    print("📡 Make sure your speakers are on to hear GGWave audio transmission")
    input("Press Enter to start comprehensive transport test...")

    working, partial, failed = asyncio.run(comprehensive_transport_test())

    print(f"\n" + "="*60)
    print(f"🏁 TEST COMPLETE!")
    print(f"✅ Working: {len(working)} transports")
    print(f"⚠️  Partial: {len(partial)} transports")
    print(f"❌ Failed: {len(failed)} transports")
    print(f"="*60)
