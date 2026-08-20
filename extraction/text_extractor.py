"""
US 1.1 — Extraction du texte des documents
Lit des fichiers PDF/DOCX et retourne le texte brut nettoyé + métadonnées.
"""
import re
import os
from datetime import datetime, timezone
from pathlib import Path

import pdfplumber
from docx import Document as DocxDocument
from docx.oxml.ns import qn
from docx.text.paragraph import Paragraph
from docx.table import Table


def extract_pdf(filepath: str) -> str:
    """Extrait le texte d'un PDF, page par page, en préservant les tableaux
    sans dupliquer leur contenu dans le texte brut (les tableaux sont
    retirés de la zone de texte avant extraction du reste)."""
    texte_complet = []
    with pdfplumber.open(filepath) as pdf:
        for page in pdf.pages:
            tables = page.find_tables()

            # Exclut la zone de chaque tableau avant d'extraire le texte "normal"
            # pour éviter que son contenu apparaisse deux fois (une fois brut,
            # une fois proprement structuré dans [TABLEAU])
            page_hors_tableaux = page
            for table in tables:
                page_hors_tableaux = page_hors_tableaux.outside_bbox(table.bbox)

            texte_page = page_hors_tableaux.extract_text() or ""
            texte_complet.append(texte_page)

            for table in tables:
                donnees = table.extract()
                lignes = ["\t".join(str(cell) if cell else "" for cell in row) for row in donnees]
                texte_complet.append("\n[TABLEAU]\n" + "\n".join(lignes) + "\n[/TABLEAU]\n")

    return "\n".join(texte_complet)


def _iter_block_items(doc):
    """Parcourt le corps du document DOCX dans l'ordre réel (paragraphes ET
    tableaux mélangés tels qu'ils apparaissent), au lieu des collections
    séparées doc.paragraphs / doc.tables qui perdent l'ordre d'origine."""
    body = doc.element.body
    for child in body.iterchildren():
        if child.tag == qn("w:p"):
            yield Paragraph(child, doc)
        elif child.tag == qn("w:tbl"):
            yield Table(child, doc)


def extract_docx(filepath: str) -> str:
    """Extrait le texte d'un fichier Word en préservant l'ordre réel
    paragraphes/tableaux (cf. Bug 3 du cahier des charges : un tableau
    extrait hors de son contexte devient incompréhensible pour le LLM)."""
    doc = DocxDocument(filepath)
    morceaux = []

    for block in _iter_block_items(doc):
        if isinstance(block, Paragraph):
            if block.text.strip():
                morceaux.append(block.text)
        elif isinstance(block, Table):
            lignes = ["\t".join(cell.text for cell in row.cells) for row in block.rows]
            morceaux.append("\n[TABLEAU]\n" + "\n".join(lignes) + "\n[/TABLEAU]\n")

    return "\n".join(morceaux)


def nettoyer_texte(texte: str) -> str:
    """Nettoie le texte extrait : espaces multiples, caractères de contrôle,
    sauts de ligne excessifs — sans casser les tableaux marqués."""
    texte = texte.replace("\x00", "")
    texte = re.sub(r"[ \t]+", " ", texte)          # espaces multiples -> un seul
    texte = re.sub(r"\n{3,}", "\n\n", texte)         # +2 lignes vides -> 1 seule
    texte = "\n".join(line.strip() for line in texte.split("\n"))
    return texte.strip()


def extraire_document(filepath: str, source_bucket: str = None, source_key: str = None) -> dict:
    """
    Point d'entrée principal : détecte le type de fichier, extrait, nettoie,
    et retourne un dict avec le texte + les métadonnées (US 1.1, critère
    "les métadonnées de base -nom du fichier, date- sont conservées").
    """
    ext = Path(filepath).suffix.lower()

    if ext == ".pdf":
        texte_brut = extract_pdf(filepath)
    elif ext == ".docx":
        texte_brut = extract_docx(filepath)
    else:
        raise ValueError(f"Extension non supportée: {ext} (seuls .pdf et .docx sont gérés pour US 1.1)")

    texte_nettoye = nettoyer_texte(texte_brut)

    nom_fichier = source_key if source_key else Path(filepath).name

    metadonnees = {
        
        "nom_fichier": nom_fichier,
        "type": ext.replace(".", ""),
        "date_extraction": datetime.now(timezone.utc).isoformat(),
        "source_bucket": source_bucket,
        "source_key": source_key,
        "nb_caracteres": len(texte_nettoye),
    }

    return {"texte": texte_nettoye, "metadonnees": metadonnees}


if __name__ == "__main__":
    # Test rapide en local avant de brancher S3 (voir s3_reader.py)
    import sys
    resultat = extraire_document(sys.argv[1])
    print("--- Métadonnées ---")
    print(resultat["metadonnees"])
    print("\n--- Aperçu du texte (500 premiers caractères) ---")
    print(resultat["texte"][:500])