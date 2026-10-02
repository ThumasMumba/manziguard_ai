# ManziGuard AI

**Know if your water is safe, from a photo of a paper strip.**

ManziGuard AI is a low-cost climate-health platform that helps households and communities in Zambia check whether borehole and well water is safe to drink. A user dips a "K5" paper test strip, photographs it, and gets a plain-language **Safe / Risky / Unsafe** result in **Bemba, Nyanja or English**, together with practical purification guidance. When water is Unsafe, the system alerts the nearest Community Health Worker (CHW) and WASH officer by SMS, with GPS coordinates.

> _Manzi_ means "water" in Nyanja.

**Status:** Prototype stage. The AI model has been prototyped from an existing health self-diagnosis app. Built for the PachiPanda Innovation Challenge 2026 (Jacaranda Hub), water pillar.

---

## Table of Contents

1.  [The Problem](#the-problem)
2.  [The Solution](#the-solution)
3.  [Key Features](#key-features)
4.  [How It Works](#how-it-works)
5.  [Architecture](#architecture)
6.  [Access Channels](#access-channels)
7.  [AI Model](#ai-model)
8.  [Result Classification](#result-classification)
9.  [Purification Guidance](#purification-guidance)
10. [Alerting Workflow](#alerting-workflow)
11. [Live Dashboard](#live-dashboard)
12. [Data, Privacy and Ethics](#data-privacy-and-ethics)
13. [Getting Started](#getting-started)
14. [Project Structure](#project-structure)
15. [Configuration](#configuration)
16. [Deployment](#deployment)
17. [Testing](#testing)
18. [Roadmap](#roadmap)
19. [Beneficiaries and Impact](#beneficiaries-and-impact)
20. [Stakeholders and Partners](#stakeholders-and-partners)
21. [Contributing](#contributing)
22. [License](#license)
23. [Contact](#contact)

---

## The Problem

Many households in Zambia depend on boreholes and shallow wells with no routine way to test water quality. Laboratory testing is expensive, slow and often far away. Contamination risks are real and changing:

- **Nitrates** from agricultural runoff and sanitation seepage.
- **Bacterial contamination** (e.g. faecal indicators), especially after heavy rainfall and flooding.
- **pH imbalance**, including acidification linked to **mining waste** in mining regions.

People usually find out water is unsafe only after someone falls ill. There is no early-warning link between a household's water point and the local health system.

## The Solution

ManziGuard AI turns a cheap paper strip and a phone camera into a water-quality screening tool, and connects the result to the people who can act on it.

1. **Test** with a low-cost K5 strip.
2. **Snap** a photo (smartphone) or **report** the strip colours (basic phone via USSD/SMS).
3. **Understand** the result in your own language.
4. **Act** on clear purification steps, while health workers are notified of dangerous results.
5. **Monitor** at community level through an anonymized live dashboard.

## Key Features

- **Photo-based strip analysis:** reads nitrate, pH and bacterial-indicator pads from a photo of the K5 strip.
- **Context-aware AI:** combines strip colour with GPS location, recent rainfall and proximity to mining-waste sites for a more reliable verdict than colour alone.
- **Three-level result:** Safe, Risky, Unsafe.
- **Local languages:** Bemba, Nyanja and English.
- **Works on any phone:** mobile web app plus USSD/SMS for feature phones and low connectivity.
- **Actionable guidance:** chlorine treatment, boiling and Moringa seed clarification.
- **Automatic escalation:** Unsafe results trigger an SMS with GPS to the nearest CHW and WASH officer via MTN.
- **Live public-health dashboard:** anonymized results for the Council, WWF and the Ministry of Health.

## How It Works

```
┌────────────┐   ┌─────────────┐   ┌────────────────┐   ┌──────────────┐
│ Dip K5     │──▶│ Photo / USSD│──▶│ AI analysis    │──▶│ Safe / Risky │
│ test strip │   │ / SMS input │   │ colour + GPS + │   │ / Unsafe in  │
└────────────┘   └─────────────┘   │ rain + mining  │   │ user language│
                                   └───────┬────────┘   └──────┬───────┘
                                           │                   │
                            ┌──────────────▼─────┐    ┌────────▼────────┐
                            │ Anonymized data    │    │ Purification    │
                            │ → live dashboard   │    │ guidance        │
                            └────────────────────┘    └────────┬────────┘
                                                               │ if Unsafe
                                                     ┌─────────▼─────────┐
                                                     │ SMS + GPS to CHW  │
                                                     │ and WASH officer  │
                                                     └───────────────────┘
```

## Architecture

| Layer                        | Responsibility                                                               |
| ---------------------------- | ---------------------------------------------------------------------------- |
| **Client (mobile web app)**  | Camera capture, guided strip photography, language selection, result display |
| **USSD/SMS gateway**         | Menu-driven and text-based input for users without smartphones or data       |
| **API service**              | Request handling, validation, orchestration, localization                    |
| **AI analysis service**      | Strip color interpretation and risk classification using contextual data     |
| **Context data services**    | Rainfall data, mining-waste proximity, GPS/geospatial lookups                |
| **Alerting service**         | SMS dispatch to CHWs and WASH officers through MTN                           |
| **Data store and dashboard** | Anonymized result storage and live visualization for institutional partners  |

### Tech Stack

- **Frontend:** Flask/Jinja2 templates, CSS, JavaScript (camera capture via file input / `getUserMedia`), mobile-first
- **Backend/API:** Flask with Blueprints (`analysis`, `alerts`, `ussd`, `dashboard`, `auth`), Flask-SQLAlchemy, Flask-Migrate, Flask-WTF, Flask-Limiter, Flask-Login (CHW/WASH admin accounts only)
- **AI/ML:** Python + TensorFlow/Keras for training; TFLite for server-side inference; OpenCV for strip and pad detection (see [AI Model](#ai-model))
- **Messaging:** MTN SMS/USSD integration via Flask webhook endpoints
- **Database:** MySQL via SQLAlchemy (SQLite for local development)
- **Dashboard:** Flask/Jinja2 + Tailwind, Chart.js for trends, Leaflet for the hotspot map
- **Hosting (testing):** Railway (see [Deployment](#deployment))

## Access Channels

| Channel            | Who it serves       | Input                                        | Output                          |
| ------------------ | ------------------- | -------------------------------------------- | ------------------------------- |
| **Mobile web app** | Smartphone users    | Photo of K5 strip                          | Result, guidance, map of nearby help |
| **USSD**           | Feature-phone users | Menu selections describing strip pad colours | Short result and guidance       |
| **SMS**            | Low/no data users   | Structured text reply                        | Result and guidance by SMS      |

## AI Model

The analysis pipeline combines:

1. **Strip color reading:** extracts color values for nitrate, pH and bacterial-indicator pads from the photo, with lighting and white-balance normalization.
2. **Contextual signals:**
   - **GPS location** of the water point
   - **Recent rainfall** (runoff and flooding raise contamination risk)
   - **Proximity to mining waste** (raises risk of acidic or contaminated water)
3. **Classification:** produces a Safe / Risky / Unsafe verdict.

The model has been prototyped from the team's existing health self-diagnosis app. Validation against laboratory reference measurements is a priority (see [Roadmap](#roadmap)).

### Pipeline (TensorFlow)

The analysis is split into two stages so that each is simple, testable and data-efficient:

1. **Strip and pad detection (OpenCV):** locate the strip, crop each reagent pad, and normalize lighting using a reference color (white/grey patch on the strip or holder). This step matters more than the choice of neural network, because phone cameras and daylight vary widely.
2. **Classification (Keras):** predict the result from each pad's colour plus context.
   - **Baseline (recommended first):** a small dense network (or gradient-boosted trees) on colour features (mean/median Lab and HSV per pad) concatenated with context features (rainfall, distance to mining waste, season). Small, fast and works with limited data.
   - **Image-based option:** transfer learning with **MobileNetV3-Small** on pad crops, with strong augmentation (brightness, white balance, blur). Use this only if colour features prove insufficient, and only once enough labelled photos exist.
3. **Export:** convert the trained model to **TFLite** and serve it from the Flask API, so the deployed server does not need full TensorFlow.

Training data should be strip photos paired with laboratory-verified measurements, captured across phones, lighting conditions and water types. Data quality and volume will limit accuracy more than model architecture.

> **Important:** ManziGuard AI is a **screening tool**, not a replacement for laboratory analysis. Results near thresholds, or any doubt, should lead to confirmatory testing and conservative handling of the water.

## Result Classification

| Result     | Meaning                                                     | System behavior                                                                         |
| ---------- | ----------------------------------------------------------------- | ------------------------------------------------------------------------------------------ |
| **Safe**   | Indicators within acceptable ranges                               | Shows result and routine water-safety tips                                                 |
| **Risky**  | One or more indicators borderline, or contextual risk is elevated | Shows result and recommends treatment before drinking, and retesting                       |
| **Unsafe** | Indicators clearly outside safe ranges                            | Shows result, urgent guidance, and **triggers SMS alert with GPS to CHW and WASH officer** |

_(Exact thresholds: `TODO`. Document the reference values and their source, e.g. WHO / Zambian drinking-water standards.)_

## Purification Guidance

Depending on the result, users are guided through household-level options:

- **Chlorination:** disinfect water with chlorine.
- **Boiling:** for bacterial contamination.
- **Moringa seeds:** natural clarification of turbid water.

Guidance is delivered in the user's chosen language. Note that boiling and Moringa do not remove nitrates or correct pH; for those, users should be directed to an alternative water source and health staff.

## Alerting Workflow

When a result is **Unsafe**:

1. The system identifies the nearest **Community Health Worker** and **WASH officer** using the water point's GPS location.
2. An **SMS** containing the location and result summary is sent via **MTN**.
3. The user receives immediate guidance and is told that local health staff have been notified.
4. The event appears (anonymized) on the dashboard.

## Live Dashboard

Anonymized results are aggregated into a live dashboard for:

- **Local Council**
- **WWF**
- **Ministry of Health**

Typical views: hotspot map, Safe/Risky/Unsafe trends over time, correlation with rainfall events and mining-waste proximity, and alert response tracking.

## Data, Privacy and Ethics

- **Anonymization:** dashboard data contains no names or phone numbers.
- **Minimal collection:** only data needed for analysis and alerting is collected.
- **Location handling:** GPS is used for analysis and CHW/WASH routing; public views show coarse locations only.
- **Consent:** users are informed that Unsafe results share location with health workers.
- **Transparency:** clear communication that results are screening-level.
- **Language access:** results and guidance are provided in Bemba, Nyanja and English.

## Getting Started

### Prerequisites

- Python 3.11 or 3.12 (check TensorFlow's supported Python versions before training)
- MySQL (optional locally; SQLite is used by default in development)
- MTN SMS/USSD gateway credentials (not needed for local development, alerts can be logged to the console)
- Rainfall data source access and mining-site geodata

### Installation

```bash
git clone https://github.com/<your-org>/manziguard-ai.git
cd manziguard-ai

python3 -m venv .venv
source .venv/bin/activate          # Windows: .venv\Scripts\activate

python -m pip install --upgrade pip
pip install -r requirements.txt    # serving dependencies (lightweight)
# only for model training:
# pip install -r requirements-train.txt

cp .env.example .env               # then edit values
# To start the application
flask --app run.py run --debug
```

## Project Structure
```
manziguard-ai/
├── README.md
├── requirements.txt            # runtime (Flask, SQLAlchemy, PyMySQL, gunicorn, pyotp, ...)
├── requirements-train.txt      # untouched this sprint
├── .env.example
├── Procfile / Dockerfile
├── + Makefile                  # i18n, test, lint shortcuts
├── + .github/workflows/ci.yml
├── + .pre-commit-config.yaml
├── + babel.cfg
├── + scripts/seed_data.py, scripts/i18n.sh
├── + translations/{en,bem,nya}/LC_MESSAGES/
├── app/
│   ├── __init__.py             # create_app(config_name)
│   ├── config.py
│   ├── extensions.py           # db, migrate, limiter, login_manager, csrf, babel
│   ├── models/                 # user, responder, sample, alert, geo, ops (see §3)
│   ├── blueprints/
│   │   ├── auth/               # login, logout, password change, MFA
│   │   ├── + admin/            # users, responders, districts, audit log
│   │   ├── analysis/           # routing placeholder only
│   │   ├── ussd/               # stub webhook
│   │   ├── + sms/              # stub webhook (or inside ussd/)
│   │   ├── alerts/             # placeholder
│   │   └── dashboard/          # placeholder + coarse-location serializer
│   ├── services/
│   │   ├── i18n.py             # locale selection, Babel wiring
│   │   ├── + geo.py            # haversine, nearest(), coarsen()
│   │   ├── + security.py       # headers, roles_required, field encryption
│   │   └── strip_reader.py, classifier.py, context.py   # empty stubs
│   ├── templates/ (+ base.html: mobile-first, language switcher stub)
│   └── static/
├── ml/ data/ docs/ migrations/ tests/
```
 ```
  strip_reader.py: Image & Data Ingestion — Functions or classes to load, crop, preprocess, and extract raw visual or sensor data (e.g., color values, pixel intensity, regions of interest) from physical test strips or image inputs.

  classifier.py: Machine Learning / Model Classification — Model loading, feature extraction, inference logic, and prediction models (e.g., classifying strip results into categories or classes).

  calibration.py (Calibration): Sensor & Color Calibration — Routines for normalizing lighting, white balancing, scaling reference colors, or adjusting raw readings against standard control values before processing.

  analysis.py: Data Analysis & Processing — Core analytical logic that converts classified features or raw measurements into meaningful domain metrics, statistical summaries, or diagnostic results.
  pipeline.py: End-to-End Orchestration — The master workflow script/class that chains together ingestion (strip_reader), normalization (calibration), classification (classifier), and post-processing (analysis) into a single executable pipeline.  
  
  context.py: Execution Context & Config — Configuration objects, session state management, environment variables, or metadata passed across different stages of the processing run.  
  
  geo.py: Geolocation & Mapping — Utility functions for handling GPS coordinates, reverse geocoding, spatial calculations, or region tagging for data submissions.  
   
  security.py: Security & Authentication — Data encryption/decryption, token validation, API key verification, user permission checks, or anonymization of sensitive data.  
    
  il8n.py (Internationalization / i18n): Localization & Multilingual Support — Translations, localized string mappings, date/number formatting, and language detection routines for user-facing outputs. 
 ```
## Configuration

Set via environment variables (names are examples):

| Variable                        | Purpose                                                              |
| ------------------------------- | -------------------------------------------------------------------- |
| `SECRET_KEY`                    | Flask session signing                                                |
| `DATABASE_URL`                  | Result storage (`sqlite:///dev.db` locally, MySQL URL in deployment) |
| `MTN_API_KEY` / `MTN_SENDER_ID` | SMS and USSD gateway                                                 |
| `RAINFALL_API_KEY`              | Rainfall data provider                                               |
| `MODEL_PATH`                    | Path to the TFLite model                                             |
| `DEFAULT_LANGUAGE`              | `en`, `bem` or `nya`                                                 |

Never commit secrets. Keep `.env` out of version control.

## Deployment

**Testing/staging: Railway.** ManziGuard runs a long-lived Flask service, loads a model into memory, needs a database and receives USSD/SMS webhooks. Railway suits this because it runs a normal always-on web process (via `Procfile` or `Dockerfile`), offers a managed MySQL service, and gives you a public HTTPS URL for MTN/gateway callbacks.

Basic flow:

1. Push the repo to GitHub and create a Railway project from it.
2. Add a MySQL service and set `DATABASE_URL` from its connection variables.
3. Set the environment variables above in Railway's Variables tab.
4. Start with Gunicorn: `gunicorn "app:create_app()" --workers 2 --timeout 60`.
5. Run migrations once (`flask --app app db upgrade`).
6. Point the USSD/SMS gateway callbacks at the Railway URL.

**Why not Vercel or Cloudflare for the backend (as far as we know):**

- **Vercel** runs Python as serverless functions with bundle size limits and no persistent local storage. Small TFLite inference could fit, but cold starts, the filesystem and database setup make it a poorer match for this app. It is fine for a static frontend if you later split the frontend from the API.
- **Cloudflare** Workers do not run a standard Flask + TensorFlow/OpenCV stack. It is useful as a free DNS/CDN/SSL layer in front of the app, not as the app host.

Check each platform's current limits and pricing before committing, since they change.

## Testing

- **Unit tests:** classification logic, localization, alert routing.
- **Image tests:** strips photographed under varied lighting, phones and backgrounds.
- **Field validation:** compare ManziGuard results against laboratory measurements from real boreholes and wells.
- **Channel tests:** USSD/SMS flows on real networks.
- **Usability tests:** with community members and CHWs in each supported language.

## Roadmap

- [ ] AI model
- [ ] Mobile web app: guided strip capture and results
- [ ] Bemba and Nyanja localization review with native speakers
- [ ] USSD/SMS channel via MTN
- [ ] CHW / WASH officer directory and SMS alerting with GPS
- [ ] Rainfall and mining-waste data integration
- [ ] Live anonymized dashboard for Council, WWF and Ministry of Health
- [ ] Field pilot and lab validation
- [ ] Threshold calibration and accuracy reporting
- [ ] Scale to additional districts

## Beneficiaries and Impact

**Primary beneficiaries:** households and communities relying on boreholes and wells, especially in areas exposed to agricultural runoff, flooding and mining waste.

**Secondary beneficiaries:** Community Health Workers, WASH officers, local councils, NGOs and the Ministry of Health, who gain early-warning data on water-related health risks.

**Intended impact:**

- Fewer waterborne illnesses through earlier detection and action
- Faster response by health workers to dangerous water points
- Better evidence for planning and resource allocation
- Greater climate resilience for communities facing floods and pollution

_(Add measurable targets, e.g. households reached, tests completed, alerts responded to, once the pilot is defined.)_

## Stakeholders and Partners

- Local Council
- WWF
- Ministry of Health
- Community Health Workers and WASH officers
- MTN (messaging and USSD)
- Jacaranda Hub / PachiPanda Innovation Challenge 2026

## Contributing

Contributions are welcome.

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/your-feature`
3. Commit your changes with clear messages
4. Open a pull request describing the change and how it was tested

Please do not include personal or identifiable health or location data in issues, commits or test fixtures. Translation improvements for Bemba and Nyanja are especially valuable.

## License

`TODO`: choose a license (e.g. MIT, Apache-2.0) and add a `LICENSE` file.

## Contact

- Project lead: Thumas
- Email: thomasmumba300@gmail.com
- Location: Ndola, Zambia

---

_ManziGuard AI is a screening aid and does not replace laboratory testing or professional medical advice._
