"""
Monitoring de latence du pipeline RAG — mesure le temps de chaque étape
(vectorisation, recherche OpenSearch, génération Claude) séparément, pour
pouvoir diagnostiquer précisément le Bug 2 du cahier des charges (lenteur
OpenSearch / timeouts) si jamais il se produit.
"""
import json
import time
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path

from embeddings import get_client as get_bedrock_client, get_embedding
from bulk_index import get_client as get_opensearch_client, INDEX_NAME
from generation import generer_reponse

FICHIER_LATENCE = Path("./monitoring_latency.json")
TOP_K_DEFAUT = 5


@contextmanager
def chronometre(mesures: dict, nom_etape: str):
    """Context manager simple : mesure le temps passé dans le bloc `with`
    et l'ajoute au dict `mesures` sous la clé `nom_etape` (en secondes)."""
    debut = time.perf_counter()
    yield
    mesures[nom_etape] = round(time.perf_counter() - debut, 4)


def executer_avec_monitoring(question: str, top_k: int = TOP_K_DEFAUT) -> dict:
    """
    Exécute le pipeline RAG complet (vectorisation -> recherche -> génération)
    en mesurant le temps de chaque étape séparément, puis sauvegarde la
    mesure dans monitoring_latency.json.
    """
    mesures = {}
    client_bedrock = get_bedrock_client()
    client_opensearch = get_opensearch_client()

    with chronometre(mesures, "vectorisation_question"):
        vecteur_question = get_embedding(question, client=client_bedrock)

    with chronometre(mesures, "recherche_opensearch"):
        requete = {
            "size": top_k,
            "query": {"knn": {"vecteur": {"vector": vecteur_question, "k": top_k}}},
            "_source": ["texte", "chunk_id", "document_source", "position"],
        }
        reponse_os = client_opensearch.search(index=INDEX_NAME, body=requete)
        chunks = [
            {
                "score": hit["_score"],
                "texte": hit["_source"]["texte"],
                "chunk_id": hit["_source"]["chunk_id"],
                "document_source": hit["_source"]["document_source"],
                "position": hit["_source"]["position"],
            }
            for hit in reponse_os["hits"]["hits"]
        ]

    with chronometre(mesures, "generation_claude"):
        resultat = generer_reponse(question, chunks, client=client_bedrock)

    mesures["total"] = round(sum(mesures.values()), 4)

    enregistrement = {
        "horodatage": datetime.now(timezone.utc).isoformat(),
        "question": question,
        "nb_chunks_trouves": len(chunks),
        "mesures_secondes": mesures,
        "fiable": resultat["fiable"],
    }
    _sauvegarder(enregistrement)

    return {"reponse": resultat["reponse"], "fiable": resultat["fiable"], "mesures": mesures}


def _sauvegarder(enregistrement: dict):
    """Ajoute l'enregistrement au fichier JSON (créé s'il n'existe pas)."""
    historique = []
    if FICHIER_LATENCE.exists():
        with open(FICHIER_LATENCE, encoding="utf-8") as f:
            historique = json.load(f)

    historique.append(enregistrement)

    with open(FICHIER_LATENCE, "w", encoding="utf-8") as f:
        json.dump(historique, f, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    import sys

    question = sys.argv[1] if len(sys.argv) > 1 else "Combien de jours de congés pour un stagiaire ?"
    resultat = executer_avec_monitoring(question)

    print(f"Question : {question}\n")
    print(f"Réponse : {resultat['reponse']}\n")
    print("Temps par étape :")
    for etape, duree in resultat["mesures"].items():
        print(f"  {etape} : {duree}s")
