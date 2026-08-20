"""
US 2.1 (partie data-plane) — Création de l'index k-NN
Terraform crée la collection (control plane AWS) ; ce script crée l'index
vectoriel à l'intérieur (data plane OpenSearch), avec la dimensionnalité
correspondant à Titan Embeddings (1536 — confirmé lors du test de l'US 1.2).
"""
import os

import boto3
from opensearchpy import OpenSearch, RequestsHttpConnection, AWSV4SignerAuth
from dotenv import load_dotenv

load_dotenv()

# Récupéré depuis l'output "collection_endpoint" de `terraform apply`,
# format: https://xxxxxxxxxx.us-east-1.aoss.amazonaws.com
COLLECTION_ENDPOINT = os.getenv("OPENSEARCH_COLLECTION_ENDPOINT")
INDEX_NAME = "rag-documents-index"
DIMENSION_EMBEDDING = 1536  # Titan Embeddings v1 — confirmé par le test US 1.2


def get_client() -> OpenSearch:
    region = COLLECTION_ENDPOINT.split(".")[-4]
    credentials = boto3.Session().get_credentials()
    auth = AWSV4SignerAuth(credentials, region, "aoss")  # "aoss" = service name pour Serverless

    host = COLLECTION_ENDPOINT.replace("https://", "")

    return OpenSearch(
        hosts=[{"host": host, "port": 443}],
        http_auth=auth,
        use_ssl=True,
        verify_certs=True,
        connection_class=RequestsHttpConnection,
        pool_maxsize=20,
    )


def creer_index():
    client = get_client()

    if client.indices.exists(index=INDEX_NAME):
        print(f"L'index '{INDEX_NAME}' existe déjà, rien à faire.")
        return

    # Mapping k-NN : le champ "vecteur" est de type knn_vector avec la bonne
    # dimension, + les champs texte/métadonnées nécessaires pour US 2.2 et US 3.1
    body = {
        "settings": {
            "index": {
                "knn": True,
            }
        },
        "mappings": {
            "properties": {
                "vecteur": {
                    "type": "knn_vector",
                    "dimension": DIMENSION_EMBEDDING,
                    "method": {
                        "name": "hnsw",
                        "engine": "nmslib",
                        "space_type": "cosinesimil",
                    },
                },
                "texte": {"type": "text"},
                "chunk_id": {"type": "keyword"},
                "document_source": {"type": "keyword"},
                "position": {"type": "integer"},
            }
        },
    }

    client.indices.create(index=INDEX_NAME, body=body)
    print(f"Index '{INDEX_NAME}' créé avec succès (dimension={DIMENSION_EMBEDDING}).")


if __name__ == "__main__":
    if not COLLECTION_ENDPOINT:
        raise SystemExit(
            "OPENSEARCH_COLLECTION_ENDPOINT manquant dans .env — "
            "récupère-le avec `terraform output collection_endpoint` après le apply."
        )
    creer_index()
