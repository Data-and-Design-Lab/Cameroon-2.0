import os
import pandas as pd
import numpy as np
import torch
from torch.utils.data import Dataset, DataLoader
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import train_test_split
import joblib

class ClaimDataset(Dataset):
    """PyTorch Dataset wrapper for Healthcare Claim Feature Matrices."""
    def __init__(self, X: np.ndarray, y: np.ndarray = None, rejection_codes: np.ndarray = None, hfids: np.ndarray = None):
        self.X = torch.tensor(X, dtype=torch.float32)
        self.y = torch.tensor(y, dtype=torch.float32) if y is not None else None
        self.rejection_codes = rejection_codes
        self.hfids = hfids

    def __len__(self):
        return len(self.X)

    def __getitem__(self, idx):
        item = {'X': self.X[idx]}
        if self.y is not None:
            item['y'] = self.y[idx]
        return item

def load_and_preprocess_claim_data(data_dir: str, sample_size: int = 500000, random_state: int = 42):
    """
    Ingests and joins openIMIS datasets, performs feature engineering,
    splits into 70% Train (Accepted only), 15% Validation (Mixed), 15% Test (Mixed),
    and fits StandardScaler ONLY on the Train set to prevent data leakage.
    """
    print(f"Ingesting claim data from {data_dir} (Sample size: {sample_size:,})...")
    
    # Load primary datasets
    claim_path = os.path.join(data_dir, 'TblClaim.csv')
    df_claims = pd.read_csv(claim_path, nrows=sample_size, low_memory=False)
    
    # Target definition: Binary Rejection Flag (1 = Rejected, 0 = Accepted / Non-Rejected)
    df_claims['Target_Rejected'] = (df_claims['ClaimStatus'] == 1).astype(int)
    
    # Extract Rejection Code cleanly
    df_claims['RejectionCode_Clean'] = df_claims['RejectionReason'].fillna(0).astype(str).str.replace('.0', '', regex=False)
    
    # Feature Engineering
    # 1. Financial Features
    claimed_num = pd.to_numeric(df_claims['Claimed'], errors='coerce').fillna(0)
    approved_num = pd.to_numeric(df_claims['Approved'], errors='coerce').fillna(0)
    df_claims['FE_Claimed'] = claimed_num
    df_claims['FE_Approved'] = approved_num
    df_claims['FE_Claimed_Minus_Approved'] = (claimed_num - approved_num).clip(lower=0)
    df_claims['FE_Claimed_Ratio'] = np.where(claimed_num > 0, approved_num / claimed_num, 1.0)
    
    # 2. Temporal Features
    d_from = pd.to_datetime(df_claims['DateFrom'], errors='coerce')
    d_to = pd.to_datetime(df_claims['DateTo'], errors='coerce')
    d_claimed = pd.to_datetime(df_claims['DateClaimed'], errors='coerce')
    
    df_claims['FE_LengthOfStay'] = (d_to - d_from).dt.days.fillna(1).clip(lower=0)
    df_claims['FE_SubmissionDelay'] = (d_claimed - d_to).dt.days.fillna(0).clip(lower=0)
    
    # 3. Categorical Encodings (Frequency / Target Frequency)
    df_claims['FE_Hfid_Freq'] = df_claims['Hfid'].map(df_claims['Hfid'].value_counts(normalize=True)).fillna(0)
    df_claims['FE_Icdid_Freq'] = df_claims['Icdid'].map(df_claims['Icdid'].value_counts(normalize=True)).fillna(0)
    df_claims['FE_CareType'] = pd.to_numeric(df_claims['CareType'], errors='coerce').fillna(0)
    df_claims['FE_VisitType'] = pd.to_numeric(df_claims['VisitType'], errors='coerce').fillna(0)
    
    feature_cols = [
        'FE_Claimed', 'FE_Approved', 'FE_Claimed_Minus_Approved', 'FE_Claimed_Ratio',
        'FE_LengthOfStay', 'FE_SubmissionDelay', 'FE_Hfid_Freq', 'FE_Icdid_Freq',
        'FE_CareType', 'FE_VisitType'
    ]
    
    X = df_claims[feature_cols].values
    y = df_claims['Target_Rejected'].values
    rejection_codes = df_claims['RejectionCode_Clean'].values
    hfids = df_claims['Hfid'].values
    
    # Filter valid non-NaN rows
    valid_mask = ~np.isnan(X).any(axis=1)
    X = X[valid_mask]
    y = y[valid_mask]
    rejection_codes = rejection_codes[valid_mask]
    hfids = hfids[valid_mask]
    
    # ================= 70% / 15% / 15% SPLIT LOGIC =================
    # Separate Accepted (y=0) and Rejected (y=1)
    accepted_idx = np.where(y == 0)[0]
    rejected_idx = np.where(y == 1)[0]
    
    # Shuffle indices
    np.random.seed(random_state)
    np.random.shuffle(accepted_idx)
    np.random.shuffle(rejected_idx)
    
    # Train set (70% total size, containing ONLY Accepted claims)
    n_total = len(X)
    n_train = int(n_total * 0.70)
    n_val = int(n_total * 0.15)
    
    train_idx = accepted_idx[:n_train]
    remaining_accepted = accepted_idx[n_train:]
    
    # Validation & Test split from remaining Accepted + Rejected
    n_val_rej = int(len(rejected_idx) * 0.50)
    n_val_acc = int(len(remaining_accepted) * 0.50)
    
    val_idx = np.concatenate([remaining_accepted[:n_val_acc], rejected_idx[:n_val_rej]])
    test_idx = np.concatenate([remaining_accepted[n_val_acc:], rejected_idx[n_val_rej:]])
    
    np.random.shuffle(val_idx)
    np.random.shuffle(test_idx)
    
    # Fit StandardScaler ONLY on Training Set (Accepted claims)
    scaler = StandardScaler()
    X_train = scaler.fit_transform(X[train_idx])
    X_val = scaler.transform(X[val_idx])
    X_test = scaler.transform(X[test_idx])
    
    y_train = y[train_idx]
    y_val = y[val_idx]
    y_test = y[test_idx]
    
    rej_val = rejection_codes[val_idx]
    rej_test = rejection_codes[test_idx]
    
    hfid_val = hfids[val_idx]
    hfid_test = hfids[test_idx]
    
    print(f"Data Split Summary:")
    print(f"  - Train Set (100% Accepted): {len(X_train):,} samples (70.0%)")
    print(f"  - Validation Set: {len(X_val):,} samples (15.0%) | Rejection Rate: {y_val.mean()*100:.2f}%")
    print(f"  - Test Set: {len(X_test):,} samples (15.0%) | Rejection Rate: {y_test.mean()*100:.2f}%")
    print(f"  - Features ({len(feature_cols)}): {feature_cols}")
    
    return {
        'X_train': X_train, 'y_train': y_train,
        'X_val': X_val, 'y_val': y_val, 'rej_val': rej_val, 'hfid_val': hfid_val,
        'X_test': X_test, 'y_test': y_test, 'rej_test': rej_test, 'hfid_test': hfid_test,
        'scaler': scaler, 'feature_cols': feature_cols
    }
