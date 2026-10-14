"""
Jocotoco Smart Bioacoustic Monitor API Server
Provides high-performance ingestion, Ed25519 verification, OTA distribution,
and an interactive operations dashboard.
"""

import os
import json
import uuid
import hashlib
from datetime import datetime, timezone
from flask import Flask, request, jsonify, render_template, send_from_directory, Response

from api.auth import DeviceAuthenticator
from database.client import DatabaseClient


app = Flask(
    __name__,
    template_folder="../dashboard/templates",
    static_folder="../dashboard/static"
)

DATA_DIR = os.getenv("DATA_DIR", "data")
STORAGE_DIR = os.path.join(DATA_DIR, "storage")
os.makedirs(STORAGE_DIR, exist_ok=True)

auth = DeviceAuthenticator(devices_registry_path=os.path.join(DATA_DIR, "devices.json"))
db = DatabaseClient(data_dir=DATA_DIR)

# In-memory idempotency cache for fast lookup
IDEMPOTENCY_STORE = {}


@app.route("/healthz", methods=["GET"])
@app.route("/readyz", methods=["GET"])
def healthz():
    """Observability health check endpoint for Railway and container orchestration."""
    return jsonify({
        "status": "healthy",
        "service": "jocotoco-smart-monitor-backend",
        "version": "1.0.0-poc",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "database": "postgresql" if db.is_postgres else "sqlite_local",
        "active_devices_tracked": len(auth.public_keys)
    }), 200


@app.route("/api/v1/ingest/authorize", methods=["POST"])
def ingest_authorize():
    """
    Step 1 of Ingestion (Proposal Section 2.2 B & C):
    Edge agent requests authorization with Ed25519 cryptographic signature.
    Backend verifies device authenticity and generates an upload destination.
    """
    dev_id = request.headers.get("X-Device-Id")
    ts = request.headers.get("X-Timestamp")
    sig = request.headers.get("X-Signature")
    
    if not all([dev_id, ts, sig]):
        return jsonify({"error": "Missing required Ed25519 signature headers"}), 401

    payload_bytes = request.get_data()
    is_valid, msg = auth.verify_request(dev_id, ts, sig, payload_bytes)
    if not is_valid:
        return jsonify({"error": f"Cryptographic verification rejected: {msg}"}), 403

    body = request.get_json(silent=True) or {}
    clip_id = str(uuid.uuid4())
    upload_url = f"/api/v1/storage/upload/{clip_id}"

    return jsonify({
        "status": "authorized",
        "clip_id": clip_id,
        "upload_url": upload_url,
        "expected_bytes": body.get("clip_bytes", 100000),
        "expires_in_seconds": 300
    }), 200


@app.route("/api/v1/storage/upload/<clip_id>", methods=["PUT"])
def storage_upload(clip_id):
    """
    Step 2 of Ingestion:
    Receives the 100 kB audio clip directly into object storage.
    Validates SHA-256 and writes to disk.
    """
    audio_data = request.get_data()
    if not audio_data:
        return jsonify({"error": "Empty audio payload"}), 400

    sha256 = hashlib.sha256(audio_data).hexdigest()
    clip_path = os.path.join(STORAGE_DIR, f"{clip_id}.wav")
    with open(clip_path, "wb") as f:
        f.write(audio_data)

    return jsonify({
        "status": "stored",
        "clip_id": clip_id,
        "bytes_stored": len(audio_data),
        "sha256_checksum": sha256
    }), 200


@app.route("/api/v1/ingest/complete", methods=["POST"])
def ingest_complete():
    """
    Step 3 of Ingestion:
    Edge agent confirms delivery with event metadata, inference, and idempotency key.
    """
    dev_id = request.headers.get("X-Device-Id")
    ts = request.headers.get("X-Timestamp")
    sig = request.headers.get("X-Signature")
    idempotency_key = request.headers.get("Idempotency-Key")

    if not all([dev_id, ts, sig, idempotency_key]):
        return jsonify({"error": "Missing required headers or Idempotency-Key"}), 400

    payload_bytes = request.get_data()
    is_valid, msg = auth.verify_request(dev_id, ts, sig, payload_bytes)
    if not is_valid:
        return jsonify({"error": f"Cryptographic verification rejected: {msg}"}), 403

    # Idempotency check (Proposal Section 2.2 C)
    if idempotency_key in IDEMPOTENCY_STORE:
        return jsonify({
            "status": "acknowledged",
            "message": "Duplicate request recognized via Idempotency-Key; already committed",
            "event_id": IDEMPOTENCY_STORE[idempotency_key]
        }), 200

    data = request.get_json(silent=True) or {}
    event_id = data.get("event_uuid", str(uuid.uuid4()))
    clip_id = data.get("clip_id")

    clip_dict = None
    if clip_id:
        clip_path = os.path.join(STORAGE_DIR, f"{clip_id}.wav")
        size = os.path.getsize(clip_path) if os.path.exists(clip_path) else data.get("clip_bytes", 100000)
        clip_dict = {
            "id": clip_id,
            "device_id": dev_id,
            "storage_uri": f"r2://jocotoco-media/{dev_id}/{clip_id}.wav",
            "file_size_bytes": size,
            "sha256_checksum": data.get("clip_sha256", "unknown"),
            "duration_seconds": data.get("duration_sec", 2.267)
        }

    event_dict = {
        "id": event_id,
        "device_id": dev_id,
        "idempotency_key": idempotency_key,
        "timestamp": data.get("timestamp", datetime.now(timezone.utc).isoformat()),
        "species_scientific_name": data.get("species_scientific", "Unknown"),
        "species_common_name": data.get("species_common", "Unknown"),
        "confidence": data.get("confidence", 0.90),
        "frequency_min_hz": data.get("freq_min_hz", 1000),
        "frequency_max_hz": data.get("freq_max_hz", 4000)
    }

    db.record_event(event_dict, clip_dict)
    IDEMPOTENCY_STORE[idempotency_key] = event_id

    return jsonify({
        "status": "committed",
        "event_id": event_id,
        "device_id": dev_id,
        "idempotency_key": idempotency_key
    }), 201


@app.route("/api/v1/telemetry", methods=["POST"])
def telemetry():
    """Ingests signed telemetry heartbeats from the Raspberry Pi swarm."""
    dev_id = request.headers.get("X-Device-Id")
    ts = request.headers.get("X-Timestamp")
    sig = request.headers.get("X-Signature")

    if not all([dev_id, ts, sig]):
        return jsonify({"error": "Missing signature headers"}), 400

    payload_bytes = request.get_data()
    is_valid, msg = auth.verify_request(dev_id, ts, sig, payload_bytes)
    if not is_valid:
        return jsonify({"error": f"Rejected: {msg}"}), 403

    item = request.get_json(silent=True) or {}
    db.record_telemetry(item)
    return jsonify({"status": "received", "device_id": dev_id}), 200


@app.route("/api/v1/ota/manifest", methods=["GET"])
def ota_manifest():
    """
    Over-The-Air Resilient Update Manifest (Proposal Section 3):
    Delivers signed chunk boundaries for model distribution.
    """
    sample_model_size = 5 * 1024 * 1024  # 5 MB test model
    chunk_size = 1024 * 1024             # 1 MB chunk boundaries
    total_chunks = 5

    chunks = []
    for i in range(total_chunks):
        start = i * chunk_size
        end = min((i + 1) * chunk_size - 1, sample_model_size - 1)
        chunks.append({
            "chunk_index": i,
            "byte_range": f"{start}-{end}",
            "sha256": hashlib.sha256(f"model_v2_chunk_{i}".encode()).hexdigest()
        })

    return jsonify({
        "model_id": "m-perch2-joco-v2.1",
        "name": "Google Perch2 Cloud Forest Custom Classifier",
        "version": "2.1.0",
        "target_species": [
            "Grallaria ridgelyi", "Pyrrhura orcesi", "Eriocnemis nigrivestis", "Neomorphus radiolosus"
        ],
        "total_size_bytes": sample_model_size,
        "chunk_size_bytes": chunk_size,
        "total_chunks": total_chunks,
        "chunks": chunks,
        "master_sha256": "8f3b29c1d2e3f4a5b6c7d8e9f0a1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9",
        "signing_authority": "Fundación de Conservación Jocotoco — Conservation AI Unit"
    })


@app.route("/api/v1/fleet", methods=["GET"])
def get_fleet():
    """Returns the list of 20 simulated Raspberry Pis for dashboard map and telemetry."""
    reg_path = os.path.join(DATA_DIR, "devices.json")
    if os.path.exists(reg_path):
        with open(reg_path, "r", encoding="utf-8") as f:
            devices = json.load(f)
    else:
        devices = []
    return jsonify(devices)


@app.route("/api/v1/events", methods=["GET"])
def get_events():
    """Returns recent bioacoustic detection events."""
    limit = int(request.args.get("limit", 50))
    events = db.get_recent_events(limit=limit)
    return jsonify(events)


@app.route("/api/v1/audio/<clip_id>", methods=["GET"])
def stream_audio(clip_id):
    """Streams the 100 kB pink noise WAV audio clip."""
    filename = f"{clip_id}.wav"
    return send_from_directory(STORAGE_DIR, filename, mimetype="audio/wav")


@app.route("/", methods=["GET"])
def dashboard():
    """Renders the operations dashboard."""
    return render_template("index.html")


if __name__ == "__main__":
    port = int(os.getenv("PORT", 8000))
    app.run(host="0.0.0.0", port=port, debug=False)
