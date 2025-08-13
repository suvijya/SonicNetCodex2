#!/usr/bin/env python3
"""
SonicWave Client Usage Example
Simple example showing how to use the SonicWave emergency communication client.
"""

import asyncio
import logging
from datetime import datetime

from client import SonicWaveClient

# Setup basic logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(message)s')

async def basic_usage_example():
    """Basic example of using SonicWave client."""
    print("🚀 SonicWave Client Basic Usage Example")
    print("=" * 50)

    # Create and start the client
    client = SonicWaveClient()
    print(f"📱 Created client with ID: {client.node_id}")

    try:
        # Start the client (initializes all transports and services)
        await client.start()
        print("✅ Client started successfully!")

        # Set a test location for demonstration
        client.set_mock_location(40.7128, -74.0060)  # New York coordinates
        print("📍 Set mock location: New York City")

        # Send different types of SOS messages
        print("\n📤 Sending SOS messages...")

        # 1. Basic SOS with automatic location
        packet_id1 = await client.send_sos(
            message="Help! I'm lost in the city",
            urgency="HIGH"
        )
        print(f"✅ SOS sent (auto location): {packet_id1}")

        await asyncio.sleep(1)

        # 2. SOS with manual location text
        packet_id2 = await client.send_sos(
            message="Car accident on highway",
            location="I-95 near Exit 15",
            urgency="CRITICAL"
        )
        print(f"✅ SOS sent (manual location): {packet_id2}")

        await asyncio.sleep(1)

        # 3. SOS with specific coordinates
        packet_id3 = await client.send_sos_with_coordinates(
            message="Hiking emergency in mountains",
            latitude=34.0522,
            longitude=-118.2437,
            altitude=500.0,
            urgency="HIGH"
        )
        print(f"✅ SOS sent (coordinates): {packet_id3}")

        await asyncio.sleep(2)

        # Check client statistics
        stats = client.get_stats()
        print(f"\n📊 Client Statistics:")
        print(f"   Messages sent: {stats['client']['messages_sent']}")
        print(f"   Active transports: {stats['client']['transports_active']}")
        print(f"   Running: {stats['running']}")

        # Check location info
        location_info = await client.get_current_location_info()
        print(f"\n📍 Location Information:")
        print(f"   Available: {location_info.get('available')}")
        if location_info.get('available'):
            print(f"   Coordinates: {location_info['latitude']:.6f}, {location_info['longitude']:.6f}")
            print(f"   Formatted: {location_info['formatted']}")

        # Check BLE peers (if any discovered)
        ble_peers = client.get_ble_peers()
        print(f"\n📡 BLE Network:")
        print(f"   Discovered peers: {len(ble_peers)}")

        print(f"\n⏳ Keeping client running for 30 seconds...")
        print(f"   (This allows time for mesh network communication)")
        await asyncio.sleep(30)

    except Exception as e:
        print(f"❌ Error: {e}")
    finally:
        # Always stop the client cleanly
        await client.stop()
        print("🛑 Client stopped successfully")

async def advanced_usage_example():
    """Advanced example with multiple location updates."""
    print("\n🔬 Advanced Usage: Moving Emergency Scenario")
    print("=" * 50)

    client = SonicWaveClient()

    try:
        await client.start()
        print("✅ Client started for advanced demo")

        # Simulate a moving emergency
        locations = [
            (40.7589, -73.9851, "Times Square, NYC"),
            (40.7614, -73.9776, "Moving towards Central Park"),
            (40.7829, -73.9654, "Now at Central Park")
        ]

        for i, (lat, lon, description) in enumerate(locations):
            print(f"\n📍 Location update {i+1}: {description}")

            # Update location
            client.set_mock_location(lat, lon)

            # Send update
            packet_id = await client.send_sos(
                message=f"Moving emergency - update {i+1}: {description}",
                urgency="HIGH"
            )

            print(f"✅ Update sent: {packet_id}")
            await asyncio.sleep(5)

        print("\n✅ Moving emergency scenario completed")

    except Exception as e:
        print(f"❌ Error in advanced demo: {e}")
    finally:
        await client.stop()

async def monitoring_example():
    """Example of monitoring client status."""
    print("\n📊 Monitoring Example")
    print("=" * 30)

    client = SonicWaveClient()

    try:
        await client.start()

        # Monitor for 15 seconds
        for i in range(3):
            print(f"\n⏱️  Status check {i+1}:")

            # Get comprehensive stats
            stats = client.get_stats()
            print(f"   Messages sent: {stats['client']['messages_sent']}")
            print(f"   Messages received: {stats['client']['messages_received']}")
            print(f"   Errors: {stats['client']['errors']}")
            print(f"   Queue size: {stats['queue_size']}")
            print(f"   Cached packets: {stats['packet_cache_size']}")

            # Check transport status
            transport_results = await client.test_transports()
            for transport_name, result in transport_results.items():
                status = "✅" if result.get('running') else "❌"
                print(f"   {status} {transport_name}")

            await asyncio.sleep(5)

    except Exception as e:
        print(f"❌ Monitoring error: {e}")
    finally:
        await client.stop()

async def main():
    """Main example function."""
    print("📱 SonicWave Client Examples")
    print(f"⏰ Started at: {datetime.now()}")
    print("\nThis example shows how to use the SonicWave emergency client.")
    print("The client will automatically:")
    print("  • Initialize BLE and UDP transports")
    print("  • Connect location services")
    print("  • Send emergency messages to the mesh network")
    print("  • Forward messages to the central server")

    try:
        # Run basic example
        await basic_usage_example()

        # Wait between examples
        await asyncio.sleep(2)

        # Run advanced example
        await advanced_usage_example()

        # Wait between examples
        await asyncio.sleep(2)

        # Run monitoring example
        await monitoring_example()

        print("\n🎉 All examples completed successfully!")
        print("\n💡 Tips for real usage:")
        print("  • Run the server (python server.py) to see messages in dashboard")
        print("  • Use multiple clients to test mesh networking")
        print("  • Enable real GPS on mobile devices for actual coordinates")
        print("  • Configure rescue authorities in the server database")

    except KeyboardInterrupt:
        print("\n⚡ Examples interrupted by user")
    except Exception as e:
        print(f"\n💥 Example failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(main())
