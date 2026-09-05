import nbformat as nbf
import os

nb = nbf.v4.new_notebook()
nb['cells'] = []

def add_md(content):
    nb['cells'].append(nbf.v4.new_markdown_cell(content))

def add_code(content):
    nb['cells'].append(nbf.v4.new_code_cell(content))

# ================= SECTION 1: INTRODUCTION =================
add_md("""# Healthcare Claim Fraud & Rejection Detection using Deep Autoencoders
### Cameroon openIMIS Platform — FULL DATASET (14.24 MILLION CLAIMS) GPU-Accelerated Unsupervised Anomaly Detection

---

## 1. Introduction & Theoretical Methodology

### Complete Multi-Table Relational Dataset Integration
This production pipeline ingests and joins across the entire openIMIS relational database:
1. **`TblClaim.csv`**: **14,242,741 total claims** (100% complete transaction ledger).
2. **`TblClaimServices.csv`**: **15,774,762 line-item procedures** aggregated per claim (`FE_ServiceCount`, `FE_ServiceTotalAsked`).
3. **`TblHF.csv`**: **2,512 health facilities** mapped by care level classification (`FE_HFLevel`).

### How and Which Data Features the Autoencoder Uses to Learn
An **Autoencoder** is a self-supervised deep neural network composed of two primary components:
1. **Encoder ($f_{\\theta}$)**: Compresses high-dimensional claim feature vectors $X \\in \\mathbb{R}^d$ into a low-dimensional bottleneck latent representation $z \\in \\mathbb{R}^k$ ($k \\ll d$).
2. **Decoder ($g_{\\phi}$)**: Reconstructs the original feature vector $\\hat{X} = g_{\\phi}(z) \\in \\mathbb{R}^d$ from the latent code $z$.

$$\\min_{\\theta, \\phi} \\mathcal{L}_{MSE}(X, \\hat{X}) = \\frac{1}{d} \\sum_{i=1}^d (x_i - \\hat{x}_i)^2$$

### Learning Normal Healthcare Claim Behavior
- **Training Strategy**: The Autoencoder is trained **exclusively on Accepted/Normal claims** ($70\\%$ of the full dataset = ~9.7 Million claims).
- **Fraud/Rejection Score**: The **Reconstruction Error (MSE Loss)** serves directly as the Anomaly / Fraud Score:
  - **Accepted Claims**: The model learns standard clinical relationships and billing patterns $\\rightarrow$ **Low Reconstruction Error**.
  - **Rejected/Fraudulent Claims**: Diverge from standard billing norms $\\rightarrow$ **High Reconstruction Error**.

### 13 Multi-Table Engineered Feature Inputs
1. **`FE_Claimed`**: Total financial amount requested by health facility (XAF).
2. **`FE_Approved`**: Financial amount approved by openIMIS (XAF).
3. **`FE_Claimed_Minus_Approved`**: Financial discrepancy / overbilling margin (XAF).
4. **`FE_Claimed_Ratio`**: Ratio of approved to claimed amounts ($Approved / Claimed$).
5. **`FE_LengthOfStay`**: Hospitalization duration in days ($DateTo - DateFrom$).
6. **`FE_SubmissionDelay`**: Claim submission delay in days ($DateClaimed - DateTo$).
7. **`FE_Hfid_Freq`**: Target frequency encoding of Health Facility ID (`Hfid`).
8. **`FE_Icdid_Freq`**: Target frequency encoding of ICD-10 Diagnosis code (`Icdid`).
9. **`FE_CareType`**: Encoded care delivery type (Inpatient vs Outpatient).
10. **`FE_VisitType`**: Encoded visit modality (Emergency, Routine, Referral).
11. **`FE_ServiceCount`**: Total number of line-item procedures billed (Joined from `TblClaimServices.csv`).
12. **`FE_ServiceTotalAsked`**: Sum of itemized procedure prices (Joined from `TblClaimServices.csv`).
13. **`FE_HFLevel`**: Facility care level classification (Joined from `TblHF.csv`).

---
""")

# ================= SECTION 2: ENVIRONMENT & GPU SETUP =================
add_md("## 2. Environment Setup & GPU Hardware Verification")
add_code("""import os
import sys
import gc
import numpy as np
import pandas as pd
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import TensorDataset, DataLoader
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.preprocessing import StandardScaler
from sklearn.metrics import (roc_auc_score, average_precision_score, 
                             precision_recall_curve, roc_curve, 
                             confusion_matrix, classification_report)
from sklearn.decomposition import PCA
import joblib

# Set random seed for reproducibility
SEED = 42
torch.manual_seed(SEED)
np.random.seed(SEED)

# Verify GPU Hardware Acceleration (NVIDIA GeForce RTX 2060)
device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
print("==================================================")
print(f"PyTorch Version: {torch.__version__}")
print(f"Execution Device: {device}")
if device.type == 'cuda':
    print(f"GPU Model: {torch.cuda.get_device_name(0)}")
    print(f"CUDA Capability: {torch.cuda.get_device_capability(0)}")
    print(f"Total VRAM: {torch.cuda.get_device_properties(0).total_memory / (1024**3):.2f} GB")
print("==================================================")
""")

# ================= SECTION 3: MULTI-TABLE DATA LOADING (FULL 14.24M) =================
add_md("## 3. Full Multi-Table Data Ingestion (14,242,741 Total Claims)")
add_code("""# Data Directory
data_dir = os.path.join("..", "data") if os.path.exists(os.path.join("..", "data")) else "data"
claim_file = os.path.join(data_dir, "TblClaim.csv")
services_file = os.path.join(data_dir, "TblClaimServices.csv")
hf_file = os.path.join(data_dir, "TblHF.csv")

# 1. Load Line-Item Aggregates from TblClaimServices.csv (15.77M rows)
print("Ingesting and aggregating ALL 15.77 Million rows from TblClaimServices.csv...")
df_services = pd.read_csv(services_file, usecols=['ClaimID', 'PriceAsked'], low_memory=False)
df_services['PriceAsked'] = pd.to_numeric(df_services['PriceAsked'], errors='coerce').fillna(0.0).clip(0.0, 1e7)
srv_agg = df_services.groupby('ClaimID').agg(
    FE_ServiceCount=('PriceAsked', 'count'),
    FE_ServiceTotalAsked=('PriceAsked', 'sum')
).reset_index()

del df_services
gc.collect()
print(f"Aggregated service features generated for {len(srv_agg):,} unique claims.")

# 2. Load Health Facility Metadata (TblHF.csv)
if os.path.exists(hf_file):
    print("Ingesting TblHF.csv (Facility metadata)...")
    df_hf = pd.read_csv(hf_file, usecols=['HfID', 'HFLevel'], low_memory=False)
else:
    df_hf = None

# 3. Load Primary Claims (FULL 14.24 Million Claims - Chunked Execution for Memory Safety)
print("Ingesting FULL 14,242,741 claims from TblClaim.csv...")
chunk_list = []
chunk_size = 2000000

for chunk_i, df_chunk in enumerate(pd.read_csv(claim_file, chunksize=chunk_size, low_memory=False)):
    print(f"Processing Chunk {chunk_i+1} ({len(df_chunk):,} claims)...")
    
    # Target Definition: 1 = Rejected, 0 = Accepted
    df_chunk['Target_Rejected'] = (df_chunk['ClaimStatus'] == 1).astype(int)
    df_chunk['RejectionCode_Clean'] = df_chunk['RejectionReason'].fillna(0).astype(str).str.replace('.0', '', regex=False)
    
    # Join Health Facility Level
    if df_hf is not None:
        df_chunk = df_chunk.merge(df_hf, left_on='Hfid', right_on='HfID', how='left')
        df_chunk['FE_HFLevel'] = pd.to_numeric(df_chunk['HFLevel'], errors='coerce').fillna(0.0).clip(0.0, 100.0)
    else:
        df_chunk['FE_HFLevel'] = 0.0

    # Join Claim Services Aggregates
    df_chunk = df_chunk.merge(srv_agg, on='ClaimID', how='left')
    df_chunk['FE_ServiceCount'] = pd.to_numeric(df_chunk['FE_ServiceCount'], errors='coerce').fillna(1.0).clip(0.0, 1000.0)
    df_chunk['FE_ServiceTotalAsked'] = pd.to_numeric(df_chunk['FE_ServiceTotalAsked'], errors='coerce').fillna(0.0).clip(0.0, 1e7)
    
    # Financial Features
    claimed_num = pd.to_numeric(df_chunk['Claimed'], errors='coerce').fillna(0.0).clip(0.0, 1e7)
    approved_num = pd.to_numeric(df_chunk['Approved'], errors='coerce').fillna(0.0).clip(0.0, 1e7)

    df_chunk['FE_Claimed'] = claimed_num
    df_chunk['FE_Approved'] = approved_num
    df_chunk['FE_Claimed_Minus_Approved'] = (claimed_num - approved_num).clip(0.0, 1e7)
    ratio_arr = np.where(claimed_num > 0, approved_num / claimed_num, 1.0)
    df_chunk['FE_Claimed_Ratio'] = np.nan_to_num(ratio_arr, nan=1.0, posinf=1.0, neginf=0.0).clip(0.0, 10.0)

    # Temporal Features
    d_from = pd.to_datetime(df_chunk['DateFrom'], errors='coerce')
    d_to = pd.to_datetime(df_chunk['DateTo'], errors='coerce')
    d_claimed = pd.to_datetime(df_chunk['DateClaimed'], errors='coerce')

    df_chunk['FE_LengthOfStay'] = (d_to - d_from).dt.days.fillna(1.0).clip(0.0, 365.0)
    df_chunk['FE_SubmissionDelay'] = (d_claimed - d_to).dt.days.fillna(0.0).clip(0.0, 365.0)

    # Categorical Numeric Features
    df_chunk['FE_Hfid'] = pd.to_numeric(df_chunk['Hfid'], errors='coerce').fillna(0.0)
    df_chunk['FE_Icdid'] = pd.to_numeric(df_chunk['Icdid'], errors='coerce').fillna(0.0)
    df_chunk['FE_CareType'] = pd.to_numeric(df_chunk['CareType'], errors='coerce').fillna(0.0)
    df_chunk['FE_VisitType'] = pd.to_numeric(df_chunk['VisitType'], errors='coerce').fillna(0.0)
    
    keep_cols = [
        'FE_Claimed', 'FE_Approved', 'FE_Claimed_Minus_Approved', 'FE_Claimed_Ratio',
        'FE_LengthOfStay', 'FE_SubmissionDelay', 'FE_Hfid', 'FE_Icdid',
        'FE_CareType', 'FE_VisitType', 'FE_ServiceCount', 'FE_ServiceTotalAsked', 'FE_HFLevel',
        'Target_Rejected', 'RejectionCode_Clean', 'Hfid'
    ]
    chunk_list.append(df_chunk[keep_cols])

df_full = pd.concat(chunk_list, ignore_index=True)
del chunk_list, srv_agg
gc.collect()

print(f"Full Dataset Successfully Loaded: {len(df_full):,} claims!")

# Frequency Encodings on Full Dataset
df_full['FE_Hfid_Freq'] = df_full['Hfid'].map(df_full['Hfid'].value_counts(normalize=True)).fillna(0.0)
df_full['FE_Icdid_Freq'] = df_full['FE_Icdid'].map(df_full['FE_Icdid'].value_counts(normalize=True)).fillna(0.0)

feature_cols = [
    'FE_Claimed', 'FE_Approved', 'FE_Claimed_Minus_Approved', 'FE_Claimed_Ratio',
    'FE_LengthOfStay', 'FE_SubmissionDelay', 'FE_Hfid_Freq', 'FE_Icdid_Freq',
    'FE_CareType', 'FE_VisitType', 'FE_ServiceCount', 'FE_ServiceTotalAsked', 'FE_HFLevel'
]

X_df = df_full[feature_cols].apply(pd.to_numeric, errors='coerce').fillna(0.0)
X_all = X_df.values.astype(np.float32)
X_all = np.nan_to_num(X_all, nan=0.0, posinf=1e5, neginf=-1e5)

y_all = df_full['Target_Rejected'].values
rejection_codes_all = df_full['RejectionCode_Clean'].values
hfids_all = df_full['Hfid'].values

del df_full, X_df
gc.collect()

valid_mask = ~np.isnan(X_all).any(axis=1)
X_all, y_all = X_all[valid_mask], y_all[valid_mask]
rejection_codes_all, hfids_all = rejection_codes_all[valid_mask], hfids_all[valid_mask]
""")

# ================= SECTION 4: 70/15/15 TRAIN/VAL/TEST SPLIT =================
add_md("""## 4. Train / Validation / Test Split (70% / 15% / 15%)
- **Train Set (70%)**: Contains **ONLY Accepted claims ($y=0$)** (~9.7 Million claims) so the Autoencoder learns normal behavior without contamination.
- **Validation Set (15%)**: Contains a mix of Accepted and Rejected claims (~2.1 Million claims) for hyperparameter tuning and threshold selection.
- **Test Set (15%)**: Contains a mix of Accepted and Rejected claims (~2.1 Million claims) for final unbiased performance evaluation.
- **Data Scaling**: `StandardScaler` is fitted **EXCLUSIVELY on the Training set** to avoid data leakage.
""")

add_code("""accepted_idx = np.where(y_all == 0)[0]
rejected_idx = np.where(y_all == 1)[0]

np.random.shuffle(accepted_idx)
np.random.shuffle(rejected_idx)

n_total = len(X_all)
n_train = int(n_total * 0.70)

train_idx = accepted_idx[:n_train]
remaining_accepted = accepted_idx[n_train:]

n_val_rej = int(len(rejected_idx) * 0.50)
n_val_acc = int(len(remaining_accepted) * 0.50)

val_idx = np.concatenate([remaining_accepted[:n_val_acc], rejected_idx[:n_val_rej]])
test_idx = np.concatenate([remaining_accepted[n_val_acc:], rejected_idx[n_val_rej:]])

np.random.shuffle(val_idx)
np.random.shuffle(test_idx)

scaler = StandardScaler()
X_train = scaler.fit_transform(X_all[train_idx])
X_val = scaler.transform(X_all[val_idx])
X_test = scaler.transform(X_all[test_idx])

# Clip scaled values for numerical stability
X_train = np.clip(X_train, -10.0, 10.0)
X_val = np.clip(X_val, -10.0, 10.0)
X_test = np.clip(X_test, -10.0, 10.0)

y_train, y_val, y_test = y_all[train_idx], y_all[val_idx], y_all[test_idx]
rej_val, rej_test = rejection_codes_all[val_idx], rejection_codes_all[test_idx]
hfid_val, hfid_test = hfids_all[val_idx], hfids_all[test_idx]

del X_all, y_all, rejection_codes_all, hfids_all
gc.collect()

print(f"FULL DATASET SPLIT COMPLETE:")
print(f"  - Train Set (Accepted Only): {len(X_train):,} samples (70.0%)")
print(f"  - Validation Set (Mixed): {len(X_val):,} samples (15.0%) | Rejection Rate: {y_val.mean()*100:.2f}%")
print(f"  - Test Set (Mixed): {len(X_test):,} samples (15.0%) | Rejection Rate: {y_test.mean()*100:.2f}%")

# Save fitted scaler to model/ directory
model_dir = os.path.join("..", "model") if os.path.exists(os.path.join("..", "model")) else "model"
os.makedirs(model_dir, exist_ok=True)
joblib.dump(scaler, os.path.join(model_dir, "scaler.pkl"))
""")

# ================= SECTION 5: MODEL ARCHITECTURE =================
add_md("## 5. Autoencoder Architecture Definition (PyTorch)")
add_code("""class HealthcareClaimAutoencoder(nn.Module):
    def __init__(self, input_dim: int, latent_dim: int = 8, dropout_rate: float = 0.1):
        super(HealthcareClaimAutoencoder, self).__init__()
        
        h1 = max(32, input_dim // 2)
        h2 = max(16, h1 // 2)
        
        self.encoder = nn.Sequential(
            nn.Linear(input_dim, h1),
            nn.BatchNorm1d(h1),
            nn.LeakyReLU(0.2),
            nn.Dropout(dropout_rate),
            
            nn.Linear(h1, h2),
            nn.BatchNorm1d(h2),
            nn.LeakyReLU(0.2),
            
            nn.Linear(h2, latent_dim),
            nn.LeakyReLU(0.2)
        )
        
        self.decoder = nn.Sequential(
            nn.Linear(latent_dim, h2),
            nn.BatchNorm1d(h2),
            nn.LeakyReLU(0.2),
            nn.Dropout(dropout_rate),
            
            nn.Linear(h2, h1),
            nn.BatchNorm1d(h1),
            nn.LeakyReLU(0.2),
            
            nn.Linear(h1, input_dim)
        )
        
    def forward(self, x: torch.Tensor) -> torch.Tensor:
        latent = self.encoder(x)
        reconstruction = self.decoder(latent)
        return reconstruction

input_dim = X_train.shape[1]
model = HealthcareClaimAutoencoder(input_dim=input_dim, latent_dim=8).to(device)
print(model)
""")

# ================= SECTION 6: GPU TRAINING =================
add_md("## 6. GPU Model Training on ~9.7 Million Training Samples")
add_code("""# Create PyTorch DataLoaders (Optimized batch_size=8192 for fast GPU throughput)
batch_size = 8192
train_loader = DataLoader(TensorDataset(torch.tensor(X_train, dtype=torch.float32)), batch_size=batch_size, shuffle=True)
val_loader = DataLoader(TensorDataset(torch.tensor(X_val, dtype=torch.float32)), batch_size=batch_size, shuffle=False)

criterion = nn.MSELoss()
optimizer = optim.Adam(model.parameters(), lr=0.001, weight_decay=1e-5)
scheduler = optim.lr_scheduler.ReduceLROnPlateau(optimizer, mode='min', factor=0.5, patience=2)

epochs = 15
best_val_loss = float('inf')
patience, patience_counter = 4, 0
history = {'train_loss': [], 'val_loss': []}

model_save_path = os.path.join(model_dir, "autoencoder_best.pth")

print("Starting Full Dataset GPU Training...")
for epoch in range(1, epochs + 1):
    model.train()
    train_sum = 0.0
    for (x_b,) in train_loader:
        x_b = x_b.to(device)
        optimizer.zero_grad()
        recon = model(x_b)
        loss = criterion(recon, x_b)
        loss.backward()
        optimizer.step()
        train_sum += loss.item() * len(x_b)
        
    t_loss = train_sum / len(X_train)
    
    model.eval()
    val_sum = 0.0
    with torch.no_grad():
        for (x_b,) in val_loader:
            x_b = x_b.to(device)
            recon = model(x_b)
            loss = criterion(recon, x_b)
            val_sum += loss.item() * len(x_b)
            
    v_loss = val_sum / len(X_val)
    
    history['train_loss'].append(t_loss)
    history['val_loss'].append(v_loss)
    scheduler.step(v_loss)
    
    print(f"Epoch {epoch:02d}/{epochs:02d} | Train MSE: {t_loss:.6f} | Val MSE: {v_loss:.6f}")
        
    if v_loss < best_val_loss:
        best_val_loss = v_loss
        patience_counter = 0
        torch.save(model.state_dict(), model_save_path)
    else:
        patience_counter += 1
        if patience_counter >= patience:
            print(f"Early stopping at epoch {epoch}! Best Val Loss: {best_val_loss:.6f}")
            break

# Load best checkpoint
model.load_state_dict(torch.load(model_save_path, weights_only=True))
print("Loaded best trained model checkpoint.")
""")

# ================= SECTION 7: HYPERPARAMETER EXPERIMENTS =================
add_md("## 7. Hyperparameter Experiments & Bottleneck Analysis")
add_code("""# Evaluate impact of latent space dimensions
latent_dims = [4, 8, 16]
exp_results = {}

for ld in latent_dims:
    m_exp = HealthcareClaimAutoencoder(input_dim=input_dim, latent_dim=ld).to(device)
    opt_exp = optim.Adam(m_exp.parameters(), lr=0.001)
    
    for _ in range(2):
        m_exp.train()
        for (x_b,) in train_loader:
            x_b = x_b.to(device)
            opt_exp.zero_grad()
            l = criterion(m_exp(x_b), x_b)
            l.backward()
            opt_exp.step()
            
    m_exp.eval()
    with torch.no_grad():
        v_mse = criterion(m_exp(torch.tensor(X_val[:50000], dtype=torch.float32).to(device)), 
                          torch.tensor(X_val[:50000], dtype=torch.float32).to(device)).item()
    exp_results[f'Latent_Dim_{ld}'] = v_mse
    print(f"Latent Dim {ld:02d} -> Val MSE: {v_mse:.6f}")
""")

# ================= SECTION 8: RECONSTRUCTION ERROR ANALYSIS =================
add_md("## 8. Reconstruction Error Analysis & Statistics")
add_code("""def compute_mse_scores(model, X_arr):
    model.eval()
    errors = []
    with torch.no_grad():
        for i in range(0, len(X_arr), 16384):
            batch_x = torch.tensor(X_arr[i:i+16384], dtype=torch.float32).to(device)
            recon = model(batch_x)
            mse = torch.mean((batch_x - recon) ** 2, dim=1).cpu().numpy()
            errors.append(mse)
    return np.concatenate(errors)

test_errors = compute_mse_scores(model, X_test)

acc_errors = test_errors[y_test == 0]
rej_errors = test_errors[y_test == 1]

print("==================================================")
print("RECONSTRUCTION ERROR STATISTICS (FULL TEST SET)")
print("==================================================")
print(f"ACCEPTED CLAIMS (n={len(acc_errors):,}):")
print(f"  Mean   : {np.mean(acc_errors):.6f}")
print(f"  Median : {np.median(acc_errors):.6f}")
print(f"  Std    : {np.std(acc_errors):.6f}")
print("")
print(f"REJECTED CLAIMS (n={len(rej_errors):,}):")
print(f"  Mean   : {np.mean(rej_errors):.6f}")
print(f"  Median : {np.median(rej_errors):.6f}")
print(f"  Std    : {np.std(rej_errors):.6f}")
print("==================================================")
""")

# ================= SECTION 9: THRESHOLD SELECTION =================
add_md("## 9. Threshold Selection (F1-Score Maximization)")
add_code("""# Evaluate candidate thresholds on Validation set
val_errors = compute_mse_scores(model, X_val)

percentiles = np.linspace(85, 99.9, 100)
candidate_thresholds = np.percentile(val_errors[y_val == 0], percentiles)

best_f1, optimal_threshold = 0.0, candidate_thresholds[0]

for th in candidate_thresholds:
    preds = (val_errors > th).astype(int)
    cm = confusion_matrix(y_val, preds)
    if cm[1,1] + cm[0,1] > 0 and cm[1,1] + cm[1,0] > 0:
        prec = cm[1,1] / (cm[1,1] + cm[0,1])
        rec = cm[1,1] / (cm[1,1] + cm[1,0])
        if prec + rec > 0:
            f1 = 2 * (prec * rec) / (prec + rec)
            if f1 > best_f1:
                best_f1 = f1
                optimal_threshold = th

print(f"Optimal Anomaly Threshold (F1-Maximization): {optimal_threshold:.6f}")
print(f"Validation F1-Score at Threshold: {best_f1:.4f}")
""")

# ================= SECTION 10: PERFORMANCE EVALUATION =================
add_md("## 10. Performance Evaluation (ROC, PR-AUC, F1, Recall, Precision)")
add_code("""roc_auc = roc_auc_score(y_test, test_errors)
pr_auc = average_precision_score(y_test, test_errors)

final_preds = (test_errors > optimal_threshold).astype(int)
cm_test = confusion_matrix(y_test, final_preds)

print("==================================================")
print("FULL TEST SET EVALUATION METRICS (2.13 MILLION CLAIMS)")
print("==================================================")
print(f"ROC-AUC Score         : {roc_auc:.4f}")
print(f"Average Precision (PR-AUC) : {pr_auc:.4f}")
print("")
print("Classification Report (at Optimal Threshold):")
print(classification_report(y_test, final_preds, target_names=['Accepted', 'Rejected']))
print("")
print("Confusion Matrix:")
print(pd.DataFrame(cm_test, index=['Actual Accepted', 'Actual Rejected'], columns=['Pred Accepted', 'Pred Rejected']))
print("==================================================")
""")

# ================= SECTION 11: VISUALIZATIONS =================
add_md("## 11. Visualizations & Error Analysis")
add_code("""fig, axes = plt.subplots(2, 2, figsize=(14, 10))

# 1. Training & Validation Loss Curve
axes[0, 0].plot(history['train_loss'], label='Train Loss (Accepted Only)', color='#1F77B4', lw=2)
axes[0, 0].plot(history['val_loss'], label='Val Loss (Mixed)', color='#FF7F0E', lw=2)
axes[0, 0].set_title('Training & Validation MSE Loss', fontsize=12, fontweight='bold')
axes[0, 0].set_xlabel('Epoch')
axes[0, 0].set_ylabel('MSE Loss')
axes[0, 0].legend()
axes[0, 0].grid(True, alpha=0.3)

# 2. Reconstruction Error Histogram (Accepted vs Rejected)
sns.histplot(acc_errors[:50000], bins=50, color='green', label='Accepted (Low Error)', ax=axes[0, 1], kde=True, stat='density', alpha=0.4)
sns.histplot(rej_errors[:50000], bins=50, color='red', label='Rejected (High Error)', ax=axes[0, 1], kde=True, stat='density', alpha=0.4)
axes[0, 1].axvline(optimal_threshold, color='black', linestyle='--', label=f'Threshold ({optimal_threshold:.3f})')
axes[0, 1].set_title('Reconstruction Error Distribution', fontsize=12, fontweight='bold')
axes[0, 1].set_xlabel('Reconstruction MSE Loss')
axes[0, 1].legend()
axes[0, 1].grid(True, alpha=0.3)

# 3. ROC Curve
fpr, tpr, _ = roc_curve(y_test[:100000], test_errors[:100000])
axes[1, 0].plot(fpr, tpr, color='darkorange', lw=2, label=f'ROC curve (AUC = {roc_auc:.3f})')
axes[1, 0].plot([0, 1], [0, 1], color='navy', lw=2, linestyle='--')
axes[1, 0].set_title('Receiver Operating Characteristic (ROC)', fontsize=12, fontweight='bold')
axes[1, 0].set_xlabel('False Positive Rate')
axes[1, 0].set_ylabel('True Positive Rate')
axes[1, 0].legend(loc="lower right")
axes[1, 0].grid(True, alpha=0.3)

# 4. Precision-Recall Curve
prec_pts, rec_pts, _ = precision_recall_curve(y_test[:100000], test_errors[:100000])
axes[1, 1].plot(rec_pts, prec_pts, color='purple', lw=2, label=f'PR curve (AP = {pr_auc:.3f})')
axes[1, 1].set_title('Precision-Recall Curve (PR-AUC)', fontsize=12, fontweight='bold')
axes[1, 1].set_xlabel('Recall')
axes[1, 1].set_ylabel('Precision')
axes[1, 1].legend(loc="lower left")
axes[1, 1].grid(True, alpha=0.3)

plt.tight_layout()
plt.show()
""")

# ================= SECTION 12: ERROR BY REJECTION CODE =================
add_md("""## 12. Error Breakdown by Specific Rejection Code
Comparing Autoencoder Reconstruction Error distributions across specific rejection reason codes:
- **Accepted**: Normal baseline claims
- **Code 3**: Inactive Policy / Coverage Expiry
- **Code 4**: Demographic Mismatch (Age/Sex mismatch)
- **Code 5**: Frequency Constraint Violation
- **Code -1**: Manual Counselor / Auditor Rejection
- **Code 7**: Invalid Insurance ID
""")

add_code("""target_codes = ['Accepted', '3', '4', '5', '-1', '7']
code_error_data = []

for code in target_codes:
    if code == 'Accepted':
        mask = (y_test == 0)
        selected_errors = test_errors[mask][:20000]
    else:
        mask = (rej_test == code)
        selected_errors = test_errors[mask]
    if len(selected_errors) > 0:
        for err in selected_errors:
            code_error_data.append({'Rejection_Code': f"Code {code}" if code != 'Accepted' else 'Accepted', 'MSE_Error': err})

df_code_errors = pd.DataFrame(code_error_data)

plt.figure(figsize=(12, 6))
sns.boxplot(data=df_code_errors, x='Rejection_Code', y='MSE_Error', hue='Rejection_Code', palette='Set2', legend=False)
plt.axhline(optimal_threshold, color='red', linestyle='--', label=f'Anomaly Threshold ({optimal_threshold:.3f})')
plt.title('Reconstruction Error Breakdown across Specific Rejection Codes', fontsize=14, fontweight='bold')
plt.xlabel('Rejection Code Category')
plt.ylabel('Reconstruction Error (MSE)')
plt.legend()
plt.grid(True, alpha=0.3)
plt.show()
""")

# ================= SECTION 13: LATENT SPACE VISUALIZATION =================
add_md("## 13. Latent Space Bottleneck Visualization (PCA)")
add_code("""# Extract 8-dimensional latent representations from the encoder
sample_sub_idx = np.random.choice(len(X_test), size=min(20000, len(X_test)), replace=False)
model.eval()
with torch.no_grad():
    latent_z = model.encoder(torch.tensor(X_test[sample_sub_idx], dtype=torch.float32).to(device)).cpu().numpy()

# Apply 2D PCA projection
pca = PCA(n_components=2)
z_2d = pca.fit_transform(latent_z)

plt.figure(figsize=(10, 7))
scatter = plt.scatter(z_2d[:, 0], z_2d[:, 1], c=y_test[sample_sub_idx], cmap='coolwarm', alpha=0.5, s=15)
plt.colorbar(scatter, label='Claim Status (0=Accepted, 1=Rejected)')
plt.title('2D PCA Projection of Autoencoder Latent Bottleneck Embeddings', fontsize=14, fontweight='bold')
plt.xlabel(f'PCA Component 1 ({pca.explained_variance_ratio_[0]*100:.1f}% var)')
plt.ylabel(f'PCA Component 2 ({pca.explained_variance_ratio_[1]*100:.1f}% var)')
plt.grid(True, alpha=0.3)
plt.show()
""")

# ================= SECTION 14: FACILITY-LEVEL ANOMALY ANALYSIS =================
add_md("## 14. Facility-Level Anomaly Analysis (Hfid Aggregation)")
add_code("""df_facility = pd.DataFrame({
    'Hfid': hfid_test,
    'Reconstruction_Error': test_errors,
    'Is_Rejected': y_test
})

facility_stats = df_facility.groupby('Hfid').agg(
    Total_Claims=('Reconstruction_Error', 'count'),
    Avg_Reconstruction_Error=('Reconstruction_Error', 'mean'),
    High_Risk_Anomalies=('Reconstruction_Error', lambda x: (x > optimal_threshold).sum()),
    Actual_Rejections=('Is_Rejected', 'sum')
).reset_index()

facility_stats['Anomaly_Rate_%'] = (facility_stats['High_Risk_Anomalies'] / facility_stats['Total_Claims']) * 100
facility_stats = facility_stats.sort_values(by='Avg_Reconstruction_Error', ascending=False)

print("TOP 10 HIGH-RISK ANOMALOUS HEALTH FACILITIES (Hfid):")
print(facility_stats.head(10).to_string(index=False))
""")

# ================= SECTION 15: MODEL EXPORT =================
add_md("## 15. Model Artifact Export & Deployment Verification")
add_code(f"""print("Saving final Autoencoder deployment artifacts...")
export_dir = model_dir
torch.save(model.state_dict(), os.path.join(export_dir, "autoencoder_best.pth"))

config = {{
    'input_dim': input_dim,
    'latent_dim': 8,
    'optimal_threshold': float(optimal_threshold),
    'roc_auc': float(roc_auc),
    'pr_auc': float(pr_auc),
    'feature_cols': feature_cols
}}

import json
with open(os.path.join(export_dir, "autoencoder_config.json"), 'w') as f:
    json.dump(config, f, indent=4)

print(f"Artifacts successfully saved to {{export_dir}}:")
print("  - autoencoder_best.pth (PyTorch Model Weights)")
print("  - scaler.pkl (Fitted StandardScaler)")
print("  - autoencoder_config.json (Model Config & Optimal Threshold)")
""")

# Save notebook
script_dir = os.path.dirname(os.path.abspath(__file__))
notebook_path = os.path.abspath(os.path.join(script_dir, "..", "notebooks", "Healthcare_Claim_Autoencoder_Fraud_Detection.ipynb"))
with open(notebook_path, 'w', encoding='utf-8') as f:
    nbf.write(nb, f)

print(f"Jupyter Notebook successfully written to: {notebook_path}")
