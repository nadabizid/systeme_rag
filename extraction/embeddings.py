"""
US 1.2 — Vectorisation via Amazon Bedrock (Titan Embeddings)
Gère le rate limiting avec retry + backoff exponentiel (critère d'acceptation).
"""
import json
import random
import time

import boto3

import os
from dotenv import load_dotenv

load_dotenv()

MODEL_ID = "amazon.titan-embed-text-v1"
MAX_TENTATIVES = 5


def get_client():
    """Client Bedrock Runtime (région lue depuis AWS_DEFAULT_REGION / .env)."""
    return boto3.client("bedrock-runtime")


def get_embedding(texte: str, client=None, max_tentatives: int = MAX_TENTATIVES) -> list[float]:
    """
    Appelle Titan Embeddings pour un texte et retourne le vecteur.
    Retry automatique avec backoff exponentiel en cas de throttling
    (dépassement des limites de l'API — critère d'acceptation US 1.2).
    """
    client = client or get_client()
    body = json.dumps({"inputText": texte})

    for tentative in range(max_tentatives):
        try:
            reponse = client.invoke_model(
                modelId=MODEL_ID,
                body=body,
                contentType="application/json",
                accept="application/json",
            )
            resultat = json.loads(reponse["body"].read())
            return resultat["embedding"]

        except client.exceptions.ThrottlingException:
            attente = (2 ** tentative) + random.uniform(0, 1)
            print(f"    Rate limit atteint, retry dans {attente:.1f}s "
                  f"(tentative {tentative + 1}/{max_tentatives})...")
            time.sleep(attente)

        except client.exceptions.ValidationException as e:
            # Erreur de contenu (texte vide, trop long...) — pas la peine de retry
            raise ValueError(f"Texte invalide pour l'embedding: {e}")

    raise RuntimeError(
        f"Échec après {max_tentatives} tentatives — rate limiting persistant. "
        "Vérifie les quotas Bedrock de ton compte."
    )


if __name__ == "__main__":
    # Test rapide : nécessite un accès Bedrock actif (voir étapes 1-2 du guide)
    import sys
    texte_test = sys.argv[1] if len(sys.argv) > 1 else "Ceci est un test de vectorisation."
    vecteur = get_embedding(texte_test)
    print(f"Vecteur généré : dimension {len(vecteur)}")
    print(f"Premiers éléments : {vecteur[:5]}")
