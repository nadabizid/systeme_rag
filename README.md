# Système RAG — Smartovate Consulting

Assistant documentaire interne basé sur Retrieval-Augmented Generation (RAG),
combinant Amazon Bedrock (Titan Embeddings + Claude) et Amazon OpenSearch
Serverless pour interroger en langage naturel la base documentaire de
l'entreprise.

## Architecture

```
                    ┌─────────────────┐
   Documents  ───►  │  S3 (stockage)   │
   (PDF/DOCX)       └────────┬─────────┘
                              │ extraction (text_extractor.py)
                              ▼
                    ┌─────────────────┐
                    │  Chunking        │  chunking.py
                    │  + Embeddings    │  embeddings.py (Bedrock Titan)
                    └────────┬─────────┘
                              │ bulk insert (bulk_index.py)
                              ▼
                    ┌─────────────────┐
                    │  OpenSearch      │  index k-NN
                    │  Serverless      │  (create_index.py, Terraform)
                    └────────┬─────────┘
                              │ recherche sémantique (search.py)
                              ▼
                    ┌─────────────────┐
                    │  Bedrock Claude  │  génération anti-hallucination
                    │  (generation.py) │  (temperature=0)
                    └────────┬─────────┘
                              │
                    ┌─────────────────┐
                    │  API FastAPI     │  api.py + db.py (SQLite,
                    │                  │  conversations persistées)
                    └────────┬─────────┘
                              │ HTTP/JSON
                    ┌─────────────────┐
                    │  Frontend React  │  frontend/
                    └─────────────────┘
```

Les deux services (backend FastAPI + frontend React) sont conteneurisés
avec Docker et orchestrés via `docker-compose.yml` à la racine du projet.

## Prérequis

- Compte AWS avec accès à Bedrock activé pour : Titan Embeddings, Claude
- Collection OpenSearch Serverless provisionnée (voir `terraform/`)
- Bucket S3 contenant les documents source
- [Docker Desktop](https://www.docker.com/products/docker-desktop/) installé et lancé
- Python 3.12+ et Node.js 18+ (uniquement nécessaires pour le pipeline
  d'ingestion et le développement hors conteneur — pas requis pour lancer
  l'application via Docker Compose)

## Configuration

Copier `.env.example` en `.env` (dans `extraction/`, à côté de `api.py` —
c'est l'emplacement que `docker-compose.yml` charge automatiquement pour
le backend) et remplir :

```
AWS_ACCESS_KEY_ID=...
AWS_SECRET_ACCESS_KEY=...
AWS_SESSION_TOKEN=...          # si compte à identifiants temporaires (IAM Identity Center)
AWS_DEFAULT_REGION=...
S3_BUCKET_NAME=...
OPENSEARCH_COLLECTION_ENDPOINT=...   # sortie de terraform apply
```

> Avec des identifiants temporaires (SSO), `AWS_SESSION_TOKEN` expire
> généralement au bout d'une heure — il faut alors régénérer les 3 valeurs
> et **redémarrer le conteneur backend** (`docker-compose restart backend`
> ou `docker-compose up --build`) pour qu'il recharge le `.env` à jour.

## Exécution du pipeline d'ingestion (ordre requis, une seule fois)

```bash
# 1. Provisionner l'infrastructure OpenSearch
cd terraform && terraform init && terraform apply

# 2. Créer l'index vectoriel
cd ../extraction
python create_index.py

# 3. Extraire le texte des documents S3
python main.py

# 4. Découper en chunks + vectoriser
python main_chunking_embedding.py

# 5. Indexer dans OpenSearch
python bulk_index.py
```

## Lancer l'application

### Méthode recommandée : Docker Compose

Depuis la racine du projet (là où se trouve `docker-compose.yml`) :

```bash
docker-compose up --build
```

- Backend disponible sur `http://localhost:8000` (documentation interactive
  sur `http://localhost:8000/docs`)
- Frontend disponible sur `http://localhost` (port 80, servi par nginx)

Pour arrêter : `Ctrl+C`, puis `docker-compose down`.

### Méthode alternative : lancement manuel (développement)

```bash
# Backend (terminal 1)
cd extraction
pip install -r requirements.txt
uvicorn api:app --reload --port 8000

# Frontend (terminal 2)
cd frontend
npm install
npm run dev
```

Ouvrir `http://localhost:5173`.

## Déploiement

**Important** : AWS App Runner n'accepte plus de nouveaux services depuis le
30 avril 2026. Un déploiement cloud réel se ferait via **Amazon ECS Express
Mode** (remplaçant recommandé par AWS) — fournir une image de conteneur,
obtenir une URL HTTPS publique automatiquement, sans configuration manuelle
de load balancer/certificat/auto-scaling.

Pour ce projet, le déploiement s'arrête volontairement à la conteneurisation
locale (Docker Compose) — l'application est entièrement fonctionnelle et
reproductible sur n'importe quelle machine avec Docker installé, ce qui
couvre les exigences du cahier des charges. Le passage à ECS Express Mode
reste une extension possible, documentée ici pour référence.

## Limites connues (documentées volontairement, pas des oublis)

- **SQLite non persistant en conteneur** : les conversations sont stockées
  dans un fichier local (`conversations.db`). Dans un environnement de
  conteneur éphémère (ex: ECS), ce stockage n'est pas garanti entre les
  redéploiements. Pour une vraie mise en production, remplacer par RDS ou
  DynamoDB — hors périmètre du PoC (cf. cahier des charges, section
  "Exclu").
- **Ordre tableau/texte en PDF** : `pdfplumber` ne garantit pas la position
  exacte d'un tableau par rapport au texte environnant dans un PDF
  (contrairement aux DOCX, où l'ordre réel est préservé). Le contenu n'est
  jamais dupliqué, mais peut apparaître légèrement décalé par rapport à sa
  position d'origine.
- **OpenSearch Serverless n'autorise pas d'ID de document personnalisé** —
  les ID sont générés automatiquement, donc relancer `bulk_index.py`
  plusieurs fois sur les mêmes documents crée des doublons dans l'index.
- **Approximation du nombre de tokens** pour le chunking (règle empirique
  ~4 caractères/token) — pas de tokenizer exact disponible pour Titan.

## Bugs anticipés (cahier des charges) — statut

| Bug | Statut | Note |
|---|---|---|
| Bug 1 — Hallucination | ✅ Résolu | Prompt système strict + temperature=0, testé en conditions réelles |
| Bug 2 — Lenteur OpenSearch | ⚠️ Surveillé | Non observé sur le corpus de test (3 docs) ; monitoring en place (`latency_monitor.py`) pour détecter si ça survient à plus grande échelle |
| Bug 3 — Perte de formatage PDF | ✅ Résolu (partiellement) | Tableaux préservés et non dupliqués ; limite d'ordre documentée ci-dessus |
