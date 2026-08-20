"""
US 1.2 — Point d'entrée : output_extraction/*.json -> chunks -> embeddings -> JSON
Prend la sortie de l'US 1.1 (main.py) et produit des chunks vectorisés,
prêts pour l'indexation OpenSearch (US 2.2).
Usage : python main_chunking_embedding.py
"""
import json
from pathlib import Path

from chunking import chunk_document
from embeddings import get_client, get_embedding

DOSSIER_ENTREE = Path("./output_extraction")
DOSSIER_SORTIE = Path("./output_chunks_embeddings")


def main():
    DOSSIER_SORTIE.mkdir(exist_ok=True)
    client_bedrock = get_client()

    fichiers = sorted(DOSSIER_ENTREE.glob("*.json"))
    fichiers = [f for f in fichiers if not f.name.startswith("_")]  # ignore _erreurs.json
    print(f"{len(fichiers)} document(s) extrait(s) à chunker/vectoriser.")

    total_chunks = 0
    erreurs = []

    for fichier in fichiers:
        with open(fichier, encoding="utf-8") as f:
            doc = json.load(f)

        nom_doc = doc["metadonnees"]["nom_fichier"]
        chunks = chunk_document(doc["texte"], nom_doc)
        print(f"\n{nom_doc} -> {len(chunks)} chunk(s)")

        for chunk in chunks:
            try:
                chunk["vecteur"] = get_embedding(chunk["texte"], client=client_bedrock)
                print(f"  ✓ {chunk['chunk_id']} vectorisé (dim={len(chunk['vecteur'])})")
                total_chunks += 1
            except Exception as e:
                print(f"  ✗ {chunk['chunk_id']} -> ERREUR: {e}")
                erreurs.append({"chunk_id": chunk["chunk_id"], "erreur": str(e)})
                chunk["vecteur"] = None

        nom_sortie = DOSSIER_SORTIE / f"{Path(nom_doc).stem}_chunks.json"
        with open(nom_sortie, "w", encoding="utf-8") as f:
            json.dump(chunks, f, ensure_ascii=False, indent=2)

    print(f"\nTerminé : {total_chunks} chunk(s) vectorisé(s), {len(erreurs)} échec(s).")
    if erreurs:
        with open(DOSSIER_SORTIE / "_erreurs.json", "w", encoding="utf-8") as f:
            json.dump(erreurs, f, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    main()
