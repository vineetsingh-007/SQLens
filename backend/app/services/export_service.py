import io
import base64
from datetime import datetime
from typing import List, Dict, Any
import pandas as pd
from PIL import Image as PILImage

from docx import Document
from docx.shared import Inches, Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_TABLE_ALIGNMENT
from docx.oxml import OxmlElement
from docx.oxml.ns import qn

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter, landscape
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, KeepTogether, Image as RLImage
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER, TA_LEFT

from app.schemas.export import ExportRequest



def generate_excel(request: ExportRequest) -> bytes:
    """Generate Excel (.xlsx) file bytes from query results."""
    columns = request.columns or []
    rows = request.rows or []

    if rows:
        df = pd.DataFrame(rows)
        # Reorder/select specified columns
        existing_cols = [c for c in columns if c in df.columns]
        # Add any missing specified columns with None
        for col in columns:
            if col not in df.columns:
                df[col] = None
        df = df[columns]
    else:
        df = pd.DataFrame(columns=columns)

    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, sheet_name='Results', index=False)
        worksheet = writer.sheets['Results']

        # Format column widths
        for i, col_name in enumerate(columns):
            max_len = len(str(col_name))
            if rows:
                col_vals = [str(r.get(col_name, '')) for r in rows[:100]]
                if col_vals:
                    max_len = max(max_len, max(len(v) for v in col_vals))
            col_letter = openpyxl_col_name(i + 1)
            worksheet.column_dimensions[col_letter].width = min(max(max_len + 4, 12), 50)

    output.seek(0)
    return output.getvalue()


def openpyxl_col_name(n: int) -> str:
    """Convert 1-based column index to Excel column letter (A, B, ..., Z, AA, etc.)."""
    result = ""
    while n > 0:
        n, remainder = divmod(n - 1, 26)
        result = chr(65 + remainder) + result
    return result


def set_cell_background(cell, fill_hex: str):
    """Helper to set cell background color in python-docx."""
    tc_pr = cell._element.get_or_add_tcPr()
    shd = OxmlElement('w:shd')
    shd.set(qn('w:val'), 'clear')
    shd.set(qn('w:color'), 'auto')
    shd.set(qn('w:fill'), fill_hex)
    tc_pr.append(shd)


def generate_docx(request: ExportRequest) -> bytes:
    """Generate Word (.docx) file bytes from query results."""
    doc = Document()
    
    # Page Margins
    for section in doc.sections:
        section.top_margin = Inches(0.8)
        section.bottom_margin = Inches(0.8)
        section.left_margin = Inches(0.8)
        section.right_margin = Inches(0.8)

    # Document Header Title
    title_p = doc.add_paragraph()
    title_run = title_p.add_run("SQLens Query Result")
    title_run.font.name = "Arial"
    title_run.font.size = Pt(20)
    title_run.font.bold = True
    title_run.font.color.rgb = RGBColor(15, 23, 42)  # slate-900
    title_p.alignment = WD_ALIGN_PARAGRAPH.LEFT

    # Timestamp & Subtitle
    sub_p = doc.add_paragraph()
    time_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S UTC")
    sub_run = sub_p.add_run(f"Generated on {time_str}")
    sub_run.font.name = "Arial"
    sub_run.font.size = Pt(9)
    sub_run.font.italic = True
    sub_run.font.color.rgb = RGBColor(100, 116, 139)

    # User Question Section
    if request.question:
        q_p = doc.add_paragraph()
        q_p.paragraph_format.space_before = Pt(8)
        q_p.paragraph_format.space_after = Pt(12)
        q_label = q_p.add_run("Question: ")
        q_label.font.name = "Arial"
        q_label.font.bold = True
        q_label.font.size = Pt(11)
        q_label.font.color.rgb = RGBColor(79, 70, 229)  # indigo-600
        
        q_val = q_p.add_run(request.question)
        q_val.font.name = "Arial"
        q_val.font.size = Pt(11)
        q_val.font.color.rgb = RGBColor(30, 41, 59)

    # Truncation disclaimer if applicable
    if request.truncated:
        trun_p = doc.add_paragraph()
        trun_run = trun_p.add_run(f"Note: Export contains the {len(request.rows):,} rows returned by SQLens.")
        trun_run.font.name = "Arial"
        trun_run.font.size = Pt(9.5)
        trun_run.font.italic = True
        trun_run.font.color.rgb = RGBColor(217, 119, 6)  # amber-600

    # Exact Visualization Chart Image (if requested and provided)
    if request.include_visualization and request.chart_image_base64:
        try:
            b64_data = request.chart_image_base64
            if "," in b64_data:
                b64_data = b64_data.split(",", 1)[1]
            img_bytes = base64.b64decode(b64_data)
            img_stream = io.BytesIO(img_bytes)

            chart_p = doc.add_paragraph()
            chart_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            chart_p.paragraph_format.space_before = Pt(10)
            chart_p.paragraph_format.space_after = Pt(14)
            chart_run = chart_p.add_run()
            chart_run.add_picture(img_stream, width=Inches(6.0))
        except Exception as err:
            print(f"Failed to embed chart image in Word export: {err}")

    # Result Table
    columns = request.columns or []
    rows = request.rows or []


    if columns:
        table = doc.add_table(rows=len(rows) + 1, cols=len(columns))
        table.alignment = WD_TABLE_ALIGNMENT.CENTER
        table.style = 'Table Grid'

        # Format Header Row
        hdr_cells = table.rows[0].cells
        for idx, col_name in enumerate(columns):
            cell = hdr_cells[idx]
            cell.text = str(col_name)
            set_cell_background(cell, "1E293B")  # Slate-800
            for paragraph in cell.paragraphs:
                paragraph.alignment = WD_ALIGN_PARAGRAPH.LEFT
                for run in paragraph.runs:
                    run.font.name = "Arial"
                    run.font.bold = True
                    run.font.size = Pt(9.5)
                    run.font.color.rgb = RGBColor(255, 255, 255)

        # Format Data Rows
        for r_idx, row_dict in enumerate(rows):
            row_cells = table.rows[r_idx + 1].cells
            bg_color = "F8FAFC" if r_idx % 2 == 1 else "FFFFFF"
            for c_idx, col_name in enumerate(columns):
                cell = row_cells[c_idx]
                val = row_dict.get(col_name)
                cell.text = "" if val is None else str(val)
                set_cell_background(cell, bg_color)
                for paragraph in cell.paragraphs:
                    for run in paragraph.runs:
                        run.font.name = "Arial"
                        run.font.size = Pt(9)
                        run.font.color.rgb = RGBColor(30, 41, 59)
    else:
        empty_p = doc.add_paragraph("No columns or data available.")
        empty_p.runs[0].font.italic = True

    # AI Insight Section if present
    if request.insight:
        doc.add_paragraph().paragraph_format.space_before = Pt(12)
        ins_head = doc.add_paragraph()
        ins_label = ins_head.add_run("AI Insight Summary")
        ins_label.font.name = "Arial"
        ins_label.font.bold = True
        ins_label.font.size = Pt(12)
        ins_label.font.color.rgb = RGBColor(15, 23, 42)

        ins_p = doc.add_paragraph()
        ins_run = ins_p.add_run(request.insight)
        ins_run.font.name = "Arial"
        ins_run.font.size = Pt(10)
        ins_run.font.color.rgb = RGBColor(51, 65, 85)

    output = io.BytesIO()
    doc.save(output)
    output.seek(0)
    return output.getvalue()


def generate_pdf(request: ExportRequest) -> bytes:
    """Generate PDF (.pdf) file bytes from query results using ReportLab."""
    output = io.BytesIO()
    
    columns = request.columns or []
    rows = request.rows or []

    # Decide orientation based on column count and width
    is_landscape = len(columns) > 5
    pagesize = landscape(letter) if is_landscape else letter

    doc = SimpleDocTemplate(
        output,
        pagesize=pagesize,
        rightMargin=36,
        leftMargin=36,
        topMargin=36,
        bottomMargin=36
    )

    styles = getSampleStyleSheet()

    # Custom styles
    title_style = ParagraphStyle(
        'PDFTitle',
        parent=styles['Heading1'],
        fontName='Helvetica-Bold',
        fontSize=18,
        leading=22,
        textColor=colors.HexColor('#0F172A'),
        spaceAfter=4
    )

    sub_style = ParagraphStyle(
        'PDFSubtitle',
        parent=styles['Normal'],
        fontName='Helvetica-Oblique',
        fontSize=9,
        leading=11,
        textColor=colors.HexColor('#64748B'),
        spaceAfter=10
    )

    q_style = ParagraphStyle(
        'PDFQuestion',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=10,
        leading=14,
        textColor=colors.HexColor('#4F46E5'),
        spaceAfter=10
    )

    trun_style = ParagraphStyle(
        'PDFTruncated',
        parent=styles['Normal'],
        fontName='Helvetica-Oblique',
        fontSize=9,
        leading=12,
        textColor=colors.HexColor('#D97706'),
        spaceAfter=8
    )

    cell_hdr_style = ParagraphStyle(
        'PDFCellHdr',
        parent=styles['Normal'],
        fontName='Helvetica-Bold',
        fontSize=8.5,
        leading=10,
        textColor=colors.white
    )

    cell_body_style = ParagraphStyle(
        'PDFCellBody',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=8,
        leading=10,
        textColor=colors.HexColor('#1E293B')
    )

    insight_title_style = ParagraphStyle(
        'PDFInsightTitle',
        parent=styles['Heading2'],
        fontName='Helvetica-Bold',
        fontSize=11,
        leading=14,
        textColor=colors.HexColor('#0F172A'),
        spaceBefore=12,
        spaceAfter=4
    )

    insight_text_style = ParagraphStyle(
        'PDFInsightText',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=9.5,
        leading=13,
        textColor=colors.HexColor('#334155')
    )

    story = []

    # Title & Header
    story.append(Paragraph("SQLens Query Result", title_style))
    time_str = datetime.now().strftime("%Y-%m-%d %H:%M:%S UTC")
    story.append(Paragraph(f"Generated on {time_str} • {len(rows):,} rows", sub_style))

    # Question
    if request.question:
        story.append(Paragraph(f"Question: {request.question}", q_style))

    # Truncation Disclaimer
    if request.truncated:
        story.append(Paragraph(f"Note: Export contains the {len(rows):,} rows returned by SQLens.", trun_style))

    # Exact Visualization Chart Image (if requested and provided)
    if request.include_visualization and request.chart_image_base64:
        try:
            b64_data = request.chart_image_base64
            if "," in b64_data:
                b64_data = b64_data.split(",", 1)[1]
            img_bytes = base64.b64decode(b64_data)

            pil_img = PILImage.open(io.BytesIO(img_bytes))
            img_w, img_h = pil_img.size
            aspect = img_h / float(img_w) if img_w > 0 else 0.5

            page_printable_width = (11 * 72 - 72) if is_landscape else (8.5 * 72 - 72)
            target_w = min(500 if not is_landscape else 650, page_printable_width)
            target_h = target_w * aspect

            max_h = 320 if is_landscape else 280
            if target_h > max_h:
                target_h = max_h
                target_w = target_h / aspect if aspect > 0 else target_w

            pdf_img = RLImage(io.BytesIO(img_bytes), width=target_w, height=target_h)
            pdf_img.hAlign = 'CENTER'
            story.append(Spacer(1, 6))
            story.append(pdf_img)
            story.append(Spacer(1, 12))
        except Exception as err:
            print(f"Failed to embed chart image in PDF export: {err}")

    # Table
    if columns:

        table_data = []
        
        # Header Row wrapped in Paragraphs
        hdr_row = [Paragraph(str(col), cell_hdr_style) for col in columns]
        table_data.append(hdr_row)

        # Body Rows wrapped in Paragraphs
        for r_dict in rows:
            row_items = []
            for col in columns:
                val = r_dict.get(col)
                val_str = "" if val is None else str(val)
                row_items.append(Paragraph(val_str, cell_body_style))
            table_data.append(row_items)

        # Available width calculation
        page_width = 11 * 72 if is_landscape else 8.5 * 72
        avail_width = page_width - 72  # 36 margin on left and right
        col_width = avail_width / max(len(columns), 1)

        pdf_table = Table(table_data, colWidths=[col_width] * len(columns), repeatRows=1)

        t_style = [
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1E293B')),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('VALIGN', (0, 0), (-1, -1), 'TOP'),
            ('INNERGRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#CBD5E1')),
            ('BOX', (0, 0), (-1, -1), 1, colors.HexColor('#94A3B8')),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
            ('LEFTPADDING', (0, 0), (-1, -1), 5),
            ('RIGHTPADDING', (0, 0), (-1, -1), 5),
        ]

        # Alternate row background colors
        for i in range(1, len(table_data)):
            if i % 2 == 0:
                t_style.append(('BACKGROUND', (0, i), (-1, i), colors.HexColor('#F8FAFC')))

        pdf_table.setStyle(TableStyle(t_style))
        story.append(pdf_table)

    # Insight Section
    if request.insight:
        story.append(Spacer(1, 10))
        story.append(Paragraph("AI Insight Summary", insight_title_style))
        story.append(Paragraph(request.insight, insight_text_style))

    doc.build(story)
    output.seek(0)
    return output.getvalue()
