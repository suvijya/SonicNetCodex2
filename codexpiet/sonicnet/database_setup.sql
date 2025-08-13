 -- SonicWave Emergency Database Setup Script
-- Run this script to create the required database and tables

-- Create database (run this as MySQL admin user)
CREATE DATABASE IF NOT EXISTS sonicwave_emergency CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;

-- Create user and grant permissions (run this as MySQL admin user)
CREATE USER IF NOT EXISTS 'sonicwave'@'localhost' IDENTIFIED BY 'sonicwave123';
GRANT ALL PRIVILEGES ON sonicwave_emergency.* TO 'sonicwave'@'localhost';
FLUSH PRIVILEGES;

-- Use the database
USE sonicwave_emergency;

-- Table 1: SOS Packets (Main emergency data storage)
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
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

    -- Indexes for performance
    INDEX idx_packet_id (packet_id),
    INDEX idx_sender_id (sender_id),
    INDEX idx_urgency (urgency),
    INDEX idx_location (latitude, longitude),
    INDEX idx_timestamp (packet_timestamp),
    INDEX idx_thread_id (thread_id),
    INDEX idx_processed (processed),
    INDEX idx_created_at (created_at)
);

-- Table 2: Rescue Authorities (Emergency services contacts)
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
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

    -- Indexes
    INDEX idx_active (active),
    INDEX idx_contact_type (contact_type),
    INDEX idx_priority (priority_level)
);

-- Table 3: Notifications (Track sent notifications)
CREATE TABLE IF NOT EXISTS notifications (
    id INT AUTO_INCREMENT PRIMARY KEY,
    packet_id VARCHAR(32) NOT NULL,
    notification_type ENUM('nearby_alert', 'authority_alert', 'broadcast') NOT NULL,
    recipient VARCHAR(500) NOT NULL,
    message TEXT NOT NULL,
    status ENUM('pending', 'sent', 'failed', 'delivered') DEFAULT 'pending',
    sent_at TIMESTAMP NULL,
    response_received BOOLEAN DEFAULT FALSE,
    error_message TEXT,
    retry_count INT DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

    -- Foreign key
    FOREIGN KEY (packet_id) REFERENCES sos_packets(packet_id) ON DELETE CASCADE,

    -- Indexes
    INDEX idx_packet_id (packet_id),
    INDEX idx_status (status),
    INDEX idx_type (notification_type),
    INDEX idx_sent_at (sent_at)
);

-- Table 4: Network Statistics (Daily performance metrics)
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
    successful_deliveries INT DEFAULT 0,
    failed_deliveries INT DEFAULT 0,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

    -- Unique constraint
    UNIQUE KEY unique_date (date),

    -- Indexes
    INDEX idx_date (date)
);

-- Table 5: Node Registry (Track active mesh network nodes)
CREATE TABLE IF NOT EXISTS node_registry (
    id INT AUTO_INCREMENT PRIMARY KEY,
    node_id VARCHAR(100) UNIQUE NOT NULL,
    node_name VARCHAR(200),
    last_seen TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    total_packets_sent INT DEFAULT 0,
    total_packets_relayed INT DEFAULT 0,
    avg_signal_strength DECIMAL(5, 2),
    battery_level DECIMAL(5, 2),
    location_lat DECIMAL(10, 8),
    location_lon DECIMAL(11, 8),
    is_active BOOLEAN DEFAULT TRUE,
    transport_types JSON,
    capabilities JSON,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,

    -- Indexes
    INDEX idx_node_id (node_id),
    INDEX idx_last_seen (last_seen),
    INDEX idx_active (is_active),
    INDEX idx_location (location_lat, location_lon)
);

-- Insert sample rescue authorities
INSERT INTO rescue_authorities (name, contact_type, contact_value, coverage_area, priority_level, active) VALUES
('Local Emergency Services', 'phone', '911', 'City-wide coverage', 1, TRUE),
('Fire Department', 'phone', '911', 'Fire emergencies', 1, TRUE),
('Police Department', 'phone', '911', 'Security emergencies', 1, TRUE),
('Emergency Webhook', 'webhook', 'http://localhost:8000/test-webhook', 'Test webhook endpoint', 2, TRUE),
('Test SMS Service', 'sms', '+1234567890', 'Test SMS notifications', 3, FALSE);

-- Create a view for active emergencies
CREATE OR REPLACE VIEW active_emergencies AS
SELECT
    sp.packet_id,
    sp.sender_id,
    sp.message,
    sp.urgency,
    sp.location_text,
    sp.latitude,
    sp.longitude,
    sp.packet_timestamp,
    sp.hop_count,
    sp.notifications_sent,
    sp.created_at,
    COUNT(n.id) as notification_count
FROM sos_packets sp
LEFT JOIN notifications n ON sp.packet_id = n.packet_id
WHERE sp.created_at >= DATE_SUB(NOW(), INTERVAL 24 HOUR)
GROUP BY sp.packet_id
ORDER BY sp.created_at DESC;

-- Create a view for network topology
CREATE OR REPLACE VIEW network_topology AS
SELECT
    nr.node_id,
    nr.node_name,
    nr.last_seen,
    nr.total_packets_sent,
    nr.total_packets_relayed,
    nr.is_active,
    COUNT(DISTINCT sp.packet_id) as recent_packets,
    AVG(sp.hop_count) as avg_hop_count
FROM node_registry nr
LEFT JOIN sos_packets sp ON nr.node_id = sp.sender_id
    AND sp.created_at >= DATE_SUB(NOW(), INTERVAL 24 HOUR)
GROUP BY nr.node_id
ORDER BY nr.last_seen DESC;

-- Show table creation status
SELECT 'Database setup completed successfully!' as Status;
SHOW TABLES;
