from pydantic import BaseModel
from typing import List, Dict, Any, Optional

class ExportRequest(BaseModel):
    columns: List[str]
    rows: List[Dict[str, Any]]
    question: Optional[str] = "SQLens Query Result"
    insight: Optional[str] = None
    truncated: Optional[bool] = False
    total_rows: Optional[int] = None
    include_visualization: Optional[bool] = False
    chart_image_base64: Optional[str] = None

