from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List
from app.schemas.ai import IntentAnalysis


class BaseAIProvider(ABC):
    """
    Abstract Base Class for SQLens AI Providers.
    Encapsulates LLM interaction to keep the service modular and independent of specific AI vendors.
    """

    @abstractmethod
    async def test_connection(self) -> Dict[str, Any]:
        """
        Tests connection to the underlying LLM provider.
        Returns dictionary with keys: success (bool), status (str), message (str).
        """
        pass

    @abstractmethod
    async def analyze_intent(
        self,
        question: str,
        schema_text: str,
        clarification_context: Optional[str] = None,
        previous_turns: Optional[List[Dict[str, Any]]] = None
    ) -> IntentAnalysis:
        """
        Sends natural language question and schema context to the LLM and returns structured IntentAnalysis.
        """
        pass

    @abstractmethod
    async def refine_intent_with_clarification(
        self,
        original_question: str,
        clarification_answer: str,
        schema_text: str,
        previous_turns: Optional[List[Dict[str, Any]]] = None
    ) -> IntentAnalysis:
        """
        Sends original question + user clarification answer + schema context to LLM for refined IntentAnalysis.
        """
        pass

    async def refine_intent_followup(
        self,
        question: str,
        previous_intent: Optional[Dict[str, Any]],
        previous_question: Optional[str],
        schema_text: str
    ) -> IntentAnalysis:
        """
        Refines intent based on follow-up question and previous structured intent context.
        Default implementation delegates to analyze_intent for provider backwards compatibility.
        """
        return await self.analyze_intent(question=question, schema_text=schema_text)
