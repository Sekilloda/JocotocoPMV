"""
Ed25519 Device Authentication Middleware
Enforces the per-request cryptographic signature scheme defined in Proposal Section 2.2 B:
- Validates X-Device-Id, X-Timestamp, X-Signature
- Prevents replay attacks via maximum 120-second validity window
- Validates Ed25519 digital signature over SHA-256(payload) + timestamp
"""

import os
import json
import hashlib
from datetime import datetime, timezone
from typing import Dict, Optional, Tuple

from cryptography.hazmat.primitives.asymmetric import ed25519
from cryptography.exceptions import InvalidSignature


class DeviceAuthenticator:
    def __init__(self, devices_registry_path: str = "data/devices.json"):
        self.devices_registry_path = devices_registry_path
        self.public_keys: Dict[str, ed25519.Ed25519PublicKey] = {}
        self.device_statuses: Dict[str, str] = {}
        self.reload_keys()

    def reload_keys(self):
        """Loads registered device public keys from registry file or database."""
        if not os.path.exists(self.devices_registry_path):
            return
        try:
            with open(self.devices_registry_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            for item in data:
                dev_id = item["id"]
                pub_hex = item["public_key_hex"]
                status = item.get("status", "ACTIVE")
                raw_bytes = bytes.fromhex(pub_hex)
                self.public_keys[dev_id] = ed25519.Ed25519PublicKey.from_public_bytes(raw_bytes)
                self.device_statuses[dev_id] = status
        except Exception as e:
            print(f"[!] Error loading device registry: {e}")

    def verify_request(
        self,
        device_id: str,
        timestamp_iso: str,
        signature_hex: str,
        payload_bytes: bytes,
        max_clock_skew_sec: int = 120
    ) -> Tuple[bool, str]:
        """
        Validates request signature against registered public key.
        
        Returns:
            (is_valid: bool, error_message: str)
        """
        # 1. Device existence check
        if device_id not in self.public_keys:
            self.reload_keys()
            if device_id not in self.public_keys:
                return False, f"Unknown device ID: {device_id}"

        # 2. Device revocation check
        if self.device_statuses.get(device_id) == "REVOKED":
            return False, f"Device {device_id} has been revoked by institutional administrator"

        # 3. Timestamp replay prevention window
        try:
            req_time = datetime.fromisoformat(timestamp_iso.replace("Z", "+00:00"))
            now_time = datetime.now(timezone.utc)
            skew = abs((now_time - req_time).total_seconds())
            if skew > max_clock_skew_sec:
                return False, f"Request timestamp expired (skew: {skew:.1f}s > {max_clock_skew_sec}s)"
        except Exception:
            return False, "Invalid ISO-8601 timestamp in X-Timestamp"

        # 4. Signature verification over SHA-256(payload) + timestamp
        try:
            payload_hash = hashlib.sha256(payload_bytes).hexdigest()
            message_to_verify = f"{payload_hash}:{timestamp_iso}".encode("utf-8")
            signature_bytes = bytes.fromhex(signature_hex)
            pub_key = self.public_keys[device_id]
            pub_key.verify(signature_bytes, message_to_verify)
            return True, "Signature valid"
        except InvalidSignature:
            return False, "Invalid Ed25519 signature"
        except Exception as e:
            return False, f"Cryptographic verification error: {str(e)}"
