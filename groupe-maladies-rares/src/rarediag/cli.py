"""Interface en ligne de commande.

Exemples :
    python -m rarediag.cli search "ectopia lentis"
    python -m rarediag.cli diagnose HP:0001166 HP:0001083 HP:0002616 --explain 3
    python -m rarediag.cli diagnose HP:0001166 HP:0001083 --absent HP:0001250 --next
    python -m rarediag.cli diagnose HP:0001166 HP:0001083 --json results/diagnostic.json
"""
from __future__ import annotations

import argparse
import json
import sys

from . import load_index
from .explain import explain, explain_text
from .next_question import best_questions


def cmd_search(args) -> None:
    index = load_index(args.data)
    for tid, name in index.onto.search(args.text, limit=args.limit):
        print(f"{tid}\t{name}\tIC={index.ic[tid]:.2f}")


def cmd_diagnose(args) -> None:
    index = load_index(args.data)
    query = index.clean_query(args.terms)
    unknown = [t for t in args.terms if index.onto.resolve(t) is None]
    if unknown:
        print(f"Termes ignorés (inconnus ou hors « Phenotypic abnormality ») : {', '.join(unknown)}",
              file=sys.stderr)
    if not query:
        sys.exit("Aucun terme HPO valide.")
    absent = index.clean_query(args.absent or [])
    ranking = index.rank(query, method=args.method, absent=absent, absent_weight=args.absent_weight,
                         top=args.top)

    print("Profil patient :")
    for q in query:
        print(f"  + {q} {index.onto.name(q)} (IC={index.ic[q]:.2f})")
    for x in absent:
        print(f"  − {x} {index.onto.name(x)} (absent)")
    print(f"\nTop {args.top} ({args.method}) :")
    for k, (did, s) in enumerate(ranking, 1):
        print(f"{k:3d}. {s:6.3f}  {did:14s} {index.diseases[did].name}")
    for did, _ in ranking[: args.explain]:
        print()
        print(explain_text(index, query, did, args.method))
    if args.next:
        print("\nQuestions suivantes les plus discriminantes :")
        for q in best_questions(index, query, absent, method=args.method):
            print(f"  ? {q.term} {q.name}  — gain {q.gain:.2f} bits, P(présent)={q.p_yes:.2f}")

    if args.json:
        payload = {
            "hpo_version": index.onto.version,
            "annotations_version": index.annotations_version,
            "method": args.method, "query": query, "absent": absent,
            "absent_weight": args.absent_weight,
            "ranking": [
                {"rank": k, "disease_id": did, "name": index.diseases[did].name, "score": s,
                 "explanation": [m.__dict__ for m in explain(index, query, did)]}
                for k, (did, s) in enumerate(ranking, 1)
            ],
        }
        with open(args.json, "w", encoding="utf-8") as fh:
            json.dump(payload, fh, indent=2, ensure_ascii=False)
        print(f"\nRésultat écrit dans {args.json} (vérifiable avec verifier/verify.py)")


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(prog="rarediag", description=__doc__,
                                 formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--data", default=None, help="dossier contenant hp.obo et phenotype.hpoa")
    sub = ap.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("search", help="chercher un terme HPO par son libellé")
    s.add_argument("text")
    s.add_argument("--limit", type=int, default=10)
    s.set_defaults(func=cmd_search)

    d = sub.add_parser("diagnose", help="classer les maladies pour une liste de signes HPO")
    d.add_argument("terms", nargs="+", help="identifiants HPO (HP:xxxxxxx)")
    d.add_argument("--absent", nargs="*", help="signes vérifiés absents")
    d.add_argument("--absent-weight", type=float, default=1.0)
    d.add_argument("--method", choices=["resnik", "resnik_sym"], default="resnik_sym")
    d.add_argument("--top", type=int, default=10)
    d.add_argument("--explain", type=int, default=3, help="nombre de diagnostics expliqués")
    d.add_argument("--next", action="store_true", help="proposer la question suivante")
    d.add_argument("--json", help="écrire le résultat en JSON")
    d.set_defaults(func=cmd_diagnose)

    args = ap.parse_args(argv)
    args.func(args)


if __name__ == "__main__":
    main()
