from __future__ import annotations
import os, json
import click
from rich.console import Console
from rich.table import Table
from dotenv import load_dotenv
from pyzstd import ZstdCompressor, ZstdDecompressor

from .detect import detect_mime
from .crypto import encrypt, decrypt
from .container import Header, pack, unpack
from .ipfs import upload_web3, upload_pinata, gateway_url
from .utils import now_iso, read_bytes, write_bytes

console = Console()
load_dotenv()

@click.group()
def cli():
    """Pied Piper Phase 1 CLI (.ppc universal container)"""


@cli.command()
@click.argument("input_path", type=click.Path(exists=True, dir_okay=False))
@click.option("-o", "--output", type=click.Path(dir_okay=False), help="Output .ppc path")
@click.option("-p", "--passphrase", prompt=True, hide_input=True, confirmation_prompt=False,
              help="Passphrase for AES-GCM encryption")
@click.option("--level", default=7, show_default=True, help="Zstd compression level (1-22)")
@click.option("--upload", type=click.Choice(["none","web3","pinata"], case_sensitive=False), default="none",
              show_default=True, help="Upload container to IPFS via service")
@click.option("--name", default=None, help="Override original filename in header")
def compress(input_path, output, passphrase, level, upload, name):
    """Compress + encrypt INPUT into a .ppc container (optionally upload)."""
    mime = detect_mime(input_path)
    orig_name = name or os.path.basename(input_path)
    console.rule("Compress")
    console.print(f"[bold]Input[/]: {input_path} ({mime})")

    raw = read_bytes(input_path)
    comp = ZstdCompressor(level_or_option=level).compress(raw)
    console.print(f"[green]Compressed[/] {len(raw)} -> {len(comp)} bytes")

    ciphertext, crypt_hdr = encrypt(comp, passphrase)

    header = Header(
        mime=mime,
        orig_name=orig_name,
        created=now_iso(),
        kdf=crypt_hdr["kdf"],
        cipher=crypt_hdr["cipher"],
        comp={"name": "zstd", "level": level},
        notes="Phase-1 universal container",
    )

    blob = pack(header, ciphertext)

    out = output or (os.path.splitext(input_path)[0] + ".ppc")
    write_bytes(out, blob)
    console.print(f"[bold green]Wrote[/] {out} ({len(blob)} bytes)")

    if upload.lower() != "none":
        console.rule("Upload")
        if upload.lower() == "web3":
            token = os.getenv("WEB3_STORAGE_TOKEN")
            if not token:
                raise click.ClickException("WEB3_STORAGE_TOKEN missing in .env")
            cid = upload_web3(blob, os.path.basename(out), token)
        else:
            jwt = os.getenv("PINATA_JWT")
            if not jwt:
                raise click.ClickException("PINATA_JWT missing in .env")
            cid = upload_pinata(blob, os.path.basename(out), jwt)
        url = gateway_url(cid)
        console.print(f"CID: [bold]{cid}[/]\nURL: {url}")


@cli.command()
@click.argument("container_path", type=click.Path(exists=True, dir_okay=False))
@click.option("-o", "--output", type=click.Path(dir_okay=False), help="Output original file path")
@click.option("-p", "--passphrase", prompt=True, hide_input=True)
def decompress(container_path, output, passphrase):
    """Decrypt + decompress a .ppc container back to its original file."""
    blob = read_bytes(container_path)
    header, payload = unpack(blob)

    comp = decrypt(payload, passphrase, header.kdf["salt_b64"], header.cipher["nonce_b64"])
    raw = ZstdDecompressor().decompress(comp)

    out = output or header.orig_name
    write_bytes(out, raw)

    console.rule("Decompress")
    console.print(f"[bold]Output[/]: {out}\n[bold]MIME[/]: {header.mime}")


@cli.command()
@click.argument("container_path", type=click.Path(exists=True, dir_okay=False))
def inspect(container_path):
    """View container header metadata."""
    blob = read_bytes(container_path)
    header, payload = unpack(blob)

    table = Table(title="PPC Header")
    table.add_column("Field")
    table.add_column("Value")

    for k, v in header.__dict__.items():
        if isinstance(v, dict):
            table.add_row(k, json.dumps(v))
        else:
            table.add_row(k, str(v))

    table.add_row("payload_bytes", str(len(payload)))
    console.print(table)


@cli.command()
@click.argument("cid")
def gateway(cid):
    """Print a public IPFS gateway URL for a CID."""
    console.print(gateway_url(cid))


if __name__ == "__main__":
    cli()