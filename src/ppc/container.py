from __future__ import annotations
import io, json, struct
from dataclasses import dataclass

MAGIC = b"PPC1"
VERSION = 1

@dataclass
class Header:
    mime: str
    orig_name: str
    created: str
    kdf: dict
    cipher: dict
    comp: dict
    notes: str | None = None

    def to_json(self) -> bytes:
        return json.dumps(self.__dict__, separators=(",", ":")).encode("utf-8")

    @staticmethod
    def from_json(data: bytes) -> "Header":
        obj = json.loads(data.decode("utf-8"))
        return Header(**obj)


def pack(header: Header, payload: bytes) -> bytes:
    head_json = header.to_json()
    buf = io.BytesIO()
    buf.write(MAGIC)
    buf.write(struct.pack("<B", VERSION))
    buf.write(struct.pack("<I", len(head_json)))
    buf.write(head_json)
    buf.write(payload)
    return buf.getvalue()


def unpack(blob: bytes) -> tuple[Header, bytes]:
    buf = io.BytesIO(blob)
    if buf.read(4) != MAGIC:
        raise ValueError("Not a PPC container")
    ver = struct.unpack("<B", buf.read(1))[0]
    if ver != VERSION:
        raise ValueError(f"Unsupported PPC version: {ver}")
    hlen = struct.unpack("<I", buf.read(4))[0]
    hjson = buf.read(hlen)
    if len(hjson) < hlen:
        raise ValueError("Container is truncated or header length is corrupt")
    header = Header.from_json(hjson)
    payload = buf.read()
    return header, payload