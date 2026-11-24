"""Le vérificateur doit accepter un résultat correct et rejeter un résultat altéré."""
import json
import subprocess
import sys
from pathlib import Path

import pytest

from rarediag.cli import main as cli_main

ROOT = Path(__file__).resolve().parents[1]


def run_verifier(path):
    return subprocess.run([sys.executable, str(ROOT / "verifier" / "verify.py"), "diagnostic", str(path)],
                          capture_output=True, text=True)


def test_verificateur_accepte_puis_rejette(real, tmp_path):
    out = tmp_path / "diag.json"
    cli_main(["diagnose", "HP:0001166", "HP:0001083", "HP:0000098", "--top", "5", "--json", str(out)])
    ok = run_verifier(out)
    assert ok.returncode == 0, ok.stdout
    data = json.loads(out.read_text())
    data["ranking"][1]["score"] += 0.05
    bad = tmp_path / "bad.json"
    bad.write_text(json.dumps(data))
    ko = run_verifier(bad)
    assert ko.returncode == 1 and "NON CONFORME" in ko.stdout
