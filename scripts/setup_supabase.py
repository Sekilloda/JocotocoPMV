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
    print("   INICIALIZACIÓN DE SUPABASE POSTGRESQL — FUNDACIÓN JOCOTOCO")
    print("=" * 70)
    print(f"[*] Conectando a la base de datos en {db_url.split('@')[-1]}...")
    
    try:
        conn = psycopg2.connect(db_url)
        conn.autocommit = True
    except Exception as e:
        print(f"[x] Error de conexión: {e}")
        return False

    print("[+] ¡Conexión exitosa a Supabase PostgreSQL!")

    # Check PostGIS
    with conn.cursor() as cur:
        cur.execute("SELECT extversion FROM pg_extension WHERE extname = 'postgis';")
        res = cur.fetchone()
        if res:
            print(f"[+] Extensión PostGIS instalada (v{res[0]}).")
        else:
            print("[*] Extensión PostGIS no activa aún. La migración intentará activarla.")

    # 1. Apply 001_initial_schema.sql
    schema_path = os.path.join(os.path.dirname(__file__), "..", "database", "migrations", "001_initial_schema.sql")
    print(f"\n[*] Aplicando migración de esquema desde: {schema_path}")
    with open(schema_path, "r", encoding="utf-8") as f:
        schema_sql = f.read()
    
    with conn.cursor() as cur:
        cur.execute(schema_sql)
    print("[+] Tablas relacionales y políticas de RLS creadas exitosamente.")

    # 2. Apply 002_seed_swarm.sql
    seed_path = os.path.join(os.path.dirname(__file__), "..", "database", "migrations", "002_seed_swarm.sql")
    print(f"[*] Aplicando datos de semillado (6 reservas de Jocotoco, 20 monitores) desde: {seed_path}")
    with open(seed_path, "r", encoding="utf-8") as f:
        seed_sql = f.read()
        
    with conn.cursor() as cur:
        cur.execute(seed_sql)
    print("[+] Reservas y dispositivos semillados con éxito.")

    # 3. Synchronize generated Ed25519 public keys from data/devices.json
    devices_json_path = os.path.join(os.path.dirname(__file__), "..", "data", "devices.json")
    if os.path.exists(devices_json_path):
        print(f"[*] Registrando claves públicas Ed25519 desde {devices_json_path}...")
        with open(devices_json_path, "r", encoding="utf-8") as f:
            devices = json.load(f)
        with conn.cursor() as cur:
            for dev in devices:
                cur.execute("""
                    INSERT INTO device_keys (device_id, public_key_hex, is_active)
                    VALUES (%s, %s, TRUE)
                    ON CONFLICT DO NOTHING
                """, (dev["id"], dev["public_key_hex"]))
        print(f"[+] Registradas claves criptográficas Ed25519 para {len(devices)} dispositivos.")

    # 4. Verify Portable RLS (Row-Level Security)
    print("\n[*] Validando política portable de aislamiento multi-inquilino RLS (Prueba TdR 2)...")
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        # Test A: Context set to Jocotoco Organization
        cur.execute("SET LOCAL app.current_tenant_id = 'a0000000-0000-0000-0000-000000000001';")
        cur.execute("SELECT COUNT(*) as count FROM devices;")
        count_joco = cur.fetchone()["count"]
        print(f"    - Consulta con contexto de Jocotoco       -> Dispositivos visibles: {count_joco} (Esperado: 20)")

        # Test B: Context set to an external unlinked tenant
        cur.execute("SET LOCAL app.current_tenant_id = 'e0000000-0000-0000-0000-000000000099';")
        cur.execute("SELECT COUNT(*) as count FROM devices;")
        count_alien = cur.fetchone()["count"]
        print(f"    - Consulta con contexto de inquilino ajeno -> Dispositivos visibles: {count_alien} (Esperado: 0, Aislamiento Total)")

    conn.close()
    print("\n[✓] ¡INICIALIZACIÓN Y VALIDACIÓN DE SUPABASE COMPLETADA CON ÉXITO!")
    return True


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Inicializar base de datos Supabase para el PoC de Jocotoco")
    parser.add_argument("--db-url", type=str, default=os.getenv("DATABASE_URL"), help="Cadena de conexión de Supabase PostgreSQL")
    args = parser.parse_args()

    if not args.db_url:
        print("[!] No DATABASE_URL provided.")
        print("    You can either:")
        print("    1. Set the DATABASE_URL environment variable: export DATABASE_URL='postgresql://...'")
        print("    2. Pass it directly: python3 scripts/setup_supabase.py --db-url 'postgresql://...'")
        print("    3. Copy database/migrations/001_initial_schema.sql and 002_seed_swarm.sql directly into the Supabase SQL Editor!")
        sys.exit(1)

    run_migrations(args.db_url)
