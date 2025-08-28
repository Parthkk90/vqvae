# VQ-VAE Image Compression

This directory contains scripts to compress and decompress images using a Vector Quantized-Variational Autoencoder (VQ-VAE) model.

## Structure

- `model.py`: Contains the PyTorch definitions for the VQ-VAE model, including Encoder, Decoder, and the quantization layer.
- `huffman.py`: Implements the Huffman coding algorithm for lossless compression of the quantized indices.
- `compression.py`: The main script to compress an image.
- `decompression.py`: The main script to decompress a file back into an image.
- `requirements.txt`: A list of Python dependencies.

## How to use

### 1. Setup

First, install the required Python packages:

```bash
pip install -r requirements.txt
```

### 2. Train the Model

This compression script requires a pre-trained VQ-VAE model. A training script (`train.py`) is available in the root of this repository. Run it to generate the `vqvae_model.pth` file.

```bash
# From the root directory of the vqvae project
python train.py
```

This will create `vqvae_model.pth` in the root directory.

### 3. Compress an Image

Place an image you want to compress (e.g., `test_image.png`) in this `compression` directory. Then run the compression script:

```bash
python compression.py
```

This will load `test_image.png`, use `../vqvae_model.pth` to encode it, and create a compressed file named `encoded.json`. You can change the input image and model path inside `compression.py`.

### 4. Decompress an Image

To decompress `encoded.json`, run the decompression script:

```bash
python decompression.py
```

This will read `encoded.json`, use `../vqvae_model.pth` to decode it, and create the reconstructed image `reconstructed_image.png`. You can change the file paths inside `decompression.py`.