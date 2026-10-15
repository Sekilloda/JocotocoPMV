"""
Database Client with Supabase / PostgreSQL and Local SQLite Fallback
Supports portable multi-tenant Row-Level Security (RLS) via session variables:
    SET LOCAL app.current_tenant_id = '...';
"""

import os
import sqlite3
from typing import List, Dict, Any, Optional

try:
    import psycopg2
    from psycopg2.extras import RealDictCursor
    PSYCOPG2_AVAILABLE = True
except ImportError:
    PSYCOPG2_AVAILABLE = False


class DatabaseClient:
    def __init__(self, database_url: Optional[str] = None, data_dir: str = "data"):
        self.database_url = database_url or os.getenv("DATABASE_URL")
        self.data_dir = data_dir
        self.is_postgres = bool(self.database_url and PSYCOPG2_AVAILABLE)
        
        if not self.is_postgres:
            self.sqlite_path = os.path.join(data_dir, "central_platform.db")
            self._init_local_sqlite()

    def _init_local_sqlite(self):
        """Initializes fallback local SQLite for zero-config offline demonstration."""
        os.makedirs(self.data_dir, exist_ok=True)
        with sqlite3.connect(self.sqlite_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS devices (
                    id TEXT PRIMARY KEY,
                    organization_id TEXT NOT NULL,
                    project_id TEXT NOT NULL,
                    name TEXT NOT NULL,
                    hardware_model TEXT DEFAULT 'Raspberry Pi 5 8GB',
                    firmware_version TEXT DEFAULT '1.0.4',
                    latitude REAL NOT NULL,
                    longitude REAL NOT NULL,
                    elevation_m REAL,
                    status TEXT DEFAULT 'ACTIVE',
                    last_seen_at TEXT
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS audio_clips (
                    id TEXT PRIMARY KEY,
                    device_id TEXT NOT NULL,
                    organization_id TEXT NOT NULL,
                    storage_uri TEXT NOT NULL,
                    file_size_bytes INTEGER NOT NULL,
                    sha256_checksum TEXT NOT NULL,
                    format TEXT DEFAULT 'wav',
                    sample_rate_hz INTEGER DEFAULT 22050,
                    duration_seconds REAL NOT NULL,
                    uploaded_at TEXT
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS bioacoustic_events (
                    id TEXT PRIMARY KEY,
                    organization_id TEXT NOT NULL,
                    project_id TEXT NOT NULL,
                    device_id TEXT NOT NULL,
                    clip_id TEXT,
                    idempotency_key TEXT UNIQUE NOT NULL,
                    timestamp TEXT NOT NULL,
                    species_scientific_name TEXT NOT NULL,
                    species_common_name TEXT NOT NULL,
                    confidence REAL NOT NULL,
                    frequency_min_hz REAL,
                    frequency_max_hz REAL,
                    raw_metadata TEXT,
                    created_at TEXT
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS telemetry_logs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    device_id TEXT NOT NULL,
                    recorded_at TEXT NOT NULL,
                    battery_pct REAL,
                    solar_input_mw REAL,
                    cpu_temp_c REAL,
                    disk_used_pct REAL,
                    rssi_dbm INTEGER,
                    queue_depth INTEGER DEFAULT 0
                )
            """)
            conn.commit()

        # Seed local devices registry if present
        reg_file = os.path.join(self.data_dir, "devices.json")
        if os.path.exists(reg_file):
            import json
            try:
                with open(reg_file, "r", encoding="utf-8") as f:
                    devs = json.load(f)
                with sqlite3.connect(self.sqlite_path) as conn:
                    for d in devs:
                        conn.execute("""
                            INSERT OR IGNORE INTO devices (
                                id, organization_id, project_id, name,
                                latitude, longitude, elevation_m, status
                            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                        """, (
                            d["id"], "a0000000-0000-0000-0000-000000000001",
                            "b0000000-0000-0000-0000-000000000001",
                            d.get("name", d["id"]), d.get("latitude", 0.0),
                            d.get("longitude", 0.0), d.get("elevation_m", 0.0),
                            d.get("status", "ACTIVE")
                        ))
                    conn.commit()
            except Exception:
                pass

    def get_pg_connection(self, tenant_id: Optional[str] = None):
        """Creates a PostgreSQL connection and sets the tenant RLS context if specified."""
        if not self.is_postgres:
            return None
        conn = psycopg2.connect(self.database_url)
        if tenant_id:
            with conn.cursor() as cur:
                cur.execute("SET LOCAL app.current_tenant_id = %s;", (tenant_id,))
        return conn

    def record_event(
        self,
        event_dict: Dict[str, Any],
        clip_dict: Optional[Dict[str, Any]] = None,
        tenant_id: str = "a0000000-0000-0000-0000-000000000001"
    ) -> bool:
        """Stores bioacoustic event and clip metadata transactionally."""
        if self.is_postgres:
            try:
                conn = self.get_pg_connection(tenant_id=tenant_id)
                with conn:
                    with conn.cursor() as cur:
                        if clip_dict:
                            cur.execute("""
                                INSERT INTO audio_clips (
                                    id, device_id, organization_id, storage_uri,
                                    file_size_bytes, sha256_checksum, audio_format,
                                    sample_rate_hz, duration_seconds
                                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                                ON CONFLICT (id) DO NOTHING
                            """, (
                                clip_dict["id"], clip_dict["device_id"], tenant_id,
                                clip_dict["storage_uri"], clip_dict["file_size_bytes"],
                                clip_dict["sha256_checksum"], clip_dict.get("format", "wav"),
                                clip_dict.get("sample_rate_hz", 22050), clip_dict["duration_seconds"]
                            ))
                        cur.execute("""
                            INSERT INTO bioacoustic_events (
                                id, organization_id, project_id, device_id, clip_id,
                                idempotency_key, timestamp, species_scientific_name,
                                species_common_name, confidence, frequency_min_hz,
                                frequency_max_hz
                            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                            ON CONFLICT (idempotency_key) DO NOTHING
                        """, (
                            event_dict["id"], tenant_id,
                            event_dict.get("project_id", "b0000000-0000-0000-0000-000000000001"),
                            event_dict["device_id"], clip_dict["id"] if clip_dict else None,
                            event_dict["idempotency_key"], event_dict["timestamp"],
                            event_dict["species_scientific_name"], event_dict["species_common_name"],
                            event_dict["confidence"], event_dict.get("frequency_min_hz"),
                            event_dict.get("frequency_max_hz")
                        ))
                conn.close()
                return True
            except Exception as e:
                print(f"[!] PostgreSQL insertion error: {e}")
                return False
        else:
            with sqlite3.connect(self.sqlite_path) as conn:
                if clip_dict:
                    conn.execute("""
                        INSERT OR IGNORE INTO audio_clips (
                            id, device_id, organization_id, storage_uri,
                            file_size_bytes, sha256_checksum, duration_seconds, uploaded_at
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, datetime('now'))
                    """, (
                        clip_dict["id"], clip_dict["device_id"], tenant_id,
                        clip_dict["storage_uri"], clip_dict["file_size_bytes"],
                        clip_dict["sha256_checksum"], clip_dict["duration_seconds"]
                    ))
                conn.execute("""
                    INSERT OR IGNORE INTO bioacoustic_events (
                        id, organization_id, project_id, device_id, clip_id,
                        idempotency_key, timestamp, species_scientific_name,
                        species_common_name, confidence, frequency_min_hz,
                        frequency_max_hz, created_at
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now'))
                """, (
                    event_dict["id"], tenant_id,
                    event_dict.get("project_id", "b0000000-0000-0000-0000-000000000001"),
                    event_dict["device_id"], clip_dict["id"] if clip_dict else None,
                    event_dict["idempotency_key"], event_dict["timestamp"],
                    event_dict["species_scientific_name"], event_dict["species_common_name"],
                    event_dict["confidence"], event_dict.get("frequency_min_hz"),
                    event_dict.get("frequency_max_hz")
                ))
                conn.commit()
                return True

    def record_telemetry(self, item: Dict[str, Any]) -> bool:
        """Stores periodic device telemetry."""
        if self.is_postgres:
            try:
                conn = self.get_pg_connection()
                with conn:
                    with conn.cursor() as cur:
                        cur.execute("""
                            INSERT INTO telemetry_logs (
                                device_id, recorded_at, battery_pct, solar_input_mw,
                                cpu_temp_c, disk_used_pct, rssi_dbm, queue_depth
                            ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                        """, (
                            item["device_id"], item["recorded_at"],
                            item["battery_pct"], item["solar_mw"],
                            item["cpu_temp_c"], item["disk_used_pct"],
                            item["rssi_dbm"], item.get("queue_depth", 0)
                        ))
                        cur.execute("""
                            UPDATE devices SET last_seen_at = %s WHERE id = %s
                        """, (item["recorded_at"], item["device_id"]))
                conn.close()
                return True
            except Exception as e:
                print(f"[!] Error de telemetría en PostgreSQL: {e}")
                return False
        else:
            with sqlite3.connect(self.sqlite_path) as conn:
                conn.execute("""
                    INSERT INTO telemetry_logs (
                        device_id, recorded_at, battery_pct, solar_input_mw,
                        cpu_temp_c, disk_used_pct, rssi_dbm, queue_depth
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    item["device_id"], item["recorded_at"],
                    item["battery_pct"], item["solar_mw"],
                    item["cpu_temp_c"], item["disk_used_pct"],
                    item["rssi_dbm"], item.get("queue_depth", 0)
                ))
                conn.commit()
                return True

    def get_recent_events(self, limit: int = 50) -> List[Dict[str, Any]]:
        """Retrieves recent bioacoustic events."""
        if self.is_postgres:
            try:
                conn = self.get_pg_connection()
                with conn.cursor(cursor_factory=RealDictCursor) as cur:
                    cur.execute("""
                        SELECT e.id, e.device_id, e.timestamp, e.species_scientific_name,
                               e.species_common_name, e.confidence, e.clip_id,
                               d.name as device_name, c.storage_uri, c.file_size_bytes
                        FROM bioacoustic_events e
                        LEFT JOIN devices d ON e.device_id = d.id
                        LEFT JOIN audio_clips c ON e.clip_id = c.id
                        ORDER BY e.timestamp DESC LIMIT %s
                    """, (limit,))
                    res = cur.fetchall()
                conn.close()
                return [dict(r) for r in res]
            except Exception:
                return []
        else:
            with sqlite3.connect(self.sqlite_path) as conn:
                conn.row_factory = sqlite3.Row
                cur = conn.cursor()
                cur.execute("""
                    SELECT e.id, e.device_id, e.timestamp, e.species_scientific_name,
                           e.species_common_name, e.confidence, e.clip_id,
                           d.name as device_name, c.storage_uri, c.file_size_bytes
                    FROM bioacoustic_events e
                    LEFT JOIN devices d ON e.device_id = d.id
                    LEFT JOIN audio_clips c ON e.clip_id = c.id
                    ORDER BY e.timestamp DESC LIMIT ?
                """, (limit,))
                return [dict(r) for r in cur.fetchall()]
