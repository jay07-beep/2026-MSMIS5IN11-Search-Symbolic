# Données HPO et annotations Orphanet

Les fichiers réels sont téléchargés par :

```bash
python scripts/download_data.py
```

Le script récupère `hp.obo` et `phenotype.hpoa` depuis la release HPO `v2026-09-01`, puis contrôle leurs sommes SHA-256. La version interne des annotations de référence est `2026-09-02`.

Sources :

- HPO et fichiers de release : https://github.com/obophenotype/human-phenotype-ontology/releases/tag/v2026-09-01
- HPO : https://hpo.jax.org
- Orphanet : https://www.orpha.net

Ces données restent soumises aux licences et obligations de citation de leurs producteurs. Consulter les conditions de la distribution HPO et d'Orphanet avant toute redistribution. Les références scientifiques sont données dans le README principal.

Les fichiers téléchargés ne sont pas inclus dans l'archive de remise et ne doivent pas être ajoutés à Git. Les fichiers de `tests/fixtures/` constituent un jeu synthétique local aux tests, documenté séparément.
