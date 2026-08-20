"""
US 1.2 — Découpage du texte en chunks (chunking)
Chunks de ~500-1000 tokens avec 10% de chevauchement (overlap),
sans couper un mot en plein milieu.
"""

# Approximation : 1 token ≈ 4 caractères pour du texte français/anglais courant.
# Titan n'a pas de tokenizer public simple à installer — cette approximation
# est suffisante pour dimensionner des chunks, pas pour un comptage exact.
CARACTERES_PAR_TOKEN = 4


def chunk_text(texte: str, taille_max_tokens: int = 800, overlap_ratio: float = 0.10) -> list[str]:
    """
    Découpe `texte` en chunks d'environ `taille_max_tokens` tokens,
    avec un chevauchement de `overlap_ratio` entre chunks consécutifs.
    Coupe toujours sur un espace pour ne jamais tronquer un mot.
    """
    if not texte or not texte.strip():
        return []

    taille_max_chars = taille_max_tokens * CARACTERES_PAR_TOKEN
    overlap_chars = int(taille_max_chars * overlap_ratio)

    chunks = []
    debut = 0
    n = len(texte)

    while debut < n:
        fin = min(debut + taille_max_chars, n)

        # Si on ne touche pas la toute fin du texte, recule jusqu'au
        # dernier espace pour ne pas couper un mot en deux
        if fin < n:
            espace = texte.rfind(" ", debut, fin)
            if espace > debut:
                fin = espace

        chunk = texte[debut:fin].strip()
        if chunk:
            chunks.append(chunk)

        if fin >= n:
            break

        # Prochain chunk : on recule de overlap_chars pour créer le chevauchement
        nouveau_debut = fin - overlap_chars
        debut = nouveau_debut if nouveau_debut > debut else fin

    return chunks


def chunk_document(texte: str, document_source: str, taille_max_tokens: int = 800,
                    overlap_ratio: float = 0.10) -> list[dict]:
    """Découpe un document et retourne une liste de chunks avec métadonnées,
    prêts à être vectorisés (US 1.2) puis indexés (US 2.2)."""
    morceaux = chunk_text(texte, taille_max_tokens, overlap_ratio)

    return [
        {
            "chunk_id": f"{document_source}_chunk{i}",
            "document_source": document_source,
            "position": i,
            "texte": morceau,
            "nb_caracteres": len(morceau),
        }
        for i, morceau in enumerate(morceaux)
    ]


if __name__ == "__main__":
    # Test rapide en local (voir main_chunking_embedding.py pour l'usage complet)
    import json
    import sys

    with open(sys.argv[1], encoding="utf-8") as f:
        doc = json.load(f)

    chunks = chunk_document(doc["texte"], doc["metadonnees"]["nom_fichier"])
    print(f"{len(chunks)} chunk(s) généré(s) pour {doc['metadonnees']['nom_fichier']}")
    for c in chunks:
        print(f"  - {c['chunk_id']} ({c['nb_caracteres']} caractères)")
