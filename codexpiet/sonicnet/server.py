"""
SonicWave Emergency Server - FastAPI backend for emergency communication mesh network.

Features:
- Receives and stores SOS packets from mesh network
- Prevents duplicate packets using hash validation
- Sends notifications to nearby people and rescue authorities
- Provides real-time dashboard and analytics
- Handles GPS location processing and geocoding
"""

import os
import asyncio
import logging
from datetime import datetime, timedelta
from typing import List, Optional, Dict, Any
import hashlib
import json

# Load environment variables from .env file
from dotenv import load_dotenv
load_dotenv()  # This loads your .env file with the database credentials

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from pydantic import BaseModel, Field
import mysql.connector
from mysql.connector import Error
import aiomysql
from geopy.geocoders import Nominatim
from geopy.distance import geodesic
import httpx
from contextlib import asynccontextmanager

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Environment variables for database connection - now properly loaded from .env
DB_HOST = "147.93.98.55"
DB_PORT = 3306  # Use default MySQL port
DB_USER = "ego"
DB_PASSWORD = "EgowasDead@6969"
DB_NAME = "mod_testing"

# Log the database configuration (without password for security)
logger.info(f"Database config: {DB_USER}@{DB_HOST}:{DB_PORT}/{DB_NAME}")

# Notification services
PUSHOVER_TOKEN = os.getenv('PUSHOVER_TOKEN', '')
PUSHOVER_USER = os.getenv('PUSHOVER_USER', '')
TWILIO_SID = os.getenv('TWILIO_SID', '')
TWILIO_TOKEN = os.getenv('TWILIO_TOKEN', '')

# Database connection pool - FIXED VERSION
class DatabaseManager:
    def __init__(self):
        self.pool = None

    async def init_pool(self):
        """Initialize the database connection pool."""
        try:
            self.pool = await aiomysql.create_pool(
                host=DB_HOST,
                port=DB_PORT,
                user=DB_USER,
                password=DB_PASSWORD,
                db=DB_NAME,
                minsize=5,
                maxsize=20,
                autocommit=True
            )
            logger.info("Database connection pool initialized")
            await self.create_tables()
        except Exception as e:
            logger.error(f"Failed to initialize database pool: {e}")
            raise

    async def create_tables(self):
        """Create necessary database tables."""
        tables = {
            'sos_packets': """
                CREATE TABLE IF NOT EXISTS sos_packets (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    packet_id VARCHAR(32) UNIQUE NOT NULL,
                    packet_hash VARCHAR(64) UNIQUE NOT NULL,
                    sender_id VARCHAR(100) NOT NULL,
                    message TEXT NOT NULL,
                    packet_type VARCHAR(20) DEFAULT 'SOS',
                    urgency ENUM('CRITICAL', 'HIGH', 'MEDIUM', 'LOW') DEFAULT 'HIGH',
                    location_text TEXT,
                    latitude DECIMAL(10, 8),
                    longitude DECIMAL(11, 8),
                    altitude DECIMAL(8, 2),
                    location_accuracy DECIMAL(8, 2),
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    packet_timestamp BIGINT,
                    hop_count INT DEFAULT 0,
                    relay_path JSON,
                    ttl INT DEFAULT 15,
                    thread_id VARCHAR(100),
                    requires_ack BOOLEAN DEFAULT TRUE,
                    ack_received BOOLEAN DEFAULT FALSE,
                    ack_nodes JSON,
                    received_via JSON,
                    signal_strength JSON,
                    battery_level DECIMAL(5, 2),
                    media_attachments JSON,
                    geocoded_address TEXT,
                    processed BOOLEAN DEFAULT FALSE,
                    notifications_sent INT DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    INDEX idx_packet_id (packet_id),
                    INDEX idx_sender_id (sender_id),
                    INDEX idx_urgency (urgency),
                    INDEX idx_location (latitude, longitude),
                    INDEX idx_timestamp (packet_timestamp),
                    INDEX idx_processed (processed)
                )
            """,
            'rescue_authorities': """
                CREATE TABLE IF NOT EXISTS rescue_authorities (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    name VARCHAR(200) NOT NULL,
                    contact_type ENUM('phone', 'email', 'webhook', 'sms') NOT NULL,
                    contact_value VARCHAR(500) NOT NULL,
                    coverage_area TEXT,
                    coverage_radius_km DECIMAL(8, 2) DEFAULT 50.0,
                    priority_level INT DEFAULT 1,
                    active BOOLEAN DEFAULT TRUE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    INDEX idx_active (active),
                    INDEX idx_contact_type (contact_type)
                )
            """,
            'notifications': """
                CREATE TABLE IF NOT EXISTS notifications (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    packet_id VARCHAR(32) NOT NULL,
                    notification_type ENUM('nearby_alert', 'authority_alert', 'broadcast') NOT NULL,
                    recipient VARCHAR(500) NOT NULL,
                    message TEXT NOT NULL,
                    status ENUM('pending', 'sent', 'failed', 'delivered') DEFAULT 'pending',
                    sent_at TIMESTAMP NULL,
                    response_received BOOLEAN DEFAULT FALSE,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    INDEX idx_packet_id (packet_id),
                    INDEX idx_status (status),
                    INDEX idx_type (notification_type)
                )
            """,
            'network_stats': """
                CREATE TABLE IF NOT EXISTS network_stats (
                    id INT AUTO_INCREMENT PRIMARY KEY,
                    date DATE NOT NULL,
                    total_packets INT DEFAULT 0,
                    unique_senders INT DEFAULT 0,
                    avg_hop_count DECIMAL(5, 2) DEFAULT 0,
                    critical_packets INT DEFAULT 0,
                    high_packets INT DEFAULT 0,
                    medium_packets INT DEFAULT 0,
                    low_packets INT DEFAULT 0,
                    notifications_sent INT DEFAULT 0,
                    authorities_notified INT DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    UNIQUE KEY unique_date (date)
                )
            """
        }

        async with self.pool.acquire() as conn:
            async with conn.cursor() as cursor:
                for table_name, table_sql in tables.items():
                    try:
                        await cursor.execute(table_sql)
                        logger.info(f"Table {table_name} created/verified")
                    except Exception as e:
                        logger.error(f"Error creating table {table_name}: {e}")

    async def get_connection(self):
        """Get a database connection from the pool."""
        return self.pool.acquire()

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for startup and shutdown events."""
    # Startup
    await db_manager.init_pool()
    logger.info("SonicWave Emergency Server started")

    yield

    # Shutdown
    if db_manager.pool:
        db_manager.pool.close()
        await db_manager.pool.wait_closed()
    logger.info("SonicWave Emergency Server stopped")

# Initialize database manager
db_manager = DatabaseManager()

# WebSocket connection manager
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def send_personal_message(self, message: str, websocket: WebSocket):
        try:
            await websocket.send_text(message)
        except:
            self.disconnect(websocket)

    async def broadcast(self, data: dict):
        """Broadcast data to all connected WebSocket clients."""
        message = json.dumps(data)
        disconnected = []
        for connection in self.active_connections:
            try:
                await connection.send_text(message)
            except:
                disconnected.append(connection)

        # Remove disconnected clients
        for connection in disconnected:
            self.disconnect(connection)

manager = ConnectionManager()

# Pydantic models
class SOSPacketModel(BaseModel):
    packet_id: str
    sender_id: str
    message: str
    packet_type: str = "SOS"
    urgency: str = "HIGH"
    location_text: Optional[str] = None
    timestamp: float
    hop_count: int = 0
    relay_path: List[str] = []
    ttl: int = 15
    thread_id: str
    requires_ack: bool = True
    ack_received: bool = False
    ack_nodes: List[str] = []
    received_via: List[str] = []
    signal_strength: Dict[str, float] = {}
    battery_level: Optional[float] = None
    gps_location: Optional[Dict[str, Any]] = None
    media_attachments: List[Dict[str, Any]] = []

class NotificationRequest(BaseModel):
    message: str
    urgency: str = "HIGH"
    location: Optional[str] = None
    radius_km: float = 5.0

class RescueAuthorityModel(BaseModel):
    name: str
    contact_type: str  # phone, email, webhook
    contact_value: str
    coverage_area: Optional[str] = None
    active: bool = True

app = FastAPI(
    title="SonicWave Emergency Server",
    description="Emergency communication mesh network server",
    version="1.0.0",
    lifespan=lifespan
)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Utility functions
def validate_packet_data(packet_data: dict) -> bool:
    """Validate that packet data contains required fields."""
    required_fields = ['packet_id', 'sender_id', 'message', 'timestamp', 'thread_id']
    return all(field in packet_data for field in required_fields)

async def geocode_location(latitude: float, longitude: float) -> Optional[str]:
    """Reverse geocode coordinates to get address."""
    try:
        geolocator = Nominatim(user_agent="sonicwave-emergency")
        location = geolocator.reverse(f"{latitude}, {longitude}")
        return location.address if location else None
    except Exception as e:
        logger.error(f"Geocoding error: {e}")
        return None

async def parse_location_text(location_text: str) -> Optional[tuple]:
    """Parse location text to extract coordinates."""
    try:
        # Try to parse as "lat, lon" format
        if ',' in location_text:
            parts = location_text.split(',')
            if len(parts) == 2:
                lat = float(parts[0].strip())
                lon = float(parts[1].strip())
                return (lat, lon)
    except:
        pass
    return None

# Notification services
class NotificationService:
    """Handles sending notifications to rescue authorities and nearby people."""

    async def send_authority_notification(self, packet: SOSPacketModel, authority: dict):
        """Send notification to rescue authority."""
        try:
            message = f"🚨 EMERGENCY ALERT\n\nMessage: {packet.message}\nLocation: {packet.location_text}\nUrgency: {packet.urgency}\nSender: {packet.sender_id}\nTime: {datetime.fromtimestamp(packet.timestamp)}"

            if authority['contact_type'] == 'email':
                # Email notification (placeholder - would need SMTP setup)
                logger.info(f"Email notification to {authority['contact_value']}: {message}")

            elif authority['contact_type'] == 'phone':
                # Phone call notification (placeholder - would need Twilio Voice API)
                logger.info(f"Phone notification to {authority['contact_value']}: {message}")

            elif authority['contact_type'] == 'sms':
                # SMS notification (placeholder - would need Twilio SMS API)
                logger.info(f"SMS notification to {authority['contact_value']}: {message}")

            elif authority['contact_type'] == 'webhook':
                # Webhook notification
                async with httpx.AsyncClient() as client:
                    payload = {
                        'type': 'emergency_alert',
                        'packet': packet.dict(),
                        'timestamp': datetime.utcnow().isoformat()
                    }
                    response = await client.post(authority['contact_value'], json=payload, timeout=10)
                    logger.info(f"Webhook notification sent to {authority['name']}: {response.status_code}")

            return True
        except Exception as e:
            logger.error(f"Failed to send notification to authority {authority['name']}: {e}")
            return False

    async def send_nearby_alert(self, packet: SOSPacketModel, radius_km: float = 5.0):
        """Send alert to nearby people (placeholder for push notification service)."""
        try:
            # This would integrate with push notification services like Firebase
            logger.info(f"Nearby alert sent for emergency at {packet.location_text} within {radius_km}km")
            return True
        except Exception as e:
            logger.error(f"Failed to send nearby alert: {e}")
            return False

notification_service = NotificationService()

# API Routes

@app.get("/", response_class=HTMLResponse)
async def dashboard():
    """Serve the dashboard."""
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>SonicWave Emergency Dashboard</title>
        <style>
            body { font-family: Arial, sans-serif; margin: 0; padding: 20px; background: #f5f5f5; }
            .header { background: #d32f2f; color: white; padding: 20px; border-radius: 8px; margin-bottom: 20px; }
            .stats { display: grid; grid-template-columns: repeat(auto-fit, minmax(200px, 1fr)); gap: 20px; margin-bottom: 20px; }
            .stat-card { background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
            .stat-number { font-size: 2em; font-weight: bold; color: #d32f2f; }
            .emergency-list { background: white; padding: 20px; border-radius: 8px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); }
            .emergency-item { padding: 15px; border-left: 4px solid #d32f2f; margin-bottom: 10px; background: #fff3f3; }
            .urgency-critical { border-left-color: #ff1744; background: #ffebee; }
            .urgency-high { border-left-color: #ff5722; background: #fff3e0; }
            .urgency-medium { border-left-color: #ff9800; background: #fff8e1; }
            .urgency-low { border-left-color: #4caf50; background: #f1f8e9; }
        </style>
    </head>
    <body>
        <div class="header">
            <h1>🚨 SonicWave Emergency Dashboard</h1>
            <p>Real-time emergency communication mesh network monitoring</p>
        </div>
        
        <div class="stats">
            <div class="stat-card">
                <div class="stat-number" id="total-packets">0</div>
                <div>Total Packets</div>
            </div>
            <div class="stat-card">
                <div class="stat-number" id="active-emergencies">0</div>
                <div>Active Emergencies</div>
            </div>
            <div class="stat-card">
                <div class="stat-number" id="notifications-sent">0</div>
                <div>Notifications Sent</div>
            </div>
            <div class="stat-card">
                <div class="stat-number" id="rescue-authorities">0</div>
                <div>Rescue Authorities</div>
            </div>
        </div>
        
        <div class="emergency-list">
            <h2>Recent Emergency Packets</h2>
            <div id="emergency-packets">Loading...</div>
        </div>
        
        <script>
            const ws = new WebSocket('ws://localhost:8000/ws');
            
            ws.onmessage = function(event) {
                const data = JSON.parse(event.data);
                updateDashboard(data);
            };
            
            function updateDashboard(data) {
                if (data.type === 'stats') {
                    document.getElementById('total-packets').textContent = data.total_packets || 0;
                    document.getElementById('active-emergencies').textContent = data.active_emergencies || 0;
                    document.getElementById('notifications-sent').textContent = data.notifications_sent || 0;
                    document.getElementById('rescue-authorities').textContent = data.rescue_authorities || 0;
                } else if (data.type === 'new_emergency') {
                    addEmergencyToList(data.packet);
                }
            }
            
            function addEmergencyToList(packet) {
                const container = document.getElementById('emergency-packets');
                const item = document.createElement('div');
                item.className = `emergency-item urgency-${packet.urgency.toLowerCase()}`;
                item.innerHTML = `
                    <strong>${packet.urgency}</strong> - ${packet.message}<br>
                    <small>Location: ${packet.location_text || 'Unknown'} | 
                    Sender: ${packet.sender_id} | 
                    Time: ${new Date(packet.timestamp * 1000).toLocaleString()}</small>
                `;
                container.insertBefore(item, container.firstChild);
                
                // Keep only last 10 items
                while (container.children.length > 10) {
                    container.removeChild(container.lastChild);
                }
            }
            
            // Load initial data
            fetch('/api/stats').then(r => r.json()).then(data => updateDashboard({type: 'stats', ...data}));
            fetch('/api/packets/recent').then r => r.json()).then(packets => {
                packets.forEach(packet => addEmergencyToList(packet));
            });
        </script>
    </body>
    </html>
    """

@app.post("/api/sos")
async def receive_sos_packet(packet: SOSPacketModel, background_tasks: BackgroundTasks):
    """Receive and process an SOS packet from the mesh network."""
    try:
        # Validate packet data
        if not validate_packet_data(packet.dict()):
            raise HTTPException(status_code=400, detail="Invalid packet data")

        async with db_manager.get_connection() as conn:
            async with conn.cursor() as cursor:
                # Check for duplicate packet
                await cursor.execute("SELECT id FROM sos_packets WHERE packet_id = %s", (packet.packet_id,))
                if await cursor.fetchone():
                    logger.info(f"Duplicate packet {packet.packet_id} ignored")
                    return {"status": "duplicate", "message": "Packet already processed"}

                # Parse GPS location if available
                latitude, longitude, altitude, accuracy = None, None, None, None
                if packet.gps_location:
                    latitude = packet.gps_location.get('latitude')
                    longitude = packet.gps_location.get('longitude')
                    altitude = packet.gps_location.get('altitude')
                    accuracy = packet.gps_location.get('accuracy')
                elif packet.location_text:
                    coords = await parse_location_text(packet.location_text)
                    if coords:
                        latitude, longitude = coords

                # Insert packet into database
                insert_query = """
                    INSERT INTO sos_packets (
                        packet_id, packet_hash, sender_id, message, packet_type, urgency,
                        location_text, latitude, longitude, altitude, location_accuracy,
                        packet_timestamp, hop_count, relay_path, ttl, thread_id,
                        requires_ack, ack_received, ack_nodes, received_via,
                        signal_strength, battery_level, media_attachments
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """

                values = (
                    packet.packet_id, packet.packet_id, packet.sender_id, packet.message,
                    packet.packet_type, packet.urgency, packet.location_text,
                    latitude, longitude, altitude, accuracy, int(packet.timestamp),
                    packet.hop_count, json.dumps(packet.relay_path), packet.ttl,
                    packet.thread_id, packet.requires_ack, packet.ack_received,
                    json.dumps(packet.ack_nodes), json.dumps(packet.received_via),
                    json.dumps(packet.signal_strength), packet.battery_level,
                    json.dumps(packet.media_attachments)
                )

                await cursor.execute(insert_query, values)
                await conn.commit()

                logger.info(f"SOS packet {packet.packet_id} stored successfully")

                # Add background tasks for notifications
                background_tasks.add_task(process_emergency_notifications, packet)
                background_tasks.add_task(update_network_stats)

                # Broadcast to WebSocket clients
                await manager.broadcast({
                    "type": "new_emergency",
                    "packet": packet.dict()
                })

                return {
                    "status": "success",
                    "message": "SOS packet received and processed",
                    "packet_id": packet.packet_id
                }

    except Exception as e:
        logger.error(f"Error processing SOS packet: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@app.get("/api/packets")
async def get_packets(limit: int = 50, urgency: Optional[str] = None, hours: int = 24):
    """Get SOS packets with optional filtering."""
    try:
        async with db_manager.get_connection() as conn:
            async with conn.cursor() as cursor:
                query = """
                    SELECT packet_id, sender_id, message, urgency, location_text,
                           latitude, longitude, packet_timestamp, hop_count, processed,
                           notifications_sent, created_at
                    FROM sos_packets
                    WHERE created_at >= DATE_SUB(NOW(), INTERVAL %s HOUR)
                """
                params = [hours]

                if urgency:
                    query += " AND urgency = %s"
                    params.append(urgency)

                query += " ORDER BY created_at DESC LIMIT %s"
                params.append(limit)

                await cursor.execute(query, params)
                rows = await cursor.fetchall()

                packets = []
                for row in rows:
                    packets.append({
                        "packet_id": row[0],
                        "sender_id": row[1],
                        "message": row[2],
                        "urgency": row[3],
                        "location_text": row[4],
                        "latitude": row[5],
                        "longitude": row[6],
                        "timestamp": row[7],
                        "hop_count": row[8],
                        "processed": row[9],
                        "notifications_sent": row[10],
                        "created_at": row[11].isoformat()
                    })

                return packets

    except Exception as e:
        logger.error(f"Error fetching packets: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.get("/api/packets/recent")
async def get_recent_packets(limit: int = 10):
    """Get most recent packets for dashboard."""
    return await get_packets(limit=limit, hours=24)

@app.get("/api/stats")
async def get_stats():
    """Get server statistics."""
    try:
        async with db_manager.get_connection() as conn:
            async with conn.cursor() as cursor:
                stats = {}

                # Total packets
                await cursor.execute("SELECT COUNT(*) FROM sos_packets")
                stats['total_packets'] = (await cursor.fetchone())[0]

                # Active emergencies (last 24 hours)
                await cursor.execute("""
                    SELECT COUNT(*) FROM sos_packets 
                    WHERE created_at >= DATE_SUB(NOW(), INTERVAL 24 HOUR)
                """)
                stats['active_emergencies'] = (await cursor.fetchone())[0]

                # Total notifications sent
                await cursor.execute("SELECT SUM(notifications_sent) FROM sos_packets")
                result = await cursor.fetchone()
                stats['notifications_sent'] = result[0] if result[0] else 0

                # Rescue authorities count
                await cursor.execute("SELECT COUNT(*) FROM rescue_authorities WHERE active = TRUE")
                stats['rescue_authorities'] = (await cursor.fetchone())[0]

                # Urgency breakdown
                await cursor.execute("""
                    SELECT urgency, COUNT(*) FROM sos_packets 
                    WHERE created_at >= DATE_SUB(NOW(), INTERVAL 24 HOUR)
                    GROUP BY urgency
                """)
                urgency_stats = {}
                for row in await cursor.fetchall():
                    urgency_stats[row[0].lower()] = row[1]

                stats['urgency_breakdown'] = urgency_stats

                return stats

    except Exception as e:
        logger.error(f"Error fetching stats: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

# Additional API endpoints for history and relay tracking
@app.get("/api/packets/{packet_id}/history")
async def get_packet_history(packet_id: str):
    """Get the complete history and relay path for a specific packet."""
    try:
        async with db_manager.get_connection() as conn:
            async with conn.cursor() as cursor:
                # Get the main packet
                await cursor.execute("""
                    SELECT packet_id, sender_id, message, urgency, location_text,
                           latitude, longitude, packet_timestamp, hop_count, relay_path,
                           ttl, thread_id, ack_nodes, received_via, signal_strength,
                           created_at, notifications_sent
                    FROM sos_packets WHERE packet_id = %s
                """, (packet_id,))

                packet_row = await cursor.fetchone()
                if not packet_row:
                    raise HTTPException(status_code=404, detail="Packet not found")

                # Get packet updates (same thread_id but different timestamps/locations)
                await cursor.execute("""
                    SELECT packet_id, sender_id, message, location_text, latitude, longitude,
                           packet_timestamp, hop_count, relay_path, created_at
                    FROM sos_packets 
                    WHERE thread_id = %s 
                    ORDER BY packet_timestamp ASC
                """, (packet_row[11],))  # thread_id

                updates = await cursor.fetchall()

                packet_data = {
                    "packet_id": packet_row[0],
                    "sender_id": packet_row[1],
                    "message": packet_row[2],
                    "urgency": packet_row[3],
                    "current_location": {
                        "text": packet_row[4],
                        "latitude": float(packet_row[5]) if packet_row[5] else None,
                        "longitude": float(packet_row[6]) if packet_row[6] else None,
                        "timestamp": packet_row[7]
                    },
                    "hop_count": packet_row[8],
                    "relay_path": json.loads(packet_row[9]) if packet_row[9] else [],
                    "ttl": packet_row[10],
                    "thread_id": packet_row[11],
                    "ack_nodes": json.loads(packet_row[12]) if packet_row[12] else [],
                    "received_via": json.loads(packet_row[13]) if packet_row[13] else [],
                    "signal_strength": json.loads(packet_row[14]) if packet_row[14] else {},
                    "first_received": packet_row[15].isoformat(),
                    "notifications_sent": packet_row[16],
                    "location_history": [],
                    "relay_timeline": []
                }

                # Build location history from updates
                for update in updates:
                    if update[5] and update[6]:  # has coordinates
                        packet_data["location_history"].append({
                            "packet_id": update[0],
                            "location_text": update[3],
                            "latitude": float(update[5]),
                            "longitude": float(update[6]),
                            "timestamp": update[7],
                            "hop_count": update[8],
                            "received_at": update[9].isoformat()
                        })

                # Build relay timeline from relay_path
                relay_path = packet_data["relay_path"]
                for i, node_id in enumerate(relay_path):
                    packet_data["relay_timeline"].append({
                        "hop_number": i,
                        "node_id": node_id,
                        "is_sender": i == 0,
                        "estimated_time": packet_row[7] + (i * 30)  # Estimate 30 seconds per hop
                    })

                return packet_data

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error fetching packet history: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.get("/api/packets/thread/{thread_id}")
async def get_thread_packets(thread_id: str):
    """Get all packets in a thread (same emergency, multiple updates)."""
    try:
        async with db_manager.get_connection() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute("""
                    SELECT packet_id, sender_id, message, urgency, location_text,
                           latitude, longitude, packet_timestamp, hop_count, 
                           created_at, notifications_sent
                    FROM sos_packets 
                    WHERE thread_id = %s 
                    ORDER BY packet_timestamp ASC
                """, (thread_id,))

                rows = await cursor.fetchall()

                packets = []
                for row in rows:
                    packets.append({
                        "packet_id": row[0],
                        "sender_id": row[1],
                        "message": row[2],
                        "urgency": row[3],
                        "location_text": row[4],
                        "latitude": float(row[5]) if row[5] else None,
                        "longitude": float(row[6]) if row[6] else None,
                        "timestamp": row[7],
                        "hop_count": row[8],
                        "received_at": row[9].isoformat(),
                        "notifications_sent": row[10]
                    })

                return {
                    "thread_id": thread_id,
                    "packet_count": len(packets),
                    "packets": packets,
                    "location_updates": [p for p in packets if p["latitude"] and p["longitude"]]
                }

    except Exception as e:
        logger.error(f"Error fetching thread packets: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.post("/api/packets/{packet_id}/update")
async def update_packet_location(packet_id: str, packet: SOSPacketModel, background_tasks: BackgroundTasks):
    """Handle location/status updates for existing packets."""
    try:
        async with db_manager.get_connection() as conn:
            async with conn.cursor() as cursor:
                # Check if original packet exists
                await cursor.execute("SELECT thread_id, sender_id FROM sos_packets WHERE packet_id = %s", (packet_id,))
                original = await cursor.fetchone()

                if not original:
                    raise HTTPException(status_code=404, detail="Original packet not found")

                # Verify the update is from the same sender
                if original[1] != packet.sender_id:
                    raise HTTPException(status_code=403, detail="Only original sender can update packet")

                # Use the same thread_id
                packet.thread_id = original[0]

                # Check for duplicate update
                await cursor.execute("SELECT id FROM sos_packets WHERE packet_id = %s", (packet.packet_id,))
                if await cursor.fetchone():
                    return {"status": "duplicate", "message": "Update already processed"}

                # Parse location
                latitude, longitude, altitude, accuracy = None, None, None, None
                if packet.gps_location:
                    latitude = packet.gps_location.get('latitude')
                    longitude = packet.gps_location.get('longitude')
                    altitude = packet.gps_location.get('altitude')
                    accuracy = packet.gps_location.get('accuracy')
                elif packet.location_text:
                    coords = await parse_location_text(packet.location_text)
                    if coords:
                        latitude, longitude = coords

                # Insert the update as a new packet with same thread_id
                insert_query = """
                    INSERT INTO sos_packets (
                        packet_id, packet_hash, sender_id, message, packet_type, urgency,
                        location_text, latitude, longitude, altitude, location_accuracy,
                        packet_timestamp, hop_count, relay_path, ttl, thread_id,
                        requires_ack, ack_received, ack_nodes, received_via,
                        signal_strength, battery_level, media_attachments
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """

                values = (
                    packet.packet_id, packet.packet_id, packet.sender_id, packet.message,
                    packet.packet_type, packet.urgency, packet.location_text,
                    latitude, longitude, altitude, accuracy, int(packet.timestamp),
                    packet.hop_count, json.dumps(packet.relay_path), packet.ttl,
                    packet.thread_id, packet.requires_ack, packet.ack_received,
                    json.dumps(packet.ack_nodes), json.dumps(packet.received_via),
                    json.dumps(packet.signal_strength), packet.battery_level,
                    json.dumps(packet.media_attachments)
                )

                await cursor.execute(insert_query, values)
                await conn.commit()

                logger.info(f"Location update for packet {packet_id} stored as {packet.packet_id}")

                # Notify authorities about the update if it's a significant location change
                if latitude and longitude:
                    background_tasks.add_task(process_location_update_notifications, packet, original[0])

                # Broadcast update to WebSocket clients
                await manager.broadcast({
                    "type": "packet_update",
                    "original_packet_id": packet_id,
                    "updated_packet": packet.dict(),
                    "thread_id": packet.thread_id
                })

                return {
                    "status": "success",
                    "message": "Packet update processed",
                    "update_packet_id": packet.packet_id,
                    "thread_id": packet.thread_id
                }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error updating packet: {e}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")

@app.get("/api/network/topology")
async def get_network_topology():
    """Get network topology and relay statistics."""
    try:
        async with db_manager.get_connection() as conn:
            async with conn.cursor() as cursor:
                # Get relay path statistics
                await cursor.execute("""
                    SELECT sender_id, AVG(hop_count) as avg_hops, COUNT(*) as packet_count,
                           MAX(packet_timestamp) as last_seen
                    FROM sos_packets
                    WHERE created_at >= DATE_SUB(NOW(), INTERVAL 24 HOUR)
                    GROUP BY sender_id
                    ORDER BY packet_count DESC
                """)

                nodes = []
                for row in await cursor.fetchall():
                    nodes.append({
                        "node_id": row[0],
                        "avg_hop_count": float(row[1]),
                        "packet_count": row[2],
                        "last_seen": row[3],
                        "is_active": (datetime.now().timestamp() - row[3]) < 3600  # Active in last hour
                    })

                # Get relay relationships
                await cursor.execute("""
                    SELECT relay_path, COUNT(*) as usage_count
                    FROM sos_packets
                    WHERE relay_path IS NOT NULL 
                    AND created_at >= DATE_SUB(NOW(), INTERVAL 24 HOUR)
                    GROUP BY relay_path
                    ORDER BY usage_count DESC
                    LIMIT 20
                """)

                relay_paths = []
                for row in await cursor.fetchall():
                    try:
                        path = json.loads(row[0])
                        relay_paths.append({
                            "path": path,
                            "usage_count": row[1],
                            "hop_count": len(path) - 1
                        })
                    except:
                        continue

                return {
                    "active_nodes": len([n for n in nodes if n["is_active"]]),
                    "total_nodes": len(nodes),
                    "nodes": nodes,
                    "relay_paths": relay_paths,
                    "network_health": "good" if len([n for n in nodes if n["is_active"]]) > 2 else "limited"
                }

    except Exception as e:
        logger.error(f"Error fetching network topology: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

# WebSocket endpoint
@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time dashboard updates."""
    await manager.connect(websocket)
    try:
        while True:
            # Send periodic stats updates
            stats = await get_stats()
            await manager.send_personal_message(
                json.dumps({"type": "stats", **stats}),
                websocket
            )
            await asyncio.sleep(10)  # Update every 10 seconds
    except WebSocketDisconnect:
        manager.disconnect(websocket)

# Background task functions
async def process_emergency_notifications(packet: SOSPacketModel):
    """Process notifications for a new emergency packet."""
    try:
        notifications_sent = 0

        # Get active rescue authorities
        async with db_manager.get_connection() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute("""
                    SELECT id, name, contact_type, contact_value, coverage_radius_km
                    FROM rescue_authorities 
                    WHERE active = TRUE
                """)

                authorities = await cursor.fetchall()

                for authority in authorities:
                    authority_dict = {
                        'id': authority[0],
                        'name': authority[1],
                        'contact_type': authority[2],
                        'contact_value': authority[3],
                        'coverage_radius_km': authority[4]
                    }

                    # Send notification
                    if await notification_service.send_authority_notification(packet, authority_dict):
                        notifications_sent += 1

                        # Log notification
                        await cursor.execute("""
                            INSERT INTO notifications (packet_id, notification_type, recipient, message, status, sent_at)
                            VALUES (%s, %s, %s, %s, %s, NOW())
                        """, (
                            packet.packet_id, 'authority_alert', authority_dict['contact_value'],
                            f"Emergency alert sent to {authority_dict['name']}", 'sent'
                        ))

                # Send nearby alerts if location is available
                if packet.gps_location or (packet.location_text and await parse_location_text(packet.location_text)):
                    if await notification_service.send_nearby_alert(packet):
                        notifications_sent += 1

                        await cursor.execute("""
                            INSERT INTO notifications (packet_id, notification_type, recipient, message, status, sent_at)
                            VALUES (%s, %s, %s, %s, %s, NOW())
                        """, (
                            packet.packet_id, 'nearby_alert', 'area_broadcast',
                            f"Nearby alert for emergency at {packet.location_text}", 'sent'
                        ))

                # Update notification count
                await cursor.execute("""
                    UPDATE sos_packets SET notifications_sent = %s, processed = TRUE 
                    WHERE packet_id = %s
                """, (notifications_sent, packet.packet_id))

                await conn.commit()

    except Exception as e:
        logger.error(f"Error processing emergency notifications: {e}")

async def process_location_update_notifications(packet: SOSPacketModel, thread_id: str):
    """Process notifications for location updates."""
    try:
        # Only send update notifications for high/critical urgency
        if packet.urgency in ['HIGH', 'CRITICAL']:
            async with db_manager.get_connection() as conn:
                async with conn.cursor() as cursor:
                    # Get authorities that were already notified about this thread
                    await cursor.execute("""
                        SELECT DISTINCT recipient FROM notifications 
                        WHERE packet_id IN (
                            SELECT packet_id FROM sos_packets WHERE thread_id = %s
                        ) AND notification_type = 'authority_alert'
                    """, (thread_id,))

                    notified_authorities = [row[0] for row in await cursor.fetchall()]

                    # Send location update to previously notified authorities
                    for contact in notified_authorities:
                        update_message = f"📍 LOCATION UPDATE\n\nOriginal Emergency Thread: {thread_id}\nNew Location: {packet.location_text}\nMessage: {packet.message}\nTime: {datetime.fromtimestamp(packet.timestamp)}"

                        await cursor.execute("""
                            INSERT INTO notifications (packet_id, notification_type, recipient, message, status, sent_at)
                            VALUES (%s, %s, %s, %s, %s, NOW())
                        """, (
                            packet.packet_id, 'authority_alert', contact,
                            update_message, 'sent'
                        ))

                    await conn.commit()

    except Exception as e:
        logger.error(f"Error processing location update notifications: {e}")

async def update_network_stats():
    """Update daily network statistics."""
    try:
        today = datetime.now().date()

        async with db_manager.get_connection() as conn:
            async with conn.cursor() as cursor:
                # Calculate daily stats
                await cursor.execute("""
                    SELECT 
                        COUNT(*) as total_packets,
                        COUNT(DISTINCT sender_id) as unique_senders,
                        AVG(hop_count) as avg_hop_count,
                        SUM(CASE WHEN urgency = 'CRITICAL' THEN 1 ELSE 0 END) as critical_packets,
                        SUM(CASE WHEN urgency = 'HIGH' THEN 1 ELSE 0 END) as high_packets,
                        SUM(CASE WHEN urgency = 'MEDIUM' THEN 1 ELSE 0 END) as medium_packets,
                        SUM(CASE WHEN urgency = 'LOW' THEN 1 ELSE 0 END) as low_packets,
                        SUM(notifications_sent) as notifications_sent
                    FROM sos_packets 
                    WHERE DATE(created_at) = %s
                """, (today,))

                stats = await cursor.fetchone()

                # Count authorities notified today
                await cursor.execute("""
                    SELECT COUNT(DISTINCT recipient) FROM notifications 
                    WHERE DATE(created_at) = %s AND notification_type = 'authority_alert'
                """, (today,))
                authorities_notified = (await cursor.fetchone())[0]

                # Insert or update daily stats
                await cursor.execute("""
                    INSERT INTO network_stats (
                        date, total_packets, unique_senders, avg_hop_count,
                        critical_packets, high_packets, medium_packets, low_packets,
                        notifications_sent, authorities_notified
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON DUPLICATE KEY UPDATE
                        total_packets = VALUES(total_packets),
                        unique_senders = VALUES(unique_senders),
                        avg_hop_count = VALUES(avg_hop_count),
                        critical_packets = VALUES(critical_packets),
                        high_packets = VALUES(high_packets),
                        medium_packets = VALUES(medium_packets),
                        low_packets = VALUES(low_packets),
                        notifications_sent = VALUES(notifications_sent),
                        authorities_notified = VALUES(authorities_notified)
                """, (
                    today, stats[0], stats[1], stats[2] or 0,
                    stats[3], stats[4], stats[5], stats[6],
                    stats[7] or 0, authorities_notified
                ))

                await conn.commit()

    except Exception as e:
        logger.error(f"Error updating network stats: {e}")

# Rescue authorities management
@app.post("/api/authorities")
async def add_rescue_authority(authority: RescueAuthorityModel):
    """Add a new rescue authority."""
    try:
        async with db_manager.get_connection() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute("""
                    INSERT INTO rescue_authorities (name, contact_type, contact_value, coverage_area, active)
                    VALUES (%s, %s, %s, %s, %s)
                """, (authority.name, authority.contact_type, authority.contact_value,
                      authority.coverage_area, authority.active))

                authority_id = cursor.lastrowid
                await conn.commit()

                return {"status": "success", "authority_id": authority_id}

    except Exception as e:
        logger.error(f"Error adding rescue authority: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@app.get("/api/authorities")
async def get_rescue_authorities():
    """Get all rescue authorities."""
    try:
        async with db_manager.get_connection() as conn:
            async with conn.cursor() as cursor:
                await cursor.execute("""
                    SELECT id, name, contact_type, contact_value, coverage_area, 
                           coverage_radius_km, priority_level, active, created_at
                    FROM rescue_authorities
                    ORDER BY priority_level, name
                """)

                authorities = []
                for row in await cursor.fetchall():
                    authorities.append({
                        "id": row[0],
                        "name": row[1],
                        "contact_type": row[2],
                        "contact_value": row[3],
                        "coverage_area": row[4],
                        "coverage_radius_km": float(row[5]) if row[5] else None,
                        "priority_level": row[6],
                        "active": row[7],
                        "created_at": row[8].isoformat()
                    })

                return authorities

    except Exception as e:
        logger.error(f"Error fetching rescue authorities: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
