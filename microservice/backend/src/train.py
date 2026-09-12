import os
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import DataLoader, TensorDataset
import numpy as np
from src.model import HealthcareClaimAutoencoder

def train_autoencoder(
    X_train: np.ndarray,
    X_val: np.ndarray,
    latent_dim: int = 8,
    epochs: int = 50,
    batch_size: int = 1024,
    learning_rate: float = 0.001,
    patience: int = 7,
    save_path: str = os.path.join("models", "model_autoencoder", "autoencoder_best.pth")
):
    """
    Trains the PyTorch Autoencoder using GPU (NVIDIA GeForce RTX 2060).
    Saves the best model checkpoint based on Validation Reconstruction Loss (MSE).
    """
    # Detect GPU (RTX 2060)
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    print(f"==================================================")
    print(f"Autoencoder Training Execution Device: {device}")
    if device.type == 'cuda':
        print(f"GPU Name: {torch.cuda.get_device_name(0)}")
        print(f"Allocated VRAM: {torch.cuda.memory_allocated(0)/(1024**2):.2f} MB")
    print(f"==================================================")

    # Convert NumPy arrays to PyTorch Tensors
    train_tensor = torch.tensor(X_train, dtype=torch.float32)
    val_tensor = torch.tensor(X_val, dtype=torch.float32)
    
    train_loader = DataLoader(TensorDataset(train_tensor), batch_size=batch_size, shuffle=True)
    val_loader = DataLoader(TensorDataset(val_tensor), batch_size=batch_size, shuffle=False)
    
    input_dim = X_train.shape[1]
    model = HealthcareClaimAutoencoder(input_dim=input_dim, latent_dim=latent_dim).to(device)
    
    criterion = nn.MSELoss()
    optimizer = optim.Adam(model.parameters(), lr=learning_rate, weight_decay=1e-5)
    scheduler = optim.lr_scheduler.ReduceLROnPlateau(optimizer, mode='min', factor=0.5, patience=3, verbose=True)
    
    history = {'train_loss': [], 'val_loss': []}
    best_val_loss = float('inf')
    patience_counter = 0
    
    for epoch in range(1, epochs + 1):
        # Training Phase
        model.train()
        train_loss_sum = 0.0
        for batch in train_loader:
            x_batch = batch[0].to(device)
            optimizer.zero_grad()
            reconstructed = model(x_batch)
            loss = criterion(reconstructed, x_batch)
            loss.backward()
            optimizer.step()
            train_loss_sum += loss.item() * x_batch.size(0)
            
        epoch_train_loss = train_loss_sum / len(train_tensor)
        
        # Validation Phase
        model.eval()
        val_loss_sum = 0.0
        with torch.no_grad():
            for batch in val_loader:
                x_batch = batch[0].to(device)
                reconstructed = model(x_batch)
                loss = criterion(reconstructed, x_batch)
                val_loss_sum += loss.item() * x_batch.size(0)
                
        epoch_val_loss = val_loss_sum / len(val_tensor)
        
        history['train_loss'].append(epoch_train_loss)
        history['val_loss'].append(epoch_val_loss)
        
        scheduler.step(epoch_val_loss)
        
        if epoch % 5 == 0 or epoch == 1:
            print(f"Epoch {epoch:02d}/{epochs:02d} | Train MSE Loss: {epoch_train_loss:.6f} | Val MSE Loss: {epoch_val_loss:.6f}")
            
        # Checkpoint saving & Early Stopping
        if epoch_val_loss < best_val_loss:
            best_val_loss = epoch_val_loss
            patience_counter = 0
            os.makedirs(os.path.dirname(save_path), exist_ok=True)
            torch.save(model.state_dict(), save_path)
        else:
            patience_counter += 1
            if patience_counter >= patience:
                print(f"Early stopping triggered at Epoch {epoch}! Best Val MSE: {best_val_loss:.6f}")
                break
                
    print(f"Model successfully saved to {save_path}")
    return model, history
