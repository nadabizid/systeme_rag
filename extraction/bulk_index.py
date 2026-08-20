"""
US 2.2 — Indexation des documents vectorisés
Insertion en masse (bulk) des chunks vectorisés (sortie de l'US 1.2) dans
l'index k-NN créé par create_index.py (US 2.1).
"""
import json
import os
from pathlib import Path

import boto3
from opensearchpy import OpenSearch, RequestsHttpConnection, AWSV4SignerAuth, helpers
from dotenv import load_dotenv

load_dotenv()

COLLECTION_ENDPOINT = os.getenv("OPENSEARCH_COLLECTION_ENDPOINT")
INDEX_NAME = "rag-documents-index"
DOSSIER_CHUNKS = Path("./output_chunks_embeddings")


def get_client() -> OpenSearch:
    region = COLLECTION_ENDPOINT.split(".")[-4]
    credentials = boto3.Session().get_credentials()
    auth = AWSV4SignerAuth(credentials, region, "aoss")
    host = COLLECTION_ENDPOINT.replace("https://", "")

    return OpenSearch(
        hosts=[{"host": host, "port": 443}],
        http_auth=auth,
        use_ssl=True,
        verify_certs=True,
        connection_class=RequestsHttpConnection,
        pool_maxsize=20,
    )


def generer_actions_bulk(chunks: list[dict]):
    """Génère les actions au format attendu par le bulk helper d'opensearch-py.
    Chaque entrée contient le vecteur, le texte du chunk, et le document
    source (critère d'acceptation US 2.2).

    Note : PAS de "_id" personnalisé — OpenSearch Serverless (VECTORSEARCH)
    n'autorise pas les IDs définis par le client sur les opérations
    d'indexation (erreur "Document ID is not supported in create/index
    operation request"). L'ID est donc généré automatiquement par le
    service ; chunk_id reste disponible comme simple champ de _source
    pour l'identification côté application (filtrage, dédoublonnage manuel).
    """
    for chunk in chunks:
        yield {
            "_index": INDEX_NAME,
            "_source": {
                "vecteur": chunk["vecteur"],
                "texte": chunk["texte"],
                "chunk_id": chunk["chunk_id"],
                "document_source": chunk["document_source"],
                "position": chunk["position"],
            },
        }


def main():
    if not COLLECTION_ENDPOINT:
        raise SystemExit("OPENSEARCH_COLLECTION_ENDPOINT manquant dans .env")

    client = get_client()
    fichiers = sorted(DOSSIER_CHUNKS.glob("*_chunks.json"))
    print(f"{len(fichiers)} fichier(s) de chunks à indexer.")

    total_succes = 0
    total_echecs = 0
    erreurs_detail = []

    for fichier in fichiers:
        with open(fichier, encoding="utf-8") as f:
            chunks = json.load(f)

        # On n'indexe que les chunks effectivement vectorisés — un chunk
        # dont l'embedding a échoué en US 1.2 (vecteur=None) est ignoré
        # plutôt que de faire planter tout le bulk insert
        chunks_valides = [c for c in chunks if c.get("vecteur") is not None]
        chunks_ignores = len(chunks) - len(chunks_valides)
        if chunks_ignores:
            print(f"  ⚠ {fichier.name} : {chunks_ignores} chunk(s) sans vecteur ignoré(s)")

        if not chunks_valides:
            continue

        try:
            succes, erreurs = helpers.bulk(
                client,
                generer_actions_bulk(chunks_valides),
                raise_on_error=False,
                stats_only=False,
            )
            total_succes += succes
            if erreurs:
                total_echecs += len(erreurs)
                erreurs_detail.extend(erreurs)
                print(f"  ✗ {fichier.name} : {succes} indexé(s), {len(erreurs)} échec(s)")
                print(f"     Détail de l'erreur : {json.dumps(erreurs[0], ensure_ascii=False, default=str)}")
            else:
                print(f"  ✓ {fichier.name} : {succes} chunk(s) indexé(s)")

        except Exception as e:
            print(f"  ✗ {fichier.name} -> ERREUR: {e}")
            erreurs_detail.append({"fichier": fichier.name, "erreur": str(e)})

    print(f"\nTerminé : {total_succes} chunk(s) indexé(s) avec succès, {total_echecs} échec(s).")

    if erreurs_detail:
        with open(DOSSIER_CHUNKS / "_erreurs_indexation.json", "w", encoding="utf-8") as f:
            json.dump(erreurs_detail, f, ensure_ascii=False, indent=2, default=str)

    # Vérification finale : compte réel de documents dans l'index.
    # Note : client.indices.refresh() N'EST PAS appelé ici — OpenSearch
    # Serverless ne supporte pas cette opération d'administration (404
    # systématique, indépendamment de l'état réel de l'index).
    try:
        total_index = client.count(index=INDEX_NAME)["count"]
        print(f"Total de documents dans l'index '{INDEX_NAME}' : {total_index}")
    except Exception as e:
        print(f"(Impossible de compter les documents : {e})")


if __name__ == "__main__":
    main()
