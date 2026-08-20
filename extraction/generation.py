"""
US 3.2 — Génération de la réponse avec Amazon Bedrock (Claude 3)
Construit un prompt anti-hallucination à partir du contexte retrouvé (US 3.1)
et génère la réponse finale, avec citation des sources (Bug 1 du cahier :
prompt système strict + temperature=0).
"""
import json
import random
import time

import boto3

MODEL_ID = "us.anthropic.claude-haiku-4-5-20251001-v1:0"
MAX_TOKENS = 1000
TEMPERATURE = 0  # réduit la variabilité du modèle -> anti-hallucination (Bug 1 du cahier)
MAX_TENTATIVES = 5

PROMPT_SYSTEME = """Tu es l'assistant interne de Smartovate Consulting. Tu réponds aux questions des consultants UNIQUEMENT à partir du contexte fourni ci-dessous, extrait de documents internes de l'entreprise.

Règles strictes à respecter absolument :
- Réponds uniquement à partir des informations présentes dans le contexte fourni.
- Si la réponse ne se trouve pas dans le contexte, réponds EXACTEMENT : "Je ne dispose pas de cette information."
- N'invente jamais d'information, même plausible, qui n'est pas explicitement dans le contexte.
- Cite le ou les documents sources RÉELLEMENT UTILISÉS pour ta réponse à la fin, sous la forme : Sources : nom_du_document. Ne cite QUE les documents dont tu t'es effectivement servi, même si d'autres documents sont présents dans le contexte fourni.
- Réponds en français, de façon claire et concise."""

MARQUEUR_HORS_CONTEXTE = "je ne dispose pas de cette information"


def get_client():
    return boto3.client("bedrock-runtime")


def construire_prompt_utilisateur(question: str, chunks: list[dict]) -> str:
    """Assemble le contexte récupéré (US 3.1) et la question en un seul message."""
    if not chunks:
        contexte = "(aucun contexte pertinent trouvé)"
    else:
        contexte = "\n\n".join(
            f"[Extrait de {c['document_source']}]\n{c['texte']}" for c in chunks
        )

    return f"Contexte :\n{contexte}\n\nQuestion : {question}"


def evaluer_fiabilite(texte_reponse: str) -> bool:
    """
    Détecte si le modèle a répondu "je ne dispose pas de cette information"
    (cas hors-contexte, US 3.2 critère anti-hallucination). Séparé de
    generer_reponse() pour être testable sans appel réseau.
    """
    return MARQUEUR_HORS_CONTEXTE not in texte_reponse.lower()


def generer_reponse(question: str, chunks: list[dict], client=None,
                     max_tentatives: int = MAX_TENTATIVES) -> dict:
    """
    Génère la réponse finale à partir de la question + du contexte retrouvé.
    Retourne {reponse, sources, fiable} — fiable=False si le modèle a
    répondu "Je ne dispose pas de cette information".
    """
    client = client or get_client()
    prompt_utilisateur = construire_prompt_utilisateur(question, chunks)

    body = json.dumps({
        "anthropic_version": "bedrock-2023-05-31",
        "max_tokens": MAX_TOKENS,
        "temperature": TEMPERATURE,
        "system": PROMPT_SYSTEME,
        "messages": [{"role": "user", "content": prompt_utilisateur}],
    })

    for tentative in range(max_tentatives):
        try:
            reponse_brute = client.invoke_model(
                modelId=MODEL_ID,
                body=body,
                contentType="application/json",
                accept="application/json",
            )
            resultat = json.loads(reponse_brute["body"].read())
            texte_reponse = resultat["content"][0]["text"]
            fiable = evaluer_fiabilite(texte_reponse)

            # Pas de champ "sources" calculé séparément : Claude cite lui-même
            # les documents réellement utilisés directement dans le texte de
            # la réponse (voir prompt système) — plus fiable qu'un calcul
            # côté code basé sur tous les chunks récupérés, dont certains
            # peuvent ne pas avoir été pertinents pour la réponse finale.
            return {"reponse": texte_reponse, "fiable": fiable}

        except client.exceptions.ThrottlingException:
            attente = (2 ** tentative) + random.uniform(0, 1)
            print(f"    Rate limit atteint, retry dans {attente:.1f}s "
                  f"(tentative {tentative + 1}/{max_tentatives})...")
            time.sleep(attente)

    raise RuntimeError(f"Échec après {max_tentatives} tentatives — rate limiting persistant.")


if __name__ == "__main__":
    import sys
    from search import rechercher_chunks_pertinents

    question = sys.argv[1] if len(sys.argv) > 1 else "Combien de jours de congés pour un stagiaire ?"
    chunks = rechercher_chunks_pertinents(question)
    resultat = generer_reponse(question, chunks)

    print(f"Question : {question}\n")
    print(f"Réponse : {resultat['reponse']}\n")
    print(f"Fiable : {resultat['fiable']}")
