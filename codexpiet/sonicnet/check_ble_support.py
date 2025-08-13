#!/usr/bin/env python3
"""
Quick BLE capability check for laptops
"""

import asyncio
import sys

async def check_ble_support():
    """Check if this laptop supports BLE."""
    print("🔍 Checking BLE Support on this laptop...")

    try:
        # Try to import bleak (BLE library)
        import bleak
        print("✅ Bleak library available")

        # Try to discover BLE devices
        print("🔍 Scanning for BLE devices...")
        scanner = bleak.BleakScanner()

        # Short scan to test capability
        devices = await scanner.discover(timeout=5.0)

        if devices:
            print(f"✅ BLE is working! Found {len(devices)} devices:")
            for i, device in enumerate(devices[:3]):  # Show first 3
                print(f"   {i+1}. {device.name or 'Unknown'} ({device.address})")
            if len(devices) > 3:
                print(f"   ... and {len(devices) - 3} more devices")
        else:
            print("⚠️  BLE hardware works but no devices found nearby")

        return True

    except ImportError:
        print("❌ Bleak library not installed")
        print("   Install with: pip install bleak")
        return False

    except Exception as e:
        print(f"❌ BLE not supported or error: {e}")
        print("   Possible reasons:")
        print("   - No Bluetooth adapter")
        print("   - Bluetooth disabled")
        print("   - Incompatible drivers")
        print("   - Permission issues")
        return False

if __name__ == "__main__":
    print(f"🔍 BLE Support Check for {sys.platform}")
    print("=" * 50)

    try:
        result = asyncio.run(check_ble_support())
        print("\n" + "=" * 50)
        if result:
            print("🎉 This laptop supports BLE! It should work with other BLE devices.")
        else:
            print("⚠️  This laptop may not support BLE mesh networking.")
            print("💡 UDP multicast will still work for same-network communication.")
    except KeyboardInterrupt:
        print("\n⚡ Check interrupted by user")
    except Exception as e:
        print(f"\n💥 Unexpected error: {e}")
