# SonicWave: Crisis Mesh Communication Grid

[![Windows](https://img.shields.io/badge/Windows-Compatible-blue.svg)](https://www.microsoft.com/windows/)
[![Python](https://img.shields.io/badge/Python-3.8+-green.svg)](https://www.python.org/)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

SonicWave is a resilient and decentralized emergency communication system designed to transmit SOS packets through a mesh network of user devices. The system ensures that critical emergency information reaches rescue services even when conventional communication infrastructure is unavailable.

## 🚨 Core Emergency Features

### **Multi-Transport Mesh Network**
- **🔵 Bluetooth Low Energy (BLE)** - Short-range device-to-device communication
- **📡 UDP Multicast** - Local network emergency broadcasting  
- **🎵 Audio (GGWave)** - Sound-based communication when all else fails

### **Intelligent Location Services**
- **🛰️ Automatic GPS Location** - Real-time coordinate acquisition
- **📍 Manual Location Input** - Text-based location descriptions
- **🌍 Multiple Location Formats** - Coordinates, addresses, landmarks
- **🗺️ Location History Tracking** - Track moving emergencies

### **Smart Emergency Management**
- **⚡ Urgency Levels** - CRITICAL, HIGH, MEDIUM, LOW priority handling
- **🔄 Location Updates** - Real-time position updates for moving emergencies
- **📋 Packet Deduplication** - Prevents duplicate emergency messages
- **🔗 Thread Management** - Groups related emergency updates

## 🏗️ Architecture Overview

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Mobile Device │    │   Mobile Device │    │   Mobile Device │
│  (SonicWave     │◄──►│  (SonicWave     │◄──►│  (SonicWave     │
│   Client)       │    │   Client)       │    │   Client)       │
└─────────────────┘    └─────────────────┘    └─────────────────┘
         │                       │                       │
         └───────────────────────┼───────────────────────┘
                                 │ (Mesh Network)
                                 ▼
                    ┌─────────────────────────┐
                    │   Central Server        │
                    │  • Emergency Dashboard  │
                    │  • Rescue Coordination │
                    │  • Real-time Monitoring │
                    │  • MySQL Database      │
                    └─────────────────────────┘
```

### **Client Components**
1. **`client.py`** - Main client orchestrating all components
2. **`packet.py`** - SOS packet data structure with GPS support
3. **`packet_manager.py`** - Intelligent packet caching and relay management
4. **`location_service.py`** - Windows-compatible GPS and location services
5. **`transports/`** - Multi-protocol communication (BLE, UDP, GGWave)
6. **`server_uploader.py`** - Reliable server communication with retry logic

### **Server Components**
1. **`server.py`** - FastAPI emergency coordination server
2. **Emergency Dashboard** - Real-time web interface for monitoring
3. **MySQL Database** - Persistent emergency data storage
4. **WebSocket Updates** - Live emergency notifications
5. **Rescue Authority Integration** - Automated emergency service alerts

## 🚀 Quick Start Guide

### **1. Environment Setup**

```bash
# Clone and navigate to project
cd sonicnet/

# Copy environment template
cp .env.example .env

# Edit .env with your MySQL credentials:
# DB_HOST=localhost
# DB_USER=sonicwave  
# DB_PASSWORD=sonicwave123
# DB_NAME=sonicwave_emergency
```

### **2. Install Dependencies**

```bash
# Install client requirements
pip install -r requirements.txt

# Install server requirements  
pip install -r server_requirements.txt
```

### **3. Database Setup**

```bash
# Automatic setup (recommended)
python setup_database.py

# Manual setup (alternative)
mysql -u root -p < database_setup.sql
```

### **4. Start the System**

```bash
# Terminal 1: Start Emergency Server
python server.py

# Terminal 2: Run Client Example
python client_example.py

# Terminal 3: View Dashboard
# Open http://localhost:8000 in browser
```

## 📱 Client Usage Examples

### **Basic Emergency SOS**

```python
import asyncio
from client import SonicWaveClient

async def send_emergency():
    client = SonicWaveClient()
    
    try:
        # Start the client (initializes all transports)
        await client.start()
        
        # Send SOS with automatic GPS location
        packet_id = await client.send_sos(
            message="Car accident on highway, need immediate help!",
            urgency="CRITICAL"
        )
        
        print(f"Emergency sent: {packet_id}")
        
        # Keep client running for mesh communication
        await asyncio.sleep(60)
        
    finally:
        await client.stop()

# Run the emergency client
asyncio.run(send_emergency())
```

### **Emergency with Specific Location**

```python
async def send_location_emergency():
    client = SonicWaveClient()
    await client.start()
    
    try:
        # Method 1: Send with text location
        await client.send_sos(
            message="Lost hiker needs rescue",
            location="Trail marker 15, Blue Ridge Mountains",
            urgency="HIGH"
        )
        
        # Method 2: Send with coordinates
        await client.send_sos_with_coordinates(
            message="Medical emergency at coordinates",
            latitude=40.7128,
            longitude=-74.0060,
            altitude=10.0,
            urgency="CRITICAL"
        )
        
        # Method 3: Send with coordinate string
        await client.send_sos(
            message="Emergency at exact location",
            location="34.0522, -118.2437",  # Auto-parsed as coordinates
            urgency="HIGH"
        )
        
    finally:
        await client.stop()
```

### **Moving Emergency with Location Updates**

```python
async def moving_emergency():
    client = SonicWaveClient()
    await client.start()
    
    try:
        # Initial emergency location
        await client.send_sos(
            message="Vehicle breakdown, starting to walk for help",
            location="Mile marker 15, I-95 North",
            urgency="MEDIUM"
        )
        
        # Wait and send location update
        await asyncio.sleep(30)
        
        await client.send_sos(
            message="Update: Walking towards town, about 0.5 miles from highway",
            location="Rural road off I-95, near water tower",
            urgency="MEDIUM"
        )
        
        # Another update
        await asyncio.sleep(60)
        
        await client.send_sos(
            message="Final update: Reached gas station, getting help",
            location="Shell Gas Station, Exit 16",
            urgency="LOW"
        )
        
    finally:
        await client.stop()
```

### **Monitoring and Testing**

```python
async def monitor_system():
    client = SonicWaveClient()
    await client.start()
    
    try:
        # Check system status
        stats = client.get_stats()
        print(f"Active transports: {stats['client']['transports_active']}")
        
        # Test all transport methods
        transport_status = await client.test_transports()
        for transport, status in transport_status.items():
            print(f"{transport}: {'✅' if status.get('running') else '❌'}")
        
        # Check location services
        location_info = await client.get_current_location_info()
        print(f"GPS available: {location_info.get('available')}")
        
        # Check BLE mesh network
        ble_peers = client.get_ble_peers()
        print(f"BLE peers discovered: {len(ble_peers)}")
        
    finally:
        await client.stop()
```

## 🖥️ Server Features

### **Emergency Dashboard**
Access the real-time emergency dashboard at `http://localhost:8000`:

- **📊 Live Statistics** - Active emergencies, total packets, notifications sent
- **🗺️ Emergency Map** - Real-time emergency locations and updates  
- **📋 Packet History** - Complete emergency communication logs
- **🚨 Alert Management** - Rescue authority notification status
- **📡 Network Health** - Mesh network topology and node status

### **REST API Endpoints**

```bash
# Get emergency statistics
GET /api/stats

# Get recent emergency packets
GET /api/packets/recent

# Get specific packet history
GET /api/packets/{packet_id}/history

# Get emergency thread (related updates)
GET /api/packets/thread/{thread_id}

# Get network topology
GET /api/network/topology

# Manage rescue authorities
GET /api/authorities
POST /api/authorities
```

### **WebSocket Real-time Updates**

```javascript
// Connect to live emergency updates
const ws = new WebSocket('ws://localhost:8000/ws');

ws.onmessage = function(event) {
    const data = JSON.parse(event.data);
    
    if (data.type === 'new_emergency') {
        // Handle new emergency alert
        displayEmergencyAlert(data.packet);
    } else if (data.type === 'stats') {
        // Update dashboard statistics
        updateDashboard(data);
    }
};
```

## 🔧 Advanced Configuration

### **Transport Configuration**

```python
# config.py - Customize transport settings

# BLE Configuration
BLE_SCAN_INTERVAL = 10  # seconds between scans
BLE_CONNECTION_TIMEOUT = 15  # connection timeout
BLE_MAX_CONNECTIONS = 5  # max simultaneous connections

# UDP Configuration  
UDP_MULTICAST_GROUP = "224.1.1.1"  # multicast address
UDP_PORT = 9999  # communication port
UDP_BROADCAST_INTERVAL = 5  # seconds between broadcasts

# GGWave Audio Configuration
GGWAVE_SAMPLE_RATE = 48000  # audio sample rate
GGWAVE_VOLUME = 50  # volume percentage
GGWAVE_PROTOCOL_AUDIBLE = True  # audible vs ultrasonic
```

### **Emergency Priorities**

```python
# Urgency levels with different TTL and routing
URGENCY_LEVELS = {
    "CRITICAL": {
        "ttl": 20,  # maximum hops
        "priority": 1,  # highest priority
        "auto_notify": True  # immediate rescue notification
    },
    "HIGH": {
        "ttl": 15,
        "priority": 2,
        "auto_notify": True
    },
    "MEDIUM": {
        "ttl": 10,
        "priority": 3,
        "auto_notify": False
    },
    "LOW": {
        "ttl": 5,
        "priority": 4,
        "auto_notify": False
    }
}
```

### **Location Service Configuration**

```python
# Mock location for testing
client.set_mock_location(40.7128, -74.0060, 10.0)

# GPS timeout settings
GPS_TIMEOUT = 10  # seconds for GPS fix
GPS_MIN_ACCURACY = 100  # meters
LOCATION_CACHE_TIME = 300  # seconds

# Geocoding (coordinates to address)
GEOCODING_ENABLED = True
```

## 🧪 Testing and Validation

### **Comprehensive System Test**

```bash
# Run complete system test (tests everything)
python comprehensive_test.py
```

This tests:
- ✅ **Server startup and database connectivity**
- ✅ **Client initialization with all transports**
- ✅ **Location services (GPS, manual, coordinates)**
- ✅ **SOS message transmission and reception**
- ✅ **WebSocket real-time updates**
- ✅ **Emergency notification system**
- ✅ **Packet deduplication and relay**
- ✅ **Network topology analysis**
- ✅ **Multi-client mesh communication**
- ✅ **Stress testing and stability**

### **Individual Component Testing**

```bash
# Test just the client functionality
python client_example.py

# Test database setup
python setup_database.py
```

## 🌐 Network Protocols

### **BLE Mesh Protocol**
- **Discovery**: Scans for SonicWave service UUID
- **Connection**: Direct device-to-device pairing
- **Data Transfer**: JSON packet transmission via GATT characteristics
- **Range**: ~50-100 meters in open areas
- **Advantages**: Low power, works without infrastructure

### **UDP Multicast Protocol**  
- **Broadcasting**: Multicast to 224.1.1.1:9999
- **Discovery**: Automatic peer discovery on local networks
- **Data Transfer**: JSON packets via UDP
- **Range**: Local network coverage
- **Advantages**: Fast, high throughput

### **GGWave Audio Protocol**
- **Encoding**: Digital data encoded as audio frequencies
- **Transmission**: Via device speakers and microphones
- **Range**: ~5-15 meters depending on volume and environment
- **Advantages**: Works when all other methods fail

## 📊 Database Schema

### **Emergency Packets Table**
```sql
CREATE TABLE sos_packets (
    packet_id VARCHAR(32) PRIMARY KEY,
    sender_id VARCHAR(100) NOT NULL,
    message TEXT NOT NULL,
    urgency ENUM('CRITICAL', 'HIGH', 'MEDIUM', 'LOW'),
    latitude DECIMAL(10, 8),
    longitude DECIMAL(11, 8),
    location_text TEXT,
    packet_timestamp BIGINT,
    hop_count INT DEFAULT 0,
    relay_path JSON,
    thread_id VARCHAR(100),
    notifications_sent INT DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### **Rescue Authorities Table**
```sql
CREATE TABLE rescue_authorities (
    id INT PRIMARY KEY,
    name VARCHAR(200) NOT NULL,
    contact_type ENUM('phone', 'email', 'webhook', 'sms'),
    contact_value VARCHAR(500) NOT NULL,
    coverage_area TEXT,
    active BOOLEAN DEFAULT TRUE
);
```

## 🔒 Security Features

- **📝 Packet Deduplication** - SHA256 hashing prevents duplicate emergencies
- **🔢 Hop Count Limiting** - TTL prevents infinite relay loops
- **⏱️ Rate Limiting** - Prevents emergency system flooding
- **🔐 Packet Validation** - Input sanitization and validation
- **📊 Audit Logging** - Complete emergency communication logs

## 🚀 Production Deployment

### **Server Deployment**
```bash
# Production server with SSL
uvicorn server:app --host 0.0.0.0 --port 443 --ssl-keyfile key.pem --ssl-certfile cert.pem

# Docker deployment
docker build -t sonicwave-server .
docker run -p 8000:8000 -e DB_HOST=mysql_server sonicwave-server
```

### **Environment Variables**
```bash
# Production environment
DB_HOST=production_mysql_server
DB_PASSWORD=secure_password
TWILIO_SID=your_twilio_sid
TWILIO_TOKEN=your_twilio_token
GOOGLE_MAPS_API_KEY=your_maps_key
```

## 🤝 Contributing

### **Development Setup**
```bash
# Install development dependencies
pip install -r requirements.txt -r server_requirements.txt

# Run tests
python comprehensive_test.py

# Code formatting
black *.py
isort *.py
```

### **Adding New Transports**
1. Create new transport class in `transports/`
2. Inherit from `BaseTransport`
3. Implement `start()`, `stop()`, and `send()` methods
4. Add to `client.py` transport initialization

### **Adding New Features**
1. Update packet structure in `packet.py` if needed
2. Extend server API in `server.py`
3. Add corresponding client methods
4. Update tests in `comprehensive_test.py`

## 📜 License

MIT License - see LICENSE file for details.

## 🆘 Emergency Contact Integration

The system can be configured to automatically notify:
- **🚑 Emergency Medical Services**
- **🚓 Police Departments**  
- **🔥 Fire Departments**
- **⛰️ Search and Rescue Teams**
- **📞 Emergency Hotlines (911, 112, etc.)**

Contact integration supports:
- **📧 Email notifications**
- **📱 SMS alerts**
- **☎️ Automated phone calls**
- **🔗 Webhook notifications**

## 🎯 Use Cases

- **🏔️ Wilderness Emergencies** - Hiking, camping, remote area incidents
- **🚗 Vehicle Breakdowns** - Highway emergencies, remote road incidents  
- **🏠 Natural Disasters** - Communication when infrastructure is down
- **🏭 Industrial Accidents** - Factory, construction site emergencies
- **👥 Mass Events** - Concert, festival, large gathering incidents
- **🌊 Maritime Emergencies** - Coastal and near-shore incidents

---

**SonicWave: When Every Second Counts, Every Device Helps** 🚨

**Built with ❤️ by Vedant jain and Suvijya Arya**
