"""
US 4.1 — Interface Chatbot Web
Interface Streamlit connectée au pipeline RAG (recherche US 3.1 +
génération US 3.2), avec historique de conversation maintenu pendant la
session et affichage des documents sources.

Usage : streamlit run app.py
"""
import streamlit as st

from search import rechercher_chunks_pertinents
from generation import generer_reponse
from embeddings import get_client as get_bedrock_client
from bulk_index import get_client as get_opensearch_client

NOM_ASSISTANT = "Cortex"

st.set_page_config(page_title=f"{NOM_ASSISTANT} — Assistant Documentaire", page_icon="🧠", layout="centered")

# Masque le menu Streamlit par défaut (hamburger, bouton Deploy, footer "Made with
# Streamlit") — pas pertinent pour une démo interne, ça fait plus fini sans.
st.markdown("""
<style>
#MainMenu {visibility: hidden;}
footer {visibility: hidden;}
[data-testid="stToolbar"] {visibility: hidden;}
[data-testid="stDecoration"] {display: none;}

.stChatMessage {
    border-radius: 14px;
}
div[data-testid="stChatMessageContent"] p {
    line-height: 1.55;
}
</style>
""", unsafe_allow_html=True)


@st.cache_resource
def get_clients():
    """Clients AWS mis en cache par Streamlit — sinon ils seraient recréés
    à chaque interaction (rerun), ce qui ralentirait chaque message inutilement."""
    return get_bedrock_client(), get_opensearch_client()


client_bedrock, client_opensearch = get_clients()

if "historique" not in st.session_state:
    st.session_state.historique = []

# --- Sidebar ---
with st.sidebar:
    st.markdown(f"## 🧠 {NOM_ASSISTANT}")
    st.caption("Assistant documentaire interne — RAG sur Amazon Bedrock & OpenSearch")
    st.divider()
    st.markdown(
        "Pose une question sur les documents internes de l'entreprise "
        "(politiques RH, procédures techniques, estimations de coûts...)."
    )
    st.divider()
    if st.button("🗑️ Nouvelle conversation", use_container_width=True):
        st.session_state.historique = []
        st.rerun()
    st.caption(f"{len(st.session_state.historique)} échange(s) dans cette session")

# --- Zone principale ---
st.markdown(f"# 🧠 {NOM_ASSISTANT}")
st.caption("Réponses générées uniquement à partir de vos documents internes — jamais inventées.")
st.divider()


def afficher_sources(chunks: list[dict]):
    """Affiche les documents consultés sous forme de cartes, avec un score
    de pertinence normalisé en pourcentage (plus lisible qu'un score brut)."""
    if not chunks:
        return
    with st.expander(f"📄 {len(chunks)} document(s) consulté(s) lors de la recherche"):
        for chunk in chunks:
            with st.container(border=True):
                col_nom, col_score = st.columns([4, 1])
                with col_nom:
                    st.markdown(f"**{chunk['document_source']}**")
                with col_score:
                    st.markdown(f":violet-badge[{chunk['score']:.0%}]")
                st.caption(chunk["texte"][:200].strip() + "...")


# Affiche les messages précédents de la session
for message in st.session_state.historique:
    with st.chat_message("user", avatar="🧑‍💼"):
        st.write(message["question"])
    with st.chat_message("assistant", avatar="🧠"):
        st.markdown(message["reponse"])
        afficher_sources(message["chunks"])

# Nouvelle question
question = st.chat_input("Pose ta question ici...")

if question:
    with st.chat_message("user", avatar="🧑‍💼"):
        st.write(question)

    with st.chat_message("assistant", avatar="🧠"):
        with st.spinner("Recherche dans les documents internes..."):
            chunks = rechercher_chunks_pertinents(
                question, client_bedrock=client_bedrock, client_opensearch=client_opensearch
            )
        with st.spinner("Génération de la réponse..."):
            resultat = generer_reponse(question, chunks, client=client_bedrock)

        st.markdown(resultat["reponse"],unsafe_allow_html=False)
        afficher_sources(chunks)

    st.session_state.historique.append({
        "question": question,
        "reponse": resultat["reponse"],
        "chunks": chunks,
    })
