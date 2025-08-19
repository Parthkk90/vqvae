from __future__ import annotations
from cryptography.hazmat.primitives.kdf.scrypt import Scrypt
from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from os import urandom
from .utils import b64e, b64d

# Scrypt parameters chosen for Windows-friendly defaults (adjustable)
SCRYPT_N = 2 ** 14
SCRYPT_R = 8
SCRYPT_P = 1
KEY_LEN = 32  # 256-bit
NONCE_LEN = 12


def derive_key(passphrase: str, salt: bytes) -> bytes:
    kdf = Scrypt(salt=salt, length=KEY_LEN, n=SCRYPT_N, r=SCRYPT_R, p=SCRYPT_P)
    return kdf.derive(passphrase.encode("utf-8"))


def encrypt(plaintext: bytes, passphrase: str) -> tuple[bytes, dict]:
    salt = urandom(16)
    key = derive_key(passphrase, salt)
    nonce = urandom(NONCE_LEN)
    aead = AESGCM(key)
    ciphertext = aead.encrypt(nonce, plaintext, associated_data=None)
    header_crypto = {
        "kdf": {"name": "scrypt", "salt_b64": b64e(salt), "n": 2 ** 14, "r": 8, "p": 1},
        "cipher": {"name": "aes-256-gcm", "nonce_b64": b64e(nonce), "tag_len": 16},
    }
    return ciphertext, header_crypto


def decrypt(ciphertext: bytes, passphrase: str, salt_b64: str, nonce_b64: str) -> bytes:
    salt = b64d(salt_b64)
    nonce = b64d(nonce_b64)
    key = derive_key(passphrase, salt)
    aead = AESGCM(key)
    return aead.decrypt(nonce, ciphertext, associated_data=None)