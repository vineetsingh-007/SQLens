import logging
from math import ceil
from typing import Dict, Any, Optional, List
from sqlalchemy.orm import Session
from sqlalchemy import desc

from app.models.query_history import QueryHistory
from app.schemas.ai import QueryHistoryItem, QueryHistoryListResponse

logger = logging.getLogger("sqlens.query_history_service")


class QueryHistoryService:
    """
    Service managing dataset-isolated Query History storage, retrieval, pagination,
    deletion, and conversation turn tracking.
    """

    @staticmethod
    def create_history_item(
        db: Session,
        dataset_id: str,
        conversation_id: str,
        user_question: str,
        intent_json: Optional[Dict[str, Any]] = None,
        generated_sql: Optional[str] = None,
        execution_status: str = "success",
        row_count: int = 0,
        chart_type: str = "none",
        insight_summary: Optional[str] = None
    ) -> QueryHistory:
        """
        Creates and stores a new query history record.
        """
        record = QueryHistory(
            dataset_id=dataset_id,
            conversation_id=conversation_id,
            user_question=user_question,
            intent_json=intent_json,
            generated_sql=generated_sql,
            execution_status=execution_status,
            row_count=row_count,
            chart_type=chart_type,
            insight_summary=insight_summary
        )
        db.add(record)
        db.commit()
        db.refresh(record)
        return record

    @staticmethod
    def get_history_by_dataset(
        db: Session,
        dataset_id: str,
        page: int = 1,
        page_size: int = 20,
        search: Optional[str] = None
    ) -> QueryHistoryListResponse:
        """
        Retrieves paginated query history scoped strictly to dataset_id.
        """
        query = db.query(QueryHistory).filter(QueryHistory.dataset_id == dataset_id)

        if search and search.strip():
            term = f"%{search.strip()}%"
            query = query.filter(QueryHistory.user_question.ilike(term))

        total = query.count()
        page = max(1, page)
        page_size = max(1, min(page_size, 100))  # Cap page size at 100
        total_pages = ceil(total / page_size) if total > 0 else 1

        offset = (page - 1) * page_size
        records = query.order_by(desc(QueryHistory.created_at)).offset(offset).limit(page_size).all()

        items = [
            QueryHistoryItem(
                id=r.id,
                conversation_id=r.conversation_id,
                dataset_id=r.dataset_id,
                user_question=r.user_question,
                intent_json=r.intent_json,
                generated_sql=r.generated_sql,
                execution_status=r.execution_status,
                row_count=r.row_count,
                chart_type=r.chart_type,
                insight_summary=r.insight_summary,
                created_at=r.created_at.isoformat()
            )
            for r in records
        ]

        return QueryHistoryListResponse(
            items=items,
            total=total,
            page=page,
            page_size=page_size,
            total_pages=total_pages
        )

    @staticmethod
    def get_history_item(db: Session, dataset_id: str, query_id: str) -> Optional[QueryHistory]:
        """
        Retrieves a single query history item, enforcing dataset isolation.
        """
        return db.query(QueryHistory).filter(
            QueryHistory.id == query_id,
            QueryHistory.dataset_id == dataset_id
        ).first()

    @staticmethod
    def delete_history_item(db: Session, dataset_id: str, query_id: str) -> bool:
        """
        Deletes a single query history item, enforcing dataset isolation.
        """
        item = QueryHistoryService.get_history_item(db, dataset_id, query_id)
        if not item:
            return False
        db.delete(item)
        db.commit()
        return True

    @staticmethod
    def get_conversation_turns(db: Session, dataset_id: str, conversation_id: str) -> List[QueryHistoryItem]:
        """
        Retrieves all query turns in a conversation sorted chronologically.
        """
        records = db.query(QueryHistory).filter(
            QueryHistory.dataset_id == dataset_id,
            QueryHistory.conversation_id == conversation_id
        ).order_by(QueryHistory.created_at.asc()).all()

        return [
            QueryHistoryItem(
                id=r.id,
                conversation_id=r.conversation_id,
                dataset_id=r.dataset_id,
                user_question=r.user_question,
                intent_json=r.intent_json,
                generated_sql=r.generated_sql,
                execution_status=r.execution_status,
                row_count=r.row_count,
                chart_type=r.chart_type,
                insight_summary=r.insight_summary,
                created_at=r.created_at.isoformat()
            )
            for r in records
        ]
