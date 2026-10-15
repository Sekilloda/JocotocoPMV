"""
Edge Sync Client
Simulates the Raspberry Pi 5 background daemon synchronizing queued events
and audio clips to the Central Ingestion API over HTTPS.
"""

import os
import sys
import json
import time
import requests
from typing import Optional

# Ensure repository root is on Python module search path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from simulator.swarm import SwarmManager


def sync_device(dev, api_url: str):
    """Synchronizes uncommitted events from a single Raspberry Pi to the API."""
    queued = dev.get_queued_events(limit=10)
    if not queued:
        return 0

    synced_count = 0
    for evt in queued:
        # Step 1: Authorize ingestion
        auth_payload = {
            "device_id": dev.device_id,
            "clip_bytes": evt["clip_bytes"],
            "clip_sha256": evt["clip_sha256"],
            "timestamp": evt["timestamp"]
        }
        headers, auth_body_bytes = dev.get_auth_headers(auth_payload)
        
        try:
            res = requests.post(f"{api_url}/api/v1/ingest/authorize", data=auth_body_bytes, headers=headers, timeout=5)
            if res.status_code != 200:
                print(f"[!] Autorización fallida para {dev.device_id}: {res.status_code} {res.text}")
                continue
            auth_data = res.json()
            clip_id = auth_data["clip_id"]
            upload_url = auth_data["upload_url"]

            # Step 2: Upload 100 kB audio clip
            with open(evt["clip_path"], "rb") as f:
                clip_bytes = f.read()
                
            storage_target = f"{api_url}{upload_url}" if upload_url.startswith("/") else upload_url
            upload_res = requests.put(storage_target, data=clip_bytes, headers={"Content-Type": "audio/wav"}, timeout=10)
            if upload_res.status_code != 200:
                print(f"[!] Carga del clip fallida para {dev.device_id}: {upload_res.status_code}")
                continue

            # Step 3: Complete ingestion
            complete_payload = {
                "event_uuid": evt["event_uuid"],
                "clip_id": clip_id,
                "species_scientific": evt["species_scientific"],
                "species_common": evt["species_common"],
                "confidence": evt["confidence"],
                "freq_min_hz": evt["freq_min_hz"],
                "freq_max_hz": evt["freq_max_hz"],
                "timestamp": evt["timestamp"],
                "clip_bytes": evt["clip_bytes"],
                "clip_sha256": evt["clip_sha256"],
                "duration_sec": evt["duration_sec"]
            }
            comp_headers, comp_body_bytes = dev.get_auth_headers(complete_payload)
            comp_headers["Idempotency-Key"] = evt["idempotency_key"]

            comp_res = requests.post(f"{api_url}/api/v1/ingest/complete", data=comp_body_bytes, headers=comp_headers, timeout=5)
            if comp_res.status_code in (200, 201):
                dev.mark_event_synced(evt["event_uuid"])
                synced_count += 1
            else:
                print(f"[!] Confirmación de ingesta fallida: {comp_res.status_code} {comp_res.text}")

        except Exception as e:
            print(f"[!] Error de red al sincronizar {dev.device_id}: {e}")

    # Send periodic telemetry
    telem = dev.record_telemetry()
    telem_headers, telem_body_bytes = dev.get_auth_headers(telem)
    try:
        requests.post(f"{api_url}/api/v1/telemetry", data=telem_body_bytes, headers=telem_headers, timeout=3)
    except Exception:
        pass

    return synced_count


def sync_all_swarm(api_url: str = "http://127.0.0.1:8000"):
    print(f"[*] Iniciando sincronización del enjambre hacia {api_url}...")
    swarm = SwarmManager(data_dir="data")
    total_synced = 0
    for dev in swarm.devices:
        count = sync_device(dev, api_url)
        if count > 0:
            print(f"[+] Dispositivo {dev.device_id} ({dev.reserve_slug}) sincronizó {count} detección(es).")
            total_synced += count
    print(f"[✓] Sincronización del enjambre completada. Total de clips subidos: {total_synced}")


if __name__ == "__main__":
    url = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8000"
    sync_all_swarm(url)
