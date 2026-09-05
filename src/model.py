import torch
import torch.nn as nn

class HealthcareClaimAutoencoder(nn.Module):
    """
    Deep PyTorch Autoencoder Architecture for Healthcare Claim Fraud Detection.
    Learns low-dimensional latent representation of normal (accepted) claims.
    Anomalous/rejected claims yield high Reconstruction Error (MSE Loss).
    
    GPU Accelerated: Compatible with CUDA (NVIDIA GeForce RTX 2060).
    """
    def __init__(self, input_dim: int, latent_dim: int = 8, dropout_rate: float = 0.1):
        super(HealthcareClaimAutoencoder, self).__init__()
        
        self.input_dim = input_dim
        self.latent_dim = latent_dim
        
        # Calculate hidden layer dimensions dynamically based on input size
        h1 = max(32, input_dim // 2)
        h2 = max(16, h1 // 2)
        
        # Encoder Network
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
        
        # Decoder Network
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
        """Forward pass: encodes input to bottleneck latent space, then reconstructs."""
        latent = self.encoder(x)
        reconstruction = self.decoder(latent)
        return reconstruction
        
    def get_latent_space(self, x: torch.Tensor) -> torch.Tensor:
        """Extract bottleneck latent representation for PCA / t-SNE visualization."""
        self.eval()
        with torch.no_grad():
            return self.encoder(x)
            
    def compute_reconstruction_error(self, x: torch.Tensor) -> torch.Tensor:
        """
        Calculates Sample-wise Mean Squared Error (MSE) Reconstruction Loss.
        Returns 1D Tensor of anomaly/fraud scores per claim.
        """
        self.eval()
        with torch.no_grad():
            reconstructed = self.forward(x)
            # Element-wise squared error averaged over features per row
            mse_per_sample = torch.mean((x - reconstructed) ** 2, dim=1)
            return mse_per_sample
