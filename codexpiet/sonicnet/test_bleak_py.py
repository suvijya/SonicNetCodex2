#!/usr/bin/env python3
"""
Test script to understand bleak_py API
"""

import asyncio
from bleak_py import discover, DeviceDiscover

async def test_discover():
    print("Testing bleak_py discover function...")

    try:
        discoverer = await discover()
        print(f"Discoverer type: {type(discoverer)}")
        print(f"Discoverer dir: {[x for x in dir(discoverer) if not x.startswith('_')]}")
        print(f"Discoverer repr: {repr(discoverer)}")
        print(f"Discoverer str: {str(discoverer)}")

        # Try different ways to check if it's iterable
        try:
            print(f"Has __iter__: {hasattr(discoverer, '__iter__')}")
            print(f"Has __len__: {hasattr(discoverer, '__len__')}")
            print(f"Is string: {isinstance(discoverer, str)}")
        except Exception as e:
            print(f"Error checking attributes: {e}")

        # Try to convert to list
        try:
            device_list = list(discoverer)
            print(f"Successfully converted to list with {len(device_list)} items")
        except Exception as e:
            print(f"Cannot convert to list: {e}")

        # Try to iterate manually
        try:
            print("Attempting manual iteration...")
            count = 0
            for device in discoverer:
                print(f"Device {count}: {device}")
                count += 1
                if count > 10:  # Limit output
                    break
            print(f"Found {count} devices through iteration")
        except Exception as e:
            print(f"Cannot iterate: {e}")

        # Check for common method names
        methods_to_try = ['devices', 'get_devices', 'scan', 'discover', 'results', 'get_results']
        for method_name in methods_to_try:
            if hasattr(discoverer, method_name):
                print(f"Found method: {method_name}")
                try:
                    method = getattr(discoverer, method_name)
                    if callable(method):
                        result = method()
                        print(f"  {method_name}() returned: {type(result)} with {len(result) if hasattr(result, '__len__') else 'unknown'} items")
                    else:
                        print(f"  {method_name} is attribute: {type(method)}")
                except Exception as e:
                    print(f"  Error calling {method_name}: {e}")

    except Exception as e:
        print(f"Error in discover: {e}")

if __name__ == "__main__":
    asyncio.run(test_discover())
