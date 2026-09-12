# Cameroon openIMIS — Claim Fraud & Rejection Detection

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-microservice-009688.svg)](https://fastapi.tiangolo.com/)
[![Next.js](https://img.shields.io/badge/Next.js-16-000000.svg)](https://nextjs.org/)
[![LightGBM](https://img.shields.io/badge/LightGBM-4.0+-brightgreen.svg)](https://lightgbm.readthedocs.io/)
[![Platform](https://img.shields.io/badge/Platform-openIMIS-007ACC.svg)](https://openimis.org/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

Machine learning research and a deployable scoring service for healthcare claim adjudication on the
Cameroon **openIMIS** database (14,242,741 claim transactions, 15.77M itemized services).

The repository holds three things that fit together:

1. **Research** — six notebooks benchmarking supervised and unsupervised detectors, each with a
   model card, a DOCX technical report, and the figures behind it.
2. **A scoring microservice** — FastAPI, serving the leakage-free LightGBM model with calibrated
   probabilities and exact TreeSHAP attributions per claim.
3. **A reviewer interface** — a Next.js page where an adjudicator enters or pastes a claim and reads
   back the risk score, the recommended action, and the factors that drove it.

Developed by the **Data and Design Lab**.

> **What the models actually predict.** The training label is **claim rejection, not fraud**. Most
> openIMIS rejections are deterministic eligibility rules the submission-time engine already
> enforces; the models are audit-queue triage aids, not fraud verdicts. Every score is advisory and
> every decision stays with a human reviewer. See each model card for the per-code analysis.

---

## Repository layout

```text
.
├── microservice/               # The deployable product: scoring API + reviewer UI
│   ├── backend/                # Python: scoring service, training code, tests
│   │   ├── service/            # FastAPI microservice
│   │   │   ├── app.py          # Routes: /health, /api/v1/predict/*, /api/v1/schema
│   │   │   ├── config.py       # Settings, model directory, decision thresholds
│   │   │   ├── engine.py       # Model loading, calibrated scoring (singleton)
│   │   │   ├── explainer.py    # TreeSHAP attribution and plain-language rationales
│   │   │   ├── transformer.py  # Claim JSON -> 51-feature model vector
│   │   │   ├── guardrails.py   # Input validation and range guards
│   │   │   ├── schemas.py      # Pydantic request/response contracts
│   │   │   └── client_example.py   # Integration example for openIMIS callers
│   │   ├── src/                # Autoencoder training package (dataset/model/train/evaluate)
│   │   ├── scripts/            # Evaluation and figure generation
│   │   ├── tests/              # Service test suite (19 tests)
│   │   ├── Dockerfile          # Service image (build from the repository root)
│   │   └── requirements.txt    # Python dependencies
│   └── frontend/               # Next.js 16 claim review interface
│       ├── app/                # Page, layout, components, shared types
│       ├── sample_claims/      # Three demo payloads (routine / suspicious / high-cost)
│       └── next.config.ts      # /api/proxy -> http://127.0.0.1:8000 rewrite
│
├── models/                     # Trained artifacts, one directory per model family
│   ├── model_lightgbm_no_leakage/   # Served by the microservice
│   ├── model_lightgbm/              # Original run, retains ClaimCategory (leaky)
│   ├── model_autoencoder/
│   ├── model_iforest/
│   └── model_ecod/
│
├── notebooks/                  # Research notebooks, one per model family
├── reports/                    # DOCX technical reports (one per model family)
├── figures/                    # Figures grouped by model family
├── data/                       # Raw openIMIS CSV exports (gitignored)
├── schemas/                    # 316-column data dictionary and table statistics
├── docker-compose.yml          # Runs the scoring service
└── README.md
```

Paths resolve relative to the repository root: the service, the notebooks, and the evaluation
scripts all locate `data/` and `models/` by walking up from their own location, so they run from
either the repository root or their own directory without edits.

---

## Quick start

### 1. Backend — scoring service

```bash
python -m venv .venv
# Windows PowerShell
.venv\Scripts\Activate.ps1
# Linux / macOS
source .venv/bin/activate

pip install --upgrade pip
pip install -r microservice/backend/requirements.txt
pip install fastapi uvicorn pydantic-settings httpx    # serving extras

cd microservice/backend
uvicorn service.app:app --host 0.0.0.0 --port 8000 --reload
```

The service loads `models/model_lightgbm_no_leakage/` at startup. Interactive API docs:
<http://127.0.0.1:8000/docs>.

### 2. Frontend — reviewer interface

```bash
cd microservice/frontend
npm install
npm run dev
```

Open <http://localhost:3000>. The page calls the service directly at `127.0.0.1:8000` and falls
back to the `/api/proxy` rewrite, so it works whether or not the ports are proxied. The header shows
live service health, test ROC-AUC, and the alert cutoff in use.

### 3. Docker

```bash
docker compose up --build
```

The image is built from the repository root (it needs `microservice/backend/service/` and
`models/model_lightgbm_no_leakage/`), exposes port 8000, and healthchecks `/health`.

### 4. Tests

```bash
cd microservice/backend
python tests/test_service.py
```

---

## API

| Method | Endpoint | Purpose |
| :--- | :--- | :--- |
| `GET` | `/` | Service metadata, endpoint index, headline model metrics |
| `GET` | `/health` | Liveness, model load state, ROC-AUC / PR-AUC, active threshold |
| `GET` | `/api/v1/schema` | The 51 model features with types and categorical levels |
| `POST` | `/api/v1/predict/claim` | Score one claim from openIMIS-shaped JSON |
| `POST` | `/api/v1/predict/features` | Score one pre-computed 51-feature vector |
| `POST` | `/api/v1/predict/batch` | Score a batch of claims in one request |

Example:

```bash
curl -X POST http://127.0.0.1:8000/api/v1/predict/claim \
  -H "Content-Type: application/json" \
  -d @microservice/frontend/sample_claims/legitimate_claim.json
```

The response carries the calibrated risk percentage, the risk tier
(`LOW_RISK` / `MODERATE_RISK` / `HIGH_RISK` / `CRITICAL`), a recommended adjudication action, the
decision threshold it was compared against, TreeSHAP risk drivers and mitigating factors, and the
scoring latency.

Configuration is environment-driven with the `FRAUD_API_` prefix — for example
`FRAUD_API_MODEL_DIR` to serve a different artifact directory, or `FRAUD_API_DECISION_THRESHOLD`
to move the alert cutoff.

---

## Models

Test-set metrics as recorded in each model card. Confidence intervals are clustered by facility;
the unsupervised detectors are evaluated against the same rejection label.

| Model | Paradigm | ROC-AUC | PR-AUC (no-skill) | Operating point | Artifacts |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **LightGBM, leakage-free** | Supervised GBDT + isotonic calibration | **0.8778** | 0.7604 (0.1623) | precision 0.918, recall 0.540, alert rate 9.6% | [`models/model_lightgbm_no_leakage/`](models/model_lightgbm_no_leakage/) |
| LightGBM, original run | Supervised GBDT | 0.9841 | 0.9635 (0.1623) | precision 0.999, recall 0.650 | [`models/model_lightgbm/`](models/model_lightgbm/) |
| Deep autoencoder | Unsupervised (PyTorch) | 0.7408 | 0.5074 (0.1750) | precision 0.944, recall 0.095 | [`models/model_autoencoder/`](models/model_autoencoder/) |
| ECOD | Non-parametric tail probability | 0.7426 | 0.5238 (0.1750) | precision 0.904, recall 0.181 | [`models/model_ecod/`](models/model_ecod/) |
| Isolation Forest | Unsupervised ensemble | 0.7235 | 0.4417 (0.1750) | precision 0.574, recall 0.148 | [`models/model_iforest/`](models/model_iforest/) |
| HDBSCAN / GLOSH | Density clustering (facility-month) | — | — | outlier ranking, not claim-level | notebook only |

**Why the leakage-free model is the one served.** The original LightGBM run reaches 0.9841 ROC-AUC
largely because `ClaimCategory` is set during adjudication — it encodes the answer. Putting that
field and 35 other adjudication-time fields on a deny-list and retraining across 11 tables gives an
honest 0.8778 ROC-AUC on 51 features, and that is the model behind the service. The ablation report
quantifies what each data block contributes.

Each artifact directory contains a `MODEL_CARD.md` with data splits, leakage controls, seed
variance, known limitations, and intended use.

---

## Reports and figures

Every report embeds its own figures; `figures/` keeps the source PNGs, grouped by model family.

| Report | Figures | Notebook |
| :--- | :--- | :--- |
| [`LightGBM_Without_ClaimCategory_Report.docx`](reports/LightGBM_Without_ClaimCategory_Report.docx) | [`figures/lightgbm_no_leakage/`](figures/lightgbm_no_leakage/) — ablation barchart, calibration, SHAP | `Healthcare_Claim_LightGBM_Ablation_Without_ClaimCategory.ipynb` |
| [`Isolation_Forest_Report.docx`](reports/Isolation_Forest_Report.docx) | [`figures/isolation_forest/`](figures/isolation_forest/) — evaluation curves, SHAP beeswarm / global bar / waterfall | `Healthcare_Claim_IsolationForest_Fraud_Detection.ipynb` |
| [`Autoencoder_Report.docx`](reports/Autoencoder_Report.docx) | [`figures/autoencoder/`](figures/autoencoder/) — evaluation curves, training diagnostics, reconstruction distributions, latent space | `Healthcare_Claim_Autoencoder_Fraud_Detection_FIXED.ipynb` |
| [`ECOD_COPOD_Report.docx`](reports/ECOD_COPOD_Report.docx) | [`figures/ecod_copod/`](figures/ecod_copod/) — evaluation curves | `Healthcare_Claim_ECOD_COPOD_Fraud_Detection.ipynb` |
| [`HDBSCAN_GLOSH_Report.docx`](reports/HDBSCAN_GLOSH_Report.docx) | [`figures/hdbscan_glosh/`](figures/hdbscan_glosh/) — UMAP clusters and GLOSH heatmap | `Healthcare_Claim_HDBSCAN_GLOSH_Fraud_Detection.ipynb` |
| [`Microservice_Architecture_and_Model_Report.docx`](reports/Microservice_Architecture_and_Model_Report.docx) | text only | — |

[`figures/lightgbm/`](figures/lightgbm/) holds the calibration and SHAP plots for the original
(leaky) LightGBM run, kept as evidence for the leakage comparison; no current report embeds them.

---

## Data and schema

Raw openIMIS exports are **not** tracked — the dataset is roughly 6.6 GB. Place the CSV tables in
[`data/`](data/); [`data/README.md`](data/README.md) lists the expected filenames and record counts
(`TblClaim.csv`, `TblClaimServices.csv`, `TblHF.csv`, `TblICDCodes.csv`, and the rest).

The relational catalog is checked in:

- [`schemas/full_schema_details.json`](schemas/full_schema_details.json) — 316 columns with types,
  missingness, and sample values across 13 tables.
- [`schemas/table_summary.json`](schemas/table_summary.json) — row counts and schema dimensions.

---

## Reproducing the research

```bash
jupyter lab            # notebooks/ resolves data/ and models/ automatically
```

Notebooks write their artifacts to `models/<model_family>/` and read from `data/`. Autoencoder
evaluation figures are regenerated with:

```bash
python microservice/backend/scripts/run_autoencoder_eval_viz.py
```

which writes into `figures/autoencoder/`.

---

## License

Released under the [MIT License](LICENSE). Developed and maintained by the **Data and Design Lab**.
