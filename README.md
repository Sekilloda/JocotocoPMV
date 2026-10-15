# Monitor Inteligente de Bioacústica — Prueba de Concepto (PoC)

> **Referencia:** Términos de Referencia (TdR) — Plataforma Integral para el Monitor Inteligente de Bioacústica  
> **Organización Destinataria:** Fundación de Conservación Jocotoco 

---

## 1. Resumen
Esta Prueba de Concepto (PoC) implementa una maqueta con los pilares técnicos fundamentales requeridos para la plataforma institucional encargada de operar la red distribuida de monitores inteligentes de bioacústica. Estas son sus características:

1. **Enjambre simulado de 20 equipos de monitoreo:**
   - 20 nodos de hardware independientes distribuidos geográficamente en 6 reservas ecológicas clave de Ecuador (*Buenaventura, Tapichalaca, Yanacocha, Canandé, Narupa y Antisanilla*).
   - Generación de archivos de audio de 100 kB en formato PCM de 16 bits con pendiente espectral $1/f$ (comúnmente conocido como ruido rosa), que representan los archivos de audio asociados a eventos de detección.
   - Buffer transaccional local en cada monitor, que aporta resiliencia a cortes de energía y ventanas prolongadas sin conectividad celular, sin pérdida de datos.

2. **Identidad criptográfica asimétrica:**
   - Parche que evita la limitación de terminación mTLS en balanceadores y proxies inversos comerciales mediante firmas digitales aplicadas directamente en la capa de aplicación sobre HTTPS estándar.
   - Cabeceras de autenticación: `X-Device-Id`, `X-Timestamp` y `X-Signature` calculada sobre llave + llave SHA-256, con ventana estricta anti-repetición de 120 segundos.

3. **Capa de datos:**
   - Esquemas SQL versionados con políticas de Row-Level Security gobernadas por la variable de sesión `app.current_tenant_id`.
   - Interfaz nativa y directa con Supabase PostgreSQL y extensiones espaciales PostGIS, con fallback automático a SQLite local para pruebas sin conexión.

4. **Gestión de actualizaciones:**
   - Servidor de manifiestos estructurados para distribución de modelos por bloques de 1 MB con persistencia de progreso y validación criptográfica SHA-256 por bloque y acumulada.

5. **Despliegue Contenerizado Listo para Railway:**
   - Orquestación mediante `Dockerfile` multi-etapa, `railway.json` y `Procfile`.
   - Panel de control operativo integrado con mapa satelital Leaflet, reproducción de audio bioacústico y telemetría de flota en tiempo real.

---

## 2. Sistemas reales que simula la prueba de concepto

El PoC modela los componentes físicos y operacionales de la red:

* **Telemetría:**
  - Voltaje y nivel de batería (10% a 100%), temperatura del procesador (°C), espacio ocupado en la tarjeta SD (%) y potencia de señal celular (RSSI en dBm).
* **Audio Bioacústico Canónico de 100 kB:**
  - Síntesis de ruido rosa con densidad espectral $1/f$ ($3\text{ dB/octava}$ de atenuación), simulando eventos de detección.
* **Condiciones adversas:**
  - Cortes de red forzados durante la sincronización, rechazo de cargas con firmas adulteradas y bloqueo de ataques de repetición con marcas temporales expiradas.

---

## 5. Diferencias con el piloto operativo

Para evolucionar este demostrador funcional hacia el piloto operativo desplegado:

1. Hace falta reescribir el agente de control en Rust y empaquetarlo en un daemon como servicio del sistema bajo `systemd` con reinicio automático.
2. Es necesario integrar el sistema con hardware real.
3. Diseño de la arquitectura de almacenamiento de datos en Cloudflare R2. Esto implica la configuración de buckets y emisión de URLs prefirmadas reales con expiración temporal.
4. Esta prueba de concepto no incluye el dashboard. Para crearlo, es necesario diseñar la interfaz con control de acceso por roles, descarga y reproducción de archivos.
5. Configuración del respaldo en NAS. Establecimiento de tareas programadas con `rclone` y respaldos cifrados de PostgreSQL hacia el almacenamiento físico de la institución.

El backend simulado en este demostrador fue diseñado enteramente en Python.

---

## 6. Estructura del Repositorio

```
smart-monitor-poc/
├── README.md                      # Manual de arquitectura y operaciones (este documento)
├── railway.json                   # Configuración para despliegue de contenedores en Railway
├── Dockerfile                     # Imagen de producción multi-etapa
├── Procfile                       # Definición de procesos para PaaS
├── requirements.txt               # Dependencias ligeras de ejecución
├── .env.example                   # Plantilla de variables de entorno
├── api/
│   ├── server.py                  # Servidor de ingesta, almacenamiento y OTA
│   └── auth.py                    # Middleware de verificación criptográfica Ed25519
├── simulator/
│   ├── pink_noise.py              # Generador de ruido rosa WAV de 100 kB en Python
│   ├── device.py                  # Simulador de daemon edge de Raspberry Pi 5
│   ├── swarm.py                   # Gestor del enjambre
│   ├── run_swarm.py               # Herramienta CLI para simular ráfagas de detecciones
│   └── sync_client.py             # Cliente de sincronización reanudable edge-to-cloud
├── database/
│   ├── client.py                  # Cliente de base de datos
│   └── migrations/
│       ├── 001_initial_schema.sql # DDL relacional con PostGIS y RLS portable
│       └── 002_seed_swarm.sql     # Semillado de 6 reservas y 20 dispositivos con GPS
├── scripts/
│   ├── setup_supabase.py          # Script de migración y validación de RLS en Supabase
│   └── test_acceptance.py         # Suite automatizada de pruebas de aceptación de los TdR
└── data/
    ├── devices.json               # Metadatos de 20 Pis y claves públicas Ed25519
    ├── audio_clips/               # Archivos de audio generados de 100 kB
    └── sqlite_buffers/            # Colas locales SQLite individuales por dispositivo
```

---

## 7. Guía de Inicio Rápido (Ejecución Local)

### Paso 1: Instalación de Dependencias
```bash
pip install -r requirements.txt
```

### Paso 2: Generar Clips de Ruido Rosa de 100 kB para el Enjambre
```bash
python3 -m simulator.run_swarm --clips 1 --bytes 100000
```
*Genera 20 clips de audio WAV de exactamente 100,000 bytes (2.0 MB en total) y 20 colas SQLite locales con sus claves criptográficas.*

### Paso 3: Ejecutar la Suite Automatizada de Pruebas de Aceptación
```bash
python3 scripts/test_acceptance.py
```
*Valida tamaño exacto de audio, verificación Ed25519, rechazo de alteraciones, defensa anti-repetición, transiciones en SQLite, idempotencia y manifiesto OTA (5/5 pruebas superadas).*

### Paso 4: Iniciar la API de Ingesta y Control
```bash
python3 -m api.server
```
Consulte **`http://localhost:8000`** o **`http://localhost:8000/healthz`** para verificar el estado de los servicios y los endpoints disponibles de la API.


### Paso 5: Simular la Sincronización del Enjambre
En una terminal paralela:
```bash
python3 simulator/sync_client.py http://127.0.0.1:8000
```
*Transmite las detecciones encoladas hacia el servidor, validando firmas Ed25519 y registrando los eventos de forma concurrente.*

---

## 8. Conexión con Supabase

Para enlazar este PoC directamente con una instancia de Supabase PostgreSQL:

### Método A: Configuración Automatizada por CLI
1. En el panel de Supabase, ingrese a **Project Settings** $\longrightarrow$ **Database** $\longrightarrow$ **Connection String (URI)**.
2. Ejecute el script de inicialización:
```bash
python3 scripts/setup_supabase.py --db-url "postgresql://postgres:[PASSWORD]@db.[PROJECT_REF].supabase.co:5432/postgres"
```
El script realiza automáticamente:
- Activación de la extensión espacial `postgis`.
- Creación de tablas relacionales y políticas portables de *Row-Level Security* (RLS).
- Inserción de las 6 reservas y los 20 monitores con coordenadas geográficas reales.
- Registro de las claves públicas Ed25519 generadas.
- Validación de aislamiento multi-inquilino mediante consultas de prueba.

### Método B: Editor SQL de Supabase (Copia y Pega)
1. Abra `database/migrations/001_initial_schema.sql` y ejecútelo en el **SQL Editor** de Supabase.
2. Abra `database/migrations/002_seed_swarm.sql` y ejecútelo en el **SQL Editor** de Supabase.

---

## 9. Despliegue en Railway

Para desplegar este demostrador en Railway sin administración de servidores:

1. Inicie sesión en [Railway.app](https://railway.app).
2. Seleccione **New Project** $\longrightarrow$ **Deploy from GitHub repo** (o utilice la CLI de Railway).
3. En las variables de entorno del proyecto (*Variables*), configure:
   - `DATABASE_URL`: Cadena de conexión de Supabase (utilizar URI del Session Pooler en el puerto `5432` o Transaction Pooler en el puerto `6543`).
   - `PORT`: `8000` (inyectado automáticamente por Railway).
4. Railway detectará automáticamente el archivo `railway.json` y el `Dockerfile`, construirá la imagen, generará el enjambre y expondrá el servicio bajo HTTPS público con chequeo de salud en `/healthz`.

---

## 10. Mapeo de Pruebas de Aceptación de los Términos de Referencia

| # | Requisito de los TdR | Implementación y Validación en la Prueba de Concepto |
| :---: | :--- | :--- |
| **1** | **Interrupción y Reanudación de Ingesta** | Los monitores edge almacenan eventos en SQLite local (`events_buffer`). Si la conexión se interrumpe, los clips permanecen en cola y se reanudan sin pérdida de datos ni registros duplicados (`simulator/device.py`, `scripts/test_acceptance.py`). |
| **2** | **Aislamiento Multi-Inquilino (RLS)** | Políticas relacionales gobernadas por `app.current_tenant_id` en el motor de base de datos, garantizando aislamiento estricto verificado en `scripts/setup_supabase.py`. |
| **3** | **Actualización OTA Reanudable de Modelos** | Manifiesto estructurado con partición por bloques de 1 MB y hashes SHA-256 (`/api/v1/ota/manifest`), validado en la prueba de aceptación 5. |
| **4** | **Autenticación Criptográfica de Hardware** | Firmas asimétricas Ed25519 sobre $\text{SHA-256}(\text{payload}) + \text{timestamp}$, con rechazo de alteraciones y defensa contra repetición (`api/auth.py`). |
| **5** | **Estándar de Audio Bioacústico de 100 kB** | Clips WAV sintetizados con pendiente $1/f$ (ruido rosa) de exactamente 100,000 bytes y cabecera RIFF canónica de 44 bytes (`simulator/pink_noise.py`). |
