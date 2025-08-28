import torch
import torch.nn as nn

class VectorQuantizer(nn.Module):
    def __init__(self, num_embeddings, embedding_dim, commitment_cost):
        super(VectorQuantizer, self).__init__()
        self.embedding_dim = embedding_dim
        self.num_embeddings = num_embeddings
        self.commitment_cost = commitment_cost
        self.embedding = nn.Embedding(self.num_embeddings, self.embedding_dim)
        self.embedding.weight.data.uniform_(-1/self.num_embeddings, 1/self.num_embeddings)

    def forward(self, x):
        # x is (B, H, W, C)
        # Flatten input
        flat_input = x.view(-1, self.embedding_dim)
        # Calculate distances
        distances = (torch.sum(flat_input**2, dim=1, keepdim=True) 
                    + torch.sum(self.embedding.weight**2, dim=1)
                    - 2 * torch.matmul(flat_input, self.embedding.weight.t()))
        # Encoding
        encoding_indices = torch.argmin(distances, dim=1).unsqueeze(1)
        encodings = torch.zeros(encoding_indices.shape[0], self.num_embeddings, device=x.device)
        encodings.scatter_(1, encoding_indices, 1)
        # Quantize and unflatten
        quantized = torch.matmul(encodings, self.embedding.weight).view(x.shape)
        # Loss
        e_latent_loss = nn.functional.mse_loss(quantized.detach(), x)
        q_latent_loss = nn.functional.mse_loss(quantized, x.detach())
        loss = q_latent_loss + self.commitment_cost * e_latent_loss
        
        # Straight-through estimator
        quantized = x + (quantized - x).detach()
        
        # Reshape encoding_indices to be (B, H, W)
        return quantized, loss, encoding_indices.view(x.shape[0], x.shape[1], x.shape[2])

class Encoder(nn.Module):
    def __init__(self, in_channels, hidden_channels, out_channels):
        super(Encoder, self).__init__()
        self.conv1 = nn.Conv2d(in_channels, hidden_channels, kernel_size=4, stride=2, padding=1)
        self.conv2 = nn.Conv2d(hidden_channels, out_channels, kernel_size=4, stride=2, padding=1)
        self.relu = nn.ReLU()

    def forward(self, x):
        x = self.relu(self.conv1(x))
        x = self.conv2(x)
        return x

class Decoder(nn.Module):
    def __init__(self, in_channels, hidden_channels, out_channels):
        super(Decoder, self).__init__()
        self.conv1 = nn.ConvTranspose2d(in_channels, hidden_channels, kernel_size=4, stride=2, padding=1)
        self.conv2 = nn.ConvTranspose2d(hidden_channels, out_channels, kernel_size=4, stride=2, padding=1)
        self.relu = nn.ReLU()
        self.tanh = nn.Tanh() # Use Tanh for output normalized to [-1, 1]

    def forward(self, x):
        x = self.relu(self.conv1(x))
        x = self.tanh(self.conv2(x))
        return x

class VQVAE(nn.Module):
    def __init__(self, in_channels, hidden_channels, embedding_dim, num_embeddings, commitment_cost):
        super(VQVAE, self).__init__()
        self.encoder = Encoder(in_channels, hidden_channels, embedding_dim)
        self.vq_layer = VectorQuantizer(num_embeddings, embedding_dim, commitment_cost)
        self.decoder = Decoder(embedding_dim, hidden_channels, in_channels)

    def forward(self, x):
        z = self.encoder(x)
        z = z.permute(0, 2, 3, 1).contiguous()
        quantized, vq_loss, _ = self.vq_layer(z)
        quantized_for_decoder = quantized.permute(0, 3, 1, 2).contiguous()
        return self.decoder(quantized_for_decoder), vq_loss

    def encode(self, x):
        z = self.encoder(x)
        z = z.permute(0, 2, 3, 1).contiguous()
        _, _, indices = self.vq_layer(z)
        return indices

    def decode_from_indices(self, indices):
        quantized = self.vq_layer.embedding(indices)
        quantized = quantized.permute(0, 3, 1, 2).contiguous()
        return self.decoder(quantized)