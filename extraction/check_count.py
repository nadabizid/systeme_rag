"""Vérification rapide : combien de documents sont réellement dans l'index."""
import time
from bulk_index import get_client, INDEX_NAME

client = get_client()

for tentative in range(4):
    total = client.count(index=INDEX_NAME)["count"]
    print(f"Tentative {tentative + 1} : {total} document(s) dans l'index")
    if total > 0:
        break
    if tentative < 3:
        print("  ...rien pour l'instant, attente 10s (cohérence éventuelle d'OpenSearch Serverless)")
        time.sleep(10)
