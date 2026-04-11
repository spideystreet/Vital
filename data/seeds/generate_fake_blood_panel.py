"""Generate a fake French blood panel PDF to test backend/blood_ocr.py.

Run with:
    uv run --with reportlab python data/seeds/generate_fake_blood_panel.py

Output: data/seeds/fake_bilan_sanguin.pdf
"""
from __future__ import annotations

from pathlib import Path

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import mm
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
)


OUT = Path(__file__).parent / "fake_bilan_sanguin.pdf"


HEADER = [
    ("Parametre", "Resultat", "Unite", "Valeurs de reference"),
]

# Mix of normal and slightly off values so extraction has something interesting to surface.
ROWS_BIOCHEMISTRY = [
    ("Glycemie a jeun",       "1,02", "g/L",   "0,74 - 1,06"),
    ("HbA1c",                 "5,4",  "%",     "< 6,0"),
    ("Cholesterol total",     "2,15", "g/L",   "< 2,00"),
    ("LDL cholesterol",       "1,38", "g/L",   "< 1,60"),
    ("HDL cholesterol",       "0,52", "g/L",   "> 0,40"),
    ("Triglycerides",         "1,24", "g/L",   "< 1,50"),
    ("Creatinine",            "9,8",  "mg/L",  "7,0 - 13,0"),
    ("CRP",                   "2,1",  "mg/L",  "< 5,0"),
]

ROWS_VITAMINS = [
    ("Ferritine",             "78",   "ng/mL", "30 - 400"),
    ("Vitamine D (25-OH)",    "22",   "ng/mL", "30 - 100"),
    ("Vitamine B12",          "310",  "pg/mL", "200 - 900"),
    ("TSH",                   "1,8",  "mUI/L", "0,4 - 4,0"),
]

ROWS_HEMATOLOGY = [
    ("Hemoglobine",           "14,6", "g/dL",  "13,0 - 17,0"),
    ("Hematocrite",           "43,2", "%",     "40,0 - 52,0"),
    ("Plaquettes",            "245",  "10^9/L","150 - 400"),
    ("Leucocytes",            "6,4",  "10^9/L","4,0 - 10,0"),
]


def build_section(title: str, rows: list[tuple[str, str, str, str]]) -> list:
    styles = getSampleStyleSheet()
    h = ParagraphStyle(
        "section",
        parent=styles["Heading3"],
        textColor=colors.HexColor("#1f2d3d"),
        spaceAfter=4,
    )
    data = HEADER + rows
    table = Table(data, colWidths=[70 * mm, 30 * mm, 25 * mm, 50 * mm])
    table.setStyle(
        TableStyle([
            ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#e6edf5")),
            ("TEXTCOLOR", (0, 0), (-1, 0), colors.HexColor("#1f2d3d")),
            ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
            ("FONTNAME", (0, 1), (-1, -1), "Helvetica"),
            ("FONTSIZE", (0, 0), (-1, -1), 9),
            ("GRID", (0, 0), (-1, -1), 0.25, colors.HexColor("#b0bec5")),
            ("ALIGN", (1, 0), (-1, -1), "LEFT"),
            ("VALIGN", (0, 0), (-1, -1), "MIDDLE"),
            ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f6f8fa")]),
            ("LEFTPADDING", (0, 0), (-1, -1), 6),
            ("RIGHTPADDING", (0, 0), (-1, -1), 6),
            ("TOPPADDING", (0, 0), (-1, -1), 4),
            ("BOTTOMPADDING", (0, 0), (-1, -1), 4),
        ])
    )
    return [Paragraph(title, h), Spacer(1, 3), table, Spacer(1, 10)]


def main() -> None:
    doc = SimpleDocTemplate(
        str(OUT),
        pagesize=A4,
        leftMargin=18 * mm,
        rightMargin=18 * mm,
        topMargin=18 * mm,
        bottomMargin=18 * mm,
        title="Bilan sanguin — fake",
        author="V.I.T.A.L test fixture",
    )
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        "title",
        parent=styles["Title"],
        fontSize=16,
        textColor=colors.HexColor("#1f2d3d"),
        spaceAfter=4,
    )
    meta_style = ParagraphStyle(
        "meta",
        parent=styles["Normal"],
        fontSize=9,
        textColor=colors.HexColor("#5f6b7a"),
        spaceAfter=10,
    )

    story: list = []
    story.append(Paragraph("Laboratoire d'Analyses Medicales LAM-EXEMPLE", title_style))
    story.append(Paragraph(
        "Patient : DUPONT Jean &nbsp;&nbsp;|&nbsp;&nbsp; Ne le : 12/06/1988 "
        "&nbsp;&nbsp;|&nbsp;&nbsp; Sexe : M "
        "&nbsp;&nbsp;|&nbsp;&nbsp; Preleve le : 08/04/2026 07:42 "
        "&nbsp;&nbsp;|&nbsp;&nbsp; Medecin : Dr MARTIN",
        meta_style,
    ))
    story.append(Paragraph("Bilan sanguin — Resultats", styles["Heading2"]))
    story.append(Spacer(1, 6))

    story += build_section("Biochimie", ROWS_BIOCHEMISTRY)
    story += build_section("Vitamines et hormones", ROWS_VITAMINS)
    story += build_section("Hematologie", ROWS_HEMATOLOGY)

    footer = ParagraphStyle(
        "footer",
        parent=styles["Normal"],
        fontSize=8,
        textColor=colors.HexColor("#8795a1"),
    )
    story.append(Spacer(1, 8))
    story.append(Paragraph(
        "Document fictif genere pour tester backend/blood_ocr.py — ne pas utiliser a des fins medicales.",
        footer,
    ))

    doc.build(story)
    print(f"wrote {OUT}")


if __name__ == "__main__":
    main()
