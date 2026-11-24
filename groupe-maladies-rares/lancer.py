"""Prépare l'environnement local puis ouvre l'interface du projet."""
from __future__ import annotations

import hashlib
import os
from pathlib import Path
import subprocess
import sys
import venv


ROOT = Path(__file__).resolve().parent


def run(command: list[str]) -> None:
    subprocess.run(command, cwd=ROOT, check=True)


def main() -> None:
    if sys.version_info < (3, 10):
        raise SystemExit("Python 3.10 ou plus recent est necessaire.")
    folder = ROOT / ".venv"
    python = folder / ("Scripts/python.exe" if os.name == "nt" else "bin/python")
    if not python.exists():
        print("1/3 - Creation de l'environnement Python...", flush=True)
        venv.EnvBuilder(with_pip=True).create(folder)

    requirements = ROOT / "requirements-app.txt"
    fingerprint = hashlib.sha256(requirements.read_bytes()).hexdigest()
    marker = folder / ".rarediag-app-ready"
    if not marker.exists() or marker.read_text() != fingerprint:
        print("1/3 - Installation des bibliotheques (premier lancement)...", flush=True)
        run([str(python), "-m", "pip", "install", "-r", str(requirements)])
        marker.write_text(fingerprint)

    print("2/3 - Verification et telechargement des donnees HPO...", flush=True)
    run([str(python), str(ROOT / "scripts" / "download_data.py")])
    print("3/3 - Ouverture de l'interface : http://localhost:8501", flush=True)
    print("Gardez cette fenetre ouverte pendant l'utilisation. Ctrl+C pour arreter.", flush=True)
    run([str(python), "-m", "streamlit", "run", str(ROOT / "app.py"),
         "--server.address", "localhost", "--server.port", "8501",
         "--server.headless", "false", "--browser.gatherUsageStats", "false"])


if __name__ == "__main__":
    try:
        main()
    except subprocess.CalledProcessError as exc:
        print("\nLe lancement s'est interrompu. Consultez le message d'erreur ci-dessus.", flush=True)
        raise SystemExit(exc.returncode)
    except KeyboardInterrupt:
        print("\nApplication arretee.")
