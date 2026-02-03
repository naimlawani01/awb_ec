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
        """Format datetime or timestamp for export."""
        if not dt:
            return "-"
        # Handle bigint timestamp (Unix timestamp in milliseconds)
        if isinstance(dt, (int, float)):
            try:
                # Convert milliseconds to seconds
                dt = datetime.fromtimestamp(dt / 1000)
            except (ValueError, OSError):
                return "-"
        return dt.strftime('%Y-%m-%d')
    
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

