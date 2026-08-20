"""
Rapport de latence — agrège les mesures de monitoring_latency.json
pour calculer moyenne/min/max par étape (diagnostic Bug 2 du cahier :
lenteur de la recherche OpenSearch).
"""
import json
from pathlib import Path
from statistics import mean

FICHIER_LATENCE = Path("./monitoring_latency.json")
FICHIER_RAPPORT = Path("./latency_report.json")

SEUIL_ALERTE_RECHERCHE_S = 3  # au-delà, on suspecte le Bug 2 (timeouts OpenSearch)


def generer_rapport():
    if not FICHIER_LATENCE.exists():
        print("Aucune mesure trouvée — lance latency_monitor.py au moins une fois d'abord.")
        return

    with open(FICHIER_LATENCE, encoding="utf-8") as f:
        historique = json.load(f)

    if not historique:
        print("Fichier de mesures vide.")
        return

    etapes = historique[0]["mesures_secondes"].keys()
    rapport = {}

    for etape in etapes:
        valeurs = [h["mesures_secondes"][etape] for h in historique if etape in h["mesures_secondes"]]
        rapport[etape] = {
            "moyenne_s": round(mean(valeurs), 4),
            "min_s": round(min(valeurs), 4),
            "max_s": round(max(valeurs), 4),
            "nb_mesures": len(valeurs),
        }

    print(f"Rapport basé sur {len(historique)} requête(s) mesurée(s) :\n")
    for etape, stats in rapport.items():
        print(f"  {etape:25s} moyenne={stats['moyenne_s']}s  min={stats['min_s']}s  max={stats['max_s']}s")

    with open(FICHIER_RAPPORT, "w", encoding="utf-8") as f:
        json.dump(rapport, f, ensure_ascii=False, indent=2)

    if "recherche_opensearch" in rapport and rapport["recherche_opensearch"]["max_s"] > SEUIL_ALERTE_RECHERCHE_S:
        print(f"\n⚠ La recherche OpenSearch a dépassé {SEUIL_ALERTE_RECHERCHE_S}s au moins une fois "
              "(Bug 2 du cahier — envisager d'augmenter les OCU ou d'optimiser la requête k-NN).")


if __name__ == "__main__":
    generer_rapport()
