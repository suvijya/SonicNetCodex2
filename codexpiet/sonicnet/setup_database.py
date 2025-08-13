#!/usr/bin/env python3
"""
Database setup helper script for SonicWave Emergency Server.
Run this script to automatically create database and tables.
"""

import os
import sys
import mysql.connector
from mysql.connector import Error
import logging

# Setup logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')
logger = logging.getLogger(__name__)

def load_env_file():
    """Load environment variables from .env file."""
    env_file = '../.env'
    if not os.path.exists(env_file):
        logger.error("❌ .env file not found! Please copy .env.example to .env and configure it.")
        return False

    with open(env_file, 'r') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                key, value = line.split('=', 1)
                os.environ[key] = value

    logger.info("✅ Environment variables loaded from .env file")
    return True

def test_mysql_connection():
    """Test MySQL connection with admin credentials."""
    try:
        # Try to connect as root first
        connection = mysql.connector.connect(
            host=os.getenv('DB_HOST', 'localhost'),
            port=int(os.getenv('DB_PORT', 3306)),
            user='root',  # Admin user
            password=input("Enter MySQL root password: ")
        )

        if connection.is_connected():
            logger.info("✅ MySQL connection successful")
            return connection

    except Error as e:
        logger.error(f"❌ MySQL connection failed: {e}")
        return None

def create_database_and_user(connection):
    """Create database and user from SQL script."""
    try:
        cursor = connection.cursor()

        # Read SQL setup script
        with open('database_setup.sql', 'r') as f:
            sql_script = f.read()

        # Split and execute SQL statements
        statements = sql_script.split(';')

        for statement in statements:
            statement = statement.strip()
            if statement and not statement.startswith('--'):
                try:
                    cursor.execute(statement)
                    logger.info(f"✅ Executed: {statement[:50]}...")
                except Error as e:
                    if "already exists" in str(e).lower():
                        logger.info(f"ℹ️  Already exists: {statement[:50]}...")
                    else:
                        logger.warning(f"⚠️  Warning: {e}")

        connection.commit()
        cursor.close()
        logger.info("✅ Database and tables created successfully!")
        return True

    except Error as e:
        logger.error(f"❌ Database creation failed: {e}")
        return False

def test_application_connection():
    """Test connection with application credentials."""
    try:
        connection = mysql.connector.connect(
            host=os.getenv('DB_HOST'),
            port=int(os.getenv('DB_PORT')),
            user=os.getenv('DB_USER'),
            password=os.getenv('DB_PASSWORD'),
            database=os.getenv('DB_NAME')
        )

        if connection.is_connected():
            cursor = connection.cursor()
            cursor.execute("SELECT COUNT(*) FROM sos_packets")
            count = cursor.fetchone()[0]
            logger.info(f"✅ Application database connection successful! Found {count} packets.")

            # Test table structure
            cursor.execute("SHOW TABLES")
            tables = [table[0] for table in cursor.fetchall()]
            logger.info(f"✅ Tables found: {', '.join(tables)}")

            cursor.close()
            connection.close()
            return True

    except Error as e:
        logger.error(f"❌ Application connection failed: {e}")
        return False

def main():
    """Main setup function."""
    print("🚀 SonicWave Database Setup")
    print("=" * 40)

    # Load environment
    if not load_env_file():
        sys.exit(1)

    # Test MySQL admin connection
    print("\n📡 Testing MySQL connection...")
    admin_connection = test_mysql_connection()
    if not admin_connection:
        sys.exit(1)

    # Create database and user
    print("\n🗄️  Creating database and tables...")
    if not create_database_and_user(admin_connection):
        sys.exit(1)

    admin_connection.close()

    # Test application connection
    print("\n🔍 Testing application connection...")
    if not test_application_connection():
        sys.exit(1)

    print("\n🎉 Database setup completed successfully!")
    print("\nNext steps:")
    print("1. Run the server: python server.py")
    print("2. Run the client: python main.py")
    print("3. View dashboard: http://localhost:8000")

if __name__ == "__main__":
    main()
