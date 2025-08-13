#!/usr/bin/env python3
"""
Quick BLE client test to identify the specific async issues.
"""

import asyncio
import sys
import traceback
import logging

# Set up basic logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

async def test_client_basic():
    """Test the basic client functionality."""
    try:
        print("🔧 Testing SonicWave client...")

        # Set Windows event loop policy
        if sys.platform == 'win32':
            asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())
            print("✅ Set Windows ProactorEventLoop policy")

        from client import SonicWaveClient
        print("✅ Client imported successfully")

        client = SonicWaveClient()
        print(f"✅ Client created: {client.node_id}")

        # Start the client
        print("🚀 Starting client...")
        await client.start()
        print("✅ Client started successfully")

        # Wait a bit to let it initialize
        await asyncio.sleep(3)

        # Send a test SOS
        print("📤 Sending test SOS...")
        packet_id = await client.send_sos("Test SOS from BLE client", "Test Location")
        if packet_id:
            print(f"✅ SOS sent successfully: {packet_id}")
        else:
            print("❌ Failed to send SOS")

        # Get stats
        stats = client.get_stats()
        print("📊 Client stats:")
        print(f"  Running: {stats['running']}")
        print(f"  Active transports: {stats['client']['transports_active']}")
        print(f"  Messages sent: {stats['client']['messages_sent']}")

        # Check BLE specifically
        for transport_name, transport_stats in stats['transports'].items():
            if 'BLE' in transport_name:
                print(f"🔵 BLE Transport ({transport_name}):")
                for key, value in transport_stats.items():
                    print(f"    {key}: {value}")

        # Get BLE peers
        ble_peers = client.get_ble_peers()
        print(f"📱 BLE peers discovered: {len(ble_peers)}")

        # Wait a bit more to see activity
        print("⏳ Waiting to observe BLE activity...")
        await asyncio.sleep(10)

        # Final stats
        final_stats = client.get_stats()
        print("📊 Final stats:")
        for transport_name, transport_stats in final_stats['transports'].items():
            if 'BLE' in transport_name:
                print(f"🔵 {transport_name} final stats:")
                for key, value in transport_stats.items():
                    print(f"    {key}: {value}")

        # Stop the client
        print("🛑 Stopping client...")
        await client.stop()
        print("✅ Client stopped")

        return True

    except Exception as e:
        print(f"❌ Test failed: {e}")
        traceback.print_exc()
        return False

def main():
    """Main function."""
    print("🚀 SonicWave BLE Client Test")
    print("=" * 40)

    try:
        result = asyncio.run(test_client_basic())
        if result:
            print("\n🎉 Test completed successfully!")
        else:
            print("\n💥 Test failed!")
    except KeyboardInterrupt:
        print("\n⚡ Test interrupted")
    except Exception as e:
        print(f"\n💥 Test crashed: {e}")
        traceback.print_exc()

if __name__ == "__main__":
    main()
