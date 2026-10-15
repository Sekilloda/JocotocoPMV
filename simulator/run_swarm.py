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
    parser = argparse.ArgumentParser(description="Simular 20 Monitores Inteligentes Raspberry Pi 5 en las Reservas de Jocotoco")
    parser.add_argument("--clips", type=int, default=1, help="Número de clips de audio de 100 kB a generar por dispositivo (por defecto: 1)")
    parser.add_argument("--bytes", type=int, default=100000, help="Tamaño exacto en bytes para el audio de ruido rosa (por defecto: 100000)")
    parser.add_argument("--data-dir", type=str, default="data", help="Directorio para almacenar los clips y buffers locales")
    args = parser.parse_args()

    print("=" * 70)
    print("   FUNDACIÓN JOCOTOCO — SIMULADOR DE ENJAMBRE DE MONITORES BIOACÚSTICOS")
    print("=" * 70)
    print(f"[*] Inicializando enjambre de 20 monitores edge Raspberry Pi 5...")
    print(f"[*] Objetivo de tamaño de audio: {args.bytes} bytes ({args.bytes / 1000:.1f} kB) por clip [Ruido Rosa]")
    print(f"[*] Directorio de salida: {args.data_dir}")
    
    swarm = SwarmManager(data_dir=args.data_dir, target_audio_bytes=args.bytes)
    print(f"[+] Cargados {len(swarm.devices)} nodos edge en 6 reservas de Jocotoco.")
    print(f"[+] Registro de claves públicas Ed25519 exportado a: {os.path.join(args.data_dir, 'devices.json')}")
    
    print(f"\n[*] Disparando eventos de detección bioacústica ({args.clips} por dispositivo = {len(swarm.devices) * args.clips} clips en total)...")
    events = swarm.generate_swarm_detections(clips_per_device=args.clips)
    
    print("\n" + "-" * 70)
    print(f"{'DISPOSITIVO':<18} {'RESERVA':<15} {'ESPECIE DETECTADA':<25} {'TAMAÑO':<8}")
    print("-" * 70)
    for evt in events[:10]:
        dev = next(d for d in swarm.devices if d.device_id == evt['device_id'])
        print(f"{evt['device_id']:<18} {dev.reserve_slug:<15} {evt['species_scientific'][:24]:<25} {evt['clip_bytes']}B")
    if len(events) > 10:
        print(f"... y {len(events) - 10} clips de detección adicionales.")
    print("-" * 70)

    print("\n[*] Recolectando telemetría y signos vitales de hardware...")
    telemetry = swarm.generate_swarm_telemetry()
    avg_bat = sum(t['battery_pct'] for t in telemetry) / len(telemetry)
    avg_temp = sum(t['cpu_temp_c'] for t in telemetry) / len(telemetry)
    total_bytes = sum(e['clip_bytes'] for e in events)

    print(f"\n[✓] SIMULACIÓN DEL ENJAMBRE COMPLETADA EXITOSAMENTE:")
    print(f"    - Nodos activos Raspberry Pi 5:   {len(swarm.devices)}")
    print(f"    - Clips de ruido rosa generados:  {len(events)} archivos")
    print(f"    - Total de datos de audio:        {total_bytes:,} bytes ({total_bytes / (1024 * 1024):.2f} MB)")
    print(f"    - Promedio de batería de flota:   {avg_bat:.1f}%")
    print(f"    - Promedio de temperatura CPU:    {avg_temp:.1f} °C")
    print(f"    - Buffers SQLite locales:         {len(swarm.devices)} archivos en {os.path.join(args.data_dir, 'sqlite_buffers')}")
    print("=" * 70)


if __name__ == "__main__":
    main()
