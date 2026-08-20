"""
US 1.1 — Point d'entrée : S3 -> extraction -> nettoyage -> sauvegarde locale (JSON)
Usage : python main.py
"""
import json
import os
from pathlib import Path

from s3_reader import lister_documents, telecharger_document
from text_extractor import extraire_document

DOSSIER_SORTIE = Path("./output_extraction")


def main():
    DOSSIER_SORTIE.mkdir(exist_ok=True)

    cles = lister_documents()
    print(f"{len(cles)} document(s) à traiter.")

    resultats = []
    erreurs = []

    for cle in cles:
        try:
            chemin_local = telecharger_document(cle)
            resultat = extraire_document(chemin_local, source_key=cle)
            resultats.append(resultat)

            nom_sortie = DOSSIER_SORTIE / f"{Path(cle).stem}.json"
            with open(nom_sortie, "w", encoding="utf-8") as f:
                json.dump(resultat, f, ensure_ascii=False, indent=2)

            print(f"  ✓ {cle} -> {resultat['metadonnees']['nb_caracteres']} caractères extraits")

            try:
                os.unlink(chemin_local)
            except OSError:
                pass  # nettoyage best-effort, ne doit pas faire échouer le pipeline

        except Exception as e:
            print(f"  ✗ {cle} -> ERREUR: {e}")
            erreurs.append({"fichier": cle, "erreur": str(e)})

    print(f"\nTerminé : {len(resultats)} succès, {len(erreurs)} échec(s).")
    if erreurs:
        with open(DOSSIER_SORTIE / "_erreurs.json", "w", encoding="utf-8") as f:
            json.dump(erreurs, f, ensure_ascii=False, indent=2)


if __name__ == "__main__":
    main()