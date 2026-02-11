"""Export service for generating Excel and PDF reports."""
import io
from datetime import datetime
from typing import List, Dict, Any, Optional
from openpyxl import Workbook
from openpyxl.styles import Font, Alignment, PatternFill, Border, Side
from openpyxl.utils import get_column_letter
from reportlab.lib import colors
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer

from app.models.awb_models import Document, Shipment, Contact
from app.services.awb_parser import AWBParser


class ExportService:
    """Service for exporting data to Excel and PDF formats."""
    
    # Styling constants
    HEADER_FILL = PatternFill(start_color="1F4E79", end_color="1F4E79", fill_type="solid")
    HEADER_FONT = Font(bold=True, color="FFFFFF", size=11)
    BORDER = Border(
        left=Side(style='thin'),
        right=Side(style='thin'),
        top=Side(style='thin'),
        bottom=Side(style='thin')
    )
    
    def export_documents_to_excel(
        self,
        documents: List[Document],
        title: str = "AWB Documents Export"
    ) -> io.BytesIO:
        """Export documents to Excel format."""
        wb = Workbook()
        ws = wb.active
        ws.title = "Documents"
        
        # Headers
        headers = [
            "ID", "Document Number", "Master Doc Number", "Reference",
            "Status", "Type", "Shipper", "Consignee",
            "Origin", "Destination", "Route",
            "Document Date", "Created Date"
        ]
        
        self._write_excel_header(ws, headers, title)
        
        # Data rows
        for row_num, doc in enumerate(documents, start=4):
            ws.cell(row=row_num, column=1, value=doc.id)
            ws.cell(row=row_num, column=2, value=doc.document_number)
            ws.cell(row=row_num, column=3, value=doc.master_document_number)
            ws.cell(row=row_num, column=4, value=doc.reference_number)
            ws.cell(row=row_num, column=5, value=self._get_status_name(doc.status))
            ws.cell(row=row_num, column=6, value=self._get_type_name(doc.document_type))
            ws.cell(row=row_num, column=7, value=doc.shipper)
            ws.cell(row=row_num, column=8, value=doc.consignee)
            ws.cell(row=row_num, column=9, value=doc.origin)
            ws.cell(row=row_num, column=10, value=doc.destination)
            ws.cell(row=row_num, column=11, value=doc.route)
            ws.cell(row=row_num, column=12, value=self._format_date(doc.document_date))
            ws.cell(row=row_num, column=13, value=self._format_date(doc.date_created))
            
            # Apply border to data cells
            for col in range(1, len(headers) + 1):
                ws.cell(row=row_num, column=col).border = self.BORDER
        
        # Adjust column widths
        self._auto_adjust_columns(ws)
        
        # Save to buffer
        buffer = io.BytesIO()
        wb.save(buffer)
        buffer.seek(0)
        
        return buffer
    
    def export_shipments_to_excel(
        self,
        shipments: List[Shipment],
        title: str = "Shipments Export"
    ) -> io.BytesIO:
        """Export shipments to Excel format."""
        wb = Workbook()
        ws = wb.active
        ws.title = "Shipments"
        
        # Headers
        headers = [
            "ID", "Master Number", "House Number", "Reference",
            "Shipper", "Consignee", "Agent",
            "Origin", "Destination", "Shipment Date",
            "Status", "Import/Export"
        ]
        
        self._write_excel_header(ws, headers, title)
        
        # Data rows
        for row_num, ship in enumerate(shipments, start=4):
            ws.cell(row=row_num, column=1, value=ship.id)
            ws.cell(row=row_num, column=2, value=ship.master_number)
            ws.cell(row=row_num, column=3, value=ship.house_number)
            ws.cell(row=row_num, column=4, value=ship.reference_number)
            ws.cell(row=row_num, column=5, value=ship.shipper)
            ws.cell(row=row_num, column=6, value=ship.consignee)
            ws.cell(row=row_num, column=7, value=ship.agent)
            ws.cell(row=row_num, column=8, value=ship.origin)
            ws.cell(row=row_num, column=9, value=ship.destination)
            ws.cell(row=row_num, column=10, value=str(ship.shipment_date) if ship.shipment_date else "")
            ws.cell(row=row_num, column=11, value=ship.event_status)
            ws.cell(row=row_num, column=12, value=self._get_import_export_name(ship.import_export))
            
            # Apply border
            for col in range(1, len(headers) + 1):
                ws.cell(row=row_num, column=col).border = self.BORDER
        
        self._auto_adjust_columns(ws)
        
        buffer = io.BytesIO()
        wb.save(buffer)
        buffer.seek(0)
        
        return buffer
    
    def export_contacts_to_excel(
        self,
        contacts: List[Contact],
        title: str = "Contacts Export"
    ) -> io.BytesIO:
        """Export contacts to Excel format."""
        wb = Workbook()
        ws = wb.active
        ws.title = "Contacts"
        
        headers = ["ID", "Display Name", "Account Number", "Contact Type", "Station ID"]
        
        self._write_excel_header(ws, headers, title)
        
        for row_num, contact in enumerate(contacts, start=4):
            ws.cell(row=row_num, column=1, value=contact.id)
            ws.cell(row=row_num, column=2, value=contact.display_name)
            ws.cell(row=row_num, column=3, value=contact.account_number)
            ws.cell(row=row_num, column=4, value=self._get_contact_type_name(contact.contact_type))
            ws.cell(row=row_num, column=5, value=contact.station_id)
            
            for col in range(1, len(headers) + 1):
                ws.cell(row=row_num, column=col).border = self.BORDER
        
        self._auto_adjust_columns(ws)
        
        buffer = io.BytesIO()
        wb.save(buffer)
        buffer.seek(0)
        
        return buffer
    
    def export_documents_to_pdf(
        self,
        documents: List[Document],
        title: str = "AWB Documents Report"
    ) -> io.BytesIO:
        """Export documents to PDF format."""
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=landscape(A4),
            rightMargin=30,
            leftMargin=30,
            topMargin=30,
            bottomMargin=30
        )
        
        elements = []
        styles = getSampleStyleSheet()
        
        # Title
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=16,
            spaceAfter=20,
            alignment=1  # Center
        )
        elements.append(Paragraph(title, title_style))
        elements.append(Paragraph(
            f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
            styles['Normal']
        ))
        elements.append(Spacer(1, 20))
        
        # Table data
        headers = ["AWB Number", "Shipper", "Consignee", "Origin", "Dest", "Date", "Status"]
        data = [headers]
        
        for doc_item in documents:
            data.append([
                doc_item.document_number or "-",
                (doc_item.shipper or "-")[:30],
                (doc_item.consignee or "-")[:30],
                doc_item.origin or "-",
                doc_item.destination or "-",
                self._format_date(doc_item.document_date),
                self._get_status_name(doc_item.status)
            ])
        
        # Create table
        table = Table(data, repeatRows=1)
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1F4E79')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
            ('BACKGROUND', (0, 1), (-1, -1), colors.white),
            ('TEXTCOLOR', (0, 1), (-1, -1), colors.black),
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
            ('FONTSIZE', (0, 1), (-1, -1), 8),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#F5F5F5')]),
        ]))
        
        elements.append(table)
        
        # Footer
        elements.append(Spacer(1, 20))
        elements.append(Paragraph(
            f"Total Records: {len(documents)}",
            styles['Normal']
        ))
        
        doc.build(elements)
        buffer.seek(0)
        
        return buffer
    
    def export_statistics_to_pdf(
        self,
        stats: Dict[str, Any],
        title: str = "AWB Statistics Report"
    ) -> io.BytesIO:
        """Export statistics to PDF format."""
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            rightMargin=50,
            leftMargin=50,
            topMargin=50,
            bottomMargin=50
        )
        
        elements = []
        styles = getSampleStyleSheet()
        
        # Title
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=18,
            spaceAfter=30,
            alignment=1
        )
        elements.append(Paragraph(title, title_style))
        elements.append(Paragraph(
            f"Report Date: {datetime.now().strftime('%Y-%m-%d %H:%M')}",
            styles['Normal']
        ))
        elements.append(Spacer(1, 30))
        
        # Summary section
        elements.append(Paragraph("Summary", styles['Heading2']))
        elements.append(Spacer(1, 10))
        
        summary_data = [
            ["Total Documents", str(stats.get('total_documents', 0))],
            ["Total Shipments", str(stats.get('total_shipments', 0))],
            ["Total Contacts", str(stats.get('total_contacts', 0))],
            ["Documents Today", str(stats.get('documents_today', 0))],
            ["Documents This Week", str(stats.get('documents_this_week', 0))],
            ["Documents This Month", str(stats.get('documents_this_month', 0))],
        ]
        
        summary_table = Table(summary_data, colWidths=[3*inch, 2*inch])
        summary_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (0, -1), colors.HexColor('#E8E8E8')),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('PADDING', (0, 0), (-1, -1), 8),
        ]))
        elements.append(summary_table)
        
        doc.build(elements)
        buffer.seek(0)
        
        return buffer
    
    def _write_excel_header(self, ws, headers: List[str], title: str):
        """Write Excel header row with styling."""
        # Title row
        ws.merge_cells(start_row=1, start_column=1, end_row=1, end_column=len(headers))
        title_cell = ws.cell(row=1, column=1, value=title)
        title_cell.font = Font(bold=True, size=14)
        title_cell.alignment = Alignment(horizontal='center')
        
        # Date row
        ws.merge_cells(start_row=2, start_column=1, end_row=2, end_column=len(headers))
        date_cell = ws.cell(row=2, column=1, value=f"Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
        date_cell.alignment = Alignment(horizontal='center')
        
        # Header row
        for col_num, header in enumerate(headers, start=1):
            cell = ws.cell(row=3, column=col_num, value=header)
            cell.fill = self.HEADER_FILL
            cell.font = self.HEADER_FONT
            cell.alignment = Alignment(horizontal='center')
            cell.border = self.BORDER
    
    def _auto_adjust_columns(self, ws):
        """Auto-adjust column widths based on content."""
        for column in ws.columns:
            max_length = 0
            column_letter = get_column_letter(column[0].column)
            
            for cell in column:
                try:
                    if len(str(cell.value)) > max_length:
                        max_length = len(str(cell.value))
                except:
                    pass
            
            adjusted_width = min(max_length + 2, 50)
            ws.column_dimensions[column_letter].width = adjusted_width
    
    @staticmethod
    def _format_date(dt) -> str:
        """Format datetime for export."""
        if not dt:
            return "-"
        if isinstance(dt, datetime):
            return dt.strftime('%Y-%m-%d')
        return str(dt)
    
    @staticmethod
    def _get_status_name(status: int) -> str:
        """Get document status name."""
        statuses = {0: "Draft", 1: "Active", 2: "Completed", 3: "Cancelled", 4: "Archived"}
        return statuses.get(status, f"Unknown ({status})")
    
    @staticmethod
    def _get_type_name(doc_type: Optional[int]) -> str:
        """Get document type name."""
        if doc_type is None:
            return "-"
        types = {1: "AWB", 2: "HAWB", 3: "MAWB", 4: "Invoice", 5: "Packing List"}
        return types.get(doc_type, f"Type {doc_type}")
    
    @staticmethod
    def _get_import_export_name(ie_type: Optional[int]) -> str:
        """Get import/export type name."""
        if ie_type is None:
            return "-"
        types = {1: "Import", 2: "Export", 3: "Transit"}
        return types.get(ie_type, f"Type {ie_type}")
    
    @staticmethod
    def _get_contact_type_name(contact_type: int) -> str:
        """Get contact type name."""
        types = {1: "Shipper", 2: "Consignee", 3: "Agent", 4: "Notify", 5: "Forwarder"}
        return types.get(contact_type, f"Type {contact_type}")
    
    def export_detailed_awb_report_excel(
        self,
        documents: List[Document],
        title: str = "Rapport AWB Détaillé"
    ) -> io.BytesIO:
        """
        Export AWB documents with full rate description details to Excel.
        Includes pieces, weights, charges, routing, etc.
        """
        wb = Workbook()
        
        # ========== Feuille 1: Récapitulatif ==========
        ws_summary = wb.active
        ws_summary.title = "Récapitulatif"
        
        headers_summary = [
            "N° AWB", "Référence", "Date", "Expéditeur", "Destinataire",
            "Origine", "Destination", "Pièces", "Poids Brut (kg)", 
            "Poids Taxable (kg)", "Devise", "Total Fret", 
            "Autres Frais", "Total Prépayé", "Statut"
        ]
        
        self._write_excel_header(ws_summary, headers_summary, title)
        
        # Parse all documents and collect data
        parsed_docs = []
        total_pieces = 0
        total_gross_weight = 0
        total_chargeable_weight = 0
        total_freight = 0
        total_other_charges = 0
        total_prepaid = 0
        
        for row_num, doc in enumerate(documents, start=4):
            awb_details = AWBParser.parse(doc.document_data) if doc.document_data else None
            parsed_docs.append((doc, awb_details))
            
            pieces = 0
            gross_weight = 0
            chargeable_weight = 0
            currency = ""
            items_total = 0
            other_charges_sum = 0
            prepaid_total = 0
            
            if awb_details:
                pieces = awb_details.total_pieces
                gross_weight = awb_details.total_weight
                chargeable_weight = sum(item.chargeable_weight for item in awb_details.items)
                currency = awb_details.currency
                items_total = awb_details.items_total
                other_charges_sum = sum(charge.amount for charge in awb_details.other_charges)
                prepaid_total = awb_details.charges_summary.total_prepaid
                
                total_pieces += pieces
                total_gross_weight += gross_weight
                total_chargeable_weight += chargeable_weight
                total_freight += items_total
                total_other_charges += other_charges_sum
                total_prepaid += prepaid_total
            
            ws_summary.cell(row=row_num, column=1, value=doc.document_number)
            ws_summary.cell(row=row_num, column=2, value=doc.reference_number)
            ws_summary.cell(row=row_num, column=3, value=self._format_date(doc.document_date))
            ws_summary.cell(row=row_num, column=4, value=doc.shipper)
            ws_summary.cell(row=row_num, column=5, value=doc.consignee)
            ws_summary.cell(row=row_num, column=6, value=doc.origin)
            ws_summary.cell(row=row_num, column=7, value=doc.destination)
            ws_summary.cell(row=row_num, column=8, value=pieces)
            ws_summary.cell(row=row_num, column=9, value=gross_weight)
            ws_summary.cell(row=row_num, column=10, value=chargeable_weight)
            ws_summary.cell(row=row_num, column=11, value=currency)
            ws_summary.cell(row=row_num, column=12, value=items_total)
            ws_summary.cell(row=row_num, column=13, value=other_charges_sum)
            ws_summary.cell(row=row_num, column=14, value=prepaid_total)
            ws_summary.cell(row=row_num, column=15, value=self._get_status_name(doc.status))
            
            for col in range(1, len(headers_summary) + 1):
                ws_summary.cell(row=row_num, column=col).border = self.BORDER
        
        # Add totals row
        total_row = len(documents) + 4
        ws_summary.cell(row=total_row, column=1, value="TOTAUX")
        ws_summary.cell(row=total_row, column=1).font = Font(bold=True)
        ws_summary.cell(row=total_row, column=8, value=total_pieces).font = Font(bold=True)
        ws_summary.cell(row=total_row, column=9, value=total_gross_weight).font = Font(bold=True)
        ws_summary.cell(row=total_row, column=10, value=total_chargeable_weight).font = Font(bold=True)
        ws_summary.cell(row=total_row, column=12, value=total_freight).font = Font(bold=True)
        ws_summary.cell(row=total_row, column=13, value=total_other_charges).font = Font(bold=True)
        ws_summary.cell(row=total_row, column=14, value=total_prepaid).font = Font(bold=True)
        
        for col in range(1, len(headers_summary) + 1):
            cell = ws_summary.cell(row=total_row, column=col)
            cell.border = self.BORDER
            cell.fill = PatternFill(start_color="E2EFDA", end_color="E2EFDA", fill_type="solid")
        
        self._auto_adjust_columns(ws_summary)
        
        # ========== Feuille 2: Détail des lignes de tarification ==========
        ws_items = wb.create_sheet("Lignes de tarification")
        
        headers_items = [
            "N° AWB", "Date", "Expéditeur", "Pièces", "Poids Brut",
            "Poids Taxable", "Tarif Unitaire", "Total Ligne", 
            "Nature des marchandises", "Devise"
        ]
        
        self._write_excel_header(ws_items, headers_items, "Détail des Lignes de Tarification")
        
        item_row = 4
        for doc, awb_details in parsed_docs:
            if awb_details and awb_details.items:
                for item in awb_details.items:
                    ws_items.cell(row=item_row, column=1, value=doc.document_number)
                    ws_items.cell(row=item_row, column=2, value=self._format_date(doc.document_date))
                    ws_items.cell(row=item_row, column=3, value=doc.shipper)
                    ws_items.cell(row=item_row, column=4, value=item.pieces)
                    ws_items.cell(row=item_row, column=5, value=item.gross_weight)
                    ws_items.cell(row=item_row, column=6, value=item.chargeable_weight)
                    ws_items.cell(row=item_row, column=7, value=item.rate_charge)
                    ws_items.cell(row=item_row, column=8, value=item.total)
                    ws_items.cell(row=item_row, column=9, value=item.nature[:100] if item.nature else "")
                    ws_items.cell(row=item_row, column=10, value=awb_details.currency)
                    
                    for col in range(1, len(headers_items) + 1):
                        ws_items.cell(row=item_row, column=col).border = self.BORDER
                    
                    item_row += 1
        
        self._auto_adjust_columns(ws_items)
        
        # ========== Feuille 3: Autres frais ==========
        ws_charges = wb.create_sheet("Autres Frais")
        
        headers_charges = [
            "N° AWB", "Date", "Code Frais", "Description", "Montant", 
            "Dû à", "Devise"
        ]
        
        self._write_excel_header(ws_charges, headers_charges, "Autres Frais et Taxes")
        
        charge_code_names = {
            "PS": "Frais de sécurité",
            "AWC": "Air Waybill Charge",
            "FC": "Fuel Surcharge",
            "SC": "Security Charge",
            "MY": "Miscellaneous Charges",
            "RA": "Dangerous Goods",
            "SR": "Screen Charge",
            "AW": "AWB Fee",
        }
        
        charge_row = 4
        for doc, awb_details in parsed_docs:
            if awb_details and awb_details.other_charges:
                for charge in awb_details.other_charges:
                    ws_charges.cell(row=charge_row, column=1, value=doc.document_number)
                    ws_charges.cell(row=charge_row, column=2, value=self._format_date(doc.document_date))
                    ws_charges.cell(row=charge_row, column=3, value=charge.code)
                    ws_charges.cell(row=charge_row, column=4, value=charge_code_names.get(charge.code, charge.code))
                    ws_charges.cell(row=charge_row, column=5, value=charge.amount)
                    ws_charges.cell(row=charge_row, column=6, value=charge.due)
                    ws_charges.cell(row=charge_row, column=7, value=awb_details.currency)
                    
                    for col in range(1, len(headers_charges) + 1):
                        ws_charges.cell(row=charge_row, column=col).border = self.BORDER
                    
                    charge_row += 1
        
        self._auto_adjust_columns(ws_charges)
        
        # ========== Feuille 4: Routing/Vols ==========
        ws_routing = wb.create_sheet("Routing")
        
        headers_routing = [
            "N° AWB", "Date", "Origine", "Destination", "Escales", 
            "Compagnies", "Vols", "Manutention"
        ]
        
        self._write_excel_header(ws_routing, headers_routing, "Informations de Routing")
        
        routing_row = 4
        for doc, awb_details in parsed_docs:
            via = ""
            carriers = ""
            flights = ""
            handling = ""
            
            if awb_details:
                if awb_details.route.to:
                    via = " → ".join(filter(None, awb_details.route.to))
                if awb_details.route.by:
                    carriers = ", ".join(filter(None, awb_details.route.by))
                if awb_details.route.flights:
                    flights = ", ".join(filter(None, awb_details.route.flights))
                handling = awb_details.handling_information
            
            ws_routing.cell(row=routing_row, column=1, value=doc.document_number)
            ws_routing.cell(row=routing_row, column=2, value=self._format_date(doc.document_date))
            ws_routing.cell(row=routing_row, column=3, value=doc.origin)
            ws_routing.cell(row=routing_row, column=4, value=doc.destination)
            ws_routing.cell(row=routing_row, column=5, value=via)
            ws_routing.cell(row=routing_row, column=6, value=carriers)
            ws_routing.cell(row=routing_row, column=7, value=flights)
            ws_routing.cell(row=routing_row, column=8, value=handling)
            
            for col in range(1, len(headers_routing) + 1):
                ws_routing.cell(row=routing_row, column=col).border = self.BORDER
            
            routing_row += 1
        
        self._auto_adjust_columns(ws_routing)
        
        # ========== Feuille 5: Statistiques ==========
        ws_stats = wb.create_sheet("Statistiques")
        
        # Title
        ws_stats.merge_cells('A1:D1')
        ws_stats.cell(row=1, column=1, value="Statistiques du Rapport")
        ws_stats.cell(row=1, column=1).font = Font(bold=True, size=14)
        
        ws_stats.cell(row=3, column=1, value="Métrique")
        ws_stats.cell(row=3, column=2, value="Valeur")
        ws_stats.cell(row=3, column=1).font = Font(bold=True)
        ws_stats.cell(row=3, column=2).font = Font(bold=True)
        
        stats_data = [
            ("Nombre de documents", len(documents)),
            ("Total pièces", total_pieces),
            ("Poids brut total (kg)", round(total_gross_weight, 2)),
            ("Poids taxable total (kg)", round(total_chargeable_weight, 2)),
            ("Total fret", round(total_freight, 2)),
            ("Total autres frais", round(total_other_charges, 2)),
            ("Total prépayé", round(total_prepaid, 2)),
            ("Moyenne pièces/AWB", round(total_pieces / len(documents), 1) if documents else 0),
            ("Moyenne poids/AWB (kg)", round(total_gross_weight / len(documents), 1) if documents else 0),
            ("Moyenne montant/AWB", round(total_prepaid / len(documents), 2) if documents else 0),
        ]
        
        for idx, (metric, value) in enumerate(stats_data, start=4):
            ws_stats.cell(row=idx, column=1, value=metric)
            ws_stats.cell(row=idx, column=2, value=value)
            ws_stats.cell(row=idx, column=1).border = self.BORDER
            ws_stats.cell(row=idx, column=2).border = self.BORDER
        
        ws_stats.column_dimensions['A'].width = 30
        ws_stats.column_dimensions['B'].width = 20
        
        # Save to buffer
        buffer = io.BytesIO()
        wb.save(buffer)
        buffer.seek(0)
        
        return buffer
    
    def export_detailed_awb_report_pdf(
        self,
        documents: List[Document],
        stats: Dict[str, Any],
        title: str = "Rapport AWB Détaillé"
    ) -> io.BytesIO:
        """
        Export AWB documents with statistics to PDF.
        """
        buffer = io.BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=landscape(A4),
            rightMargin=30,
            leftMargin=30,
            topMargin=30,
            bottomMargin=30
        )
        
        elements = []
        styles = getSampleStyleSheet()
        
        # Custom styles
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=18,
            spaceAfter=20,
            alignment=1,
            textColor=colors.HexColor('#1F4E79')
        )
        
        section_style = ParagraphStyle(
            'SectionTitle',
            parent=styles['Heading2'],
            fontSize=12,
            spaceAfter=10,
            spaceBefore=20,
            textColor=colors.HexColor('#1F4E79')
        )
        
        # Title
        elements.append(Paragraph(title, title_style))
        elements.append(Paragraph(
            f"Généré le: {datetime.now().strftime('%d/%m/%Y à %H:%M')}",
            styles['Normal']
        ))
        elements.append(Spacer(1, 20))
        
        # Parse documents for totals
        total_pieces = 0
        total_weight = 0
        total_prepaid = 0
        currencies = set()
        
        for doc_item in documents:
            awb_details = AWBParser.parse(doc_item.document_data) if doc_item.document_data else None
            if awb_details:
                total_pieces += awb_details.total_pieces
                total_weight += awb_details.total_weight
                total_prepaid += awb_details.charges_summary.total_prepaid
                if awb_details.currency:
                    currencies.add(awb_details.currency)
        
        # KPIs Summary
        elements.append(Paragraph("Résumé", section_style))
        
        kpi_data = [
            ["Documents", "Pièces totales", "Poids total", "Montant total"],
            [
                str(len(documents)),
                str(total_pieces),
                f"{total_weight:,.1f} kg",
                f"{total_prepaid:,.2f} {', '.join(currencies) if currencies else ''}"
            ]
        ]
        
        kpi_table = Table(kpi_data, colWidths=[2*inch, 2*inch, 2*inch, 2.5*inch])
        kpi_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1F4E79')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 10),
            ('FONTSIZE', (0, 1), (-1, -1), 12),
            ('FONTNAME', (0, 1), (-1, -1), 'Helvetica-Bold'),
            ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#E8F4FD')),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('PADDING', (0, 0), (-1, -1), 10),
        ]))
        elements.append(kpi_table)
        elements.append(Spacer(1, 20))
        
        # Documents table
        elements.append(Paragraph("Détail des documents", section_style))
        
        headers = ["N° AWB", "Expéditeur", "Destinataire", "Route", "Pièces", "Poids", "Total"]
        data = [headers]
        
        for doc_item in documents[:50]:  # Limit to 50 for PDF
            awb_details = AWBParser.parse(doc_item.document_data) if doc_item.document_data else None
            
            pieces = "-"
            weight = "-"
            total = "-"
            
            if awb_details:
                pieces = str(awb_details.total_pieces)
                weight = f"{awb_details.total_weight} kg"
                total = f"{awb_details.charges_summary.total_prepaid:.2f}"
            
            route = f"{doc_item.origin or '?'} → {doc_item.destination or '?'}"
            
            data.append([
                doc_item.document_number or "-",
                (doc_item.shipper or "-")[:25],
                (doc_item.consignee or "-")[:25],
                route,
                pieces,
                weight,
                total
            ])
        
        if len(documents) > 50:
            data.append(["...", f"+ {len(documents) - 50} autres documents", "", "", "", "", ""])
        
        doc_table = Table(data, repeatRows=1, colWidths=[1.3*inch, 2*inch, 2*inch, 1.2*inch, 0.8*inch, 1*inch, 1*inch])
        doc_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1F4E79')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('ALIGN', (4, 0), (-1, -1), 'CENTER'),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 9),
            ('FONTSIZE', (0, 1), (-1, -1), 8),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
            ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor('#F5F5F5')]),
            ('PADDING', (0, 0), (-1, -1), 5),
        ]))
        elements.append(doc_table)
        
        # Footer
        elements.append(Spacer(1, 30))
        elements.append(Paragraph(
            f"Total: {len(documents)} documents | {total_pieces} pièces | {total_weight:,.1f} kg | {total_prepaid:,.2f} {', '.join(currencies) if currencies else ''}",
            ParagraphStyle('Footer', parent=styles['Normal'], fontSize=10, textColor=colors.HexColor('#666666'))
        ))
        
        doc.build(elements)
        buffer.seek(0)
        
        return buffer

