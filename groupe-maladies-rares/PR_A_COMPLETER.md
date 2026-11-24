## Groupe et sujet

- **Dossier :** `groupe-maladies-rares/` (adapter si Mathis a déjà choisi un autre nom)
- **Sujet :** E1 — Diagnostic différentiel des maladies rares par ontologies
- **Membres :** @PSEUDO_JEROME_A_COMPLETER @MathisGramaglia
- **Issue(s) d'accompagnement éventuelle(s) :** à compléter, ou aucune

## Résumé

Démonstrateur Python de classement expliqué des maladies rares à partir de signes cliniques HPO et d'annotations Orphanet. Le cœur compare Resnik patient → maladie et Resnik symétrique aux baselines par mots-clés, termes exacts et Jaccard hiérarchique. Le projet inclut une CLI, une interface Streamlit, un notebook, un vérificateur indépendant, les tests et des extensions sur les signes absents, les questions et OWL/HermiT.

Les résultats enregistrés sur 500 patients simulés par scénario donnent, avec imprécision 50 % et bruit +2, un top 10 de 87,4 % pour Resnik symétrique contre 60 % pour les mots-clés. Les patients sont simulés à partir des annotations du corpus, ce qui rend l'évaluation optimiste par rapport à des cas indépendants.

## Vérifications

À compléter après avoir relu et testé le dossier sur votre branche. Ne cochez que ce que vous avez vérifié.

- [ ] Cette PR ne modifie qu'un dossier de groupe et aucun travail d'un autre groupe.
- [ ] Le dossier n'est présent qu'une fois dans le dépôt.
- [ ] Le README explique installation, exécution, tests, résultats, limites et contributions.
- [ ] Le code, le notebook ou la démonstration et les slides sont présents.
- [ ] Les tests ont été exécutés et leur commande est documentée.
- [ ] Le diff ne contient ni `.env`, ni clé, token, mot de passe, cookie ou donnée confidentielle.
- [ ] Aucun environnement virtuel, `node_modules`, poids de modèle ou artefact lourd n'est ajouté.
- [ ] Les licences des modèles, données, bibliothèques et médias sont respectées.
- [ ] La branche a été synchronisée sans supprimer ou remplacer le contenu du dépôt amont.
- [ ] Les éventuels blocages ont été signalés avant la dernière semaine.

## Démonstration

```bash
cd groupe-maladies-rares
pip install -r requirements.txt
pip install -e .
python scripts/download_data.py
streamlit run app.py
```

Charger l'exemple Marfan (4 signes) et montrer classement, explications et question suivante.

Plan B : notebook exécuté `notebooks/demo.ipynb`, figures et tableaux déjà présents dans `results/`. Préparer également une capture de démonstration locale avant la soutenance.

Assistance IA déclarée dans le README du groupe.
