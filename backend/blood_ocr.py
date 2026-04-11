"""Blood panel PDF OCR — Mistral files upload + OCR + biomarker extraction.

Flow:
    1. Upload the PDF to Mistral files API with purpose='ocr'.
    2. Get a signed URL for the uploaded file.
    3. Run `ocr.process` to get markdown for every page.
    4. Ask the LLM to extract known biomarkers from the markdown as JSON.

No memory side-effects — the endpoint just returns the extracted data and
the frontend decides what to do with it.
"""
from __future__ import annotations

import json
import logging
from typing import Any

from mistralai.client import Mistral

from backend.config import LLM_MODEL, OCR_MODEL

log = logging.getLogger(__name__)


# Biomarkers we try to pull out of a routine French blood panel.
# Keys are the JSON fields returned to the frontend.
BIOMARKER_LABELS: dict[str, str] = {
    "glucose": "Glycemie a jeun",
    "hba1c": "HbA1c",
    "cholesterol_total": "Cholesterol total",
    "ldl": "LDL cholesterol",
    "hdl": "HDL cholesterol",
    "triglycerides": "Triglycerides",
    "ferritin": "Ferritine",
    "vitamin_d": "Vitamine D (25-OH)",
    "vitamin_b12": "Vitamine B12",
    "tsh": "TSH",
    "creatinine": "Creatinine",
    "crp": "CRP",
    "hemoglobin": "Hemoglobine",
    "hematocrit": "Hematocrite",
    "platelets": "Plaquettes",
    "wbc": "Leucocytes",
}


_EXTRACTION_SYSTEM = """Tu extrais des biomarqueurs depuis un bilan sanguin au format markdown.

Pour chaque biomarqueur trouve dans le document, renvoie un objet JSON :
{{
  "glucose": {{"value": 0.95, "unit": "g/L"}},
  "hba1c": {{"value": 5.4, "unit": "%"}}
}}

Cles JSON attendues (utilise EXACTEMENT ces cles) :
{fields_doc}

REGLES :
- Si un biomarqueur n'est PAS dans le document, NE L'INCLUS PAS.
- Garde les unites telles qu'ecrites dans le document (g/L, mmol/L, %, ng/mL, etc.).
- Accepte le point ou la virgule pour les decimales. Renvoie un nombre JSON.
- Ignore les colonnes "valeurs de reference" / "normes" — tu veux LA valeur du patient.
- Reponds uniquement le JSON, rien d'autre.
"""


def _fields_doc() -> str:
    return "\n".join(f"- {key} : {label}" for key, label in BIOMARKER_LABELS.items())


def ocr_pdf(client: Mistral, pdf_bytes: bytes, filename: str = "bilan.pdf") -> str:
    """Upload the PDF, run OCR, return the concatenated markdown of all pages."""
    uploaded = client.files.upload(
        file={"file_name": filename, "content": pdf_bytes},
        purpose="ocr",
    )
    signed = client.files.get_signed_url(file_id=uploaded.id)
    result = client.ocr.process(
        model=OCR_MODEL,
        document={"type": "document_url", "document_url": signed.url},
    )
    pages = result.pages or []
    return "\n\n".join(getattr(p, "markdown", "") or "" for p in pages)


def extract_biomarkers(client: Mistral, markdown: str) -> dict[str, Any]:
    """Call the LLM to extract structured biomarkers from OCR markdown."""
    if not markdown.strip():
        return {}

    system = _EXTRACTION_SYSTEM.format(fields_doc=_fields_doc())
    try:
        response = client.chat.complete(
            model=LLM_MODEL,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": markdown},
            ],
            response_format={"type": "json_object"},
        )
        parsed = json.loads(response.choices[0].message.content)
    except Exception:
        log.exception("biomarker extraction failed")
        return {}

    if not isinstance(parsed, dict):
        return {}

    cleaned: dict[str, Any] = {}
    for key, raw in parsed.items():
        if key not in BIOMARKER_LABELS or not isinstance(raw, dict):
            continue
        value = raw.get("value")
        try:
            if isinstance(value, str):
                value = value.replace(",", ".")
            number = float(value)
        except (TypeError, ValueError):
            continue
        cleaned[key] = {"value": number, "unit": str(raw.get("unit", ""))}
    return cleaned


def process_blood_panel(
    client: Mistral,
    pdf_bytes: bytes,
    filename: str = "bilan.pdf",
) -> dict:
    """End-to-end: PDF bytes -> OCR markdown -> structured biomarkers."""
    markdown = ocr_pdf(client, pdf_bytes, filename=filename)
    biomarkers = extract_biomarkers(client, markdown)
    return {
        "biomarkers": biomarkers,
        "markdown": markdown,
        "page_count": len([p for p in markdown.split("\n\n") if p.strip()]) or 0,
    }
