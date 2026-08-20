const BASE_URL = "http://localhost:8000";

export async function listerConversations() {
  const res = await fetch(`${BASE_URL}/conversations`);
  if (!res.ok) throw new Error("Impossible de charger les conversations");
  return res.json();
}

export async function obtenirConversation(id) {
  const res = await fetch(`${BASE_URL}/conversations/${id}`);
  if (!res.ok) throw new Error("Conversation introuvable");
  return res.json();
}

export async function envoyerMessage(conversationId, question) {
  const res = await fetch(`${BASE_URL}/conversations/${conversationId}/messages`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ question }),
  });
  if (!res.ok) throw new Error("Échec de l'envoi du message");
  return res.json();
}

export async function supprimerConversation(id) {
  const res = await fetch(`${BASE_URL}/conversations/${id}`, { method: "DELETE" });
  if (!res.ok) throw new Error("Échec de la suppression");
  return res.json();
}
