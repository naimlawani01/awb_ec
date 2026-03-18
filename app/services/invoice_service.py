"""Invoice generation service - Word document (Delphinus format)."""
from datetime import datetime
from io import BytesIO
from typing import Optional, Dict, Any

from docx import Document as DocxDocument
from docx.shared import Pt
from docx.enum.text import WD_ALIGN_PARAGRAPH

from app.utils.number_to_words import number_to_french_words


def generate_invoice_word(
    document,
    awb_details: Optional[Dict[str, Any]],
    amount_usd: float,
    usd_to_gnf: int,
) -> bytes:
    """
    Generate invoice as Word document (Delphinus format).
    Returns docx file as bytes.
    """
    doc = DocxDocument()
    
    # Set default font
    style = doc.styles['Normal']
    font = style.font
    font.name = 'Times New Roman'
    font.size = Pt(12)
    
    def add_para(text: str, size_pt: int = 12, bold: bool = False, align: str = None):
        p = doc.add_paragraph()
        run = p.add_run(text)
        run.font.name = 'Times New Roman'
        run.font.size = Pt(size_pt)
        run.bold = bold
        if align == 'right':
            p.alignment = WD_ALIGN_PARAGRAPH.RIGHT
        return p
    
    # Date
    doc_date = document.document_date.strftime('%d %B %Y') if document.document_date else '-'
    # French month names
    months_fr = {'January': 'janvier', 'February': 'février', 'March': 'mars', 'April': 'avril',
                 'May': 'mai', 'June': 'juin', 'July': 'juillet', 'August': 'août',
                 'September': 'septembre', 'October': 'octobre', 'November': 'novembre',
                 'December': 'décembre'}
    for en, fr in months_fr.items():
        doc_date = doc_date.replace(en, fr)
    
    add_para(f'Conakry, le {doc_date}', 14)
    
    invoice_number = document.reference_number or f"{document.document_number or document.id}/EC/{datetime.now().strftime('%d/%m/%y')}"
    add_para(f"Facture N° {invoice_number}", 14, bold=True)
    doc.add_paragraph()
    
    # Client (right aligned, no border)
    client_name = document.consignee or document.shipper or 'Client'
    client_para = doc.add_paragraph()
    client_para.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    run = client_para.add_run(f'Client :\n{client_name}')
    run.font.name = 'Times New Roman'
    run.font.size = Pt(12)
    if awb_details and awb_details.get('consignee_details'):
        run = client_para.add_run(f'\n{awb_details["consignee_details"]}')
        run.font.name = 'Times New Roman'
        run.font.size = Pt(12)
    doc.add_paragraph()
    
    # Route
    awb_details = awb_details or {}
    origin_code = (awb_details.get('routing', {}).get('departure_code') or document.origin or '---')[:3].upper()
    to_list = awb_details.get('routing', {}).get('to') or []
    dest_code = (to_list[-1] if to_list else document.destination or '---')[:3].upper()
    route = f'{origin_code}-{dest_code}'.replace('---', '-')
    
    total_pieces = 0
    total_weight = 0.0
    weight_scale = 'K'
    nature_desc = 'Transport aérien'
    if awb_details:
        rd = awb_details.get('rate_description') or {}
        total_pieces = rd.get('total_pieces') or awb_details.get('total_pieces') or 0
        total_weight = rd.get('total_weight') or awb_details.get('total_weight') or 0.0
        weight_scale = rd.get('weight_scale') or awb_details.get('weight_scale') or 'K'
        items = rd.get('items') or []
        if items:
            nature_desc = items[0].get('nature') or 'Marchandises'
    weight_label = 'Kg' if weight_scale == 'K' else weight_scale
    
    pieces_part = f'{total_pieces} colis' if total_pieces else ''
    weight_part = f'{total_weight} {weight_label}' if total_weight else ''
    libelle = f"Transport de {pieces_part} {weight_part} de {nature_desc} {route}".strip()
    
    add_para("Nature de l'opération :", 12, bold=True)
    add_para(libelle)
    add_para(f"LTA : {document.document_number or '-'}")
    doc.add_paragraph()
    
    add_para("Montant Total de l'opération :", 12, bold=True)
    add_para(f"{amount_usd:,.2f} USD (1 USD = {usd_to_gnf:,} GNF)")
    doc.add_paragraph()
    
    # Table
    currency = (awb_details or {}).get('currency') or 'USD'
    total_gnf = round(amount_usd * usd_to_gnf)
    
    table = doc.add_table(rows=3, cols=5)
    table.style = 'Table Grid'
    hdr = table.rows[0].cells
    headers = ['N°', 'LIBELLE', 'NOMBRE', f'Montant en {currency}', 'MONTANT en GNF']
    for i, h in enumerate(headers):
        hdr[i].text = h
        for p in hdr[i].paragraphs:
            for r in p.runs:
                r.font.bold = True
                r.font.name = 'Times New Roman'
                r.font.size = Pt(12)
    
    data_row = table.rows[1].cells
    data_row[0].text = '1'
    data_row[1].text = f"{libelle} {document.document_number or ''}"
    data_row[2].text = f'{total_pieces} colis'
    data_row[3].text = f'{amount_usd:,.2f}'
    data_row[4].text = f'{total_gnf:,}'
    for cell in data_row:
        for p in cell.paragraphs:
            for r in p.runs:
                r.font.name = 'Times New Roman'
                r.font.size = Pt(12)
    
    total_row = table.rows[2].cells
    total_row[0].merge(total_row[1])
    total_row[0].merge(total_row[2])
    total_row[0].merge(total_row[3])
    total_row[0].text = 'MONTANT TOTAL'
    total_row[4].text = f'{total_gnf:,}'
    for cell in total_row:
        for p in cell.paragraphs:
            for r in p.runs:
                r.font.bold = True
                r.font.name = 'Times New Roman'
                r.font.size = Pt(12)
    
    doc.add_paragraph()
    
    # Montant total à Payer (no border)
    add_para(f"Montant total à Payer : ………………………. {total_gnf:,} GNF")
    doc.add_paragraph()
    
    # Amount in words
    amount_words = number_to_french_words(total_gnf) + ' francs guinéens.'
    p = doc.add_paragraph()
    run = p.add_run(f"Arrêtée la présente facture à la somme de : {amount_words}")
    run.font.name = 'Times New Roman'
    run.font.size = Pt(12)
    run.italic = True
    doc.add_paragraph()
    
    # Signature
    sig = doc.add_paragraph()
    sig.alignment = WD_ALIGN_PARAGRAPH.RIGHT
    run = sig.add_run('Le Service Administratif & Financier')
    run.font.name = 'Times New Roman'
    run.font.size = Pt(12)
    
    buffer = BytesIO()
    doc.save(buffer)
    buffer.seek(0)
    return buffer.getvalue()
