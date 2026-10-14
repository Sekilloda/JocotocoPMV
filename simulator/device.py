"""
Raspberry Pi 5 Edge Node Emulator
Simulates a field monitor daemon running in a Jocotoco reserve:
- Ed25519 cryptographic key generation & request signing
- Transactional local SQLite buffer resilient to power cuts and network loss
- Generates 100 kB pink noise audio clips on bioacoustic triggers
- Idempotency handling and resumable synchronization
"""

import os
import time
import json
import uuid
import sqlite3
import hashlib
from datetime import datetime, timezone
from typing import Dict, Any, Optional, Tuple

from cryptography.hazmat.primitives.asymmetric import ed25519

from simulator.pink_noise import generate_pink_noise_wav


# Bioacoustic targets mapped to Jocotoco reserves
RESERVE_SPECIES = {
    "buenaventura": [
        {"scientific": "Pyrrhura orcesi", "common": "El Oro Parakeet", "freq_range": [2800, 6200]},
        {"scientific": "Grallaria ridgelyi", "common": "Jocotoco Antpitta", "freq_range": [950, 1850]},
        {"scientific": "Phaethornis yaruqui", "common": "White-whiskered Hermit", "freq_range": [4200, 8500]}
    ],
    "tapichalaca": [
        {"scientific": "Grallaria ridgelyi", "common": "Jocotoco Antpitta", "freq_range": [900, 1800]},
        {"scientific": "Heliangelus regalis", "common": "Royal Sunangel", "freq_range": [5000, 9200]},
        {"scientific": "Scytalopus latebricola", "common": "Brown-rumped Tapaculo", "freq_range": [1400, 3100]}
    ],
    "yanacocha": [
        {"scientific": "Eriocnemis nigrivestis", "common": "Black-breasted Puffleg", "freq_range": [4800, 9500]},
        {"scientific": "Oreomanes fraseri", "common": "Giant Conebill", "freq_range": [2200, 4800]},
        {"scientific": "Anairetes alpinus", "common": "Ash-breasted Tit-Tyrant", "freq_range": [3000, 6100]}
    ],
    "canande": [
        {"scientific": "Neomorphus radiolosus", "common": "Banded Ground-Cuckoo", "freq_range": [650, 1400]},
        {"scientific": "Ara ambiguus", "common": "Great Green Macaw", "freq_range": [1100, 4200]},
        {"scientific": "Cephalopterus penduliger", "common": "Long-wattled Umbrellabird", "freq_range": [400, 950]}
    ],
    "narupa": [
        {"scientific": "Setophaga cerulea", "common": "Cerulean Warbler", "freq_range": [3800, 7800]},
        {"scientific": "Ara militaris", "common": "Military Macaw", "freq_range": [1200, 4400]},
        {"scientific": "Aburria aburri", "common": "Wattled Guan", "freq_range": [800, 2100]}
    ],
    "antisanilla": [
        {"scientific": "Vultur gryphus", "common": "Andean Condor", "freq_range": [350, 1100]},
        {"scientific": "Oreotrochilus chimborazo", "common": "Ecuadorian Hillstar", "freq_range": [4500, 9200]},
        {"scientific": "Cinclodes excelsior", "common": "Stout-billed Cinclodes", "freq_range": [1800, 3900]}
    ]
}


class SimulatedRaspberryPi:
    def __init__(
        self,
        device_id: str,
        reserve_slug: str,
        name: str,
        lat: float,
        lon: float,
        elevation: float,
        data_dir: str = "data",
        target_audio_bytes: int = 100000
    ):
        self.device_id = device_id
        self.reserve_slug = reserve_slug
        self.name = name
        self.lat = lat
        self.lon = lon
        self.elevation = elevation
        self.data_dir = data_dir
        self.target_audio_bytes = target_audio_bytes
        
        self.clips_dir = os.path.join(data_dir, "audio_clips", device_id)
        self.db_dir = os.path.join(data_dir, "sqlite_buffers")
        os.makedirs(self.clips_dir, exist_ok=True)
        os.makedirs(self.db_dir, exist_ok=True)
        
        self.db_path = os.path.join(self.db_dir, f"{device_id}.sqlite")
        
        # Hardware & power status simulation
        self.battery_pct = round(85.0 + (hash(device_id) % 15) - 5.0, 1)
        self.solar_input_mw = round(1200.0 + (hash(device_id) % 800), 1)
        self.cpu_temp_c = round(42.5 + (hash(device_id) % 10), 1)
        self.disk_used_pct = round(18.0 + (hash(device_id) % 12), 1)
        self.rssi_dbm = -68 - (hash(device_id) % 25)
        
        # Cryptographic Identity (Ed25519)
        self._init_crypto_keys()
        
        # Local SQLite Transactional Buffer
        self._init_sqlite_buffer()

    def _init_crypto_keys(self):
        """Initializes or loads the persistent Ed25519 keypair for this device."""
        key_file = os.path.join(self.db_dir, f"{self.device_id}.key")
        if os.path.exists(key_file):
            with open(key_file, "rb") as f:
                raw_bytes = f.read()
            self.private_key = ed25519.Ed25519PrivateKey.from_private_bytes(raw_bytes)
        else:
            self.private_key = ed25519.Ed25519PrivateKey.generate()
            with open(key_file, "wb") as f:
                f.write(self.private_key.private_bytes_raw())
        self.public_key = self.private_key.public_key()
        self.public_key_hex = self.public_key.public_bytes_raw().hex()

    def _init_sqlite_buffer(self):
        """Creates the local transactional SQLite schema if it doesn't exist."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS events_buffer (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    event_uuid TEXT UNIQUE NOT NULL,
                    idempotency_key TEXT UNIQUE NOT NULL,
                    timestamp TEXT NOT NULL,
                    species_scientific TEXT NOT NULL,
                    species_common TEXT NOT NULL,
                    confidence REAL NOT NULL,
                    freq_min_hz REAL,
                    freq_max_hz REAL,
                    clip_path TEXT NOT NULL,
                    clip_bytes INTEGER NOT NULL,
                    clip_sha256 TEXT NOT NULL,
                    duration_sec REAL NOT NULL,
                    status TEXT DEFAULT 'QUEUED' CHECK (status IN ('QUEUED', 'UPLOADING', 'ACKNOWLEDGED', 'FAILED')),
                    retry_count INTEGER DEFAULT 0,
                    created_at TEXT NOT NULL
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS telemetry_buffer (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    recorded_at TEXT NOT NULL,
                    battery_pct REAL,
                    solar_mw REAL,
                    cpu_temp_c REAL,
                    disk_used_pct REAL,
                    rssi_dbm INTEGER,
                    status TEXT DEFAULT 'QUEUED'
                )
            """)
            conn.commit()

    def sign_payload(self, payload_bytes: bytes, timestamp_iso: str) -> str:
        """
        Signs the payload as defined in Proposal Section 2.2 B:
        Signature computed over SHA-256(payload) concatenated with timestamp.
        """
        payload_hash = hashlib.sha256(payload_bytes).hexdigest()
        message_to_sign = f"{payload_hash}:{timestamp_iso}".encode("utf-8")
        signature_bytes = self.private_key.sign(message_to_sign)
        return signature_bytes.hex()

    def get_auth_headers(self, payload: Any) -> Tuple[Dict[str, str], bytes]:
        """Produces authentication headers: X-Device-Id, X-Timestamp, X-Signature and matching payload bytes."""
        timestamp_iso = datetime.now(timezone.utc).isoformat()
        if isinstance(payload, bytes):
            payload_bytes = payload
        else:
            payload_bytes = json.dumps(payload, sort_keys=True).encode("utf-8")
        signature_hex = self.sign_payload(payload_bytes, timestamp_iso)
        headers = {
            "X-Device-Id": self.device_id,
            "X-Timestamp": timestamp_iso,
            "X-Signature": signature_hex,
            "Content-Type": "application/json"
        }
        return headers, payload_bytes


    def trigger_detection(self) -> Dict[str, Any]:
        """
        Simulates an edge ML detection event (e.g. Google Perch2 inference trigger).
        Generates an authentic 100 kB pink noise WAV audio clip and records it in SQLite.
        """
        import random
        species_list = RESERVE_SPECIES.get(self.reserve_slug, RESERVE_SPECIES["buenaventura"])
        target = random.choice(species_list)
        
        event_uuid = str(uuid.uuid4())
        idempotency_key = str(uuid.uuid4())
        timestamp = datetime.now(timezone.utc).isoformat()
        confidence = round(random.uniform(0.86, 0.98), 4)
        
        # Generate exact 100 kB pink noise audio clip
        clip_filename = f"clip_{event_uuid[:8]}.wav"
        clip_path = os.path.join(self.clips_dir, clip_filename)
        _, clip_bytes, duration_sec, clip_sha256 = generate_pink_noise_wav(
            clip_path,
            target_bytes=self.target_audio_bytes,
            sample_rate=22050
        )
        
        # Enqueue in local persistent SQLite buffer
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT INTO events_buffer (
                    event_uuid, idempotency_key, timestamp, species_scientific,
                    species_common, confidence, freq_min_hz, freq_max_hz,
                    clip_path, clip_bytes, clip_sha256, duration_sec,
                    status, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'QUEUED', ?)
            """, (
                event_uuid, idempotency_key, timestamp, target["scientific"],
                target["common"], confidence, target["freq_range"][0], target["freq_range"][1],
                clip_path, clip_bytes, clip_sha256, duration_sec, timestamp
            ))
            conn.commit()
            
        return {
            "event_uuid": event_uuid,
            "idempotency_key": idempotency_key,
            "device_id": self.device_id,
            "timestamp": timestamp,
            "species_scientific": target["scientific"],
            "species_common": target["common"],
            "confidence": confidence,
            "clip_path": clip_path,
            "clip_bytes": clip_bytes,
            "clip_sha256": clip_sha256,
            "duration_sec": duration_sec
        }

    def record_telemetry(self) -> Dict[str, Any]:
        """Captures hardware vitals and queues them locally."""
        import random
        # Drift slightly
        self.battery_pct = max(10.0, min(100.0, self.battery_pct + random.uniform(-0.5, 0.4)))
        self.cpu_temp_c = max(35.0, min(75.0, self.cpu_temp_c + random.uniform(-0.8, 0.8)))
        now_iso = datetime.now(timezone.utc).isoformat()
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM events_buffer WHERE status = 'QUEUED'")
            queue_depth = cursor.fetchone()[0]
            
            conn.execute("""
                INSERT INTO telemetry_buffer (recorded_at, battery_pct, solar_mw, cpu_temp_c, disk_used_pct, rssi_dbm)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (now_iso, self.battery_pct, self.solar_input_mw, self.cpu_temp_c, self.disk_used_pct, self.rssi_dbm))
            conn.commit()
            
        return {
            "device_id": self.device_id,
            "recorded_at": now_iso,
            "battery_pct": round(self.battery_pct, 1),
            "solar_mw": round(self.solar_input_mw, 1),
            "cpu_temp_c": round(self.cpu_temp_c, 1),
            "disk_used_pct": round(self.disk_used_pct, 1),
            "rssi_dbm": self.rssi_dbm,
            "queue_depth": queue_depth
        }

    def get_queued_events(self, limit: int = 10):
        """Retrieves uncommitted events from local buffer."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM events_buffer WHERE status IN ('QUEUED', 'FAILED') ORDER BY id ASC LIMIT ?", (limit,))
            return [dict(row) for row in cursor.fetchall()]

    def mark_event_synced(self, event_uuid: str):
        """Marks event as confirmed by server."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("UPDATE events_buffer SET status = 'ACKNOWLEDGED' WHERE event_uuid = ?", (event_uuid,))
            conn.commit()
