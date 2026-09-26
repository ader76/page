# Audit : opinion en ligne et législatives marocaines 2026

Rapport principal : **[RAPPORT.md](RAPPORT.md)**.

## État au 26 septembre 2026

| Volet | État |
|---|---|
| Résultats officiels, participation, mode de scrutin | fait, sourcé (`data/`) |
| Répartition urbain/rural, quotient, indice de conversion, 33 circonscriptions documentées, bulletins nuls | fait (`resultats/`) |
| Allégations d'irrégularités (A à G), observateurs | fait (`data/allegations_irregularites.csv`, `data/observateurs.csv`) |
| Collecte des commentaires en ligne | **non réalisée** : accès réseau bloqué par l'environnement (`data/acces_plateformes.csv`) |
| Nettoyage, coordination, classification, validation | code prêt et testé, **jamais exécuté sur des données réelles** |
| Voix par parti, données provinciales (ASD, pauvreté) | non publiées ou inaccessibles |

## Arborescence

```
RAPPORT.md                  rapport en 11 parties + réponses Q1-Q8
data/                       données sourcées (une source par ligne)
resultats/                  sorties d'analyse et figures
pipeline/                   chaîne de collecte et d'analyse
  common.py                 schéma commun, périodes P1-P5, langue, pseudonymisation
  queries.py                plan de 870 requêtes (neutres / favorables / critiques / ...)
  collect_youtube.py        YouTube via yt-dlp
  collect_reddit.py         Reddit (JSON public ou OAuth)
  collect_web_comments.py   sites de médias (sélecteurs À VALIDER)
  import_exports.py         exports Facebook / Instagram / TikTok / X
  clean_dedup.py            DATASET_BRUT -> DATASET_NETTOYE
  coordination.py           probabilité de coordination par compte (jamais « bot »)
  lexicon.py, classify.py   dictionnaire darija/arabe/arabizi/français + classifieur à règles
  classify_llm.py           classifieur optionnel par modèle de langage (Claude)
  validate.py               échantillon >= 500 et taux d'erreur
  analyze_opinion.py        trois lectures (commentaires, comptes, plateformes)
  analyze_elections.py      tests électoraux et figures
  tests/                    26 tests (jeux synthétiques générés à la volée + données publiées de data/)
```

## Relancer

```bash
pip install -r requirements.txt
cd pipeline
python -m pytest -q tests/                          # 26 tests
python analyze_elections.py ../data ../resultats     # analyses électorales + figures
```

## Compléter l'audit quand l'accès aux données existe

1. **Ouvrir l'accès réseau** de l'environnement (réglage « Network access » de l'environnement cloud : niveau plus large, ou ajout des domaines youtube.com, googlevideo.com, reddit.com, hespress.com, etc.), **ou** fournir des exports de commentaires.
2. Collecter (les auteurs sont pseudonymisés dès la collecte ; le sel reste dans `.salt`, non versionné) :
   ```bash
   python queries.py > ../data/plan_requetes.csv
   python collect_youtube.py ../data/plan_requetes.csv data_work/raw/youtube.jsonl
   python collect_reddit.py ../data/plan_requetes.csv data_work/raw/reddit.jsonl
   python import_exports.py export_facebook.csv facebook data_work/raw/facebook.jsonl --mapping facebook_generique
   ```
3. Nettoyer, détecter la coordination, classer :
   ```bash
   python clean_dedup.py data_work/raw data_work
   python coordination.py data_work/dataset_dedup_technique.jsonl data_work/dataset_nettoye.jsonl data_work
   python classify.py data_work/dataset_nettoye_coord.jsonl data_work/dataset_classe.jsonl
   ```
4. **Valider** (obligatoire) : tirer ≥ 500 commentaires, les relire dans leur contexte, mesurer l'erreur.
   ```bash
   python validate.py sample data_work/dataset_classe.jsonl validation/a_annoter.csv --n 600
   # ... annotation humaine des colonnes gold_* ...
   python validate.py score validation/a_annoter.csv validation/rapport_validation.json
   ```
   Si l'erreur dépasse 10 % : enrichir `lexicon.py` ou utiliser `classify_llm.py`, puis revalider sur un nouvel échantillon.
5. Analyser :
   ```bash
   python analyze_opinion.py data_work/dataset_classe.jsonl ../resultats/opinion
   ```

### Classifieur par modèle de langage (optionnel)

`classify_llm.py` utilise le modèle `claude-opus-5` avec une sortie JSON contrainte par schéma et une consigne de codage versionnée (son empreinte est écrite dans chaque ligne). Le mode `sync` active le **repli automatique côté serveur** (`fallbacks: "default"`) : si le modèle refuse une requête, elle est relancée sur un autre modèle ; le mode `batch` (API Message Batches, coût −50 %) liste les lots refusés ou en erreur pour les relancer en `sync`. Identifiants : variable `ANTHROPIC_API_KEY` ou profil `ant auth login`. Ses sorties passent par la même validation que le classifieur à règles.

## Données provinciales (tests participation et ASD)

Déposer `data/provinces.csv` (une ligne par province, chaque valeur sourcée) avec les colonnes `province, participation, part_PAM, part_PJD, part_RNI, part_PI, part_ASD, taux_pauvrete, taux_urbanisation`, puis relancer `analyze_elections.py` : Pearson, Spearman et corrélations partielles (contrôle urbanisation, pauvreté, participation) sont alors calculés. Une corrélation, même forte, ne prouve pas une causalité.

## Protection des personnes

Aucun nom de commentateur n'est conservé (empreinte salée) ; aucun compte n'est désigné ; la probabilité de coordination est qualitative et accompagnée de ses indices. Les données brutes (`pipeline/data_work/`) et le sel (`.salt`) sont exclus du dépôt.
