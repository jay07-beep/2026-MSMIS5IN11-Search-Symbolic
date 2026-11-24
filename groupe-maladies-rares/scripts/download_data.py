#!/usr/bin/env python3
"""Télécharge une version figée de HPO (ontologie + annotations) dans data/.

    python scripts/download_data.py              # version de référence du projet
    python scripts/download_data.py --release v2026-09-01 --no-check
    python scripts/download_data.py --latest     # dernière version (résultats différents possibles)

Les fichiers téléchargés ne doivent pas être commités (data/ est dans .gitignore).
"""
from __future__ import annotations

import argparse
import hashlib
import sys
import urllib.request
from pathlib import Path

REPO = "https://github.com/obophenotype/human-phenotype-ontology/releases"
RELEASE = "v2026-09-01"
FILES = {
    "hp.obo": "93dace952fcb3ec4728818857f6ba76bc2d5312f4d83266519b8694b8e798f22",
    "phenotype.hpoa": "e89aa39c8f97bf5a52c5d160f9250a603681d630ade8ec2679d84ac5aece1f72",
}


def sha256(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as fh:
        for chunk in iter(lambda: fh.read(1 << 20), b""):
            h.update(chunk)
    return h.hexdigest()


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--release", default=RELEASE)
    ap.add_argument("--latest", action="store_true")
    ap.add_argument("--no-check", action="store_true", help="ne pas contrôler les sommes SHA-256")
    ap.add_argument("--out", default=str(Path(__file__).resolve().parents[1] / "data"))
    args = ap.parse_args()
    out = Path(args.out)
    out.mkdir(parents=True, exist_ok=True)
    check = not (args.no_check or args.latest or args.release != RELEASE)
    ok = True
    for name, digest in FILES.items():
        url = f"{REPO}/latest/download/{name}" if args.latest else f"{REPO}/download/{args.release}/{name}"
        dest = out / name
        if dest.exists() and check and sha256(dest) == digest:
            print(f"✓ {name} déjà présent et intègre")
            continue
        print(f"↓ {url}")
        urllib.request.urlretrieve(url, dest)
        if check:
            good = sha256(dest) == digest
            ok &= good
            print(f"{'✓' if good else '✗'} {name} : SHA-256 {'conforme' if good else 'DIFFÉRENT'}")
        else:
            print(f"  {name} : {dest.stat().st_size / 1e6:.1f} Mo (sans contrôle d'intégrité)")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
