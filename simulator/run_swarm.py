"""
CLI entry point for the 20-Pi Swarm Simulation
Usage:
    python3 -m simulator.run_swarm [--clips 1] [--target-bytes 100000]
"""

import argparse
import sys
import os

from simulator.swarm import SwarmManager


def main():
    parser = argparse.ArgumentParser(description="Simulate 20 Raspberry Pi 5 Smart Monitors in Jocotoco Reserves")
    parser.add_argument("--clips", type=int, default=1, help="Number of 100kB audio clips to generate per device (default: 1)")
    parser.add_argument("--bytes", type=int, default=100000, help="Exact byte size for pink noise audio (default: 100000)")
    parser.add_argument("--data-dir", type=str, default="data", help="Directory to store clips and buffers")
    args = parser.parse_args()

    print("=" * 70)
    print("   FUNDACIÓN JOCOTOCO — SMART BIOACOUSTIC MONITOR SWARM SIMULATOR")
    print("=" * 70)
    print(f"[*] Initializing swarm of 20 Raspberry Pi 5 edge monitors...")
    print(f"[*] Audio payload target: {args.bytes} bytes ({args.bytes / 1000:.1f} kB) per clip [Pink Noise]")
    print(f"[*] Output directory: {args.data_dir}")
    
    swarm = SwarmManager(data_dir=args.data_dir, target_audio_bytes=args.bytes)
    print(f"[+] Loaded {len(swarm.devices)} edge nodes across 6 Jocotoco reserves.")
    print(f"[+] Ed25519 device key registry exported to: {os.path.join(args.data_dir, 'devices.json')}")
    
    print(f"\n[*] Triggering bioacoustic detection events ({args.clips} per device = {len(swarm.devices) * args.clips} total clips)...")
    events = swarm.generate_swarm_detections(clips_per_device=args.clips)
    
    print("\n" + "-" * 70)
    print(f"{'DEVICE ID':<18} {'RESERVE':<15} {'SPECIES DETECTED':<25} {'SIZE':<8}")
    print("-" * 70)
    for evt in events[:10]:
        dev = next(d for d in swarm.devices if d.device_id == evt['device_id'])
        print(f"{evt['device_id']:<18} {dev.reserve_slug:<15} {evt['species_scientific'][:24]:<25} {evt['clip_bytes']}B")
    if len(events) > 10:
        print(f"... and {len(events) - 10} more detection clips.")
    print("-" * 70)

    print("\n[*] Collecting hardware vitals and telemetry...")
    telemetry = swarm.generate_swarm_telemetry()
    avg_bat = sum(t['battery_pct'] for t in telemetry) / len(telemetry)
    avg_temp = sum(t['cpu_temp_c'] for t in telemetry) / len(telemetry)
    total_bytes = sum(e['clip_bytes'] for e in events)

    print(f"\n[✓] SWARM SIMULATION COMPLETED SUCCESSFULLY:")
    print(f"    - Active Raspberry Pi 5 nodes: {len(swarm.devices)}")
    print(f"    - Generated Pink Noise Clips:  {len(events)} files")
    print(f"    - Total Audio Data Generated:  {total_bytes:,} bytes ({total_bytes / (1024 * 1024):.2f} MB)")
    print(f"    - Fleet Avg Battery:          {avg_bat:.1f}%")
    print(f"    - Fleet Avg CPU Temp:         {avg_temp:.1f} °C")
    print(f"    - Local SQLite Buffers:        {len(swarm.devices)} files in {os.path.join(args.data_dir, 'sqlite_buffers')}")
    print("=" * 70)


if __name__ == "__main__":
    main()
