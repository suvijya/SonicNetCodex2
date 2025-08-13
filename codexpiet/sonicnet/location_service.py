"""
GPS and location services for SonicNet client.
Windows-compatible implementation without GPS daemon dependency.
"""

import asyncio
import logging
import time
import platform
from typing import Optional, Tuple
from packet import GPSLocation

logger = logging.getLogger(__name__)

# Try to import optional location libraries
GPS_AVAILABLE = False
GEOCODING_AVAILABLE = False
WINDOWS_LOCATION_AVAILABLE = False

try:
    from geopy.geocoders import Nominatim
    GEOCODING_AVAILABLE = True
except ImportError:
    logger.debug("geopy not available - geocoding disabled")

# Windows location API
if platform.system() == "Windows":
    try:
        import winrt.windows.devices.geolocation as wdg
        WINDOWS_LOCATION_AVAILABLE = True
        logger.info("Windows Location API available")
    except ImportError:
        logger.debug("Windows Location API not available")

# Fallback GPS libraries (for Linux/Mac)
try:
    import gpsd
    GPS_AVAILABLE = True
except ImportError:
    logger.debug("gpsd not available - using alternative location methods")

class LocationService:
    """Handles location acquisition and geocoding with Windows compatibility."""

    def __init__(self):
        self.last_location: Optional[GPSLocation] = None
        self.location_available = False
        self.geocoder = None
        self.mock_location = None  # For testing

        if GEOCODING_AVAILABLE:
            self.geocoder = Nominatim(user_agent="sonicwave_emergency_client")

    async def start(self):
        """Initialize location services - Windows compatible."""
        try:
            if platform.system() == "Windows":
                return await self._start_windows_location()
            else:
                return await self._start_gps_daemon()
        except Exception as e:
            logger.warning(f"Location service initialization failed: {e}")
            logger.info("Location service will use manual/text-based location input")
            return False

    async def _start_windows_location(self):
        """Initialize Windows location services."""
        if not WINDOWS_LOCATION_AVAILABLE:
            logger.info("Windows Location API not available - using manual location")
            return False

        try:
            # Request location permission and test access
            locator = wdg.Geolocator()

            # Set desired accuracy
            locator.desired_accuracy = wdg.PositionAccuracy.HIGH

            # Test if we can get location
            position = await locator.get_geoposition_async()
            if position:
                self.location_available = True
                logger.info("Windows location services initialized successfully")
                return True

        except Exception as e:
            logger.warning(f"Windows location initialization failed: {e}")

        return False

    async def _start_gps_daemon(self):
        """Initialize GPS daemon (Linux/Mac)."""
        if not GPS_AVAILABLE:
            logger.info("GPS daemon not available - using manual location")
            return False

        try:
            gpsd.connect()
            self.location_available = True
            logger.info("GPS daemon connected successfully")
            return True
        except Exception as e:
            logger.warning(f"GPS daemon connection failed: {e}")
            return False

    async def get_current_location(self, timeout: float = 10.0) -> Optional[GPSLocation]:
        """Get current GPS location with Windows compatibility."""

        # Use mock location if set (for testing)
        if self.mock_location:
            logger.debug("Using mock location for testing")
            return self.mock_location

        try:
            if platform.system() == "Windows":
                return await self._get_windows_location(timeout)
            else:
                return await self._get_gps_location(timeout)

        except Exception as e:
            logger.error(f"Failed to get current location: {e}")
            return self.last_location  # Return last known location

    async def _get_windows_location(self, timeout: float) -> Optional[GPSLocation]:
        """Get location using Windows Location API."""
        if not WINDOWS_LOCATION_AVAILABLE or not self.location_available:
            return None

        try:
            locator = wdg.Geolocator()

            # Get position with timeout
            position = await asyncio.wait_for(
                locator.get_geoposition_async(),
                timeout=timeout
            )

            if position and position.coordinate:
                coord = position.coordinate
                location = GPSLocation(
                    latitude=coord.latitude,
                    longitude=coord.longitude,
                    altitude=coord.altitude,
                    accuracy=coord.accuracy
                )

                self.last_location = location
                logger.debug(f"Windows location acquired: {coord.latitude:.6f}, {coord.longitude:.6f}")
                return location

        except asyncio.TimeoutError:
            logger.warning(f"Windows location timeout after {timeout}s")
        except Exception as e:
            logger.error(f"Windows location error: {e}")

        return None

    async def _get_gps_location(self, timeout: float) -> Optional[GPSLocation]:
        """Get location using GPS daemon (Linux/Mac)."""
        if not GPS_AVAILABLE or not self.location_available:
            return None

        try:
            # Get GPS data with timeout
            start_time = time.time()

            while time.time() - start_time < timeout:
                try:
                    packet = gpsd.get_current()

                    if packet.mode >= 2:  # 2D fix or better
                        location = GPSLocation(
                            latitude=packet.lat,
                            longitude=packet.lon,
                            altitude=packet.alt if hasattr(packet, 'alt') else None,
                            accuracy=packet.epx if hasattr(packet, 'epx') else None
                        )

                        self.last_location = location
                        logger.debug(f"GPS location acquired: {packet.lat:.6f}, {packet.lon:.6f}")
                        return location

                except Exception as e:
                    logger.debug(f"GPS read attempt failed: {e}")

                await asyncio.sleep(0.5)  # Wait before retry

        except Exception as e:
            logger.error(f"GPS location error: {e}")

        return None

    def set_mock_location(self, latitude: float, longitude: float, altitude: Optional[float] = None):
        """Set mock location for testing purposes."""
        self.mock_location = GPSLocation(
            latitude=latitude,
            longitude=longitude,
            altitude=altitude,
            accuracy=1.0  # High accuracy for mock
        )
        logger.info(f"Mock location set: {latitude:.6f}, {longitude:.6f}")

    def clear_mock_location(self):
        """Clear mock location."""
        self.mock_location = None
        logger.info("Mock location cleared")

    async def geocode_location(self, latitude: float, longitude: float) -> Optional[str]:
        """Convert coordinates to human-readable address."""
        if not GEOCODING_AVAILABLE or not self.geocoder:
            return None

        try:
            location = self.geocoder.reverse(f"{latitude}, {longitude}")
            if location:
                return location.address
        except Exception as e:
            logger.error(f"Geocoding failed: {e}")

        return None

    async def get_location_string(self, include_coords: bool = True) -> str:
        """Get location as a formatted string."""
        try:
            location = await self.get_current_location()

            if location:
                coords_str = f"{location.latitude:.6f}, {location.longitude:.6f}"

                if include_coords:
                    # Try to get human-readable address
                    address = await self.geocode_location(location.latitude, location.longitude)
                    if address:
                        return f"{address} ({coords_str})"
                    else:
                        return coords_str
                else:
                    # Try to get address only
                    address = await self.geocode_location(location.latitude, location.longitude)
                    return address or coords_str
            else:
                return "Location unavailable"

        except Exception as e:
            logger.error(f"Error getting location string: {e}")
            return "Location error"

    def get_last_known_location(self) -> Optional[GPSLocation]:
        """Get the last known GPS location."""
        return self.last_location

    async def stop(self):
        """Stop location services."""
        try:
            if GPS_AVAILABLE and self.location_available:
                # Disconnect GPS if needed
                pass
        except Exception as e:
            logger.error(f"Error stopping location service: {e}")

        logger.info("Location service stopped")
