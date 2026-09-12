import numpy as np
import pandas as pd
import torch
from sklearn.metrics import roc_auc_score, average_precision_score, precision_recall_fscore_support, confusion_matrix

def compute_reconstruction_error(model, X: np.ndarray, batch_size: int = 2048) -> np.ndarray:
    """Computes MSE Reconstruction Error on GPU for every sample."""
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    model.to(device)
    model.eval()
    
    errors = []
    with torch.no_grad():
        for i in range(0, len(X), batch_size):
            batch_x = torch.tensor(X[i:i+batch_size], dtype=torch.float32).to(device)
            recon = model(batch_x)
            mse = torch.mean((batch_x - recon) ** 2, dim=1).cpu().numpy()
            errors.append(mse)
            
    return np.concatenate(errors)

def evaluate_autoencoder_performance(y_true: np.ndarray, errors: np.ndarray, rejection_codes: np.ndarray = None):
    """
    Comprehensive evaluation of Autoencoder anomaly detection.
    Treats Reconstruction Error as the Fraud/Rejection Score.
    Calculates ROC-AUC, PR-AUC, Confusion Matrix, F1, Precision, Recall,
    and Reconstruction Error Statistics for Accepted vs Rejected claims.
    """
    # 1. Compute ROC-AUC and Average Precision (PR-AUC)
    roc_auc = roc_auc_score(y_true, errors)
    pr_auc = average_precision_score(y_true, errors)
    
    # 2. Compute Reconstruction Error Statistics
    accepted_errors = errors[y_true == 0]
    rejected_errors = errors[y_true == 1]
    
    stats = {
        'Accepted': {
            'mean': float(np.mean(accepted_errors)),
            'median': float(np.median(accepted_errors)),
            'std': float(np.std(accepted_errors))
        },
        'Rejected': {
            'mean': float(np.mean(rejected_errors)),
            'median': float(np.median(rejected_errors)),
            'std': float(np.std(rejected_errors))
        }
    }
    
    # 3. Optimal Threshold Selection based on maximum F1-Score
    thresholds = np.percentile(accepted_errors, np.linspace(80, 99.9, 100))
    best_f1, best_thresh = 0.0, float(np.median(accepted_errors) * 3)
    best_prec, best_rec = 0.0, 0.0
    
    for t in thresholds:
        preds = (errors > t).astype(int)
        prec, rec, f1, _ = precision_recall_fscore_support(y_true, preds, average='binary', zero_division=0)
        if f1 > best_f1:
            best_f1 = f1
            best_thresh = t
            best_prec = prec
            best_rec = rec
            
    best_preds = (errors > best_thresh).astype(int)
    cm = confusion_matrix(y_true, best_preds)
    
    # 4. Error Breakdown by Specific Rejection Code
    code_breakdown = {}
    if rejection_codes is not None:
        target_codes = ['Accepted', '3', '4', '5', '-1', '7']
        for code in target_codes:
            if code == 'Accepted':
                mask = (y_true == 0)
            else:
                mask = (rejection_codes == code)
            if np.sum(mask) > 0:
                code_errors = errors[mask]
                code_breakdown[code] = {
                    'count': int(np.sum(mask)),
                    'mean_error': float(np.mean(code_errors)),
                    'median_error': float(np.median(code_errors)),
                    'std_error': float(np.std(code_errors))
                }
                
    results = {
        'ROC_AUC': float(roc_auc),
        'PR_AUC': float(pr_auc),
        'Best_Threshold': float(best_thresh),
        'F1_Score': float(best_f1),
        'Precision': float(best_prec),
        'Recall': float(best_rec),
        'Confusion_Matrix': cm.tolist(),
        'Error_Stats': stats,
        'Code_Breakdown': code_breakdown
    }
    
    return results
