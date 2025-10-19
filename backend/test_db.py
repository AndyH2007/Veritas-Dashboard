import os
import psycopg2
from dotenv import load_dotenv

load_dotenv()

DB_URL = os.getenv("DATABASE_URL")
print(f"Connecting to: {DB_URL}")

try:
    conn = psycopg2.connect(DB_URL)
    cur = conn.cursor()
    cur.execute("SELECT version();")
    version = cur.fetchone()
    print(f"✓ Connected successfully!")
    print(f"PostgreSQL version: {version[0]}")
    
    # Check tables
    cur.execute("""
        SELECT table_name 
        FROM information_schema.tables 
        WHERE table_schema = 'public'
    """)
    tables = cur.fetchall()
    print(f"\n✓ Tables found: {[t[0] for t in tables]}")
    
    cur.close()
    conn.close()
except Exception as e:
    print(f"✗ Connection failed: {e}")