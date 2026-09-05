import os
import gc
import json
import joblib
import numpy as np
import pandas as pd
import torch
import torch.nn as nn
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.decomposition import PCA
from sklearn.manifold import TSNE
import umap
from sklearn.metrics import (roc_auc_score, average_precision_score, 
                             precision_recall_curve, roc_curve, 
                             confusion_matrix, classification_report)

# Set seeds & plot styling
SEED = 42
np.random.seed(SEED)
torch.manual_seed(SEED)

sns.set_theme(style="whitegrid")
plt.rcParams.update({'font.sans-serif': 'DejaVu Sans', 'font.family': 'sans-serif'})

ROOT_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
data_dir = os.path.join(ROOT_DIR, "data")
model_dir = os.path.join(ROOT_DIR, "model")
img_dir = os.path.join(ROOT_DIR, "reports", "figures")
os.makedirs(img_dir, exist_ok=True)

# 1. Load Model Config and Scaler
config = json.load(open(os.path.join(model_dir, "autoencoder_config.json")))
scaler = joblib.load(os.path.join(model_dir, "scaler.pkl"))
feature_cols = config['feature_cols']

# 2. Define Model Class
class HealthcareClaimAutoencoder(nn.Module):
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
        return self.decoder(latent)

device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
model = HealthcareClaimAutoencoder(input_dim=config['input_dim'], latent_dim=config['latent_dim']).to(device)
model.load_state_dict(torch.load(os.path.join(model_dir, "autoencoder_best.pth"), map_location=device, weights_only=True))
model.eval()

print("Ingesting sample from full dataset for evaluation & visual generation...")
# Load a sample chunk (500,000 claims) for evaluation and visualization
claim_file = os.path.join(data_dir, "TblClaim.csv")
services_file = os.path.join(data_dir, "TblClaimServices.csv")
hf_file = os.path.join(data_dir, "TblHF.csv")

# Load Services Aggregates
df_services = pd.read_csv(services_file, usecols=['ClaimID', 'PriceAsked'], nrows=3000000, low_memory=False)
df_services['PriceAsked'] = pd.to_numeric(df_services['PriceAsked'], errors='coerce').fillna(0.0).clip(0.0, 1e7)
srv_agg = df_services.groupby('ClaimID').agg(
    FE_ServiceCount=('PriceAsked', 'count'),
    FE_ServiceTotalAsked=('PriceAsked', 'sum')
).reset_index()
del df_services; gc.collect()

# Load Facility Metadata
df_hf = pd.read_csv(hf_file, usecols=['HfID', 'HFLevel'], low_memory=False) if os.path.exists(hf_file) else None

# Load Claims Sample
df_sample = pd.read_csv(claim_file, nrows=500000, low_memory=False)
df_sample['Target_Rejected'] = (df_sample['ClaimStatus'] == 1).astype(int)
df_sample['RejectionCode_Clean'] = df_sample['RejectionReason'].fillna(0).astype(str).str.replace('.0', '', regex=False)

if df_hf is not None:
    df_sample = df_sample.merge(df_hf, left_on='Hfid', right_on='HfID', how='left')
    df_sample['FE_HFLevel'] = pd.to_numeric(df_sample['HFLevel'], errors='coerce').fillna(0.0).clip(0.0, 100.0)
else:
    df_sample['FE_HFLevel'] = 0.0

df_sample = df_sample.merge(srv_agg, on='ClaimID', how='left')
df_sample['FE_ServiceCount'] = pd.to_numeric(df_sample['FE_ServiceCount'], errors='coerce').fillna(1.0).clip(0.0, 1000.0)
df_sample['FE_ServiceTotalAsked'] = pd.to_numeric(df_sample['FE_ServiceTotalAsked'], errors='coerce').fillna(0.0).clip(0.0, 1e7)

claimed_num = pd.to_numeric(df_sample['Claimed'], errors='coerce').fillna(0.0).clip(0.0, 1e7)
approved_num = pd.to_numeric(df_sample['Approved'], errors='coerce').fillna(0.0).clip(0.0, 1e7)

df_sample['FE_Claimed'] = claimed_num
df_sample['FE_Approved'] = approved_num
df_sample['FE_Claimed_Minus_Approved'] = (claimed_num - approved_num).clip(0.0, 1e7)
ratio_arr = np.where(claimed_num > 0, approved_num / claimed_num, 1.0)
df_sample['FE_Claimed_Ratio'] = np.nan_to_num(ratio_arr, nan=1.0, posinf=1.0, neginf=0.0).clip(0.0, 10.0)

d_from = pd.to_datetime(df_sample['DateFrom'], errors='coerce')
d_to = pd.to_datetime(df_sample['DateTo'], errors='coerce')
d_claimed = pd.to_datetime(df_sample['DateClaimed'], errors='coerce')

df_sample['FE_LengthOfStay'] = (d_to - d_from).dt.days.fillna(1.0).clip(0.0, 365.0)
df_sample['FE_SubmissionDelay'] = (d_claimed - d_to).dt.days.fillna(0.0).clip(0.0, 365.0)

df_sample['FE_Hfid'] = pd.to_numeric(df_sample['Hfid'], errors='coerce').fillna(0.0)
df_sample['FE_Icdid'] = pd.to_numeric(df_sample['Icdid'], errors='coerce').fillna(0.0)
df_sample['FE_CareType'] = pd.to_numeric(df_sample['CareType'], errors='coerce').fillna(0.0)
df_sample['FE_VisitType'] = pd.to_numeric(df_sample['VisitType'], errors='coerce').fillna(0.0)

df_sample['FE_Hfid_Freq'] = df_sample['Hfid'].map(df_sample['Hfid'].value_counts(normalize=True)).fillna(0.0)
df_sample['FE_Icdid_Freq'] = df_sample['FE_Icdid'].map(df_sample['FE_Icdid'].value_counts(normalize=True)).fillna(0.0)

X_df = df_sample[feature_cols].apply(pd.to_numeric, errors='coerce').fillna(0.0)
X_raw = X_df.values.astype(np.float32)
X_raw = np.nan_to_num(X_raw, nan=0.0, posinf=1e5, neginf=-1e5)
X_scaled = scaler.transform(X_raw)
X_scaled = np.clip(X_scaled, -10.0, 10.0)

y_true = df_sample['Target_Rejected'].values
rejection_codes = df_sample['RejectionCode_Clean'].values
hfids = df_sample['Hfid'].values
claim_ids = df_sample['ClaimID'].values

# Calculate Reconstruction Errors and Feature-Level Attributions
model.eval()
with torch.no_grad():
    tensor_x = torch.tensor(X_scaled, dtype=torch.float32).to(device)
    tensor_recon = model(tensor_x)
    feat_sq_errors = (tensor_x - tensor_recon).pow(2).cpu().numpy()
    mse_scores = np.mean(feat_sq_errors, axis=1)

print(f"Evaluated {len(mse_scores):,} sample claims.")

# -------------------------------------------------------------
# 1. COMPUTE PRECISION@K AND RANKING METRICS
# -------------------------------------------------------------
sorted_idx = np.argsort(mse_scores)[::-1]
y_sorted = y_true[sorted_idx]

prec_k_results = {}
for top_pct in [0.1, 0.5, 1.0, 2.0, 5.0, 10.0]:
    k = int(len(y_true) * (top_pct / 100.0))
    prec_k = np.mean(y_sorted[:k])
    prec_k_results[f"Top_{top_pct}%"] = {
        "k_count": k,
        "precision_at_k": float(prec_k),
        "enrichment_factor": float(prec_k / np.mean(y_true))
    }

print("Precision@K Results:")
for k, v in prec_k_results.items():
    print(f"  - {k} (k={v['k_count']:,}): Precision = {v['precision_at_k']*100:.2f}% | Enrichment = {v['enrichment_factor']:.2f}x")

# Save Precision@K to JSON
with open(os.path.join(model_dir, "precision_at_k_metrics.json"), 'w') as f:
    json.dump(prec_k_results, f, indent=4)

# -------------------------------------------------------------
# 2. GENERATE FIGURE 1: RECONSTRUCTION ERROR DISTRIBUTION & ROC/PR CURVES
# -------------------------------------------------------------
fig, axes = plt.subplots(2, 2, figsize=(14, 10))

# Subplot A: Reconstruction Error Distribution (Log Scale KDE)
acc_mask = (y_true == 0)
rej_mask = (y_true == 1)

sns.histplot(mse_scores[acc_mask][:50000], bins=50, color='#2ECC71', label='Accepted (Normal Baseline)', ax=axes[0, 0], kde=True, stat='density', alpha=0.4, log_scale=True)
sns.histplot(mse_scores[rej_mask][:50000], bins=50, color='#E74C3C', label='Rejected (Anomalies)', ax=axes[0, 0], kde=True, stat='density', alpha=0.4, log_scale=True)
axes[0, 0].axvline(config['optimal_threshold'], color='black', linestyle='--', lw=2, label=f"Threshold ({config['optimal_threshold']:.5f})")
axes[0, 0].set_title("A. Reconstruction Error Distribution (Log Scale)", fontsize=12, fontweight='bold', pad=10)
axes[0, 0].set_xlabel("Reconstruction Error (MSE Loss)")
axes[0, 0].set_ylabel("Density")
axes[0, 0].legend(loc='upper right', frameon=True)

# Subplot B: Precision@K Curve
k_percents = [0.1, 0.5, 1.0, 2.0, 5.0, 10.0, 20.0, 50.0]
p_at_k = [np.mean(y_sorted[:int(len(y_true) * (p / 100.0))]) * 100 for p in k_percents]
axes[0, 1].plot(k_percents, p_at_k, marker='o', color='#2980B9', lw=2.5, markersize=7)
axes[0, 1].axhline(np.mean(y_true)*100, color='gray', linestyle=':', label=f"Baseline Rejection Rate ({np.mean(y_true)*100:.1f}%)")
axes[0, 1].set_title("B. Precision@K (Audit Queue Prioritization)", fontsize=12, fontweight='bold', pad=10)
axes[0, 1].set_xlabel("Top K% Highest Anomaly Scores Flagged")
axes[0, 1].set_ylabel("Precision (% Actual Rejections Caught)")
axes[0, 1].legend(loc='upper right', frameon=True)

# Subplot C: ROC Curve
roc_auc = roc_auc_score(y_true, mse_scores)
fpr, tpr, _ = roc_curve(y_true, mse_scores)
axes[1, 0].plot(fpr, tpr, color='#E67E22', lw=2.5, label=f"ROC Curve (AUC = {roc_auc:.4f})")
axes[1, 0].plot([0, 1], [0, 1], color='navy', lw=1.5, linestyle='--')
axes[1, 0].set_title("C. Receiver Operating Characteristic (ROC)", fontsize=12, fontweight='bold', pad=10)
axes[1, 0].set_xlabel("False Positive Rate")
axes[1, 0].set_ylabel("True Positive Rate")
axes[1, 0].legend(loc='lower right', frameon=True)

# Subplot D: Precision-Recall Curve
pr_auc = average_precision_score(y_true, mse_scores)
prec_pts, rec_pts, _ = precision_recall_curve(y_true, mse_scores)
axes[1, 1].plot(rec_pts, prec_pts, color='#8E44AD', lw=2.5, label=f"PR Curve (PR-AUC = {pr_auc:.4f})")
axes[1, 1].axhline(np.mean(y_true), color='gray', linestyle=':', label=f"Random Classifier ({np.mean(y_true):.3f})")
axes[1, 1].set_title("D. Precision-Recall Curve", fontsize=12, fontweight='bold', pad=10)
axes[1, 1].set_xlabel("Recall")
axes[1, 1].set_ylabel("Precision")
axes[1, 1].legend(loc='upper right', frameon=True)

plt.tight_layout()
fig_dist_path = os.path.join(img_dir, "fig1_reconstruction_distributions_and_curves.png")
plt.savefig(fig_dist_path, dpi=300, bbox_inches='tight')
plt.close()
print(f"Saved Figure 1 to: {fig_dist_path}")

# -------------------------------------------------------------
# 3. GENERATE FIGURE 2: LATENT-SPACE EMBEDDINGS (PCA, t-SNE, UMAP)
# -------------------------------------------------------------
print("Extracting latent space bottleneck embeddings...")
sub_viz_size = 10000
sub_indices = np.random.choice(len(X_scaled), size=sub_viz_size, replace=False)

with torch.no_grad():
    sub_tensor_x = torch.tensor(X_scaled[sub_indices], dtype=torch.float32).to(device)
    latent_z = model.encoder(sub_tensor_x).cpu().numpy()

sub_y = y_true[sub_indices]
sub_codes = rejection_codes[sub_indices]
sub_hfids = hfids[sub_indices]

print("Computing PCA 2D projections...")
pca_2d = PCA(n_components=2).fit_transform(latent_z)

print("Computing t-SNE 2D projections...")
tsne_2d = TSNE(n_components=2, perplexity=30, random_state=SEED).fit_transform(latent_z)

print("Computing UMAP 2D projections...")
reducer = umap.UMAP(n_components=2, n_neighbors=15, min_dist=0.1, random_state=SEED)
umap_2d = reducer.fit_transform(latent_z)

fig, axes = plt.subplots(3, 3, figsize=(16, 15))

# Row 1: PCA / t-SNE / UMAP colored by Accepted vs Rejected
s1 = axes[0, 0].scatter(pca_2d[:, 0], pca_2d[:, 1], c=sub_y, cmap='coolwarm', alpha=0.5, s=12)
axes[0, 0].set_title("PCA: Claim Status (0=Accepted, 1=Rejected)", fontweight='bold')
fig.colorbar(s1, ax=axes[0, 0])

s2 = axes[0, 1].scatter(tsne_2d[:, 0], tsne_2d[:, 1], c=sub_y, cmap='coolwarm', alpha=0.5, s=12)
axes[0, 1].set_title("t-SNE: Claim Status (0=Accepted, 1=Rejected)", fontweight='bold')
fig.colorbar(s2, ax=axes[0, 1])

s3 = axes[0, 2].scatter(umap_2d[:, 0], umap_2d[:, 1], c=sub_y, cmap='coolwarm', alpha=0.5, s=12)
axes[0, 2].set_title("UMAP: Claim Status (0=Accepted, 1=Rejected)", fontweight='bold')
fig.colorbar(s3, ax=axes[0, 2])

# Row 2: Colored by Top Health Facilities
top_facilities = pd.Series(sub_hfids).value_counts().head(5).index.tolist()
hf_category = [f"Facility {hf}" if hf in top_facilities else "Other Facilities" for hf in sub_hfids]
unique_hfs = list(set(hf_category))
palette_hf = sns.color_palette("Set1", n_colors=len(unique_hfs))
color_map_hf = {hf: palette_hf[i] for i, hf in enumerate(unique_hfs)}
c_list_hf = [color_map_hf[hf] for hf in hf_category]

axes[1, 0].scatter(pca_2d[:, 0], pca_2d[:, 1], c=c_list_hf, alpha=0.5, s=12)
axes[1, 0].set_title("PCA: Facility Cluster Distribution", fontweight='bold')

axes[1, 1].scatter(tsne_2d[:, 0], tsne_2d[:, 1], c=c_list_hf, alpha=0.5, s=12)
axes[1, 1].set_title("t-SNE: Facility Cluster Distribution", fontweight='bold')

axes[1, 2].scatter(umap_2d[:, 0], umap_2d[:, 1], c=c_list_hf, alpha=0.5, s=12)
axes[1, 2].set_title("UMAP: Facility Cluster Distribution", fontweight='bold')

# Row 3: Colored by Specific Rejection Reasons
top_reasons = ['Accepted', '3', '4', '5', '-1', '7']
code_category = [f"Code {c}" if c != 'Accepted' and c in top_reasons else ('Accepted' if c == 'Accepted' else 'Other Rejections') for c in sub_codes]
unique_codes = list(set(code_category))
palette_code = sns.color_palette("tab10", n_colors=len(unique_codes))
color_map_code = {c: palette_code[i] for i, c in enumerate(unique_codes)}
c_list_code = [color_map_code[c] for c in code_category]

axes[2, 0].scatter(pca_2d[:, 0], pca_2d[:, 1], c=c_list_code, alpha=0.5, s=12)
axes[2, 0].set_title("PCA: Rejection Code Substructures", fontweight='bold')

axes[2, 1].scatter(tsne_2d[:, 0], tsne_2d[:, 1], c=c_list_code, alpha=0.5, s=12)
axes[2, 1].set_title("t-SNE: Rejection Code Substructures", fontweight='bold')

axes[2, 2].scatter(umap_2d[:, 0], umap_2d[:, 1], c=c_list_code, alpha=0.5, s=12)
axes[2, 2].set_title("UMAP: Rejection Code Substructures", fontweight='bold')

plt.tight_layout()
fig_latent_path = os.path.join(img_dir, "fig2_latent_space_pca_tsne_umap.png")
plt.savefig(fig_latent_path, dpi=300, bbox_inches='tight')
plt.close()
print(f"Saved Figure 2 to: {fig_latent_path}")

# -------------------------------------------------------------
# 4. FALSE POSITIVE INVESTIGATION (260,489 CLAIMS)
# -------------------------------------------------------------
print("Analyzing False Positives (Accepted Claims Flagged with High MSE)...")
th = config['optimal_threshold']
fp_mask = (y_true == 0) & (mse_scores > th)
tn_mask = (y_true == 0) & (mse_scores <= th)

df_fp = df_sample[fp_mask].copy()
df_tn = df_sample[tn_mask].copy()

df_fp['MSE'] = mse_scores[fp_mask]
df_tn['MSE'] = mse_scores[tn_mask]

fp_analysis = {
    "total_false_positives_sample": int(len(df_fp)),
    "fp_rate_among_accepted": float(len(df_fp) / (len(df_fp) + len(df_tn))),
    "fp_mean_claimed": float(df_fp['FE_Claimed'].mean()),
    "tn_mean_claimed": float(df_tn['FE_Claimed'].mean()),
    "claimed_amount_ratio": float(df_fp['FE_Claimed'].mean() / max(1.0, df_tn['FE_Claimed'].mean())),
    "fp_mean_service_count": float(df_fp['FE_ServiceCount'].mean()),
    "tn_mean_service_count": float(df_tn['FE_ServiceCount'].mean()),
    "fp_mean_submission_delay": float(df_fp['FE_SubmissionDelay'].mean()),
    "tn_mean_submission_delay": float(df_tn['FE_SubmissionDelay'].mean()),
    "top_fp_facilities": df_fp['Hfid'].value_counts().head(5).to_dict()
}

print(f"False Positive Analysis:")
print(f"  - FP Mean Claimed Amount: {fp_analysis['fp_mean_claimed']:,.2f} XAF vs True Normal: {fp_analysis['tn_mean_claimed']:,.2f} XAF ({fp_analysis['claimed_amount_ratio']:.2f}x higher!)")
print(f"  - FP Mean Service Count: {fp_analysis['fp_mean_service_count']:.2f} vs True Normal: {fp_analysis['tn_mean_service_count']:.2f}")
print(f"  - FP Mean Submission Delay: {fp_analysis['fp_mean_submission_delay']:.1f} days vs True Normal: {fp_analysis['tn_mean_submission_delay']:.1f} days")

with open(os.path.join(model_dir, "false_positive_analysis.json"), 'w') as f:
    json.dump(fp_analysis, f, indent=4)

# -------------------------------------------------------------
# 5. FEATURE-LEVEL RECONSTRUCTION ERROR ATTRIBUTION
# -------------------------------------------------------------
print("Extracting feature-level reconstruction error attributions...")
top_fp_idx = np.where(fp_mask)[0][:3]
feature_attribution_cases = []

for idx in top_fp_idx:
    c_id = claim_ids[idx]
    c_mse = mse_scores[idx]
    sq_errs = feat_sq_errors[idx]
    sorted_feat_idx = np.argsort(sq_errs)[::-1]
    
    attr_list = []
    for f_i in sorted_feat_idx[:5]:
        attr_list.append({
            "feature": feature_cols[f_i],
            "sq_error": float(sq_errs[f_i]),
            "raw_value": float(X_raw[idx, f_i])
        })
        
    feature_attribution_cases.append({
        "claim_id": str(c_id),
        "total_mse": float(c_mse),
        "top_contributions": attr_list
    })

with open(os.path.join(model_dir, "feature_attribution_cases.json"), 'w') as f:
    json.dump(feature_attribution_cases, f, indent=4)

print("Evaluation & visualization script finished successfully!")
