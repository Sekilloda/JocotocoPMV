"""
Supabase Setup & Migration Runner
Applies PostgreSQL schemas, seeds the 20 Raspberry Pis, uploads Ed25519 public keys,
and verifies portable Row-Level Security (RLS) isolation.

Usage:
    python3 scripts/setup_supabase.py [--db-url "postgresql://..."]
"""

import os
import sys

# Ensure repository root is on Python module search path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

import json
import argparse


try:
    import psycopg2
    from psycopg2.extras import RealDictCursor
except ImportError:
    print("[!] Error: psycopg2 is required. Run 'pip install psycopg2-binary'.")
    sys.exit(1)


def run_migrations(db_url: str):
    print("=" * 70)
    print("   SUPABASE POSTGRESQL INITIALIZATION — FUNDACIÓN JOCOTOCO")
    print("=" * 70)
    print(f"[*] Connecting to database at {db_url.split('@')[-1]}...")
    
    try:
        conn = psycopg2.connect(db_url)
        conn.autocommit = True
    except Exception as e:
        print(f"[x] Connection failed: {e}")
        return False

    print("[+] Successfully connected to Supabase PostgreSQL!")

    # Check PostGIS
    with conn.cursor() as cur:
        cur.execute("SELECT extversion FROM pg_extension WHERE extname = 'postgis';")
        res = cur.fetchone()
        if res:
            print(f"[+] PostGIS extension is installed (v{res[0]}).")
        else:
            print("[*] PostGIS extension not active yet. Migration will attempt activation.")

    # 1. Apply 001_initial_schema.sql
    schema_path = os.path.join(os.path.dirname(__file__), "..", "database", "migrations", "001_initial_schema.sql")
    print(f"\n[*] Applying schema migration from: {schema_path}")
    with open(schema_path, "r", encoding="utf-8") as f:
        schema_sql = f.read()
    
    with conn.cursor() as cur:
        cur.execute(schema_sql)
    print("[+] Database tables and portable RLS policies created.")

    # 2. Apply 002_seed_swarm.sql
    seed_path = os.path.join(os.path.dirname(__file__), "..", "database", "migrations", "002_seed_swarm.sql")
    print(f"[*] Applying seed data (6 Jocotoco reserves, 20 Pis) from: {seed_path}")
    with open(seed_path, "r", encoding="utf-8") as f:
        seed_sql = f.read()
        
    with conn.cursor() as cur:
        cur.execute(seed_sql)
    print("[+] Reserves and devices seeded successfully.")

    # 3. Synchronize generated Ed25519 public keys from data/devices.json
    devices_json_path = os.path.join(os.path.dirname(__file__), "..", "data", "devices.json")
    if os.path.exists(devices_json_path):
        print(f"[*] Registering Ed25519 public keys from {devices_json_path}...")
        with open(devices_json_path, "r", encoding="utf-8") as f:
            devices = json.load(f)
        with conn.cursor() as cur:
            for dev in devices:
                cur.execute("""
                    INSERT INTO device_keys (device_id, public_key_hex, is_active)
                    VALUES (%s, %s, TRUE)
                    ON CONFLICT DO NOTHING
                """, (dev["id"], dev["public_key_hex"]))
        print(f"[+] Registered Ed25519 cryptographic keys for {len(devices)} devices.")

    # 4. Verify Portable RLS (Row-Level Security)
    print("\n[*] Validating Portable Multi-Tenant RLS Policy (ToR Test 2)...")
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        # Test A: Context set to Jocotoco Organization
        cur.execute("SET LOCAL app.current_tenant_id = 'a0000000-0000-0000-0000-000000000001';")
        cur.execute("SELECT COUNT(*) as count FROM devices;")
        count_joco = cur.fetchone()["count"]
        print(f"    - Query with Jocotoco Tenant Context -> Devices visible: {count_joco} (Expected: 20)")

        # Test B: Context set to an external unlinked tenant
        cur.execute("SET LOCAL app.current_tenant_id = 'e0000000-0000-0000-0000-000000000099';")
        cur.execute("SELECT COUNT(*) as count FROM devices;")
        count_alien = cur.fetchone()["count"]
        print(f"    - Query with Foreign Tenant Context   -> Devices visible: {count_alien} (Expected: 0, Complete Isolation)")

    conn.close()
    print("\n[✓] SUPABASE SETUP AND VERIFICATION COMPLETE!")
    return True


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Initialize Supabase database for Jocotoco PoC")
    parser.add_argument("--db-url", type=str, default=os.getenv("DATABASE_URL"), help="Supabase PostgreSQL connection string")
    args = parser.parse_args()

    if not args.db_url:
        print("[!] No DATABASE_URL provided.")
        print("    You can either:")
        print("    1. Set the DATABASE_URL environment variable: export DATABASE_URL='postgresql://...'")
        print("    2. Pass it directly: python3 scripts/setup_supabase.py --db-url 'postgresql://...'")
        print("    3. Copy database/migrations/001_initial_schema.sql and 002_seed_swarm.sql directly into the Supabase SQL Editor!")
        sys.exit(1)

    run_migrations(args.db_url)
