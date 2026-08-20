"""
API backend FastAPI — orchestre le flux RAG complet (recherche US 3.1 +
génération US 3.2) et persiste les conversations (SQLite, db.py) pour
permettre de reprendre une conversation après en avoir commencé une autre.

Usage : uvicorn api:app --reload --port 8000
"""
from contextlib import asynccontextmanager

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

import db
from search import rechercher_chunks_pertinents
from generation import generer_reponse
from embeddings import get_client as get_bedrock_client
from bulk_index import get_client as get_opensearch_client

TITRE_MAX_LONGUEUR = 60


@asynccontextmanager
async def lifespan(app: FastAPI):
    db.init_db()
    app.state.client_bedrock = get_bedrock_client()
    app.state.client_opensearch = get_opensearch_client()
    yield


app = FastAPI(title="API Système RAG", lifespan=lifespan)

# Autorise le frontend React (Vite, port par défaut 5173) à appeler cette API
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173", "http://localhost"],
    allow_methods=["*"],
    allow_headers=["*"],
)


class NouveauMessage(BaseModel):
    question: str


class Conversation(BaseModel):
    id: str
    titre: str
    created_at: str


@app.get("/conversations", response_model=list[Conversation])
def lister():
    return db.lister_conversations()


@app.get("/conversations/{conversation_id}")
def obtenir(conversation_id: str):
    conversation = db.obtenir_conversation(conversation_id)
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation introuvable")
    return conversation


@app.delete("/conversations/{conversation_id}")
def supprimer(conversation_id: str):
    if not db.obtenir_conversation(conversation_id):
        raise HTTPException(status_code=404, detail="Conversation introuvable")
    db.supprimer_conversation(conversation_id)
    return {"ok": True}


@app.post("/conversations/{conversation_id}/messages")
def poser_question(conversation_id: str, message: NouveauMessage):
    """
    Crée la conversation si c'est son premier message (le frontend génère
    l'ID côté client dès l'ouverture d'une "nouvelle conversation", avant
    même la première question), exécute le pipeline RAG, et persiste
    question + réponse.
    """
    conversation = db.obtenir_conversation(conversation_id)
    if not conversation:
        titre = message.question[:TITRE_MAX_LONGUEUR]
        db.creer_conversation(titre, conversation_id=conversation_id)

    chunks = rechercher_chunks_pertinents(
        message.question,
        client_bedrock=app.state.client_bedrock,
        client_opensearch=app.state.client_opensearch,
    )
    resultat = generer_reponse(message.question, chunks, client=app.state.client_bedrock)

    db.ajouter_message(conversation_id, "user", message.question)
    db.ajouter_message(
        conversation_id, "assistant", resultat["reponse"],
        sources=[c["document_source"] for c in chunks],
        fiable=resultat["fiable"],
    )

    return {
        "reponse": resultat["reponse"],
        "fiable": resultat["fiable"],
        "chunks": chunks,
    }
