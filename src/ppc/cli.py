from __future__ import annotations
import os, json
import click
from rich.console import Console
from rich.table import Table
from cryptography.exceptions import InvalidTag
from dotenv import load_dotenv
from pyzstd import compress as zstd_compress, ZstdDecompressor, ZstdError

from .detect import detect_mime
from .crypto import encrypt, decrypt
from .container import Header, pack, unpack, MAGIC
from .ipfs import upload_web3, upload_pinata, gateway_url, upload_daemon, download_daemon
from .utils import now_iso, read_bytes, write_bytes

console = Console()
load_dotenv()

@click.group()
def cli():
    """Pied Piper Phase 1 CLI (.ppc universal container)"""


@cli.command()
@click.argument("input_path", type=click.Path(exists=True, dir_okay=False))
@click.option("-o", "--output", type=click.Path(dir_okay=False), help="Output .ppc path")
@click.option("-p", "--passphrase", prompt=True, hide_input=True, confirmation_prompt=False, envvar="PPC_PASSPHRASE",
              help="Passphrase for encryption. Uses PPC_PASSPHRASE env var if set.")
@click.option("--level", default=7, show_default=True, help="Zstd compression level (1-22)")
@click.option("--upload", type=click.Choice(["none","web3","pinata"], case_sensitive=False), default="none",
              show_default=True, help="Upload container to IPFS via service")
@click.option("--name", default=None, help="Override original filename in header")
def compress(input_path, output, passphrase, level, upload, name):
    """Compress + encrypt INPUT into a .ppc container (optionally upload)."""
    console.rule("[bold cyan]Pied Piper Compression Pipeline[/bold cyan]")

    # 1. Read Input File
    raw = read_bytes(input_path)
    console.print(f"📄 [bold]Read Input File[/]")
    console.print(f"   → {input_path} ({len(raw)} bytes)")

    # 2. Detect File Type
    mime, mime_source = detect_mime(input_path)
    console.print(f"🔍 [bold]Detected File Type[/]")
    console.print(f"   → {mime} (using {mime_source})")

    # 3. Compress
    comp = zstd_compress(raw, level_or_option=level)
    console.print(f"🗜️  [bold]Compressed with Zstandard (Level {level})[/]")
    console.print(f"   → {len(raw)} bytes → {len(comp)} bytes")

    # 4. Encrypt
    ciphertext, crypt_hdr = encrypt(comp, passphrase)
    console.print(f"🔐 [bold]Encrypted with AES-256-GCM[/]")
    console.print(f"   → Payload: {len(ciphertext)} bytes (ciphertext + auth tag)")

    # 5. Wrap into .ppc container
    orig_name = name or os.path.basename(input_path)
    header = Header(
        mime=mime,
        orig_name=orig_name,
        created=now_iso(),
        kdf=crypt_hdr["kdf"],
        cipher=crypt_hdr["cipher"],
        comp={"name": "zstd", "level": level},
        notes="PPC-1: Universal container ready for AI compression.",
    )
    blob = pack(header, ciphertext)
    out = output or (os.path.splitext(input_path)[0] + ".ppc")
    write_bytes(out, blob)
    console.print(f"📦 [bold]Wrapped into .ppc Format[/]")
    console.print(f"   → Created {os.path.basename(out)} ({len(blob)} bytes)")

    # 6. Upload to IPFS
    if upload != "none":
        console.print(f"🌍 [bold]Uploading to IPFS via {upload.capitalize()}[/]")
        console.print(f"   → Decentralized, censorship-resistant storage")
        if upload == "web3":
            token = os.getenv("WEB3_STORAGE_TOKEN")
            if not token:
                raise click.ClickException("WEB3_STORAGE_TOKEN missing in .env")
            cid = upload_web3(blob, os.path.basename(out), token)
        else:  # pinata
            jwt = os.getenv("PINATA_JWT")
            if not jwt:
                raise click.ClickException("PINATA_JWT missing in .env")
            cid = upload_pinata(blob, os.path.basename(out), jwt)
        url = gateway_url(cid, service=upload)
        console.print(f"   → CID: [bold green]{cid}[/]")
        console.print(f"🌐 [bold]Generated Public Link[/]")
        console.print(f"   → {url}")
    else:
        console.print(f"\n✅ [bold green]Success![/] Container created locally.")


@cli.command()
@click.argument("container_path", type=click.Path(exists=True, dir_okay=False))
@click.option("-o", "--output", type=click.Path(dir_okay=False), help="Output original file path")
@click.option("-p", "--passphrase", prompt=True, hide_input=True, confirmation_prompt=False, envvar="PPC_PASSPHRASE")
def decompress(container_path, output, passphrase):
    """Decrypt + decompress a .ppc container back to its original file."""
    console.rule("[bold cyan]Pied Piper Decompression[/bold cyan]")
    blob = read_bytes(container_path)
    try:
        header, payload = unpack(blob)
        comp = decrypt(payload, passphrase, header.kdf["salt_b64"], header.cipher["nonce_b64"])
        raw = ZstdDecompressor().decompress(comp)
    except InvalidTag:
        raise click.ClickException("Decryption failed. Invalid passphrase or corrupted data.")
    except (ValueError, ZstdError) as e:
        # Catches container format errors (ValueError) or zstd errors
        raise click.ClickException(f"Decompression failed: {e}")

    out = output or header.orig_name
    write_bytes(out, raw)

    console.print(f"✅ [bold green]Success![/] File decompressed.")
    console.print(f"   → [bold]Output[/]: {out}\n   → [bold]MIME[/]:   {header.mime}")


@cli.command()
@click.argument("container_path", type=click.Path(exists=True, dir_okay=False))
def inspect(container_path):
    """View container header metadata."""
    blob = read_bytes(container_path)
    try:
        header, payload = unpack(blob)
    except ValueError as e:
        raise click.ClickException(f"Could not inspect file: {e}")

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


@cli.command()
@click.argument("file_path", type=click.Path(exists=True, dir_okay=False, readable=True))
def push(file_path):
    """Upload a .ppc container to a local IPFS daemon."""
    with open(file_path, "rb") as f:
        if f.read(4) != MAGIC:
            raise click.ClickException("Input is not a valid .ppc file.")

    console.rule("Push to IPFS Daemon")
    try:
        with console.status("[bold cyan]Uploading..."):
            cid = upload_daemon(file_path)
        console.print(f"File [bold]{os.path.basename(file_path)}[/] uploaded successfully.")
        console.print(f"CID: [bold green]{cid}[/]")
        console.print(f"Gateway URL: {gateway_url(cid)}")
    except (ImportError, ConnectionError, FileNotFoundError) as e:
        raise click.ClickException(str(e))
    except Exception as e:
        raise click.ClickException(f"An unexpected error occurred: {e}")

@cli.command()
@click.argument("cid")
@click.argument("output_path", type=click.Path(dir_okay=False, writable=True))
def pull(cid, output_path):
    """Download a file from a local IPFS daemon using its CID."""
    console.rule("Pull from IPFS Daemon")
    try:
        with console.status(f"[bold cyan]Downloading {cid}..."):
            download_daemon(cid, output_path)
        console.print(f"Downloaded [bold]{cid}[/] to [bold green]{output_path}[/]")
    except (ImportError, ConnectionError, FileNotFoundError) as e:
        raise click.ClickException(str(e))
    except Exception as e:
        raise click.ClickException(f"An unexpected error occurred: {e}")