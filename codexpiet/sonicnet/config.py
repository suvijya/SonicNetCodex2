"""
Enhanced configuration for the SonicWave client with comprehensive settings.
"""

# Server Configuration
SERVER_API_URL = "http://localhost:8000/api/sos"  # Updated to match our FastAPI server
SERVER_UPLOAD_INTERVAL = 10  # seconds
SERVER_TIMEOUT = 30  # seconds
SERVER_RETRY_ATTEMPTS = 3
SERVER_BACKUP_URLS = [
    "http://localhost:8001/api/sos",  # Backup server instances
    "http://localhost:8002/api/sos"
]

# UDP Multicast (Wi-Fi) Configuration
UDP_MULTICAST_GROUP = "224.1.1.1"
UDP_PORT = 9999
UDP_BROADCAST_INTERVAL = 5  # seconds
UDP_MAX_PACKET_SIZE = 4096  # bytes

# BLE Configuration
BLE_SERVICE_UUID = "12345678-1234-5678-1234-56789abcdef0"
BLE_SCAN_INTERVAL = 10  # seconds
BLE_CONNECTION_TIMEOUT = 15  # seconds
BLE_MAX_CONNECTIONS = 5
BLE_HEARTBEAT_INTERVAL = 30  # seconds

# GGWave Audio Settings (for audio-based transport)
GGWAVE_SAMPLE_RATE = 48000
GGWAVE_SAMPLES_PER_FRAME = 1024
GGWAVE_PROTOCOL_AUDIBLE = True
GGWAVE_VOLUME = 50  # percentage

# GPS and Location Services
GPS_TIMEOUT = 10  # seconds for GPS fix
GPS_MIN_ACCURACY = 100  # meters
LOCATION_CACHE_TIME = 300  # seconds
GEOCODING_ENABLED = True

# Packet Manager Configuration
PACKET_CACHE_LIMIT = 100  # Max number of packets to keep in cache
PACKET_EXPIRATION = 3600  # seconds (1 hour)
MAX_HOP_COUNT = 15  # Maximum hops before packet is dropped
TTL_CRITICAL = 20  # TTL for critical packets
TTL_HIGH = 15     # TTL for high priority packets
TTL_MEDIUM = 10   # TTL for medium priority packets
TTL_LOW = 5       # TTL for low priority packets

# Anti-flooding and Rate Limiting
MAX_PACKETS_PER_MINUTE = 10  # Per node
RATE_LIMIT_WINDOW = 60  # seconds
BLACKLIST_THRESHOLD = 5  # Failed connection attempts before blacklisting
BLACKLIST_DURATION = 3600  # seconds

# Network and Mesh Configuration
NEIGHBOR_TIMEOUT = 300  # seconds before considering neighbor offline
HEARTBEAT_INTERVAL = 60  # seconds
NETWORK_DENSITY_THRESHOLD = 3  # nodes
RELAY_PROBABILITY_DENSE = 0.3  # Probability to relay in dense networks
RELAY_PROBABILITY_SPARSE = 0.8  # Probability to relay in sparse networks

# Media and Attachments
MAX_ATTACHMENT_SIZE = 1024 * 1024  # 1MB
SUPPORTED_IMAGE_FORMATS = ['.jpg', '.jpeg', '.png', '.gif']
SUPPORTED_AUDIO_FORMATS = ['.wav', '.mp3', '.ogg']
SUPPORTED_VIDEO_FORMATS = ['.mp4', '.avi', '.mov']

# User Interface
UI_REFRESH_RATE = 1  # seconds
ALERT_SOUND_ENABLED = True
VISUAL_ALERTS_ENABLED = True
AUTO_ACKNOWLEDGE_TIMEOUT = 30  # seconds

# Security and Privacy
ENCRYPTION_ENABLED = False  # Not implemented yet
MESSAGE_SIGNING_ENABLED = False  # Not implemented yet
ANONYMOUS_MODE = False  # Hide user details in emergencies

# Performance and Resource Management
MEMORY_CLEANUP_INTERVAL = 300  # seconds
CPU_USAGE_THRESHOLD = 80  # percentage
BATTERY_LOW_THRESHOLD = 15  # percentage
POWER_SAVE_MODE_THRESHOLD = 20  # percentage

# Logging and Debugging
LOG_LEVEL = "INFO"  # DEBUG, INFO, WARNING, ERROR, CRITICAL
LOG_TO_FILE = True
LOG_FILE_PATH = "sonicnet.log"
MAX_LOG_SIZE = 10 * 1024 * 1024  # 10MB
LOG_BACKUP_COUNT = 5

# Emergency Services Integration
EMERGENCY_NUMBERS = {
    'US': '911',
    'EU': '112',
    'UK': '999',
    'IN': '108'
}
AUTO_CALL_EMERGENCY = False  # Automatically call emergency services for critical SOS
EMERGENCY_CONTACT_INTEGRATION = True

# Development and Testing
DEBUG_MODE = False
SIMULATION_MODE = False  # For testing without real hardware
MOCK_GPS_LOCATION = None  # (lat, lon) tuple for testing
TEST_PACKET_INJECTION = False
