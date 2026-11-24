#!/usr/bin/env python3
"""Vérificateur indépendant des résultats produits par `rarediag`.

Il ne réutilise AUCUN code du paquet `rarediag` :

* l'ontologie est lue avec `pronto` (et non le parseur maison) ;
* les annotations sont lues avec `pandas` ;
* l'IC est recalculé depuis zéro ;
* la similarité de Resnik est calculée par la définition directe, paire par paire
  (intersection des ancêtres, puis maximum de l'IC), sans l'optimisation par index inversé.

Deux modes :

    # 1. vérifier un diagnostic produit par `rarediag diagnose ... --json fichier.json`
    python verifier/verify.py diagnostic results/diagnostic.json [--full]

    # 2. vérifier les résultats d'évaluation (results/ranks.csv) sur un échantillon de patients
    python verifier/verify.py evaluation results --sample 30

Le code de sortie vaut 0 si tout est conforme, 1 sinon.
"""
from __future__ import annotations

import argparse
import json
import math
import sys
import warnings
from pathlib import Path

import pandas as pd

TOL = 1e-6
ROOT = "HP:0000118"


class Checker:
    def __init__(self):
        self.n_ok = 0
        self.failures: list[str] = []

    def check(self, cond: bool, msg: str) -> None:
        if cond:
            self.n_ok += 1
        else:
            self.failures.append(msg)

    def report(self) -> int:
        print(f"\n{self.n_ok} vérifications réussies, {len(self.failures)} échec(s).")
        for f in self.failures[:30]:
            print("  ✗", f)
        print("RÉSULTAT :", "CONFORME" if not self.failures else "NON CONFORME")
        return 0 if not self.failures else 1


class ReferenceModel:
    """Implémentation de référence, volontairement simple et lente."""

    def __init__(self, data_dir: Path, prefix: str = "ORPHA:"):
        import pronto
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            self.ont = pronto.Ontology(str(data_dir / "hp.obo"))
        self.version = str(self.ont.metadata.data_version or "")
        subtree = {t.id for t in self.ont[ROOT].subclasses() if not t.obsolete}
        self.anc: dict[str, frozenset[str]] = {
            tid: frozenset({t.id for t in self.ont[tid].superclasses()} & subtree) for tid in subtree
        }
        self.alias: dict[str, str] = {}
        for term in self.ont.terms():
            if term.obsolete:
                rep = [r.id for r in term.replaced_by]
                if rep and rep[0] in self.anc:
                    self.alias[term.id] = rep[0]
            elif term.id in self.anc:
                for alt in term.alternate_ids:
                    self.alias[alt] = term.id

        df = pd.read_csv(data_dir / "phenotype.hpoa", sep="\t", comment="#", dtype=str).fillna("")
        df = df[df.database_id.str.startswith(prefix) & (df.aspect == "P") & (df.qualifier != "NOT")]
        zero = (df.frequency == "HP:0040285") | df.frequency.str.match(r"^0+/") | df.frequency.str.match(r"^0+(\.0+)?%$")
        df = df[~zero]
        df["hpo"] = df.hpo_id.map(self.resolve)
        df = df[df.hpo.notna()]
        self.names = df.groupby("database_id").disease_name.first().to_dict()
        self.pheno = {d: sorted(set(g.hpo)) for d, g in df.groupby("database_id")}
        n = len(self.pheno)
        count: dict[str, int] = {}
        for terms in self.pheno.values():
            clo = set().union(*(self.anc[t] for t in terms))
            for t in clo:
                count[t] = count.get(t, 0) + 1
        self.ic = {t: (-math.log(count[t] / n) if t in count else math.log(n)) for t in self.anc}

    def resolve(self, tid: str) -> str | None:
        return tid if tid in self.anc else self.alias.get(tid)

    def resnik(self, a: str, b: str) -> tuple[float, str]:
        common = self.anc[a] & self.anc[b]
        best = max(common, key=lambda t: (self.ic[t], t))
        return self.ic[best], best

    def score(self, query: list[str], did: str, method: str) -> float:
        terms = self.pheno[did]
        a = sum(max(self.resnik(q, t)[0] for t in terms) for q in query) / len(query)
        if method == "resnik":
            return a
        b = sum(max(self.resnik(t, q)[0] for q in query) for t in terms) / len(terms)
        return (a + b) / 2


def verify_diagnostic(path: Path, data_dir: Path, full: bool) -> int:
    c = Checker()
    res = json.loads(path.read_text(encoding="utf-8"))
    ref = ReferenceModel(data_dir)
    c.check(res["hpo_version"] == ref.version,
            f"version HPO {res['hpo_version']} ≠ données {ref.version}")
    query = [ref.resolve(q) for q in res["query"]]
    c.check(all(query), "terme de requête inconnu de l'ontologie")
    method = res["method"]
    absent = res.get("absent") or []
    if absent:
        print("Remarque : signes absents présents ; seuls les scores sans pénalité sont recontrôlés "
              "via les explications.")
    ranking = res["ranking"]
    scores = [r["score"] for r in ranking]
    c.check(all(scores[i] >= scores[i + 1] - TOL for i in range(len(scores) - 1)),
            "classement non trié par score décroissant")
    print(f"Vérification de {len(ranking)} diagnostics ({method})…")
    for r in ranking:
        did = r["disease_id"]
        c.check(did in ref.pheno, f"{did} inconnue des annotations")
        if did not in ref.pheno:
            continue
        c.check(r["name"] == ref.names[did], f"{did} : nom incohérent")
        if not absent:
            expected = ref.score(query, did, method)
            c.check(abs(expected - r["score"]) < TOL,
                    f"{did} : score {r['score']:.6f} ≠ recalcul {expected:.6f}")
        # Explication : MICA ancêtre commun, IC exact, meilleur appariement, somme des contributions
        total = 0.0
        for m in r["explanation"]:
            q = m["patient_term"]
            best_ic = max(ref.resnik(q, t)[0] for t in ref.pheno[did])
            c.check(abs(m["ic"] - best_ic) < TOL, f"{did}/{q} : IC du meilleur appariement faux")
            c.check(abs(m["ic"] - ref.ic[m["mica"]]) < TOL, f"{did}/{q} : IC du MICA faux")
            c.check(m["mica"] in ref.anc[q], f"{did}/{q} : MICA non ancêtre du signe patient")
            if m["disease_term"]:
                c.check(m["disease_term"] in ref.pheno[did], f"{did}/{q} : terme apparié hors maladie")
                c.check(m["mica"] in ref.anc[m["disease_term"]], f"{did}/{q} : MICA non ancêtre du terme maladie")
            total += m["contribution"]
        c.check(abs(total - ref.score(query, did, "resnik")) < TOL,
                f"{did} : contributions ≠ score Q→D")
    if full and not absent:
        print(f"Contrôle exhaustif : recalcul des {len(ref.pheno)} maladies…")
        threshold = scores[-1]
        listed = {r["disease_id"] for r in ranking}
        missing = [d for d in ref.pheno if d not in listed and ref.score(query, d, method) > threshold + TOL]
        c.check(not missing, f"{len(missing)} maladie(s) absentes du classement ont un score supérieur : {missing[:5]}")
    return c.report()


def tie_rank(scores: dict[str, float], true: str) -> float:
    s = scores[true]
    better = sum(v > s + 1e-9 for v in scores.values())
    ties = sum(abs(v - s) <= 1e-9 for v in scores.values()) - 1
    return 1 + better + ties / 2


def verify_evaluation(results: Path, data_dir: Path, sample: int, seed: int) -> int:
    c = Checker()
    df = pd.read_csv(results / "ranks.csv")
    summ = pd.read_csv(results / "summary.csv")
    meta = json.loads((results / "meta.json").read_text(encoding="utf-8"))
    ref = ReferenceModel(data_dir)
    n = len(ref.pheno)
    c.check(meta["hpo_version"] == ref.version, "version HPO des résultats ≠ données")
    c.check(meta["n_diseases"] == n, f"nombre de maladies {meta['n_diseases']} ≠ {n}")
    c.check(df["rank"].between(1, n).all(), "rang hors de [1, N]")
    c.check(df.disease.isin(ref.pheno.keys()).all(), "maladie inconnue dans ranks.csv")
    # Le résumé doit découler exactement de ranks.csv
    for _, row in summ.iterrows():
        r = df[(df.scenario == row.scenario) & (df.method == row.method)]["rank"]
        c.check(abs(round((r <= 1).mean(), 3) - row.top1) < 1e-9, f"top1 incohérent ({row.scenario}, {row.method})")
        c.check(abs(round((r <= 10).mean(), 3) - row.top10) < 1e-9, f"top10 incohérent ({row.scenario}, {row.method})")
        c.check(abs(round((1 / r).mean(), 3) - row.MRR) < 1e-9, f"MRR incohérent ({row.scenario}, {row.method})")
    # Recalcul complet du rang pour un échantillon de patients (méthodes de Resnik)
    methods = {"Resnik Q→D": "resnik", "Resnik symétrique": "resnik_sym"}
    sub = df[df.method.isin(methods)]
    rows = sub.sample(n=min(sample, len(sub)), random_state=seed)
    print(f"Recalcul naïf du rang de {len(rows)} patients simulés (≈ {len(rows) * n} scores)…")
    for _, row in rows.iterrows():
        query = [ref.resolve(t) for t in row.terms.split()]
        scores = {d: ref.score(query, d, methods[row.method]) for d in ref.pheno}
        r = tie_rank(scores, row.disease)
        c.check(abs(r - row["rank"]) < 1e-6,
                f"{row.scenario}/{row.method}/patient {row.patient} : rang {row['rank']} ≠ recalcul {r}")
    return c.report()


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--data", default=str(Path(__file__).resolve().parents[1] / "data"))
    sub = ap.add_subparsers(dest="mode", required=True)
    d = sub.add_parser("diagnostic")
    d.add_argument("json", type=Path)
    d.add_argument("--full", action="store_true", help="vérifier aussi qu'aucune maladie n'a été oubliée")
    e = sub.add_parser("evaluation")
    e.add_argument("results", type=Path)
    e.add_argument("--sample", type=int, default=30)
    e.add_argument("--seed", type=int, default=0)
    args = ap.parse_args()
    data = Path(args.data)
    if args.mode == "diagnostic":
        sys.exit(verify_diagnostic(args.json, data, args.full))
    sys.exit(verify_evaluation(args.results, data, args.sample, args.seed))


if __name__ == "__main__":
    main()
