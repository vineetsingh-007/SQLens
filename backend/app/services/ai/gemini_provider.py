import asyncio
import json
import logging
from typing import Dict, Any, Optional, List
from google import genai
from google.genai import types
from google.genai.errors import APIError

from app.core.config import settings
from app.schemas.ai import IntentAnalysis, SQLGenerationResult, AIInsightResult
from app.services.ai.base_provider import BaseAIProvider
from app.services.ai.prompts.intent_prompt import SYSTEM_INTENT_PROMPT, build_intent_prompt
from app.services.ai.prompts.clarification_prompt import SYSTEM_CLARIFICATION_PROMPT, build_clarification_prompt
from app.services.ai.prompts.followup_prompt import SYSTEM_FOLLOWUP_PROMPT, build_followup_prompt
from app.services.ai.prompts.sql_prompt import SYSTEM_SQL_PROMPT, build_sql_prompt
from app.services.ai.prompts.insight_prompt import SYSTEM_INSIGHT_PROMPT, build_insight_prompt


logger = logging.getLogger("sqlens")


class GeminiProvider(BaseAIProvider):
    """
    Gemini LLM Provider implementation using the official google-genai SDK.
    """

    def __init__(self):
        self.api_key = settings.GEMINI_API_KEY
        self.model_name = settings.GEMINI_MODEL
        self.timeout = settings.GEMINI_TIMEOUT_SECONDS
        self.temperature = settings.GEMINI_TEMPERATURE

    def _get_client(self) -> Optional[genai.Client]:
        if not self.api_key:
            return None
        return genai.Client(api_key=self.api_key)

    async def test_connection(self) -> Dict[str, Any]:
        """
        Tests Gemini connection by sending a simple health check request.
        """
        if not self.api_key:
            return {
                "success": False,
                "configured": False,
                "status": "not_configured",
                "message": "Gemini API key is not configured. Please set GEMINI_API_KEY in backend/.env"
            }

        client = self._get_client()
        if not client:
            return {
                "success": False,
                "configured": False,
                "status": "client_error",
                "message": "Unable to initialize Gemini client."
            }

        try:
            # Send small test request
            loop = asyncio.get_running_loop()
            response = await loop.run_in_executor(
                None,
                lambda: client.models.generate_content(
                    model=self.model_name,
                    contents="Respond with the word OK."
                )
            )

            if response and response.text:
                return {
                    "success": True,
                    "configured": True,
                    "status": "connected",
                    "provider": "Gemini",
                    "model": self.model_name,
                    "message": "Gemini API connection test successful."
                }
            else:
                return {
                    "success": False,
                    "configured": True,
                    "status": "empty_response",
                    "message": "Gemini returned an empty response."
                }

        except APIError as e:
            logger.error(f"Gemini API error during connection test: {e}")
            return {
                "success": False,
                "configured": True,
                "status": "api_error",
                "message": f"Gemini API connection failed: {e.message if hasattr(e, 'message') else str(e)}"
            }
        except Exception as e:
            logger.error(f"Unexpected error during Gemini connection test: {e}")
            return {
                "success": False,
                "configured": True,
                "status": "error",
                "message": f"Gemini connection failed: {str(e)}"
            }

    async def analyze_intent(
        self,
        question: str,
        schema_text: str,
        clarification_context: Optional[str] = None,
        previous_turns: Optional[List[Dict[str, Any]]] = None
    ) -> IntentAnalysis:
        """
        Invokes Gemini with system instructions, schema, and question, requesting structured JSON output.
        """
        if not self.api_key:
            raise ValueError("Gemini API key is not configured. Please set GEMINI_API_KEY in backend/.env")

        client = self._get_client()
        if not client:
            raise RuntimeError("Gemini client initialization failed.")

        user_prompt = build_intent_prompt(
            question=question,
            schema_text=schema_text,
            clarification_context=clarification_context,
            previous_turns=previous_turns
        )

        config = types.GenerateContentConfig(
            system_instruction=SYSTEM_INTENT_PROMPT,
            response_mime_type="application/json",
            response_schema=IntentAnalysis,
            temperature=self.temperature,
            max_output_tokens=settings.GEMINI_MAX_OUTPUT_TOKENS,
        )

        loop = asyncio.get_running_loop()
        try:
            # Execute Gemini call in threadpool with timeout
            response = await asyncio.wait_for(
                loop.run_in_executor(
                    None,
                    lambda: client.models.generate_content(
                        model=self.model_name,
                        contents=user_prompt,
                        config=config
                    )
                ),
                timeout=self.timeout
            )

            if not response or not response.text:
                raise ValueError("Gemini returned an empty response.")

            response_text = response.text.strip()
            logger.info(f"Gemini Raw Response: {response_text[:300]}...")

            # Parse JSON into Pydantic model
            try:
                data = json.loads(response_text)
                intent_analysis = IntentAnalysis.model_validate(data)
                return intent_analysis
            except Exception as parse_err:
                logger.warning(f"Direct Pydantic validation failed: {parse_err}. Attempting fallback parsing.")
                data = json.loads(response_text)
                return IntentAnalysis(
                    intent=data.get("intent", "general_query"),
                    summary=data.get("summary", "Query intent processed."),
                    status=data.get("status", "ready"),
                    entities=data.get("entities", []),
                    metrics=data.get("metrics", []),
                    filters=data.get("filters", []),
                    grouping=data.get("grouping", []),
                    sorting=data.get("sorting"),
                    limit=data.get("limit"),
                    time_range=data.get("time_range"),
                    relevant_tables=data.get("relevant_tables", []),
                    relevant_columns=data.get("relevant_columns", []),
                    needs_clarification=data.get("needs_clarification", False),
                    clarification=data.get("clarification"),
                    unsupported_request=data.get("unsupported_request", False),
                    unsupported_reason=data.get("unsupported_reason"),
                    confidence=data.get("confidence", 0.9)
                )

        except asyncio.TimeoutError:
            logger.error(f"Gemini call timed out after {self.timeout} seconds.")
            raise RuntimeError(f"AI service request timed out after {self.timeout} seconds. Please try again.")
        except APIError as e:
            logger.error(f"Gemini API Error: {e}")
            raise RuntimeError(f"Gemini service error: {e.message if hasattr(e, 'message') else str(e)}")
        except Exception as e:
            logger.error(f"Error calling Gemini: {e}")
            raise

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
        if not self.api_key:
            raise ValueError("Gemini API key is not configured. Please set GEMINI_API_KEY in backend/.env")

        client = self._get_client()
        if not client:
            raise RuntimeError("Gemini client initialization failed.")

        user_prompt = build_clarification_prompt(
            original_question=original_question,
            clarification_answer=clarification_answer,
            schema_text=schema_text,
            previous_turns=previous_turns
        )

        config = types.GenerateContentConfig(
            system_instruction=SYSTEM_CLARIFICATION_PROMPT,
            response_mime_type="application/json",
            response_schema=IntentAnalysis,
            temperature=self.temperature,
            max_output_tokens=settings.GEMINI_MAX_OUTPUT_TOKENS,
        )

        loop = asyncio.get_running_loop()
        try:
            response = await asyncio.wait_for(
                loop.run_in_executor(
                    None,
                    lambda: client.models.generate_content(
                        model=self.model_name,
                        contents=user_prompt,
                        config=config
                    )
                ),
                timeout=self.timeout
            )

            if not response or not response.text:
                raise ValueError("Gemini returned an empty response.")

            response_text = response.text.strip()
            logger.info(f"Gemini Refined Raw Response: {response_text[:300]}...")

            try:
                data = json.loads(response_text)
                intent_analysis = IntentAnalysis.model_validate(data)
                intent_analysis.needs_clarification = False
                intent_analysis.status = "ready"
                return intent_analysis
            except Exception as parse_err:
                logger.warning(f"Direct Pydantic validation failed for refinement: {parse_err}.")
                data = json.loads(response_text)
                return IntentAnalysis(
                    intent=data.get("intent", "refined_query"),
                    summary=data.get("summary", f"Refined intent for: {clarification_answer}"),
                    status="ready",
                    entities=data.get("entities", []),
                    metrics=data.get("metrics", []),
                    filters=data.get("filters", []),
                    grouping=data.get("grouping", []),
                    sorting=data.get("sorting"),
                    limit=data.get("limit"),
                    time_range=data.get("time_range"),
                    relevant_tables=data.get("relevant_tables", []),
                    relevant_columns=data.get("relevant_columns", []),
                    needs_clarification=False,
                    clarification=None,
                    unsupported_request=data.get("unsupported_request", False),
                    unsupported_reason=data.get("unsupported_reason"),
                    confidence=data.get("confidence", 0.95)
                )

        except asyncio.TimeoutError:
            logger.error(f"Gemini refinement call timed out after {self.timeout} seconds.")
            raise RuntimeError(f"AI service request timed out after {self.timeout} seconds. Please try again.")
        except APIError as e:
            logger.error(f"Gemini API Error: {e}")
            raise RuntimeError(f"Gemini service error: {e.message if hasattr(e, 'message') else str(e)}")
        except Exception as e:
            logger.error(f"Error refining intent with Gemini: {e}")
            raise

    async def refine_intent_followup(
        self,
        question: str,
        previous_intent: Optional[Dict[str, Any]],
        previous_question: Optional[str],
        schema_text: str
    ) -> IntentAnalysis:
        """
        Sends follow-up question + previous intent context + schema to Gemini for refined IntentAnalysis.
        """
        if not self.api_key:
            raise ValueError("Gemini API key is not configured. Please set GEMINI_API_KEY in backend/.env")

        client = self._get_client()
        if not client:
            raise RuntimeError("Gemini client initialization failed.")

        user_prompt = build_followup_prompt(
            question=question,
            previous_intent=previous_intent,
            previous_question=previous_question,
            schema_text=schema_text
        )

        config = types.GenerateContentConfig(
            system_instruction=SYSTEM_FOLLOWUP_PROMPT,
            response_mime_type="application/json",
            response_schema=IntentAnalysis,
            temperature=self.temperature,
            max_output_tokens=settings.GEMINI_MAX_OUTPUT_TOKENS,
        )

        loop = asyncio.get_running_loop()
        try:
            response = await asyncio.wait_for(
                loop.run_in_executor(
                    None,
                    lambda: client.models.generate_content(
                        model=self.model_name,
                        contents=user_prompt,
                        config=config
                    )
                ),
                timeout=self.timeout
            )

            if not response or not response.text:
                raise ValueError("Gemini returned an empty response.")

            response_text = response.text.strip()
            logger.info(f"Gemini Followup Raw Response: {response_text[:300]}...")

            data = json.loads(response_text)
            intent_analysis = IntentAnalysis.model_validate(data)
            return intent_analysis

        except asyncio.TimeoutError:
            logger.error(f"Gemini followup call timed out after {self.timeout} seconds.")
            raise RuntimeError(f"AI service request timed out after {self.timeout} seconds. Please try again.")
        except APIError as e:
            logger.error(f"Gemini API Error: {e}")
            raise RuntimeError(f"Gemini service error: {e.message if hasattr(e, 'message') else str(e)}")
        except Exception as e:
            logger.error(f"Error refining followup intent with Gemini: {e}")
            raise

    async def generate_sql(
        self,
        question: str,
        intent: Dict[str, Any],
        schema_text: str,
        relationships_text: str = ""
    ) -> SQLGenerationResult:
        """
        Invokes Gemini to generate PostgreSQL SELECT query based on schema and Phase 5 intent.
        """
        if not self.api_key:
            raise ValueError("Gemini API key is not configured. Please set GEMINI_API_KEY in backend/.env")

        client = self._get_client()
        if not client:
            raise RuntimeError("Gemini client initialization failed.")

        user_prompt = build_sql_prompt(
            question=question,
            intent=intent,
            schema_text=schema_text,
            relationships_text=relationships_text
        )

        config = types.GenerateContentConfig(
            system_instruction=SYSTEM_SQL_PROMPT,
            response_mime_type="application/json",
            response_schema=SQLGenerationResult,
            temperature=0.1,  # Low temperature for precise SQL generation
            max_output_tokens=settings.GEMINI_MAX_OUTPUT_TOKENS,
        )

        loop = asyncio.get_running_loop()
        try:
            response = await asyncio.wait_for(
                loop.run_in_executor(
                    None,
                    lambda: client.models.generate_content(
                        model=self.model_name,
                        contents=user_prompt,
                        config=config
                    )
                ),
                timeout=self.timeout
            )

            if not response or not response.text:
                raise ValueError("Gemini returned an empty response for SQL generation.")

            response_text = response.text.strip()
            logger.info(f"Gemini Raw SQL Response: {response_text[:300]}...")

            try:
                data = json.loads(response_text)
                sql_result = SQLGenerationResult.model_validate(data)
                return sql_result
            except Exception as parse_err:
                logger.warning(f"Direct Pydantic validation failed for SQL result: {parse_err}. Attempting fallback parsing.")
                data = json.loads(response_text)
                return SQLGenerationResult(
                    sql=data.get("sql", "").strip(),
                    dialect="postgresql",
                    tables_used=data.get("tables_used", []),
                    columns_used=data.get("columns_used", []),
                    explanation=data.get("explanation", "Generated PostgreSQL query based on intent."),
                    confidence=float(data.get("confidence", 0.9))
                )

        except asyncio.TimeoutError:
            logger.error(f"Gemini Text-to-SQL call timed out after {self.timeout} seconds.")
            raise RuntimeError(f"Text-to-SQL generation timed out after {self.timeout} seconds. Please try again.")
        except APIError as e:
            logger.error(f"Gemini API Error during SQL generation: {e}")
            raise RuntimeError(f"Gemini service error: {e.message if hasattr(e, 'message') else str(e)}")
        except Exception as e:
            logger.error(f"Error generating SQL with Gemini: {e}")
            raise

    async def generate_insights(
        self,
        question: str,
        intent_summary: str,
        columns: List[str],
        sample_rows: List[Dict[str, Any]]
    ) -> AIInsightResult:
        """
        Invokes Gemini to generate concise executive insights based ONLY on returned result rows.
        """
        if not self.api_key:
            return AIInsightResult(
                summary_insight="AI insight generation is unavailable (API key not configured).",
                key_highlights=[]
            )

        client = self._get_client()
        if not client:
            return AIInsightResult(
                summary_insight="AI client initialization failed.",
                key_highlights=[]
            )

        user_prompt = build_insight_prompt(
            question=question,
            intent_summary=intent_summary,
            columns=columns,
            sample_rows=sample_rows
        )

        config = types.GenerateContentConfig(
            system_instruction=SYSTEM_INSIGHT_PROMPT,
            response_mime_type="application/json",
            response_schema=AIInsightResult,
            temperature=0.2,
            max_output_tokens=1000,
        )

        loop = asyncio.get_running_loop()
        try:
            response = await asyncio.wait_for(
                loop.run_in_executor(
                    None,
                    lambda: client.models.generate_content(
                        model=self.model_name,
                        contents=user_prompt,
                        config=config
                    )
                ),
                timeout=self.timeout
            )

            if not response or not response.text:
                return AIInsightResult(
                    summary_insight="Results returned successfully.",
                    key_highlights=[]
                )

            response_text = response.text.strip()
            logger.info(f"Gemini Raw Insight Response: {response_text[:300]}...")

            try:
                data = json.loads(response_text)
                return AIInsightResult.model_validate(data)
            except Exception as parse_err:
                logger.warning(f"Direct validation for AIInsightResult failed: {parse_err}.")
                data = json.loads(response_text)
                return AIInsightResult(
                    summary_insight=data.get("summary_insight", "Results fetched successfully."),
                    key_highlights=data.get("key_highlights", [])
                )

        except Exception as err:
            logger.error(f"Error generating AI insight: {err}")
            return AIInsightResult(
                summary_insight="Query executed successfully.",
                key_highlights=[]
            )



