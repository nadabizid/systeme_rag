"""
US 1.1 — Lecture des documents depuis Amazon S3
"""
import os
import tempfile
from pathlib import Path

import boto3
from dotenv import load_dotenv

load_dotenv()

BUCKET_NAME = os.getenv("S3_BUCKET_NAME")
EXTENSIONS_SUPPORTEES = {".pdf", ".docx"}


def lister_documents(bucket: str = None, prefix: str = "") -> list[str]:
    """Liste les clés (chemins) des fichiers PDF/DOCX présents dans le bucket."""
    bucket = bucket or BUCKET_NAME
    s3 = boto3.client("s3")
    cles = []

    paginator = s3.get_paginator("list_objects_v2")
    for page in paginator.paginate(Bucket=bucket, Prefix=prefix):
        for obj in page.get("Contents", []):
            key = obj["Key"]
            if Path(key).suffix.lower() in EXTENSIONS_SUPPORTEES:
                cles.append(key)

    return cles


def telecharger_document(cle: str, bucket: str = None) -> str:
    """Télécharge un document S3 vers un fichier temporaire local et retourne le chemin."""
    bucket = bucket or BUCKET_NAME
    s3 = boto3.client("s3")

    suffixe = Path(cle).suffix
    fichier_temp = tempfile.NamedTemporaryFile(delete=False, suffix=suffixe)
    fichier_temp.close()  # Important sur Windows : libère le verrou du fichier
                           # avant que S3 et pdfplumber/python-docx n'y accèdent
    s3.download_file(bucket, cle, fichier_temp.name)

    return fichier_temp.name


if __name__ == "__main__":
    # Test rapide : liste les documents disponibles dans le bucket configuré
    documents = lister_documents()
    print(f"{len(documents)} document(s) trouvé(s) dans {BUCKET_NAME} :")
    for doc in documents:
        print(f"  - {doc}")