# Cameroon Healthcare Claim Fraud & Rejection Detection (Cameroon 2.0)

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![PyTorch](https://img.shields.io/badge/PyTorch-2.0+-ee4c2c.svg)](https://pytorch.org/)
[![LightGBM](https://img.shields.io/badge/LightGBM-4.0+-brightgreen.svg)](https://lightgbm.readthedocs.io/)
[![Platform](https://img.shields.io/badge/Platform-openIMIS-007ACC.svg)](https://openimis.org/)
[![Organization](https://img.shields.io/badge/Lab-Data%20and%20Design%20Lab-orange.svg)](https://github.com/Data-and-Design-Lab)

Production-grade machine learning, deep learning, and unsupervised anomaly detection framework for healthcare claims adjudication, fraud detection, and rejection risk prediction across the Cameroon **openIMIS** insurance database (**14,242,741 claim transactions**, **15.77M itemized services**).

Developed by the **Data and Design Lab**.

---

## 📌 Executive Summary

Healthcare reimbursement systems in developing economies frequently suffer from administrative delays, billing inconsistencies, unbundling, and potential fraudulent activity. This repository houses an end-to-end analytical and machine learning framework that evaluates over 14 million openIMIS claims to:

1. **Detect Fraud & Anomalous Claims Unsupervised**: Using deep bottleneck Autoencoders and robust non-parametric statistical density estimators (ECOD, COPOD, Isolation Forest, HDBSCAN).
2. **Predict Claim Rejection Pre-Adjudication**: Using calibrated LightGBM gradient boosted decision trees with isotonic regression to guide adjudication workflows.
3. **Audit High-Risk Providers & Facilities**: Providing multi-level facility drift analysis, target-encoded risk metrics, and line-item financial variance analysis.
4. **Generate Exhaustive Technical Reports**: Automated generation of professional DOCX reports detailing schema quality, statistical data dictionary, and multi-model benchmark results.

---

## 🏗️ Repository Architecture

```text
Cameroon-2.0/
├── data/                               # Dataset directory (raw CSVs gitignored)
│   ├── README.md                       # Data dictionary & CSV layout instructions
│   └── .gitkeep
├── figures/                            # High-resolution evaluation charts & plots
│   ├── autoencoder.png
│   ├── lightgbgm reliability.png
│   └── lightgbm output.png
├── model/                              # PyTorch Deep Autoencoder artifacts
│   ├── MODEL_CARD.md                   # Model architecture, training & metric card
│   ├── autoencoder_best.pth            # Trained PyTorch model weights
│   ├── autoencoder_config.json         # Optimal thresholds, parameters & features
│   ├── encoders.pkl                    # Preprocessing & categorical encoders
│   └── scaler.pkl                      # Fitted StandardScaler
├── model_ecod/                         # ECOD (Empirical Cumulative Distribution) artifacts
│   ├── MODEL_CARD.md
│   ├── ecod_config.json
│   ├── ecod_reference.npz              # Empirical reference distributions
│   ├── encoders.pkl
│   └── scaler.pkl
├── model_iforest/                      # Isolation Forest outlier detection artifacts
│   ├── MODEL_CARD.md
│   ├── isolation_forest.pkl            # Serialized tree ensemble
│   ├── isolation_forest_config.json
│   ├── encoders.pkl
│   └── scaler.pkl
├── model_lightgbm/                     # LightGBM rejection predictor artifacts
│   ├── MODEL_CARD.md
│   ├── lightgbm_model.txt              # Calibrated LightGBM model
│   ├── isotonic_calibrator.pkl         # Isotonic probability calibrator
│   ├── lightgbm_config.json
│   └── feature_schema.pkl
├── notebooks/                          # Production Jupyter research notebooks
│   ├── Healthcare_Claim_Autoencoder_Fraud_Detection_FIXED.ipynb
│   ├── Healthcare_Claim_ECOD_COPOD_Fraud_Detection.ipynb
│   ├── Healthcare_Claim_HDBSCAN_GLOSH_Fraud_Detection.ipynb
│   ├── Healthcare_Claim_IsolationForest_Fraud_Detection.ipynb
│   └── Healthcare_Claim_LightGBM_Rejection_Prediction.ipynb
├── reports/                            # Technical reports & automated document generators
│   ├── figures/                        # High-resolution latent space and ROC curves
│   ├── Autoencoder_Results_Report.docx
│   ├── Data_Quality_and_Fraud_Detection_Report.docx
│   ├── Fraud_Detection_Machine_Learning_Models_Report.docx
│   ├── Independent Technical Review.docx
│   ├── Main Tables and Relationships used.docx
│   ├── generate_autoencoder_report.py  # Automated report generator for Autoencoder
│   ├── generate_data_quality_report.py # Automated report generator for OpenIMIS data quality
│   └── generate_ml_report.py          # Automated report generator for ML benchmarks
├── schemas/                            # Relational schema dictionaries & table stats
│   ├── full_schema_details.json        # 316-column itemized data dictionary
│   └── table_summary.json              # Row counts, column counts, and sizes
├── scripts/                            # Utility & evaluation execution scripts
│   ├── build_autoencoder_notebook.py   # Script to re-generate autoencoder notebook
│   └── run_autoencoder_eval_viz.py     # Evaluation, UMAP/t-SNE & figure generator
├── src/                                # Modular core Python package
│   ├── __init__.py
│   ├── dataset.py                      # Streaming & sampled dataset preprocessing
│   ├── evaluate.py                     # ROC-AUC, PR-AUC & threshold optimization
│   ├── model.py                        # PyTorch Autoencoder network architecture
│   └── train.py                        # GPU-accelerated PyTorch training pipeline
├── .gitignore                          # Strict ignore rules for large data & venvs
├── requirements.txt                    # Project dependency specification
└── README.md                           # Master project documentation
```

---

## 🤖 Models & Methodologies

| Model Family | Paradigm | Primary Objective | Key Metric | Artifact Directory |
| :--- | :--- | :--- | :--- | :--- |
| **Deep Autoencoder** | Unsupervised Deep Learning (PyTorch) | Learns normal claims manifold; reconstruction MSE flags abnormal billing & unbundling | PR-AUC / ROC-AUC, MSE Error | [`model/`](model/) |
| **LightGBM** | Supervised GBDT | Predicts claim rejection probability before submission; probability calibration | ROC-AUC, Brier Score | [`model_lightgbm/`](model_lightgbm/) |
| **Isolation Forest** | Unsupervised Ensemble | Isolates multi-attribute billing anomalies via random partitioning trees | Anomaly Score, Precision@K | [`model_iforest/`](model_iforest/) |
| **ECOD / COPOD** | Non-parametric Statistical | Tail probability outlier detection via empirical cumulative distributions | CDF Outlier Score | [`model_ecod/`](model_ecod/) |
| **HDBSCAN / GLOSH** | Density-based Clustering | Identifies spatial-billing noise clusters and localized fraud schemes | GLOSH Outlier Score | [`notebooks/`](notebooks/) |

---

## 🚀 Getting Started

### 1. Prerequisites
- Python 3.10 or higher
- NVIDIA CUDA-capable GPU recommended for deep autoencoder training (e.g., RTX 2060+, RTX 3080, V100, A100)

### 2. Clone the Repository
```bash
git clone https://github.com/Data-and-Design-Lab/Cameroon-2.0.git
cd Cameroon-2.0
```

### 3. Create & Activate Virtual Environment
```bash
# On Linux / macOS
python3 -m venv .venv
source .venv/bin/activate

# On Windows (PowerShell)
python -m venv .venv
.venv\Scripts\Activate.ps1
```

### 4. Install Dependencies
```bash
pip install --upgrade pip
pip install -r requirements.txt
```

### 5. Setup Data Files
Place the raw openIMIS CSV export files into the [`data/`](data/) directory. See [`data/README.md`](data/README.md) for table schemas and expected filenames (`TblClaim.csv`, `TblClaimServices.csv`, `TblHF.csv`, etc.).

---

## 📊 Running Pipelines & Reports

### Training the Autoencoder via Python Module
```python
from src.dataset import load_and_preprocess_claim_data
from src.train import train_autoencoder

data = load_and_preprocess_claim_data(data_dir="data", sample_size=500000)
model, history = train_autoencoder(
    X_train=data['X_train'],
    X_val=data['X_val'],
    latent_dim=8,
    epochs=25,
    save_path="model/autoencoder_best.pth"
)
```

### Running Model Evaluation & Latent Space Projections
```bash
python scripts/run_autoencoder_eval_viz.py
```
*Generates high-dimensional PCA, t-SNE, and UMAP latent space projections into `reports/figures/`.*

### Rebuilding Technical Word (DOCX) Reports
```bash
# Generate Comprehensive openIMIS Data Quality Report
python reports/generate_data_quality_report.py

# Generate Machine Learning Model Comparison Report
python reports/generate_ml_report.py

# Generate Deep Autoencoder Full Technical Report
python reports/generate_autoencoder_report.py
```

---

## 📜 Schema & Data Dictionary

The repository includes a comprehensive 316-column relational data catalog:
- [`schemas/full_schema_details.json`](schemas/full_schema_details.json): Column types, missingness ratios, and sample values across all 13 openIMIS tables.
- [`schemas/table_summary.json`](schemas/table_summary.json): Table-level row counts and schema dimensions.

---

## 🏛️ Organization & License

This project is developed and maintained by the **Data and Design Lab**.
Released under the [MIT License](LICENSE) (or organizational license where applicable).
