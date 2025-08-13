"""
All Transports Test - Test UDP, BLE, and GGWave sending/receiving with file output
"""

import sys
import os
import asyncio
import json
from datetime import datetime

# Add the current directory to Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def write_test_result(filename, data):
    """Write test results to file."""
    output_dir = os.path.join(os.path.dirname(__file__), 'test_outputs')
    os.makedirs(output_dir, exist_ok=True)
    filepath = os.path.join(output_dir, filename)

    with open(filepath, 'w', encoding='utf-8') as f:
        if isinstance(data, dict):
            json.dump(data, f, indent=2, default=str)
        else:
            f.write(str(data))

    print(f"📝 Results written to: {filepath}")

async def test_all_transports():
    """Test all three transports: UDP, BLE, and GGWave."""

    test_results = {
        'timestamp': datetime.now().isoformat(),
        'test_name': 'All Transports Send/Receive Test',
        'transports_tested': ['UDP', 'BLE', 'GGWave'],
        'results': {}
    }

    print("🚀 ALL TRANSPORTS TEST - UDP + BLE + GGWave")
    print("=" * 60)

    try:
        from enhanced_client import SonicWaveClient
        from packet import UrgencyLevel

        # Create test client
        client = SonicWaveClient("AllTransportsTest")

        # Track received packets
        received_packets = []

        def on_packet_received(packet):
            received_packets.append({
                'packet_id': packet.packet_id,
                'type': packet.packet_type.value,
                'sender': packet.sender_id,
                'message': packet.message,
                'received_via': packet.received_via,
                'timestamp': datetime.now().isoformat()
            })
            print(f"📨 RECEIVED: {packet.packet_type.value} from {packet.sender_id}")

        client.register_event_callback('packet_received', on_packet_received)

        print("🔧 Starting SonicNet client with all transports...")
        await client.start()

        # Wait for initialization
        await asyncio.sleep(3)

        # Get initial transport status
        stats = client.get_comprehensive_stats()
        initial_transport_status = {}

        for transport_name, transport_stats in stats['transport_stats'].items():
            running = transport_stats.get('running', False)
            initial_transport_status[transport_name] = {
                'running': running,
                'initial_stats': transport_stats
            }
            status = "🟢 ACTIVE" if running else "🔴 INACTIVE"
            print(f"  {transport_name}: {status}")

        test_results['results']['initial_status'] = initial_transport_status

        # Count active transports
        active_transports = [name for name, status in initial_transport_status.items()
                           if status['running']]

        print(f"\n✅ Active transports: {len(active_transports)}")
        print(f"   {', '.join(active_transports)}")

        if len(active_transports) == 0:
            test_results['results']['error'] = "No transports active"
            return test_results

        # Test packet transmission
        print(f"\n🔥 TESTING PACKET TRANSMISSION...")

        # Send test packets
        test_packets = []

        # Test 1: Critical SOS
        print("1️⃣ Sending CRITICAL SOS...")
        sos1 = await client.send_sos(
            "CRITICAL: All transports test - emergency packet",
            UrgencyLevel.CRITICAL
        )
        test_packets.append(('CRITICAL_SOS', sos1.packet_id))
        await asyncio.sleep(2)

        # Test 2: High priority SOS
        print("2️⃣ Sending HIGH priority SOS...")
        sos2 = await client.send_sos(
            "HIGH: Multi-transport mesh test packet",
            UrgencyLevel.HIGH
        )
        test_packets.append(('HIGH_SOS', sos2.packet_id))
        await asyncio.sleep(2)

        # Test 3: Status update
        print("3️⃣ Sending status update...")
        status_update = await client.send_status_update(
            "Status: All transports operational",
            sos1.thread_id
        )
        test_packets.append(('STATUS_UPDATE', status_update.packet_id))
        await asyncio.sleep(2)

        # Test 4: All clear
        print("4️⃣ Sending all clear...")
        all_clear = await client.send_all_clear(sos1.thread_id)
        test_packets.append(('ALL_CLEAR', all_clear.packet_id))
        await asyncio.sleep(3)

        # Get final transport statistics
        final_stats = client.get_comprehensive_stats()
        final_transport_status = {}

        print(f"\n📊 FINAL TRANSPORT STATISTICS:")
        for transport_name, transport_stats in final_stats['transport_stats'].items():
            final_transport_status[transport_name] = transport_stats

            print(f"\n🚀 {transport_name}:")
            print(f"   Status: {'🟢 ACTIVE' if transport_stats.get('running', False) else '🔴 INACTIVE'}")

            # Show packets sent/received
            packets_sent = (transport_stats.get('packets_sent', 0) +
                           transport_stats.get('messages_sent', 0))
            packets_received = (transport_stats.get('packets_received', 0) +
                               transport_stats.get('messages_received', 0))

            print(f"   Packets Sent: {packets_sent}")
            print(f"   Packets Received: {packets_received}")

            # Show errors
            errors = (transport_stats.get('send_errors', 0) +
                     transport_stats.get('audio_errors', 0) +
                     transport_stats.get('system_errors', 0))
            print(f"   Errors: {errors}")

            # Transport-specific info
            if transport_name == "BLEMeshTransport":
                print(f"   BLE System Works: {transport_stats.get('ble_system_works', False)}")
                print(f"   Discovered Peers: {transport_stats.get('discovered_peers', 0)}")
            elif transport_name == "GGWaveTransport":
                print(f"   Audio Available: {transport_stats.get('audio_available', False)}")
            elif transport_name == "UDPMeshTransport":
                print(f"   Multicast: {transport_stats.get('multicast_group', 'N/A')}")

        test_results['results']['final_status'] = final_transport_status
        test_results['results']['test_packets'] = test_packets
        test_results['results']['received_packets'] = received_packets

        # Overall network stats
        network_stats = final_stats['packet_stats']
        print(f"\n📈 OVERALL NETWORK STATS:")
        print(f"   Total Packets Sent: {network_stats['packets_sent']}")
        print(f"   Total Packets Received: {network_stats['packets_received']}")
        print(f"   Packets Relayed: {network_stats['packets_relayed']}")

        test_results['results']['network_stats'] = network_stats

        # Reception analysis
        print(f"\n📨 PACKET RECEPTION ANALYSIS:")
        print(f"   Test Packets Sent: {len(test_packets)}")
        print(f"   Packets Received: {len(received_packets)}")

        if received_packets:
            print(f"   Reception Details:")
            for packet in received_packets:
                print(f"     📦 {packet['packet_id'][:8]}: {packet['type']} via {packet['received_via']}")

        await client.stop()

        # Final assessment
        print(f"\n🎯 TRANSPORT ASSESSMENT:")

        working_transports = []
        partial_transports = []
        failed_transports = []

        for transport_name, transport_stats in final_transport_status.items():
            packets_sent = (transport_stats.get('packets_sent', 0) +
                           transport_stats.get('messages_sent', 0))
            errors = (transport_stats.get('send_errors', 0) +
                     transport_stats.get('audio_errors', 0) +
                     transport_stats.get('system_errors', 0))
            running = transport_stats.get('running', False)

            if running and packets_sent > 0 and errors == 0:
                working_transports.append(transport_name)
            elif running and packets_sent > 0:
                partial_transports.append(transport_name)
            else:
                failed_transports.append(transport_name)

        test_results['results']['assessment'] = {
            'working': working_transports,
            'partial': partial_transports,
            'failed': failed_transports
        }

        print(f"  ✅ Fully Working: {working_transports}")
        print(f"  ⚠️  Partially Working: {partial_transports}")
        print(f"  ❌ Not Working: {failed_transports}")

        # Success metrics
        total_working = len(working_transports) + len(partial_transports)

        if total_working >= 2:
            print(f"\n🎉 EXCELLENT! {total_working} transports working - MESH READY!")
            test_results['results']['overall_status'] = 'EXCELLENT'
        elif total_working == 1:
            print(f"\n👍 GOOD! {total_working} transport working - Basic functionality")
            test_results['results']['overall_status'] = 'GOOD'
        else:
            print(f"\n❌ ISSUES! No transports working properly")
            test_results['results']['overall_status'] = 'FAILED'

        return test_results

    except Exception as e:
        test_results['results']['error'] = str(e)
        test_results['results']['overall_status'] = 'ERROR'
        print(f"❌ Test failed: {e}")
        import traceback
        test_results['results']['traceback'] = traceback.format_exc()
        return test_results

async def main():
    """Main test function."""
    print("🧪 Testing ALL transports: UDP + BLE + GGWave")
    print("📡 This will show which transports can send/receive packets")
    print()

    results = await test_all_transports()

    # Write detailed results to file
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    write_test_result(f'all_transports_test_{timestamp}.json', results)

    # Write summary
    working = results['results'].get('assessment', {}).get('working', [])
    partial = results['results'].get('assessment', {}).get('partial', [])
    failed = results['results'].get('assessment', {}).get('failed', [])

    summary = f"""
ALL TRANSPORTS TEST SUMMARY
===========================
Timestamp: {results['timestamp']}

RESULTS:
✅ Fully Working: {len(working)} transports
   {', '.join(working) if working else 'None'}

⚠️ Partially Working: {len(partial)} transports  
   {', '.join(partial) if partial else 'None'}

❌ Not Working: {len(failed)} transports
   {', '.join(failed) if failed else 'None'}

OVERALL STATUS: {results['results'].get('overall_status', 'UNKNOWN')}

RECOMMENDATION:
{'🎉 Your SonicNet mesh is ready for deployment!' if len(working) + len(partial) >= 2 else '🔧 Some transports need fixes for full mesh capability'}
"""

    write_test_result(f'transport_summary_{timestamp}.txt', summary)

    print("\n" + "="*60)
    print("🏁 ALL TRANSPORTS TEST COMPLETE!")
    print(f"✅ Working: {len(working)}")
    print(f"⚠️ Partial: {len(partial)}")
    print(f"❌ Failed: {len(failed)}")
    print("📄 Check test_outputs/ for detailed results")

if __name__ == "__main__":
    asyncio.run(main())
