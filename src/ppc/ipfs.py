from __future__ import annotations
import os, requests

try:
    import ipfshttpclient
    _HAVE_IPFS_HTTP_CLIENT = True
except ImportError:
    _HAVE_IPFS_HTTP_CLIENT = False

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


def gateway_url(cid: str, service: str | None = None) -> str:
    if service == "pinata":
        return f"https://gateway.pinata.cloud/ipfs/{cid}"
    # Default to a good public gateway like w3s.link
    return f"https://w3s.link/ipfs/{cid}"

def upload_daemon(file_path: str) -> str:
    """Uploads a file to a local IPFS daemon."""
    if not _HAVE_IPFS_HTTP_CLIENT:
        raise ImportError("Please install 'ipfshttpclient' to use the local IPFS daemon.")
    try:
        client = ipfshttpclient.connect()  # connects to local IPFS daemon
        res = client.add(file_path)
        return res['Hash']  # CID
    except ipfshttpclient.exceptions.ConnectionError as e:
        raise ConnectionError("Could not connect to IPFS daemon. Is it running?") from e

def download_daemon(cid: str, output_path: str):
    """Downloads a file from a local IPFS daemon, handling file paths correctly."""
    if not _HAVE_IPFS_HTTP_CLIENT:
        raise ImportError("Please install 'ipfshttpclient' to use the local IPFS daemon.")
    try:
        client = ipfshttpclient.connect()
        target_dir = os.path.dirname(output_path) or "."
        os.makedirs(target_dir, exist_ok=True)
        client.get(cid, target=target_dir)
        downloaded_file_path = os.path.join(target_dir, cid)
        os.rename(downloaded_file_path, output_path)
    except ipfshttpclient.exceptions.ConnectionError as e:
        raise ConnectionError("Could not connect to IPFS daemon. Is it running?") from e
    except ipfshttpclient.exceptions.Error as e:
        raise FileNotFoundError(f"Could not find CID '{cid}' on the network.") from e
