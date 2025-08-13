#!/usr/bin/env python3
"""
Test script to understand bleak_py BLEDevice and other functions
"""

import asyncio
from bleak_py import discover, DeviceDiscover, BLEDevice, find_device_by_name, find_device_by_address

async def test_bleak_py_api():
    print("Testing bleak_py comprehensive API...")

    # Test BLEDevice class
    print("\n=== BLEDevice class ===")
    print(f"BLEDevice type: {type(BLEDevice)}")
    print(f"BLEDevice dir: {[x for x in dir(BLEDevice) if not x.startswith('_')]}")

    # Test find functions
    print("\n=== find_device_by_name function ===")
    try:
        result = await find_device_by_name("test")
        print(f"find_device_by_name result: {result}, type: {type(result)}")
    except Exception as e:
        print(f"find_device_by_name error: {e}")

    print("\n=== find_device_by_address function ===")
    try:
        result = await find_device_by_address("00:00:00:00:00:00")
        print(f"find_device_by_address result: {result}, type: {type(result)}")
    except Exception as e:
        print(f"find_device_by_address error: {e}")

    # Test discover again with more detailed inspection
    print("\n=== DeviceDiscover object detailed inspection ===")
    try:
        discoverer = await discover()
        print(f"Discoverer type: {type(discoverer)}")

        # Check if it has any private methods that might be useful
        all_attrs = [x for x in dir(discoverer)]
        print(f"All discoverer attributes: {all_attrs}")

        # Try to access some common private methods
        for attr in ['__dict__', '__class__', '__module__']:
            if hasattr(discoverer, attr):
                try:
                    value = getattr(discoverer, attr)
                    print(f"  {attr}: {value}")
                except Exception as e:
                    print(f"  {attr}: Error - {e}")

        # Check if it's a generator or has state
        print(f"Discoverer id: {id(discoverer)}")
        print(f"Discoverer hash: {hash(discoverer) if hasattr(discoverer, '__hash__') and discoverer.__hash__ is not None else 'Not hashable'}")

    except Exception as e:
        print(f"Error in discover detailed inspection: {e}")

if __name__ == "__main__":
    asyncio.run(test_bleak_py_api())
