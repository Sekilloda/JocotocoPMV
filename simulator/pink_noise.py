"""
Pink Noise Audio Generator for Bioacoustic Simulation
Produces authentic 1/f spectral pink noise WAV audio files of precise byte size.
"""

import os
import wave
import struct
import random
import hashlib
from typing import Tuple


def generate_pink_noise_wav(
    filepath: str,
    target_bytes: int = 100000,
    sample_rate: int = 22050
) -> Tuple[str, int, float, str]:
    """
    Generates a standard 16-bit mono PCM WAV file containing genuine pink noise
    matching the exact target byte size specified (default: 100,000 bytes ~ 100 kB).

    Uses Paul Kellet's refined 5-pole filter algorithm to filter white noise into pink noise (-3dB/octave).

    Returns:
        (filepath, actual_bytes, duration_seconds, sha256_checksum)
    """
    os.makedirs(os.path.dirname(os.path.abspath(filepath)), exist_ok=True)
    
    header_size = 44  # Standard canonical RIFF/WAVE header
    if target_bytes <= header_size:
        raise ValueError(f"target_bytes must be > {header_size}")
    
    data_size = target_bytes - header_size
    # 16-bit mono = 2 bytes per sample
    num_samples = data_size // 2
    
    # Kellet pink noise filter states
    b0 = b1 = b2 = b3 = b4 = b5 = b6 = 0.0
    samples = []
    
    for _ in range(num_samples):
        white = random.uniform(-1.0, 1.0)
        b0 = 0.99886 * b0 + white * 0.0555179
        b1 = 0.99332 * b1 + white * 0.0750759
        b2 = 0.96900 * b2 + white * 0.1538520
        b3 = 0.86650 * b3 + white * 0.3104856
        b4 = 0.55000 * b4 + white * 0.5329522
        b5 = -0.7616 * b5 - white * 0.0168980
        pink = b0 + b1 + b2 + b3 + b4 + b5 + b6 + white * 0.5362
        b6 = white * 0.115926
        
        # Soft-clip and map to 16-bit signed integer (-32768 to 32767)
        val = max(-1.0, min(1.0, pink * 0.18))
        samples.append(int(val * 32767))
        
    raw_frames = struct.pack(f"<{len(samples)}h", *samples)
    
    with wave.open(filepath, "wb") as wav_file:
        wav_file.setnchannels(1)       # Mono
        wav_file.setsampwidth(2)       # 16-bit
        wav_file.setframerate(sample_rate)
        wav_file.writeframes(raw_frames)
        
    actual_size = os.path.getsize(filepath)
    duration_sec = num_samples / sample_rate
    
    with open(filepath, "rb") as f:
        sha256 = hashlib.sha256(f.read()).hexdigest()
        
    return filepath, actual_size, duration_sec, sha256


if __name__ == "__main__":
    import sys
    out = sys.argv[1] if len(sys.argv) > 1 else "sample_pink_100k.wav"
    path, size, dur, sha = generate_pink_noise_wav(out)
    print(f"Generated Pink Noise WAV: {path}")
    print(f"  Size: {size} bytes ({size / 1000:.2f} kB)")
    print(f"  Duration: {dur:.3f} s")
    print(f"  SHA-256: {sha}")
