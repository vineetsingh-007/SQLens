import logging
from fastapi import APIRouter, HTTPException, Response
from app.schemas.export import ExportRequest
from app.services.export_service import generate_excel, generate_docx, generate_pdf

logger = logging.getLogger("sqlens.export")

router = APIRouter()


@router.post("/excel")
def export_excel(payload: ExportRequest):
    """Export query result to Excel (.xlsx) file."""
    try:
        if not payload.columns and not payload.rows:
            raise HTTPException(status_code=400, detail="Nothing to export: empty result set.")

        excel_bytes = generate_excel(payload)
        return Response(
            content=excel_bytes,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={
                "Content-Disposition": 'attachment; filename="results.xlsx"'
            }
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to generate Excel file: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to generate Excel file.")


@router.post("/docx")
def export_docx(payload: ExportRequest):
    """Export query result to Word (.docx) document."""
    try:
        if not payload.columns and not payload.rows:
            raise HTTPException(status_code=400, detail="Nothing to export: empty result set.")

        docx_bytes = generate_docx(payload)
        return Response(
            content=docx_bytes,
            media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            headers={
                "Content-Disposition": 'attachment; filename="results.docx"'
            }
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to generate Word document: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to generate Word document.")


@router.post("/pdf")
def export_pdf(payload: ExportRequest):
    """Export query result to PDF (.pdf) report."""
    try:
        if not payload.columns and not payload.rows:
            raise HTTPException(status_code=400, detail="Nothing to export: empty result set.")

        pdf_bytes = generate_pdf(payload)
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={
                "Content-Disposition": 'attachment; filename="results.pdf"'
            }
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to generate PDF document: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail="Failed to generate PDF document.")
