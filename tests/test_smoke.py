import os
from src.ppc.cli import compress, decompress
from click.testing import CliRunner


def test_roundtrip(tmp_path):
    p = tmp_path / "hello.txt"
    p.write_text("hello pied piper")

    runner = CliRunner()
    out_ppc = tmp_path / "hello.ppc"

    r1 = runner.invoke(compress, [str(p), "-p", "pass", "-o", str(out_ppc)])
    assert r1.exit_code == 0

    out_txt = tmp_path / "restored.txt"
    r2 = runner.invoke(decompress, [str(out_ppc), "-p", "pass", "-o", str(out_txt)])
    assert r2.exit_code == 0
    assert out_txt.read_text() == "hello pied piper"