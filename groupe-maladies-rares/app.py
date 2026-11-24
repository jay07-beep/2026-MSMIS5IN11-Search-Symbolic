"""Démonstrateur interactif.   Lancement : streamlit run app.py"""
from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
import streamlit as st

sys.path.insert(0, str(Path(__file__).parent / "src"))
from rarediag import load_index  # noqa: E402
from rarediag.explain import KIND_LABELS, explain  # noqa: E402
from rarediag.next_question import best_questions  # noqa: E402

st.set_page_config(page_title="Diagnostic différentiel — maladies rares", page_icon="🧬", layout="wide")

EXAMPLES = {
    "Marfan (4 signes)": ["HP:0001166", "HP:0001083", "HP:0002616", "HP:0000098"],
    "Profil vague (2 signes généraux)": ["HP:0001250", "HP:0001263"],
}


@st.cache_resource(show_spinner="Chargement de HPO et des annotations Orphanet…")
def get_index():
    return load_index()


index = get_index()
labels = {t: f"{index.onto.name(t)} ({t})" for t in index.onto.terms}
options = sorted(labels, key=lambda t: labels[t].lower())

for key in ("present", "absent"):
    st.session_state.setdefault(key, [])

st.title("🧬 Diagnostic différentiel des maladies rares")
st.caption(f"Human Phenotype Ontology {index.onto.version} · {len(index.disease_ids)} maladies Orphanet · "
           "similarité sémantique de Resnik (Köhler et al., 2009). Outil pédagogique, pas un dispositif médical.")

with st.sidebar:
    st.header("Profil du patient")
    ex = st.selectbox("Charger un exemple", ["—"] + list(EXAMPLES))
    if ex != "—" and st.button("Charger"):
        st.session_state.present, st.session_state.absent = list(EXAMPLES[ex]), []
        st.rerun()
    st.session_state.present = st.multiselect("Signes observés", options, default=st.session_state.present,
                                              format_func=labels.get)
    st.session_state.absent = st.multiselect("Signes vérifiés absents", options, default=st.session_state.absent,
                                             format_func=labels.get)
    method = st.radio("Mesure", ["resnik_sym", "resnik"],
                      format_func={"resnik_sym": "Resnik symétrique", "resnik": "Resnik patient → maladie"}.get)
    weight = st.slider("Poids des signes absents (λ)", 0.0, 3.0, 1.0, 0.25)
    top = st.slider("Nombre de diagnostics", 5, 30, 10)
    if st.button("Réinitialiser"):
        st.session_state.present, st.session_state.absent = [], []
        st.rerun()

query, absent = st.session_state.present, st.session_state.absent
if not query:
    st.info("Ajoutez au moins un signe observé dans le panneau de gauche (ou chargez un exemple).")
    st.stop()

ranking = index.rank(query, method=method, absent=absent, absent_weight=weight, top=top)
col1, col2 = st.columns([3, 2])
with col1:
    st.subheader("Diagnostics compatibles")
    df = pd.DataFrame([{"Rang": k, "Score": round(s, 3), "Orphanet": d, "Maladie": index.diseases[d].name}
                       for k, (d, s) in enumerate(ranking, 1)])
    st.dataframe(df, hide_index=True, width="stretch")
    st.subheader("Pourquoi ce classement ?")
    for k, (did, s) in enumerate(ranking[:5], 1):
        with st.expander(f"{k}. {index.diseases[did].name} — score {s:.3f}", expanded=(k == 1)):
            rows = [{"Signe du patient": m.patient_name, "Phénotype de la maladie": m.disease_name,
                     "Relation": KIND_LABELS[m.kind], "Ancêtre commun (MICA)": m.mica_name,
                     "IC": round(m.ic, 2),
                     "Fréquence": f"{m.frequency:.0%}" if m.frequency is not None else "—"}
                    for m in sorted(explain(index, query, did), key=lambda m: -m.ic)]
            st.dataframe(pd.DataFrame(rows), hide_index=True, width="stretch")
            hits = [labels[x] for x in absent if x in index.closure[index.index_of[did]]]
            if hits:
                st.warning("Signes absents attendus dans cette maladie : " + ", ".join(hits))

with col2:
    st.subheader("Question suivante la plus discriminante")
    st.caption("Signe dont la réponse réduit le plus l'incertitude entre les 20 premiers candidats "
               "(gain d'information attendu, en bits).")
    for q in best_questions(index, query, absent, method=method):
        c1, c2, c3 = st.columns([5, 1, 1])
        c1.markdown(f"**{q.name}**  \n`{q.term}` · gain {q.gain:.2f} bit · P(présent) {q.p_yes:.0%}")
        if c2.button("Présent", key=f"y{q.term}"):
            st.session_state.present = query + [q.term]
            st.rerun()
        if c3.button("Absent", key=f"n{q.term}"):
            st.session_state.absent = absent + [q.term]
            st.rerun()
