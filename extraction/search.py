"""
US 3.1 — Recherche sémantique (Retrieval)
Vectorise la question de l'utilisateur avec le même modèle d'embedding que
les documents (Titan), puis interroge OpenSearch en k-NN pour récupérer
les chunks les plus pertinents (Top-K=5 par défaut, comme spécifié au cahier).
"""
from embeddings import get_client as get_bedrock_client, get_embedding
from bulk_index import get_client as get_opensearch_client, INDEX_NAME

TOP_K_DEFAUT = 5


def rechercher_chunks_pertinents(
    question: str,
    top_k: int = TOP_K_DEFAUT,
    client_bedrock=None,
    client_opensearch=None,
) -> list[dict]:
    """
    Retourne les top_k chunks les plus proches sémantiquement de `question`,
    avec leur texte et leur document source (critère d'acceptation US 3.1).
    """
    client_bedrock = client_bedrock or get_bedrock_client()
    client_opensearch = client_opensearch or get_opensearch_client()

    # Même modèle d'embedding que pour l'indexation — indispensable pour
    # que la comparaison de vecteurs ait un sens
    vecteur_question = get_embedding(question, client=client_bedrock)

    requete = {
        "size": top_k,
        "query": {
            "knn": {
                "vecteur": {
                    "vector": vecteur_question,
                    "k": top_k,
                }
            }
        },
        "_source": ["texte", "chunk_id", "document_source", "position"],
    }

    reponse = client_opensearch.search(index=INDEX_NAME, body=requete)

    return [
        {
            "score": hit["_score"],
            "texte": hit["_source"]["texte"],
            "chunk_id": hit["_source"]["chunk_id"],
            "document_source": hit["_source"]["document_source"],
            "position": hit["_source"]["position"],
        }
        for hit in reponse["hits"]["hits"]
    ]


if __name__ == "__main__":
    import sys

    question = sys.argv[1] if len(sys.argv) > 1 else "Combien de jours de congés pour un stagiaire ?"
    resultats = rechercher_chunks_pertinents(question)

    print(f"Question : {question}\n")
    print(f"{len(resultats)} chunk(s) trouvé(s) :\n")
    for i, r in enumerate(resultats, 1):
        print(f"{i}. [{r['document_source']}] score={r['score']:.4f}")
        print(f"   {r['texte'][:150]}...\n")
