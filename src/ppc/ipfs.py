from __future__ import annotations
import os, requests

WEB3_ENDPOINT = "https://api.web3.storage/upload"
PINATA_ENDPOINT = "https://api.pinata.cloud/pinning/pinFileToIPFS"


def upload_web3(data: bytes, filename: str, token: str) -> str:
    headers = {"Authorization": f"Bearer {token}"}
    files = {"file": (filename, data)}
    r = requests.post(WEB3_ENDPOINT, headers=headers, files=files, timeout=120)
    r.raise_for_status()
    # web3.storage returns JSON with cid under .cid (or .cid in v5)
    resp = r.json()
    cid = resp.get("cid") or resp.get("value", {}).get("cid")
    if not cid:
        raise RuntimeError(f"Unexpected response: {resp}")
    return cid


def upload_pinata(data: bytes, filename: str, jwt: str) -> str:
    headers = {"Authorization": f"Bearer {jwt}"}
    files = {"file": (filename, data)}
    r = requests.post(PINATA_ENDPOINT, headers=headers, files=files, timeout=120)
    r.raise_for_status()
    resp = r.json()
    return resp["IpfsHash"]


def gateway_url(cid: str) -> str:
    return f"https://w3s.link/ipfs/{cid}"