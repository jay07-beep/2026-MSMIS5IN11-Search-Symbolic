"""Évaluation sur patients simulés : rang de la bonne maladie, top-k, MRR.

Usage :
    python -m rarediag.evaluate --n 500 --seed 42 --out results
"""
from __future__ import annotations

import argparse
import json
import time
from collections.abc import Callable
from pathlib import Path

import numpy as np
import pandas as pd

from . import load_index
from .baseline import Baselines
from .similarity import SemanticIndex
from .simulate import PatientSimulator, Scenario, SimulatedPatient

SCENARIOS = [
    Scenario("parfait", n_terms=5),
    Scenario("imprécision 50 %", n_terms=5, imprecision=0.5),
    Scenario("imprécision 100 %", n_terms=5, imprecision=1.0),
    Scenario("bruit +2", n_terms=5, noise=2),
    Scenario("imprécision 50 % + bruit +2", n_terms=5, imprecision=0.5, noise=2),
    Scenario("3 signes, imprécision 50 % + bruit +1", n_terms=3, imprecision=0.5, noise=1),
]


def tie_aware_rank(scores: np.ndarray, true_idx: int, atol: float = 1e-9) -> float:
    """Rang espéré de la bonne réponse quand les ex æquo sont départagés au hasard."""
    s = scores[true_idx]
    better = int((scores > s + atol).sum())
    ties = int((np.abs(scores - s) <= atol).sum()) - 1
    return 1 + better + ties / 2


def build_methods(index: SemanticIndex) -> dict[str, Callable[[list[str]], np.ndarray]]:
    b = Baselines(index)
    return {
        "Mots-clés (baseline)": b.keywords,
        "Termes exacts (Jaccard)": b.exact,
        "Jaccard hiérarchique": b.graph_jaccard,
        "Resnik Q→D": lambda q: index.scores(q, "resnik"),
        "Resnik symétrique": lambda q: index.scores(q, "resnik_sym"),
    }


def evaluate_cohort(index: SemanticIndex, patients: list[SimulatedPatient],
                    methods: dict[str, Callable[[list[str]], np.ndarray]], scenario: str) -> pd.DataFrame:
    rows = []
    for i, p in enumerate(patients):
        true_idx = index.index_of[p.disease_id]
        for name, fn in methods.items():
            r = tie_aware_rank(fn(p.terms), true_idx)
            rows.append({"scenario": scenario, "patient": i, "disease": p.disease_id,
                         "terms": " ".join(p.terms), "n_terms": len(p.terms), "method": name, "rank": r})
    return pd.DataFrame(rows)


def summarize(df: pd.DataFrame) -> pd.DataFrame:
    g = df.groupby(["scenario", "method"], sort=False)["rank"]
    return pd.DataFrame({
        "top1": g.apply(lambda r: (r <= 1).mean()),
        "top10": g.apply(lambda r: (r <= 10).mean()),
        "rang_median": g.median(),
        "MRR": g.apply(lambda r: (1 / r).mean()),
    }).round(3)


def evaluate_absent(index: SemanticIndex, n: int, seed: int) -> pd.DataFrame:
    """Extension « signes absents » : gain apporté par la pénalisation des signes absents."""
    sim = PatientSimulator(index, seed=seed)
    sc = Scenario("signes absents", n_terms=3, imprecision=0.5, noise=1, n_absent=3)
    rows = []
    for i, p in enumerate(sim.cohort(sc, n)):
        t = index.index_of[p.disease_id]
        base = index.scores(p.terms)
        rows.append({"patient": i, "method": "Resnik (signes présents seuls)", "rank": tie_aware_rank(base, t)})
        pen = index.absent_penalty(p.absent)
        for w in (0.5, 1.0, 2.0):
            rows.append({"patient": i, "method": f"Resnik + absents (λ={w})",
                         "rank": tie_aware_rank(base - w * pen, t)})
    df = pd.DataFrame(rows)
    df["scenario"] = sc.name
    return df


def evaluate_questions(index: SemanticIndex, n: int, seed: int, n_questions: int = 3) -> pd.DataFrame:
    """Extension « question suivante » : consultation simulée.

    Le patient part de 2 signes (imprécis à 50 %). À chaque tour, une stratégie choisit un signe
    à vérifier ; la réponse est tirée selon la fréquence du signe dans la vraie maladie
    (présent -> ajouté au profil, absent -> ajouté aux signes absents). On compare :
    gain d'information maximal, signe au hasard parmi ceux des 20 premiers candidats, et
    aucune question.
    """
    import random

    from .next_question import best_questions, presence_probability

    sim = PatientSimulator(index, seed=seed)
    sc = Scenario("consultation", n_terms=2, imprecision=0.5)
    patients = sim.cohort(sc, n)
    rows = []
    for strategy in ("aucune question", "question au hasard", "gain d'information max"):
        rng = random.Random(seed)
        for i, p in enumerate(patients):
            q, absent = list(p.terms), []
            t_idx = index.index_of[p.disease_id]
            rows.append({"patient": i, "method": strategy, "questions": 0,
                         "rank": tie_aware_rank(index.scores(q) - index.absent_penalty(absent), t_idx)})
            for k in range(1, n_questions + 1):
                if strategy == "aucune question":
                    r = rows[-1]["rank"]
                    rows.append({"patient": i, "method": strategy, "questions": k, "rank": r})
                    continue
                if strategy == "question au hasard":
                    top = [d for d, _ in index.rank(q, absent=absent, top=20)]
                    known = index.query_closure(q) | set(absent)
                    pool = sorted({t for d in top for t in index.diseases[d].phenotypes} - known)
                    x = rng.choice(pool)
                else:
                    x = best_questions(index, q, absent, n=1)[0].term
                if rng.random() < presence_probability(index, p.disease_id, x):
                    q.append(x)
                else:
                    absent.append(x)
                s = index.scores(q) - index.absent_penalty(absent)
                rows.append({"patient": i, "method": strategy, "questions": k,
                             "rank": tie_aware_rank(s, t_idx)})
    df = pd.DataFrame(rows)
    df["scenario"] = "consultation"
    return df


def plot_results(df: pd.DataFrame, out: Path) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    summ = summarize(df).reset_index()
    methods = list(dict.fromkeys(df["method"]))
    scenarios = list(dict.fromkeys(df["scenario"]))
    colors = ["#9aa0a6", "#c58af9", "#78d9ec", "#1a73e8", "#e8710a"]

    fig, ax = plt.subplots(figsize=(11, 5))
    width = 0.8 / len(methods)
    x = np.arange(len(scenarios))
    for k, m in enumerate(methods):
        vals = [summ[(summ.scenario == s) & (summ.method == m)]["top10"].iloc[0] for s in scenarios]
        ax.bar(x + k * width - 0.4 + width / 2, vals, width, label=m, color=colors[k % len(colors)])
    ax.set_xticks(x)
    ax.set_xticklabels([s.replace(" + ", "\n+ ") for s in scenarios], fontsize=8)
    ax.set_ylabel("Bonne maladie dans le top 10")
    ax.set_ylim(0, 1)
    ax.set_title("Taux de bonne maladie dans le top 10, par scénario de patient simulé")
    ax.legend(fontsize=8, loc="upper center", bbox_to_anchor=(0.5, -0.14), ncol=len(methods), frameon=False)
    ax.grid(axis="y", alpha=0.3)
    fig.tight_layout()
    fig.savefig(out / "top10_par_scenario.png", dpi=150)
    plt.close(fig)

    # Distribution des rangs (échelle log) sur le scénario le plus réaliste
    s = "imprécision 50 % + bruit +2"
    if s in scenarios:
        fig, ax = plt.subplots(figsize=(8, 4.5))
        sub = df[df.scenario == s]
        data = [sub[sub.method == m]["rank"].values for m in methods]
        ax.boxplot(data, orientation="horizontal", tick_labels=methods)
        ax.set_xscale("log")
        ax.set_xlabel("Rang de la bonne maladie (échelle log, 1 = premier)")
        ax.set_title(f"Distribution des rangs — scénario « {s} »")
        ax.grid(axis="x", alpha=0.3)
        fig.tight_layout()
        fig.savefig(out / "rangs_scenario_realiste.png", dpi=150)
        plt.close(fig)

    # Courbes cumulées : proportion de patients dont la maladie est dans le top k
    fig, ax = plt.subplots(figsize=(7, 4.5))
    sub = df[df.scenario == s] if s in scenarios else df
    ks = np.arange(1, 101)
    for k, m in enumerate(methods):
        r = sub[sub.method == m]["rank"].values
        ax.plot(ks, [(r <= kk).mean() for kk in ks], label=m, color=colors[k % len(colors)], lw=2)
    ax.set_xscale("log")
    ax.set_xlabel("k")
    ax.set_ylabel("Proportion dans le top k")
    ax.set_title("Courbe top-k (scénario réaliste)")
    ax.legend(fontsize=8)
    ax.grid(alpha=0.3)
    fig.tight_layout()
    fig.savefig(out / "courbe_topk.png", dpi=150)
    plt.close(fig)


def plot_extensions(absent: pd.DataFrame, questions: pd.DataFrame, out: Path) -> None:
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=(7, 4.5))
    colors = {"aucune question": "#9aa0a6", "question au hasard": "#c58af9",
              "gain d'information max": "#1a73e8"}
    for m, sub in questions.groupby("method", sort=False):
        mrr = sub.groupby("questions")["rank"].apply(lambda r: (1 / r).mean())
        ax.plot(mrr.index, mrr.values, marker="o", lw=2, label=m, color=colors.get(m))
    ax.set_xlabel("Nombre de questions posées")
    ax.set_ylabel("MRR (rang réciproque moyen)")
    ax.set_xticks(sorted(questions.questions.unique()))
    ax.set_title("Consultation simulée : apport de la question suivante")
    ax.legend()
    ax.grid(alpha=0.3)
    fig.tight_layout()
    fig.savefig(out / "questions_mrr.png", dpi=150)
    plt.close(fig)

    summ = summarize(absent).reset_index()
    fig, ax = plt.subplots(figsize=(7, 4))
    ax.barh(summ.method, summ.top10, color=["#9aa0a6"] + ["#1a73e8"] * (len(summ) - 1))
    for y, v in enumerate(summ.top10):
        ax.text(v + 0.01, y, f"{v:.0%}", va="center")
    ax.set_xlim(0, 1)
    ax.set_xlabel("Bonne maladie dans le top 10")
    ax.set_title("Signes absents : effet de la pénalité")
    ax.invert_yaxis()
    fig.tight_layout()
    fig.savefig(out / "signes_absents.png", dpi=150)
    plt.close(fig)


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(description="Évaluation sur patients simulés")
    ap.add_argument("--n", type=int, default=500, help="patients par scénario")
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--out", default="results")
    ap.add_argument("--data", default=None)
    ap.add_argument("--plot-only", action="store_true", help="refaire les figures depuis les CSV existants")
    args = ap.parse_args(argv)
    if args.plot_only:
        out = Path(args.out)
        plot_results(pd.read_csv(out / "ranks.csv"), out / "figures")
        plot_extensions(pd.read_csv(out / "ranks_absent.csv"), pd.read_csv(out / "ranks_questions.csv"),
                        out / "figures")
        return

    out = Path(args.out)
    (out / "figures").mkdir(parents=True, exist_ok=True)
    t0 = time.time()
    index = load_index(args.data)
    methods = build_methods(index)
    frames = []
    for k, sc in enumerate(SCENARIOS):
        sim = PatientSimulator(index, seed=args.seed + k)
        patients = sim.cohort(sc, args.n)
        frames.append(evaluate_cohort(index, patients, methods, sc.name))
        print(f"[{time.time() - t0:5.1f}s] scénario « {sc.name} » terminé")
    df = pd.concat(frames, ignore_index=True)
    df.to_csv(out / "ranks.csv", index=False)
    summ = summarize(df)
    summ.to_csv(out / "summary.csv")
    print(summ.to_string())

    absent = evaluate_absent(index, min(args.n, 300), args.seed + 100)
    absent.to_csv(out / "ranks_absent.csv", index=False)
    summ_abs = summarize(absent)
    summ_abs.to_csv(out / "summary_absent.csv")
    print(summ_abs.to_string())

    questions = evaluate_questions(index, min(args.n, 200), args.seed + 200)
    questions.to_csv(out / "ranks_questions.csv", index=False)
    summ_q = questions.groupby(["method", "questions"], sort=False)["rank"].agg(
        top1=lambda r: (r <= 1).mean(), top10=lambda r: (r <= 10).mean(),
        MRR=lambda r: (1 / r).mean()).round(3)
    summ_q.to_csv(out / "summary_questions.csv")
    print(summ_q.to_string())

    plot_results(df, out / "figures")
    plot_extensions(absent, questions, out / "figures")
    meta = {"hpo_version": index.onto.version, "annotations_version": index.annotations_version,
            "n_diseases": len(index.disease_ids), "n_terms": len(index.onto),
            "n_patients_per_scenario": args.n, "seed": args.seed,
            "scenarios": [sc.__dict__ for sc in SCENARIOS], "runtime_s": round(time.time() - t0, 1)}
    (out / "meta.json").write_text(json.dumps(meta, indent=2, ensure_ascii=False))
    print(f"Terminé en {time.time() - t0:.1f}s — résultats dans {out}/")


if __name__ == "__main__":
    main()
