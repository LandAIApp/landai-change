# Land AI · Change Intelligence (beta)

Detección **exploratoria** de cambios en el territorio con **Sentinel-2** y Google Earth Engine.
El usuario elige **un municipio** o **dibuja su propia área**, escoge dos fechas de referencia y obtiene
mapas y estadísticas (en hectáreas) de dónde cambió más la superficie.

> **Versión beta con recursos gratuitos.** Sirve para explorar capacidades y alcances. Por eso limita el
> tamaño del área (100 000 ha por defecto) y el número de análisis (5/hora y 20/día por usuario).
> Todos los límites se configuran por variables de entorno y la interfaz los muestra al usuario.

- **Backend**: FastAPI + Earth Engine Python API (`backend/`)
- **Frontend**: React + Vite + TypeScript + Leaflet, ES/EN, diseño Land AI (`frontend/`)
- **Resultado**: preliminar. Un píxel de "cambio alto" **no** implica deforestación, minería, urbanización ni
  actividad ilegal: indica un cambio espectral significativo entre los dos periodos.

## Qué incluye

| Función | Detalle |
|---|---|
| Área por municipio | Departamento + municipio de la colección municipal (`MUNICIPALITIES_ASSET`); vista previa del límite y medición en hectáreas |
| Área dibujada | Polígono o rectángulo sobre el mapa, vértices editables, medidor en vivo contra el límite, validación (cruces, vértices, mínimo/máximo) |
| Límites visibles | Medidor de área, aviso al acercarse, bloqueo al excederlo (en el navegador **y** en el servidor, antes de gastar cuota de Earth Engine) |
| Datos | Sentinel-2 SR Harmonized + Cloud Score+ (`cs_cdf ≥ 0.55`) + máscara SCL, ventana de ±30 días por fecha, mediana |
| Método | CVA (magnitud espectral / √6) + ángulo espectral + percentiles P50/P90/P95 del área + limpieza de parches pequeños |
| Capas | Principales: antes, después, cambio clasificado, cambio alto limpio. Avanzadas (plegadas): magnitud, ángulo, ΔNDVI, ΔNBR, ΔNDWI, ΔNDBI, >P95 |
| Idiomas | Español (por defecto) y English, conmutador ES/EN guardado en `localStorage` |
| Protección de recursos | SlowAPI (solo `/analyze`), compuerta de concurrencia, Cloud Run con 1 instancia máxima |

## Requisitos

- Python 3.11+ (probado con 3.11–3.13) y Node.js 20+ (recomendado 22)
- Una cuenta de Google con Earth Engine y un **proyecto de Google Cloud registrado** en Earth Engine
- Acceso de lectura a la colección de municipios (`users/maikolzaraza07/mpios` por defecto)

## Ejecutar en local (Windows PowerShell + conda)

```powershell
# 0) Descomprime el zip y entra a la carpeta
cd landai-change

# 1) Entorno Python
conda create -n landai python=3.11 -y
conda activate landai
pip install -r backend\requirements-dev.txt

# 2) Pruebas del backend (no usan Earth Engine real)
pytest -q

# 3) Configuración: copia el ejemplo y pon TU proyecto
Copy-Item .env.example .env
notepad .env            # EE_PROJECT=<tu-proyecto-registrado-en-earth-engine>

# 4) Autenticación de Earth Engine (una sola vez; abre el navegador)
earthengine authenticate

# 5) (Opcional) prueba de humo REAL: consume una cuota mínima, no corre el análisis completo
python backend\scripts\smoke_test.py

# 6) Backend — terminal 1
cd backend
uvicorn app.main:app --reload --port 8000
#    Documentación interactiva: http://localhost:8000/docs

# 7) Frontend — terminal 2 (nueva ventana de PowerShell)
cd frontend
Copy-Item .env.example .env
npm install
npm test
npm run dev
#    Abre http://localhost:5173
```

macOS/Linux: igual, cambiando `\` por `/` y `Copy-Item` por `cp`.

**Con Docker (opcional):** `docker compose up --build` (usa las credenciales que dejó
`earthengine authenticate`, montadas en solo lectura; el repo nunca contiene llaves).

### Problemas frecuentes

| Síntoma | Causa probable |
|---|---|
| `503 earth_engine_not_available` | `EE_PROJECT` vacío o `.env` fuera de la raíz/`backend/`; falta `earthengine authenticate`; proyecto sin registrar en Earth Engine |
| `404/502` al listar municipios | El asset `MUNICIPALITIES_ASSET` no existe o no está compartido contigo |
| El navegador no llega al backend | `CORS_ORIGINS` no incluye `http://localhost:5173` o el backend no está en el puerto 8000 |
| `429 rate_limit_exceeded` | Alcanzaste 5 análisis/hora o 20/día (sube `RATE_LIMIT_ANALYZE` solo para pruebas locales) |

## Cómo usarla

1. Elige **Por municipio** (departamento + municipio) o **Dibujar área** (polígono/rectángulo).
2. Mira el **medidor de área**: verde = dentro del límite, ámbar = cerca, rojo = excede.
3. Escoge las fechas de referencia A y B (cada una usa ±30 días). `Cargar ejemplo` solo llena el formulario.
4. `Verificar datos` (opcional, barato) → `Detectar cambios` (tarda de decenas de segundos a varios minutos).
5. Revisa las tarjetas de resultado, activa capas en el panel del mapa y lee "Acerca de este resultado".

## API

| Método | Ruta | Notas |
|---|---|---|
| GET | `/health` | Liveness; no llama a Earth Engine |
| GET | `/api/v1/config` | Límites públicos que muestra la interfaz |
| GET | `/api/v1/administrative/departments` | |
| GET | `/api/v1/administrative/municipalities?department=` | |
| GET | `/api/v1/administrative/municipality?department=&municipality=` | Área + límite simplificado (en caché) |
| POST | `/api/v1/change/preflight` | Sin límite de tasa; valida fechas/área y cuenta escenas |
| POST | `/api/v1/change/analyze` | **Limitado**: 5/hora y 20/día; respuesta 429 estructurada |

Cuerpo: `{"department","municipality","date_a","date_b"}` **o** `{"geometry":{"type":"Polygon","coordinates":[[[lon,lat],…]]},"date_a","date_b"}`.
Errores: `{"status":"error","code","message","details"}` (códigos estables, p. ej. `rate_limit_exceeded`).

## Variables de entorno

Ver [`.env.example`](.env.example) (backend) y [`frontend/.env.example`](frontend/.env.example) (`VITE_API_BASE_URL`,
`VITE_LANDAI_CONTACT_URL`, `VITE_BASE_PATH`, basemap opcional).

## Pruebas

```powershell
pytest -q                                   # raíz: 34 pruebas del backend (Earth Engine simulado)
cd frontend; npm test; npm run typecheck; npm run build
```

## Despliegue público

Frontend en **GitHub Pages**, backend en **Cloud Run**: ver [`docs/deployment.md`](docs/deployment.md).

## Documentación

- [`docs/deployment.md`](docs/deployment.md): local, GitHub Pages, Cloud Run, límites y costos
- [`docs/methodology.md`](docs/methodology.md): método y cómo interpretar el resultado
- [`docs/adaptation.md`](docs/adaptation.md): de Landsat (script de referencia) a Sentinel-2, decisión por decisión

## Seguridad

- No hay llaves, JSON de cuentas de servicio ni secretos en el repositorio ni en el `.zip`.
- En producción el backend usa la **identidad de servicio** de Cloud Run (sin llaves).
- El registro por análisis no incluye credenciales, cabeceras, IP ni coordenadas dibujadas.
- Si alguna vez subiste una llave JSON (como `ee-…json`), **revócala** en IAM y no la reutilices.
