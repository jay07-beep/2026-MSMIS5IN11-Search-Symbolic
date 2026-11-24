"""Explication d'un classement : quel signe du patient a été apparié à quel phénotype de la
maladie, par quel ancêtre commun (MICA), et pour quelle contribution au score."""
from __future__ import annotations

from dataclasses import dataclass

from .similarity import SemanticIndex


@dataclass
class Match:
    patient_term: str
    patient_name: str
    disease_term: str | None
    disease_name: str
    mica: str
    mica_name: str
    ic: float
    kind: str           # exact | plus_specifique | plus_general | apparente | aucun
    frequency: float | None
    contribution: float  # part du score Q->D (= ic / |Q|)


def explain(index: SemanticIndex, query: list[str], did: str) -> list[Match]:
    onto = index.onto
    query = index.clean_query(query)
    terms = index.diseases[did].phenotypes
    out: list[Match] = []
    for q in query:
        # Meilleur phénotype de la maladie pour q : IC du MICA maximal ; à égalité on préfère
        # le terme le plus proche (MICA égal à l'un des deux termes), puis l'ordre alphabétique.
        best = None
        for t in terms:
            m = index.mica(q, t)
            key = (index.ic[m], m in (q, t), -abs(onto.depth(t) - onto.depth(q)), t)
            if best is None or key > best[0]:
                best = (key, t, m)
        _, t, m = best
        ic = index.ic[m]
        if m == onto.root or ic == 0:
            kind, t_out = "aucun", None
        elif t == q:
            kind, t_out = "exact", t
        elif m == q:
            kind, t_out = "plus_specifique", t   # la maladie décrit un sous-type du signe observé
        elif m == t:
            kind, t_out = "plus_general", t      # le signe observé est plus précis que l'annotation
        else:
            kind, t_out = "apparente", t         # simple parenté via un ancêtre commun
        out.append(Match(
            patient_term=q, patient_name=onto.name(q),
            disease_term=t_out, disease_name=onto.name(t_out) if t_out else "—",
            mica=m, mica_name=onto.name(m), ic=ic, kind=kind,
            frequency=terms.get(t_out) if t_out else None,
            contribution=ic / len(query),
        ))
    return out


KIND_LABELS = {
    "exact": "identique",
    "plus_specifique": "la maladie précise ce signe",
    "plus_general": "signe plus précis que l'annotation",
    "apparente": "apparenté",
    "aucun": "non expliqué",
}


def explain_text(index: SemanticIndex, query: list[str], did: str, method: str = "resnik") -> str:
    d = index.diseases[did]
    lines = [f"{did} — {d.name}   (score {index.score_one(query, did, method):.3f})"]
    for m in sorted(explain(index, query, did), key=lambda m: -m.ic):
        freq = f", fréquence {m.frequency:.0%}" if m.frequency is not None else ""
        via = "" if m.kind in ("exact", "aucun") else f" via « {m.mica_name} »"
        lines.append(
            f"  • {m.patient_name} ↔ {m.disease_name} [{KIND_LABELS[m.kind]}{via}] "
            f"IC={m.ic:.2f}{freq}"
        )
    return "\n".join(lines)
