# Guía de despliegue

## Arquitectura

| Parte | Dónde | Por qué |
|---|---|---|
| Frontend (React, estático) | **GitHub Pages** | Hosting estático gratuito |
| Backend (FastAPI + Earth Engine) | **Google Cloud Run** | Es un servidor Python; **GitHub Pages no puede ejecutarlo** |
| Procesamiento | Google Earth Engine | Se ejecuta en servidores de EE, contra la cuota de tu proyecto |

El navegador llama directo a la URL del backend, así que el backend debe permitir el origen del frontend con `CORS_ORIGINS`
(solo el origen, sin ruta: `https://<usuario>.github.io`).

## 1. Local

Ver el [README](../README.md#ejecutar-en-local-windows-powershell--conda). Resumen:

```powershell
conda activate landai
pip install -r backend\requirements-dev.txt ; pytest -q
Copy-Item .env.example .env ; notepad .env       # EE_PROJECT=...
earthengine authenticate
cd backend ; uvicorn app.main:app --reload       # terminal 1
cd frontend ; npm install ; npm run dev          # terminal 2 -> http://localhost:5173
```

## 2. Publicar el código en GitHub

```powershell
cd landai-change
git init -b main
git status                       # .env, credentials\ y ee-*.json NO deben aparecer
git add -A
git commit -m "Land AI Change Intelligence beta"
git remote add origin https://github.com/<usuario>/landai-change.git
git push -u origin main
```

Si `git status` lista `.env` o un `.json` de credenciales, **detente** y revisa `.gitignore`. El nombre del repositorio
debe ser `landai-change` para que la base de Pages sea `/landai-change/` (si usas otro nombre el workflow lo ajusta solo).

## 3. Backend en Cloud Run (identidad de servicio, sin llaves)

Requisitos: `gcloud` instalado y con sesión iniciada, facturación habilitada en el proyecto (Cloud Run y Cloud Build la exigen
aunque el uso quede dentro de la capa gratuita).

```powershell
$PROJECT = "tu-proyecto-gcp"          # el registrado en Earth Engine
$REGION  = "us-central1"

gcloud config set project $PROJECT
gcloud services enable run.googleapis.com cloudbuild.googleapis.com artifactregistry.googleapis.com earthengine.googleapis.com

# 3a. Cuenta de servicio del backend (será la identidad de Cloud Run; NO se crea ninguna llave)
gcloud iam service-accounts create landai-backend
$SA = "landai-backend@$PROJECT.iam.gserviceaccount.com"
gcloud projects add-iam-policy-binding $PROJECT --member="serviceAccount:$SA" --role="roles/earthengine.viewer"
gcloud projects add-iam-policy-binding $PROJECT --member="serviceAccount:$SA" --role="roles/serviceusage.serviceUsageConsumer"
```

> **Verifica los roles.** `roles/earthengine.viewer` + `roles/serviceusage.serviceUsageConsumer` es la combinación habitual para
> lectura, pero no pude confirmarla contra la documentación vigente de Earth Engine en esta sesión. Si la primera llamada
> devuelve *permission denied*, revisa la guía oficial de acceso con cuentas de servicio de Earth Engine y ajusta los roles
> (por ejemplo, un rol personalizado con `earthengine.computations.create`).

Además:
- **Comparte el asset de municipios** (`users/maikolzaraza07/mpios`) con `landai-backend@<proyecto>.iam.gserviceaccount.com` como *Reader*
  (Code Editor → Assets → Share).
- Si tu proyecto es de uso **no comercial**, comprueba en la consola de Earth Engine que una cuenta de servicio puede usarlo
  y que el uso de una herramienta pública con enlace comercial ("Habla con Land AI") es compatible con tu tipo de registro.

```powershell
# 3b. Desplegar (límites de la beta gratuita)
gcloud run deploy landai-change-api `
  --source backend `
  --region $REGION `
  --port 8000 `
  --service-account $SA `
  --allow-unauthenticated `
  --cpu 1 --memory 2Gi `
  --min-instances 0 --max-instances 1 --concurrency 1 `
  --timeout 900 `
  --set-env-vars "EE_PROJECT=$PROJECT,TRUST_FORWARDED_FOR=true,CORS_ORIGINS=https://<usuario>.github.io"
```

Qué hace cada opción y por qué importa para consumir solo recursos gratuitos:

| Opción | Efecto |
|---|---|
| `--min-instances 0` | Escala a cero: sin costo cuando nadie lo usa (el contador de SlowAPI se reinicia al escalar a cero) |
| `--max-instances 1` + `--concurrency 1` | Un solo análisis a la vez en todo el servicio; acota cuota de EE y costo |
| `--timeout 900` | Un análisis es una petición larga (hasta 15 min) |
| `--memory 2Gi` | El análisis es ligero en memoria (EE hace el cómputo); 1 GiB suele bastar |
| `TRUST_FORWARDED_FOR=true` | Lee la IP real del cliente para el límite de tasa (sin esto todos compartirían el contador) |

Comprueba: `https://<url-de-cloud-run>/health`, `/api/v1/config` y `/api/v1/administrative/departments`.
Si `/health` responde pero `departments` da `503 earth_engine_not_available`, revisa `EE_PROJECT` y los roles de la cuenta de servicio.

Para cambiar `CORS_ORIGINS` más adelante:

```powershell
gcloud run services update landai-change-api --region $REGION --update-env-vars "^@^CORS_ORIGINS=https://a.github.io,https://midominio.com"
```

## 4. Frontend en GitHub Pages

1. Repositorio → **Settings → Pages → Source: GitHub Actions**.
2. **Settings → Secrets and variables → Actions → Variables** → crea:
   - `VITE_API_BASE_URL` = URL de Cloud Run (sin `/` final)
   - `VITE_LANDAI_CONTACT_URL` = destino del botón "Habla con Land AI" (opcional; vacío = el botón se oculta)
3. Haz push a `main` (o ejecuta el workflow *Deploy frontend to GitHub Pages*). Quedará en
   `https://<usuario>.github.io/landai-change/`.
4. Verifica que ese origen esté en `CORS_ORIGINS` del backend.

## 5. Límites y consumo de recursos gratuitos

| Control | Valor por defecto | Dónde se cambia |
|---|---|---|
| Área máxima por análisis | 100 000 ha (aviso desde 50 000) | `MAX_AOI_HECTARES`, `WARN_AOI_HECTARES` |
| Área dibujada mínima | 10 ha | `MIN_AOI_HECTARES` |
| Vértices máximos | 300 | `MAX_POLYGON_VERTICES` |
| Análisis por usuario | 5/hora y 20/día (solo `/analyze`) | `RATE_LIMIT_ANALYZE` |
| Análisis simultáneos | 1 | `MAX_CONCURRENT_ANALYSES` + `--concurrency 1 --max-instances 1` |

Los límites se aplican en el navegador (para guiar) **y** en el servidor (la autoridad). Un área excedida se rechaza antes de
tocar Earth Engine.

Límites reales de esta protección (sé honesto con los usuarios y contigo):

- El contador de SlowAPI vive en memoria: se reinicia cuando la instancia escala a cero y no se comparte entre instancias.
  Con `max-instances 1` es exacto mientras la instancia está viva.
- La API es pública y sin autenticación: alguien con muchas IPs podría agotar la cuota gratuita. La contención real es
  `max-instances 1` + `concurrency 1` + tus **alertas de presupuesto** (Billing → Budgets & alerts) y las cuotas de Earth Engine.
  Si hace falta endurecer: Cloud Armor, API keys o un contador compartido (Redis/Firestore); queda fuera del alcance de esta beta.
- Las cuotas gratuitas de Cloud Run (CPU-segundos, peticiones) y de Earth Engine cambian con el tiempo: confírmalas en sus
  páginas de precios/cuotas antes de abrir la app a mucho público.
- Un análisis de 15 min a 1 vCPU son ≈ 900 vCPU-s; con 20 análisis/día/usuario el consumo crece rápido si hay muchos usuarios.

## 6. Registro (logs)

Cada análisis escribe **una línea JSON** en stdout (Cloud Logging la indexa): tipo de área, departamento/municipio, hectáreas,
fechas, conteo de imágenes, P50/P90/P95, hectáreas de cambio alto, duración, éxito y código de error.
**No** se registran credenciales, cabeceras, IP ni coordenadas dibujadas.

## 7. Credenciales: reglas

- Nunca subas llaves JSON (`ee-*.json`) al repositorio ni las pegues en chats o capturas.
- Si una llave se expuso, **elimínala** (IAM → Cuentas de servicio → Llaves) y crea otra solo si es imprescindible.
- En producción no hace falta ninguna llave: Cloud Run usa la identidad de servicio.
