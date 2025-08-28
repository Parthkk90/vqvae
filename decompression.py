import torch
from torchvision.utils import save_image
import json
import os

from model import VQVAE
from huffman import build_huffman_tree, huffman_decoding

def decompress_image(compressed_path, model_path, output_path):
    """
    Decompresses an image from a file using a VQ-VAE model and Huffman codes.
    """
    if not os.path.exists(compressed_path):
        print(f"Error: Compressed file not found at {compressed_path}")
        return

    if not os.path.exists(model_path):
        print(f"Error: Model file not found at {model_path}")
        return

    # --- Load Compressed Data ---
    with open(compressed_path, 'r') as f:
        compressed_data = json.load(f)
    
    freq_map_str_keys = compressed_data['freq_map']
    # JSON saves dict keys as strings, convert them back to integers
    freq_map = {int(k): v for k, v in freq_map_str_keys.items()}
    image_shape = compressed_data['image_shape']
    encoded_data = compressed_data['encoded_string']

    # --- Huffman Decoding ---
    huffman_tree = build_huffman_tree(freq_map)
    decoded_indices_list = huffman_decoding(encoded_data, huffman_tree)

    # --- Model and Device Setup ---
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model = VQVAE(in_channels=3, hidden_channels=128, embedding_dim=64, num_embeddings=512, commitment_cost=0.25).to(device)
    model.load_state_dict(torch.load(model_path, map_location=device))
    model.eval()

    # --- Image Reconstruction ---
    indices_tensor = torch.tensor(decoded_indices_list, dtype=torch.long).view(image_shape).to(device)
    
    with torch.no_grad():
        reconstructed_image = model.decode_from_indices(indices_tensor)

    # --- Save Reconstructed Image ---
    # The output of the model is in [-1, 1], so we denormalize to [0, 1]
    reconstructed_image = (reconstructed_image + 1) / 2
    save_image(reconstructed_image, output_path)
    
    print(f"Image decompressed and saved to {output_path}")

if __name__ == '__main__':
    compressed_file_path = 'encoded.json'
    model_weights_path = '../vqvae_model.pth'
    reconstructed_image_path = 'reconstructed_image.png'
    
    decompress_image(compressed_file_path, model_weights_path, reconstructed_image_path)