"""
Swarm Orchestrator for 20 Simulated Raspberry Pi 5 Monitors
Coordinates data generation, Ed25519 key registry, and multi-node telemetry.
"""

import os
import json
from typing import List, Dict, Any

from simulator.device import SimulatedRaspberryPi


SWARM_CONFIG = [
    # Buenaventura Reserve (El Oro)
    {"id": "joco-rpi5-01", "reserve": "buenaventura", "name": "Monitor Buenaventura Quebrada", "lat": -3.6492, "lon": -79.7611, "elev": 880},
    {"id": "joco-rpi5-02", "reserve": "buenaventura", "name": "Monitor Buenaventura Cumbre", "lat": -3.6441, "lon": -79.7580, "elev": 1020},
    {"id": "joco-rpi5-03", "reserve": "buenaventura", "name": "Monitor Buenaventura Lek", "lat": -3.6515, "lon": -79.7645, "elev": 910},
    {"id": "joco-rpi5-04", "reserve": "buenaventura", "name": "Monitor Buenaventura Nido 1", "lat": -3.6478, "lon": -79.7562, "elev": 940},
    {"id": "joco-rpi5-05", "reserve": "buenaventura", "name": "Monitor Buenaventura Sendero", "lat": -3.6530, "lon": -79.7680, "elev": 850},
    
    # Tapichalaca Reserve (Zamora-Chinchipe)
    {"id": "joco-rpi5-06", "reserve": "tapichalaca", "name": "Monitor Tapichalaca Jocotoco A", "lat": -4.4921, "lon": -79.1312, "elev": 2450},
    {"id": "joco-rpi5-07", "reserve": "tapichalaca", "name": "Monitor Tapichalaca Jocotoco B", "lat": -4.4950, "lon": -79.1290, "elev": 2520},
    {"id": "joco-rpi5-08", "reserve": "tapichalaca", "name": "Monitor Tapichalaca Mirador", "lat": -4.4890, "lon": -79.1350, "elev": 2600},
    {"id": "joco-rpi5-09", "reserve": "tapichalaca", "name": "Monitor Tapichalaca Quebrada Honda", "lat": -4.4980, "lon": -79.1275, "elev": 2380},
    
    # Yanacocha Reserve (Pichincha)
    {"id": "joco-rpi5-10", "reserve": "yanacocha", "name": "Monitor Yanacocha Zamarrito Alto", "lat": -0.1182, "lon": -78.5834, "elev": 3450},
    {"id": "joco-rpi5-11", "reserve": "yanacocha", "name": "Monitor Yanacocha Bebederos", "lat": -0.1195, "lon": -78.5810, "elev": 3400},
    {"id": "joco-rpi5-12", "reserve": "yanacocha", "name": "Monitor Yanacocha Bosque Polylepis", "lat": -0.1160, "lon": -78.5860, "elev": 3520},
    {"id": "joco-rpi5-13", "reserve": "yanacocha", "name": "Monitor Yanacocha Quebrada Inca", "lat": -0.1220, "lon": -78.5790, "elev": 3320},
    
    # Canandé Reserve (Esmeraldas)
    {"id": "joco-rpi5-14", "reserve": "canande", "name": "Monitor Canandé Dosel Chocó", "lat": 0.5281, "lon": -79.2152, "elev": 320},
    {"id": "joco-rpi5-15", "reserve": "canande", "name": "Monitor Canandé Río Guaycán", "lat": 0.5310, "lon": -79.2110, "elev": 280},
    {"id": "joco-rpi5-16", "reserve": "canande", "name": "Monitor Canandé Límite Protector", "lat": 0.5250, "lon": -79.2190, "elev": 350},
    
    # Narupa Reserve (Napo)
    {"id": "joco-rpi5-17", "reserve": "narupa", "name": "Monitor Narupa Río Hollín", "lat": -0.7254, "lon": -77.7492, "elev": 1100},
    {"id": "joco-rpi5-18", "reserve": "narupa", "name": "Monitor Narupa Sendero Puma", "lat": -0.7290, "lon": -77.7460, "elev": 1150},
    
    # Antisanilla Reserve (Pichincha/Napo)
    {"id": "joco-rpi5-19", "reserve": "antisanilla", "name": "Monitor Antisanilla Peñón Cóndor", "lat": -0.4612, "lon": -78.3391, "elev": 3850},
    {"id": "joco-rpi5-20", "reserve": "antisanilla", "name": "Monitor Antisanilla Valle Páramo", "lat": -0.4650, "lon": -78.3340, "elev": 3790}
]


class SwarmManager:
    def __init__(self, data_dir: str = "data", target_audio_bytes: int = 100000):
        self.data_dir = data_dir
        self.target_audio_bytes = target_audio_bytes
        self.devices: List[SimulatedRaspberryPi] = []
        self._init_swarm()

    def _init_swarm(self):
        """Initializes all 20 simulated Raspberry Pis."""
        for cfg in SWARM_CONFIG:
            dev = SimulatedRaspberryPi(
                device_id=cfg["id"],
                reserve_slug=cfg["reserve"],
                name=cfg["name"],
                lat=cfg["lat"],
                lon=cfg["lon"],
                elevation=cfg["elev"],
                data_dir=self.data_dir,
                target_audio_bytes=self.target_audio_bytes
            )
            self.devices.append(dev)
        self.export_registry()

    def export_registry(self) -> str:
        """Exports device metadata and Ed25519 public keys to data/devices.json."""
        registry = []
        for dev in self.devices:
            registry.append({
                "id": dev.device_id,
                "name": dev.name,
                "reserve": dev.reserve_slug,
                "latitude": dev.lat,
                "longitude": dev.lon,
                "elevation_m": dev.elevation,
                "public_key_hex": dev.public_key_hex,
                "battery_pct": dev.battery_pct,
                "status": "ACTIVE"
            })
        out_path = os.path.join(self.data_dir, "devices.json")
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(registry, f, indent=2)
        return out_path

    def generate_swarm_detections(self, clips_per_device: int = 1) -> List[Dict[str, Any]]:
        """
        Triggers bioacoustic detection events across the entire 20-Pi swarm.
        Each event produces an exact 100 kB pink noise WAV audio clip.
        """
        all_events = []
        for dev in self.devices:
            for _ in range(clips_per_device):
                evt = dev.trigger_detection()
                all_events.append(evt)
        return all_events

    def generate_swarm_telemetry(self) -> List[Dict[str, Any]]:
        """Collects telemetry vitals across all 20 Pis."""
        return [dev.record_telemetry() for dev in self.devices]
