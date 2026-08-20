import { useEffect, useRef, useState } from "react";
import ReactMarkdown from 'react-markdown';  
import { Prism as SyntaxHighlighter } from 'react-syntax-highlighter';
import { vscDarkPlus } from 'react-syntax-highlighter/dist/esm/styles/prism';
import {
  listerConversations,
  obtenirConversation,
  envoyerMessage,
  supprimerConversation,
} from "./api";

const NOM_APP = "Système RAG";

function genererId() {
  return crypto.randomUUID();
}

export default function App() {
  const [conversations, setConversations] = useState([]);
  const [conversationActiveId, setConversationActiveId] = useState(null);
  const [messages, setMessages] = useState([]);
  const [question, setQuestion] = useState("");
  const [chargement, setChargement] = useState(false);
  const [erreur, setErreur] = useState(null);
  const finMessagesRef = useRef(null);

  useEffect(() => {
    rafraichirConversations();
  }, []);

  useEffect(() => {
    finMessagesRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages]);

  async function rafraichirConversations() {
    try {
      const liste = await listerConversations();
      setConversations(liste);
    } catch (e) {
      setErreur(e.message);
    }
  }

  function nouvelleConversation() {
    setConversationActiveId(genererId());
    setMessages([]);
    setErreur(null);
  }

  async function ouvrirConversation(id) {
    setErreur(null);
    try {
      const conv = await obtenirConversation(id);
      setConversationActiveId(id);
      setMessages(conv.messages);
    } catch (e) {
      setErreur(e.message);
    }
  }

  async function supprimer(id, evenement) {
    evenement.stopPropagation();
    try {
      await supprimerConversation(id);
      if (id === conversationActiveId) {
        setConversationActiveId(null);
        setMessages([]);
      }
      rafraichirConversations();
    } catch (e) {
      setErreur(e.message);
    }
  }

  async function envoyer(evenement) {
    evenement.preventDefault();
    const texteQuestion = question.trim();
    if (!texteQuestion || chargement) return;

    const id = conversationActiveId ?? genererId();
    if (!conversationActiveId) setConversationActiveId(id);

    setMessages((prev) => [...prev, { role: "user", contenu: texteQuestion }]);
    setQuestion("");
    setChargement(true);
    setErreur(null);

    try {
      const resultat = await envoyerMessage(id, texteQuestion);
      setMessages((prev) => [
        ...prev,
        {
          role: "assistant",
          contenu: resultat.reponse,
          chunks: resultat.chunks,
          fiable: resultat.fiable,
        },
      ]);
      rafraichirConversations();
    } catch (e) {
      setErreur(e.message);
      setMessages((prev) => prev.slice(0, -1));
    } finally {
      setChargement(false);
    }
  }

  return (
    <div className="flex h-screen bg-slate-950 text-slate-100">
      <aside className="w-72 shrink-0 border-r border-slate-800 flex flex-col">
        <div className="p-4 border-b border-slate-800">
          <h1 className="text-lg font-semibold flex items-center gap-2">
            <span className="text-indigo-400">◆</span> {NOM_APP}
          </h1>
          <p className="text-xs text-slate-500 mt-1">
            Assistant documentaire — RAG interne
          </p>
        </div>

        <button
          onClick={nouvelleConversation}
          className="m-3 px-3 py-2 rounded-lg bg-indigo-600 hover:bg-indigo-500 transition-colors text-sm font-medium"
        >
          + Nouvelle conversation
        </button>

        <div className="flex-1 overflow-y-auto px-2 space-y-1">
          {conversations.length === 0 && (
            <p className="text-xs text-slate-600 px-2 py-4 text-center">
              Aucune conversation pour l'instant
            </p>
          )}
          {conversations.map((conv) => (
            <div
              key={conv.id}
              onClick={() => ouvrirConversation(conv.id)}
              className={`group flex items-center justify-between gap-2 px-3 py-2 rounded-lg cursor-pointer text-sm transition-colors ${
                conv.id === conversationActiveId
                  ? "bg-slate-800 text-slate-100"
                  : "text-slate-400 hover:bg-slate-900 hover:text-slate-200"
              }`}
            >
              <span className="truncate">{conv.titre}</span>
              <button
                onClick={(e) => supprimer(conv.id, e)}
                className="opacity-0 group-hover:opacity-100 text-slate-500 hover:text-red-400 transition-opacity shrink-0"
                title="Supprimer"
              >
                ✕
              </button>
            </div>
          ))}
        </div>
      </aside>

      <main className="flex-1 flex flex-col">
        <header className="border-b border-slate-800 px-6 py-4">
          <p className="text-sm text-slate-400">
            Réponses générées uniquement à partir des documents internes — jamais inventées.
          </p>
        </header>

        <div className="flex-1 overflow-y-auto px-6 py-6 space-y-6">
          {messages.length === 0 && (
            <div className="h-full flex items-center justify-center text-slate-600 text-sm">
              Pose une question pour commencer.
            </div>
          )}

          {messages.map((m, i) => (
            <MessageBulle key={i} message={m} />
          ))}

          {chargement && (
  <div className="flex items-center gap-3 text-slate-500 text-sm bg-slate-900/50 rounded-lg px-4 py-3">
    <div className="flex gap-1">
      <span className="w-2 h-2 bg-indigo-400 rounded-full animate-bounce" style={{animationDelay: '0s'}}></span>
      <span className="w-2 h-2 bg-indigo-400 rounded-full animate-bounce" style={{animationDelay: '0.2s'}}></span>
      <span className="w-2 h-2 bg-indigo-400 rounded-full animate-bounce" style={{animationDelay: '0.4s'}}></span>
    </div>
    <span>Recherche et génération en cours...</span>
  </div>
)}

          {erreur && (
            <div className="text-sm text-red-400 bg-red-950/40 border border-red-900 rounded-lg px-4 py-2">
              {erreur}
            </div>
          )}

          <div ref={finMessagesRef} />
        </div>

        <form onSubmit={envoyer} className="border-t border-slate-800 p-4 flex gap-2">
          <input
            value={question}
            onChange={(e) => setQuestion(e.target.value)}
            placeholder="Pose ta question ici..."
            className="flex-1 bg-slate-900 border border-slate-800 rounded-lg px-4 py-2.5 text-sm focus:outline-none focus:ring-2 focus:ring-indigo-600 placeholder:text-slate-600"
          />
          <button
            type="submit"
            disabled={chargement}
            className="px-5 py-2.5 rounded-lg bg-indigo-600 hover:bg-indigo-500 disabled:opacity-40 disabled:cursor-not-allowed transition-colors text-sm font-medium"
          >
            Envoyer
          </button>
        </form>
      </main>
    </div>
  );
}

function MessageBulle({ message }) {
  const estUtilisateur = message.role === "user";
  const [copie, setCopie] = useState(false);

  const copierReponse = async () => {
    try {
      await navigator.clipboard.writeText(message.contenu);
      setCopie(true);
      setTimeout(() => setCopie(false), 2000);
    } catch (err) {
      console.error("Erreur de copie:", err);
    }
  };

  return (
    <div className={`flex ${estUtilisateur ? "justify-end" : "justify-start"}`}>
      <div
        className={`max-w-2xl rounded-2xl px-4 py-3 text-sm leading-relaxed ${
          estUtilisateur
            ? "bg-indigo-600 text-white"
            : "bg-slate-900 border border-slate-800 text-slate-100"
        }`}
      >
        {estUtilisateur ? (
          <p className="whitespace-pre-wrap">{message.contenu}</p>
        ) : (
          <>
            <div className="markdown-content">
              <ReactMarkdown
                components={{
                  code({node, inline, className, children, ...props}) {
                    const match = /language-(\w+)/.exec(className || '');
                    return !inline && match ? (
                      <SyntaxHighlighter
                        style={vscDarkPlus}
                        language={match[1]}
                        PreTag="div"
                        {...props}
                      >
                        {String(children).replace(/\n$/, '')}
                      </SyntaxHighlighter>
                    ) : (
                      <code className={className} {...props}>
                        {children}
                      </code>
                    );
                  },
                  h1: ({node, ...props}) => (
                    <h1 style={{fontSize: '1.5rem', fontWeight: 'bold', marginTop: '1rem', marginBottom: '0.5rem'}} {...props} />
                  ),
                  h2: ({node, ...props}) => (
                    <h2 style={{fontSize: '1.25rem', fontWeight: 'bold', marginTop: '0.75rem', marginBottom: '0.5rem'}} {...props} />
                  ),
                  h3: ({node, ...props}) => (
                    <h3 style={{fontSize: '1.1rem', fontWeight: 'bold', marginTop: '0.5rem', marginBottom: '0.25rem'}} {...props} />
                  ),
                  strong: ({node, ...props}) => (
                    <strong style={{fontWeight: 'bold', color: '#818cf8'}} {...props} />
                  ),
                  ul: ({node, ...props}) => (
                    <ul style={{listStyleType: 'disc', paddingLeft: '1.5rem', marginTop: '0.5rem', marginBottom: '0.5rem'}} {...props} />
                  ),
                  ol: ({node, ...props}) => (
                    <ol style={{listStyleType: 'decimal', paddingLeft: '1.5rem', marginTop: '0.5rem', marginBottom: '0.5rem'}} {...props} />
                  ),
                  li: ({node, ...props}) => (
                    <li style={{marginTop: '0.25rem', marginBottom: '0.25rem'}} {...props} />
                  ),
                  p: ({node, ...props}) => (
                    <p style={{marginTop: '0.5rem', marginBottom: '0.5rem', lineHeight: '1.6'}} {...props} />
                  ),
                }}
              >
                {message.contenu}
              </ReactMarkdown>
            </div>

            {/* ✅ AJOUT DU BOUTON COPIER ICI */}
            <button
              onClick={copierReponse}
              className="mt-3 text-xs text-slate-500 hover:text-slate-300 transition-colors flex items-center gap-1"
            >
              {copie ? '✅ Copié !' : '📋 Copier'}
            </button>
          </>
        )}

        {!estUtilisateur && message.chunks?.length > 0 && (
          <details className="mt-3 pt-3 border-t border-slate-800">
            <summary className="text-xs text-slate-500 cursor-pointer hover:text-slate-300">
              📄 {message.chunks.length} document(s) consulté(s)
            </summary>
            <div className="mt-2 space-y-2">
              {message.chunks.map((c, i) => (
                <div key={i} className="bg-slate-950 border border-slate-800 rounded-lg p-2">
                  <div className="flex justify-between items-center">
                    <span className="text-xs font-medium text-slate-300">
                      {c.document_source}
                    </span>
                    <span className="text-xs text-indigo-400">
                      {Math.round(c.score * 100)}%
                    </span>
                  </div>
                  <p className="text-xs text-slate-500 mt-1 line-clamp-2">{c.texte}</p>
                </div>
              ))}
            </div>
          </details>
        )}

        {!estUtilisateur && message.fiable === false && (
          <p className="mt-2 text-xs text-amber-500">
            ⚠ Réponse hors du périmètre des documents disponibles
          </p>
        )}
      </div>
    </div>
  );
}