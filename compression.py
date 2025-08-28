import torch
from torchvision import transforms
from PIL import Image
import json
import os

from model import VQVAE
from huffman import build_freq_map, build_huffman_tree, build_huffman_codes, huffman_encoding

def compress_image(image_path, model_path, output_path):
    """
    Compresses an image using a trained VQ-VAE model and Huffman coding.
    """
    if not os.path.exists(image_path):
        print(f"Error: Image file not found at {image_path}")
        return

    if not os.path.exists(model_path):
        print(f"Error: Model file not found at {model_path}")
        print("Please train the model first or provide a pre-trained model.")
        return

    # --- Model and Device Setup ---
    device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
    model = VQVAE(in_channels=3, hidden_channels=128, embedding_dim=64, num_embeddings=512, commitment_cost=0.25).to(device)
    model.load_state_dict(torch.load(model_path, map_location=device))
    model.eval()

    # --- Image Preprocessing ---
    transform = transforms.Compose([
        transforms.Resize((128, 128)),
        transforms.ToTensor(),
        transforms.Normalize((0.5, 0.5, 0.5), (0.5, 0.5, 0.5))
    ])
    image = Image.open(image_path).convert("RGB")
    image_tensor = transform(image).unsqueeze(0).to(device)
    
    # --- Encoding ---
    with torch.no_grad():
        indices = model.encode(image_tensor)
    
    indices_list = indices.cpu().numpy().flatten().tolist()
    image_shape = list(indices.shape) # [1, H, W]

    # --- Huffman Coding ---
    freq_map = build_freq_map(indices_list)
    huffman_tree = build_huffman_tree(freq_map)
    huffman_codes = build_huffman_codes(huffman_tree)
    encoded_data = huffman_encoding(indices_list, huffman_codes)

    # --- Save Compressed Data ---
    compressed_data = {
        'freq_map': freq_map,
        'image_shape': image_shape,
        'encoded_string': encoded_data
    }

    with open(output_path, 'w') as f:
        json.dump(compressed_data, f)

    print(f"Image compressed successfully and saved to {output_path}")

if __name__ == '__main__':
    image_to_compress = 'test_image.png'
    model_weights_path = '../vqvae_model.pth' 
    compressed_output_path = 'encoded.json'
    
    compress_image(image_to_compress, model_weights_path, compressed_output_path)