# Remise du projet E1

## Situation constatée le 24 novembre

Le projet est déjà présent sur le fork de Mathis, branche `groupe-maladies-rares`, sous `rarediag/rarediag/` :

https://github.com/MathisGramaglia/2026-MSMIS5IN11-Search-Symbolic/tree/groupe-maladies-rares/rarediag/rarediag

Le commit `6912ab477b1fae6716529817aea5cc7ff5669c2b` est daté du 23 novembre à 07:58:58 UTC, soit 08:58:58 à Paris. Il contient le texte prévu pour la PR dans son message. Une recherche de toutes les PR publiques, ouvertes et fermées, du dépôt du professeur n'a pas identifié de PR E1 de ce groupe au moment de la vérification.

La comparaison de cette branche avec le dépôt du professeur ajoute aussi `Search-06-AdversarialSearch-CSharp (2).ipynb` à la racine. Pour respecter le dossier unique sans toucher aux autres fichiers, la méthode recommandée ci-dessous crée une nouvelle branche à partir de la branche actuelle du professeur. La branche originale de Mathis reste conservée.

## Méthode recommandée pour Mathis

Ces commandes sont à exécuter sur le PC de Mathis avec Git installé. Elles préparent et publient une nouvelle branche sur son fork ; elles ne réécrivent pas la branche existante.

1. Extraire le ZIP fourni pour obtenir `groupe-maladies-rares/`.
2. Compléter votre pseudo et les contributions réelles dans le README et `PR_A_COMPLETER.md`.
3. Dans PowerShell ou Git Bash, se placer dans un dossier de travail puis lancer :

```bash
git clone https://github.com/MathisGramaglia/2026-MSMIS5IN11-Search-Symbolic.git rendu-e1-maladies-rares
cd rendu-e1-maladies-rares
git remote add upstream https://github.com/jsboigeEPF/2026-MSMIS5IN11-Search-Symbolic.git
git fetch upstream
git switch -c remise-e1-maladies-rares upstream/main
```

4. Copier le dossier extrait `groupe-maladies-rares/` dans le dossier local `rendu-e1-maladies-rares/`. Il doit être à la racine, à côté du README du professeur. Ne remplacer aucun fichier du professeur.
5. Revenir dans le terminal :

```bash
git add groupe-maladies-rares
git commit -m "E1 : diagnostic differentiel des maladies rares"
git diff --name-only upstream/main...HEAD
```

6. Vérifier que toutes les lignes de cette dernière commande commencent par `groupe-maladies-rares/`. Ensuite :

```bash
git push -u origin remise-e1-maladies-rares
```

7. Ouvrir cette comparaison :

https://github.com/jsboigeEPF/2026-MSMIS5IN11-Search-Symbolic/compare/main...MathisGramaglia:remise-e1-maladies-rares?expand=1

8. Vérifier la base `jsboigeEPF/2026-MSMIS5IN11-Search-Symbolic:main` et la branche source de Mathis. Cliquer « Create pull request ». Remplir le modèle avec `PR_A_COMPLETER.md`, puis vérifier et créer la PR.
9. Dans la description, préciser que les fichiers ont été poussés le 23 novembre mais que la PR est ouverte le 24, et donner le lien du commit original. Le professeur décidera du traitement de ce décalage.

La présence d'un dossier ou d'un commit sur le fork ne remplace pas la PR.


## Si Mathis a déjà ouvert une Pull Request

1. Retrouvez le lien dans https://github.com/pulls?q=is%3Apr+author%3A%40me en étant connecté au compte ayant créé la PR.
2. Vérifiez que la PR vise `jsboigeEPF/2026-MSMIS5IN11-Search-Symbolic`, branche `main`.
3. Vérifiez l'onglet « Files changed » : tous vos fichiers doivent appartenir au même dossier de groupe.
4. Si la PR est ouverte, ajoutez les éventuelles corrections sur la même branche du fork : la PR se met à jour automatiquement.
5. Si la PR a été fusionnée, utilisez une nouvelle branche et une PR complémentaire pour les changements. Conservez le même nom de dossier de groupe.
6. Si elle est fermée sans fusion, lisez le commentaire du professeur avant de choisir la suite.

Ne créez pas une seconde copie de votre projet sous un autre dossier si le projet a déjà été remis.

## Si les fichiers sont seulement dans le fork

Un dépôt ou un commit sur le fork ne constitue pas une remise. Ouvrez la PR vers le dépôt du professeur.

Depuis le fork GitHub :

1. Placez le dossier `groupe-maladies-rares/` à la racine de la branche de travail, ou utilisez le nom de groupe déjà choisi par Mathis.
2. Complétez les deux pseudos GitHub et les contributions réelles dans le README. Gardez uniquement les comptes GitHub dans le corps public de la PR.
3. Ajoutez les fichiers extraits de cette archive. Le ZIP sert au transfert : ajoutez son contenu organisé dans Git, et non le ZIP lui-même.
4. Utilisez « Contribute » puis « Open pull request », ou « Compare & pull request ».
5. Base repository : `jsboigeEPF/2026-MSMIS5IN11-Search-Symbolic`. Base branch : `main`. Head repository et branche : le fork et la branche contenant votre travail.
6. Titre proposé : `E1 — Diagnostic différentiel des maladies rares par ontologies`.
7. Remplissez le modèle officiel de PR. Un exemple à compléter est fourni dans `PR_A_COMPLETER.md`.
8. Vérifiez la liste des fichiers et créez la PR.

## Délai et confirmation

Le guide officiel fixe la création de la PR au lundi 23 novembre 2026 à 23:59. Il autorise les slides et corrections dans une PR complémentaire avant la soutenance. Une PR créée le 24 novembre ne prouve pas une remise au 23 novembre : signalez honnêtement cette situation au professeur si nécessaire.

Le guide n'exige pas de mail de confirmation d'un agent IA. Le lien de PR, son horodatage, son état et les commentaires GitHub permettent de contrôler la remise. L'absence de mail ne prouve ni un échec ni une validation du rendu.

## Références officielles

- Guide : https://github.com/jsboigeEPF/2026-MSMIS5IN11-Search-Symbolic/blob/main/docs/GUIDE-SOUMISSION.md
- Évaluation : https://github.com/jsboigeEPF/2026-MSMIS5IN11-Search-Symbolic/blob/main/docs/EVALUATION.md
- Modèle : https://github.com/jsboigeEPF/2026-MSMIS5IN11-Search-Symbolic/blob/main/.github/PULL_REQUEST_TEMPLATE.md
