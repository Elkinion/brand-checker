# Brand Checker — Streamlit

Port a Python/Streamlit del validador de piezas de marca Tigo.
Diseñado para publicar en **Streamlit Community Cloud** con autenticación por contraseña.

## Feature parity con la versión R

Incluido en v1:
- Análisis de **imágenes** (PNG/JPG): Cloud Vision + Gemini (subjetivo + logos).
- 11 tipos de pieza (KV con foto, ATL, social post/story/feed, afiches, etc.).
- 11 reglas objetivas + 7 subjetivas + reglas condicionales por flag.
- Paletas print/digital, detección de gama, matching de logos de referencia.
- Password gate con bcrypt, 5 intentos y lockout de 60 s.

Pendiente para v2 (existe en la versión R):
- Pipeline de **video** (Video Intelligence + Gemini File API + ABCD framework).
- Extractor de valla desde foto de calle (Gemini Image Gen + corrección de color).
- Descarga de reporte PDF.

## Correr local

```bash
pip install -r requirements.txt
cp .streamlit/secrets.toml.example .streamlit/secrets.toml
# editar .streamlit/secrets.toml con tus keys y hash de password
streamlit run app.py
```

Para generar el hash de la contraseña:

```bash
python -c "import bcrypt; print(bcrypt.hashpw(b'TU_PASSWORD', bcrypt.gensalt()).decode())"
```

## Deploy en Streamlit Community Cloud

1. **Push a GitHub** (podés usar repo privado — Streamlit lo lee igual). El `.gitignore` ya excluye `secrets.toml`.
2. Ir a https://share.streamlit.io → **New app** → conectá el repo.
3. Main file: `app.py` (o `brand-checker-py/app.py` si el repo es la carpeta padre).
4. En **App settings → Secrets**, pegá el contenido de tu `secrets.toml` local (los mismos campos que `secrets.toml.example`).
5. Deploy. URL final: `https://<slug>.streamlit.app`.

## Seguridad

- Todas las keys viven en `st.secrets`, nunca en el repo.
- La app pide contraseña antes de cargar cualquier UI. Sin contraseña correcta no se ejecuta ninguna llamada a Gemini/Vision (protege costos).
- Hash bcrypt con salt aleatorio; brute-force mitigado con lockout de 60 s tras 5 intentos fallidos.
- HTTPS por defecto en `*.streamlit.app`.

Para blindaje extra, considerá **Cloudflare Access** al frente de la URL (zero-trust, hasta 50 usuarios gratis, sin cambios de código).

## Estructura

```
brand-checker-py/
├── app.py                    # UI Streamlit + password gate
├── requirements.txt
├── .streamlit/
│   ├── config.toml           # tema, límite upload
│   └── secrets.toml.example  # copiar a secrets.toml
├── modules/
│   ├── auth.py               # bcrypt + rate limit
│   ├── config.py             # lectura de secrets
│   ├── utils.py              # base64, PIL, RGB helpers
│   ├── brand_rules.py        # paletas + perfiles + 11 reglas objetivas + subjetivas
│   ├── cv_analysis.py        # Google Cloud Vision
│   ├── ai_analysis.py        # Gemini subjective (gemini-2.5-pro)
│   ├── logo_matcher.py       # Gemini logo detection (gemini-2.5-flash)
│   ├── pipeline.py           # orquestación paralela (ThreadPoolExecutor)
│   └── scoring.py            # score total ponderado
└── static/
    └── logos/                # logos de referencia (matching)
```
