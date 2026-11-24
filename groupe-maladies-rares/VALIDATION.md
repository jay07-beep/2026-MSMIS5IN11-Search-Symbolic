# Vérifications de l'archive de remise

Date : 24 novembre 2026.

## Suite de tests fournie

Commande depuis le dossier du groupe, avec les données téléchargées et Java disponible :

```bash
python -m pytest -q -p no:cacheprovider
```

Sortie observée :

```text
51 passed, 1 warning in 14.31s
```

Les tests n'ont pas été désactivés. L'avertissement concerne une dépréciation interne du plugin pytest d'anyio dans l'environnement de vérification.

Les fichiers `tests/fixtures/toy.obo` et `toy.hpoa` proviennent du commit original de Mathis `6912ab477b1fae6716529817aea5cc7ff5669c2b`. Leur provenance est documentée dans `tests/fixtures/README.md`. Les assertions d'origine sont conservées.

La suite comprend les contrôles sur le jeu synthétique, les données réelles publiques téléchargées, HermiT et le test qui vérifie que le vérificateur rejette un score altéré.

## Contrôle indépendant des résultats enregistrés

```bash
python verifier/verify.py evaluation results --sample 2 --seed 42
```

Sortie observée :

```text
Recalcul naïf du rang de 2 patients simulés (≈ 8710 scores)…
96 vérifications réussies, 0 échec(s).
RÉSULTAT : CONFORME
```

Il s'agit d'un contrôle par échantillon des scores de Resnik, pas d'un recalcul de tous les patients ou de toutes les baselines. Les tableaux de synthèse des expériences principales, des signes absents et des questions ont également été recalculés depuis leurs fichiers de rangs lors de l'analyse précédente : aucune différence avec les résumés fournis.

L'évaluation complète n'a pas été régénérée pour cette archive. Le notebook et les résultats fournis sont conservés. Les figures ont été produites à partir de leurs CSV.

## Environnement utilisé

- Python : 3.12.14
- numpy : 2.3.5
- pandas : 2.2.3
- matplotlib : 3.10.8
- pytest : 9.2.0
- pronto : 2.7.4
- owlready2 : 0.51
- streamlit : 1.67.0

Les fichiers de dépendances restent déclarés avec des bornes minimales. Pour reproduire précisément l'environnement ci-dessus, utiliser les versions indiquées. Java est nécessaire pour l'extension HermiT.

## Points à compléter avant publication

- Les deux pseudos GitHub et les contributions réelles dans le README et le texte de PR.
- Le nom du dossier si Mathis a déjà remis le projet sous un autre nom : garder un seul dossier de groupe.
- Les diapositives fournies sont conservées sans modification. Les formulations sur les signes non observés et le filtre OWL demandent les précisions déjà discutées pour l'oral. Le chiffre « 356 contrôles » du diaporama ne correspond pas au contrôle par échantillon de 2 patients exécuté ici.
- Confirmer que la PR vise le bon dépôt et a été créée avant l'échéance. Aucune publication GitHub n'a été effectuée pour préparer cette archive.
