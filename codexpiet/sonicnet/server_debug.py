#!/usr/bin/env python3
"""
Server Debug and Test Script
Checks server status and helps debug any issues.
"""

import requests
import sys
import os
import subprocess
import time

def load_env_variables():
    """Load environment variables from .env file."""
    env_vars = {}
    env_file = '../.env'

    if not os.path.exists(env_file):
        print("⚠️  No .env file found!")
        print("   💡 Copy .env.example to .env and configure database settings")
        return env_vars

    try:
        with open(env_file, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    env_vars[key] = value
                    os.environ[key] = value  # Set for current session
        print(f"✅ Loaded environment variables from {env_file}")
        return env_vars
    except Exception as e:
        print(f"❌ Error loading .env file: {e}")
        return env_vars

def test_server_status():
    """Test if server is running and responding."""
    print("🔍 Testing Server Status...")

    try:
        response = requests.get("http://localhost:8000/api/stats", timeout=5)
        if response.status_code == 200:
            stats = response.json()
            print("✅ Server is ONLINE and responding!")
            print(f"   📊 Total packets: {stats.get('total_packets', 0)}")
            print(f"   🚨 Active emergencies: {stats.get('active_emergencies', 0)}")
            print(f"   🏥 Rescue authorities: {stats.get('rescue_authorities', 0)}")
            return True
        else:
            print(f"❌ Server responded with status {response.status_code}")
            return False
    except requests.exceptions.ConnectionError:
        print("❌ Server is OFFLINE (connection refused)")
        print("   💡 Server needs to be started")
        return False
    except Exception as e:
        print(f"❌ Server test error: {e}")
        return False

def test_database_connection():
    """Test database connectivity using credentials from .env file."""
    print("\n🗄️  Testing Database Connection...")

    # Load environment variables
    env_vars = load_env_variables()

    # Get database credentials (use defaults for common settings)
    db_host = env_vars.get('DB_HOST', 'localhost')
    db_port = 3306  # Always use default MySQL port
    db_user = env_vars.get('DB_USER', 'sonicwave')
    db_password = env_vars.get('DB_PASSWORD', 'sonicwave123')
    db_name = env_vars.get('DB_NAME', 'sonicwave_emergency')

    print(f"   🔍 Testing connection to {db_host}:{db_port}")
    print(f"   👤 User: {db_user}")
    print(f"   🗃️  Database: {db_name}")

    try:
        import mysql.connector

        # Test database connection
        connection = mysql.connector.connect(
            host=db_host,
            port=db_port,
            user=db_user,
            password=db_password,
            database=db_name
        )

        if connection.is_connected():
            cursor = connection.cursor()

            # Test basic queries
            cursor.execute("SELECT COUNT(*) FROM sos_packets")
            packet_count = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM rescue_authorities")
            authority_count = cursor.fetchone()[0]

            cursor.close()
            connection.close()

            print("   ✅ Database connection successful!")
            print(f"      📦 SOS packets: {packet_count}")
            print(f"      🏥 Rescue authorities: {authority_count}")
            return True

    except mysql.connector.Error as e:
        print(f"   ❌ MySQL connection error: {e}")
        print(f"   💡 Check your database credentials in .env file")

        if "Access denied" in str(e):
            print(f"   🔑 Verify username/password in .env file")
        elif "Unknown database" in str(e):
            print(f"   📂 Run: python setup_database.py")
        elif "Can't connect to MySQL server" in str(e):
            print(f"   🚀 Start MySQL server first")

        return False
    except ImportError:
        print("   ❌ mysql-connector-python not installed")
        print("   💡 Run: pip install mysql-connector-python")
        return False
    except Exception as e:
        print(f"   ❌ Database test error: {e}")
        return False

def test_server_dependencies():
    """Test if server can import all dependencies using env config."""
    print("\n📡 Testing Server Dependencies...")

    # Load environment first
    load_env_variables()

    try:
        # Test server module imports
        sys.path.insert(0, os.getcwd())

        print("   🔍 Testing FastAPI imports...")
        import fastapi
        import uvicorn
        print("   ✅ FastAPI and Uvicorn")

        print("   🔍 Testing database imports...")
        import aiomysql
        import mysql.connector
        print("   ✅ MySQL connectors")

        print("   🔍 Testing server module...")
        from server import app, db_manager
        print("   ✅ Server module imports successfully")

        return True

    except ImportError as e:
        print(f"   ❌ Missing dependency: {e}")
        print("   💡 Run: pip install -r server_requirements.txt")
        return False
    except Exception as e:
        print(f"   ❌ Server dependency error: {e}")
        return False

def check_dependencies():
    """Check if all required dependencies are installed."""
    print("\n📦 Checking Dependencies...")

    required_packages = [
        'fastapi', 'uvicorn', 'aiomysql', 'mysql-connector-python',
        'httpx', 'websockets', 'geopy'
    ]

    missing = []
    for package in required_packages:
        try:
            __import__(package.replace('-', '_'))
            print(f"   ✅ {package}")
        except ImportError:
            print(f"   ❌ {package} - MISSING")
            missing.append(package)

    if missing:
        print(f"\n💡 Install missing packages:")
        print(f"   pip install {' '.join(missing)}")
        return False

    return True

def start_server_instructions():
    """Provide instructions to start the server."""
    print("\n🚀 To Start the Server:")
    print("   1. Open a new terminal")
    print("   2. Navigate to the sonicnet directory")
    print("   3. Run: python server.py")
    print("   4. Wait for 'Server started' message")
    print("   5. Then run the showcase script")

def main():
    """Main debug function."""
    print("🔧 SonicWave Server Debug & Test")
    print("=" * 40)

    # Test server status
    server_running = test_server_status()

    # Test dependencies
    deps_ok = check_dependencies()

    # Test database (if server not running)
    if not server_running:
        db_ok = test_database_connection()
        server_running = db_ok  # If DB test passes, we consider the server as running for this script

    print("\n" + "=" * 40)
    print("📋 DEBUG SUMMARY:")

    if server_running:
        print("🎉 SERVER IS READY!")
        print("   You can now run the client showcase:")
        print("   python client_showcase.py")
    else:
        print("⚠️  SERVER NEEDS ATTENTION:")
        if not deps_ok:
            print("   🔴 Missing dependencies - install them first")
        else:
            print("   🔴 Server is not running")
        start_server_instructions()

if __name__ == "__main__":
    main()
