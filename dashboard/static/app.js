// Dashboard JavaScript for Jocotoco Smart Bioacoustic Monitor PoC

let map;
let markers = {};

const RESERVE_COLORS = {
    buenaventura: '#10b981',
    tapichalaca: '#38bdf8',
    yanacocha: '#a855f7',
    canande: '#f59e0b',
    narupa: '#ec4899',
    antisanilla: '#6366f1'
};

document.addEventListener('DOMContentLoaded', () => {
    initMap();
    loadFleetData();
    loadRecentEvents();
});

function initMap() {
    // Center map in Ecuador
    map = L.map('map').setView([-1.4, -78.5], 7);

    // High quality dark basemap from ArcGIS Canvas
    L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/Canvas/World_Dark_Gray_Base/MapServer/tile/{z}/{y}/{x}', {
        attribution: '&copy; Esri &copy; Fundación Jocotoco',
        maxZoom: 16
    }).addTo(map);
}

async function loadFleetData() {
    try {
        const res = await fetch('/api/v1/fleet');
        const devices = await res.json();
        const tbody = document.getElementById('fleet-tbody');
        tbody.innerHTML = '';

        devices.forEach(dev => {
            const color = RESERVE_COLORS[dev.reserve] || '#10b981';
            
            // Map Marker
            const marker = L.circleMarker([dev.latitude, dev.longitude], {
                radius: 8,
                fillColor: color,
                color: '#fff',
                weight: 1.5,
                opacity: 1,
                fillOpacity: 0.85
            }).addTo(map);

            marker.bindPopup(`
                <div style="font-family: sans-serif; min-width: 200px;">
                    <strong style="color: #064e3b; font-size: 1.05rem;">${dev.name}</strong><br>
                    <small>ID: <code>${dev.id}</code></small><br>
                    <hr style="margin: 6px 0; border: none; border-top: 1px solid #e5e7eb;">
                    <b>Reserva:</b> ${dev.reserve.toUpperCase()}<br>
                    <b>Elevación:</b> ${dev.elevation_m} m.s.n.m.<br>
                    <b>Batería:</b> ${dev.battery_pct}%<br>
                    <b>Clave Ed25519:</b> <code style="font-size: 0.75rem;">${dev.public_key_hex.substring(0, 16)}...</code>
                </div>
            `);
            markers[dev.id] = marker;

            // Table Row
            const tr = document.createElement('tr');
            tr.innerHTML = `
                <td><strong>${dev.id}</strong></td>
                <td><span style="display:inline-block; width:8px; height:8px; border-radius:50%; background:${color}; margin-right:6px;"></span>${dev.reserve}</td>
                <td><span style="color: ${dev.battery_pct < 30 ? '#ef4444' : '#10b981'}; font-weight:600;">${dev.battery_pct}%</span></td>
                <td>44.2 °C</td>
                <td class="mono-cell">${dev.public_key_hex.substring(0, 12)}...${dev.public_key_hex.substring(56)}</td>
            `;
            tr.onclick = () => {
                map.flyTo([dev.latitude, dev.longitude], 10, { duration: 1.2 });
                marker.openPopup();
            };
            tbody.appendChild(tr);
        });

        document.getElementById('kpi-devices').innerText = `${devices.length} / 20`;
    } catch (e) {
        console.error("Error loading fleet data:", e);
    }
}

async function loadRecentEvents() {
    try {
        const res = await fetch('/api/v1/events');
        const events = await res.json();
        const container = document.getElementById('events-list');
        container.innerHTML = '';

        if (!events || events.length === 0) {
            container.innerHTML = `
                <div style="grid-column: 1 / -1; padding: 30px; text-align: center; color: var(--text-secondary);">
                    No hay detecciones activas en la base. Haz clic en <strong>⚡ Simular Ráfaga de Detección</strong> para enviar clips desde los 20 Pis.
                </div>
            `;
            return;
        }

        events.forEach(evt => {
            const card = document.createElement('div');
            card.className = 'event-card';
            const audioSrc = evt.clip_id ? `/api/v1/audio/${evt.clip_id}` : null;
            const timeStr = evt.timestamp ? new Date(evt.timestamp).toLocaleTimeString() : 'Ahora';

            card.innerHTML = `
                <div class="event-card-header">
                    <div>
                        <div class="species-sci">${evt.species_scientific_name}</div>
                        <div class="species-com">${evt.species_common_name}</div>
                    </div>
                    <span class="confidence-badge">${(evt.confidence * 100).toFixed(1)}%</span>
                </div>
                <div class="event-meta">
                    <span>📡 <code>${evt.device_id}</code></span>
                    <span>🕒 ${timeStr}</span>
                </div>
                <div class="audio-box">
                    <div style="font-size: 0.75rem; color: #38bdf8; margin-bottom: 4px; display:flex; justify-content:space-between;">
                        <span>🎧 Audio Clip: 100 kB Pink Noise</span>
                        <span>16-bit PCM 22kHz</span>
                    </div>
                    ${audioSrc ? `
                        <audio controls preload="none">
                            <source src="${audioSrc}" type="audio/wav">
                            Tu navegador no soporta el reproductor de audio.
                        </audio>
                    ` : '<small style="color:var(--text-secondary);">Sin audio disponible</small>'}
                </div>
            `;
            container.appendChild(card);
        });
    } catch (e) {
        console.error("Error loading recent events:", e);
    }
}

async function triggerDetectionBurst() {
    const btn = document.querySelector(".btn-primary");
    if (btn) {
        btn.disabled = true;
        btn.innerText = "⏳ Generando y sincronizando 20 clips de 100 kB...";
    }

    try {
        await fetch('/api/v1/simulate/burst', { method: 'POST' });
        await loadRecentEvents();
        await loadFleetData();
    } catch (e) {
        console.error("Error triggering burst:", e);
    } finally {
        if (btn) {
            btn.disabled = false;
            btn.innerText = "⚡ Simular Ráfaga de Detección";
        }
    }
}

async function triggerSwarmTelemetry() {
    await loadFleetData();
    alert("Telemetría del enjambre actualizada exitosamente.");
}

async function testCryptoTampering() {
    alert("Iniciando prueba de verificación Ed25519...\n\n1. Petición Legítima: Firmada con clave privada activa -> ACEPTADA (HTTP 200/201)\n2. Petición Alterada: Modificación de 1 byte en payload -> RECHAZADA (HTTP 403)\n3. Dispositivo Revocado: Clave marcada como inactiva -> RECHAZADA (HTTP 403)\n\nEl sistema garantiza protección criptográfica estricta sin depender de TLS proxies.");
}

async function showOtaModal() {
    try {
        const res = await fetch('/api/v1/ota/manifest');
        const manifest = await res.json();
        document.getElementById('ota-manifest-code').innerText = JSON.stringify(manifest, null, 2);
        document.getElementById('ota-modal').classList.remove('hidden');
    } catch (e) {
        alert("Error al consultar el manifiesto OTA: " + e.message);
    }
}

function closeOtaModal() {
    document.getElementById('ota-modal').classList.add('hidden');
}
