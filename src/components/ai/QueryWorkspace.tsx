import React, { useState, useEffect } from 'react';
import {
  Sparkles,
  Send,
  Loader2,
  AlertTriangle,
  RefreshCw,
  Database,
  CheckCircle2,
  Filter as FilterIcon,
  Layers,
  ShieldAlert,
  ShieldCheck,
  Check,
  RotateCcw,
  Terminal,
  Play,
  History,
  MessageSquare,
  PlusCircle,
  BarChart2,
  Table as TableIcon
} from 'lucide-react';
import { useMemo } from 'react';
import { datasetService, aiService } from '../../services/api';
import { DatasetTable } from '../../types/dataset';
import { generateSchemaQueries } from '../../utils/schemaQueries';
import {
  IntentAnalysis,
  AIAnalysisResponse,
  AIHealthResponse,
  SQLGenerationResponse,
  SQLValidationResponse,
  FullQueryAnalysisResponse,
  ConversationTurn,
  QueryHistoryItem
} from '../../types/ai';
import { ClarificationCard } from './ClarificationCard';
import { AIDebugPanel } from './AIDebugPanel';
import { SQLViewerCard } from './SQLViewerCard';
import { ResultTable } from '../query/ResultTable';
import { ResultChart } from '../query/ResultChart';
import { ResultInsightCard } from '../query/ResultInsightCard';
import { QueryHistoryPanel } from '../query/QueryHistoryPanel';
import { VoiceInputButton } from '../common/VoiceInputButton';

interface QueryWorkspaceProps {
  datasetId: string;
  datasetName?: string;
  tables?: DatasetTable[];
}

const generateUUID = (): string => {
  return 'conv_' + Math.random().toString(36).substring(2, 11) + '_' + Date.now();
};

const STORAGE_KEY_PREFIX = 'sqlens_active_conv_';

interface StoredConversation {
  conversationId: string;
  turns: ConversationTurn[];
}

const loadStoredConversation = (datasetId: string): StoredConversation => {
  if (!datasetId) {
    return { conversationId: generateUUID(), turns: [] };
  }
  try {
    const raw = localStorage.getItem(`${STORAGE_KEY_PREFIX}${datasetId}`);
    if (raw) {
      const parsed = JSON.parse(raw);
      if (parsed && typeof parsed.conversationId === 'string' && Array.isArray(parsed.turns)) {
        return {
          conversationId: parsed.conversationId,
          turns: parsed.turns
        };
      }
    }
  } catch (err) {
    console.warn('Failed to load active conversation state for dataset:', datasetId, err);
  }
  return { conversationId: generateUUID(), turns: [] };
};

const saveStoredConversation = (datasetId: string, conversationId: string, turns: ConversationTurn[]) => {
  if (!datasetId) return;
  try {
    const data: StoredConversation = { conversationId, turns };
    localStorage.setItem(`${STORAGE_KEY_PREFIX}${datasetId}`, JSON.stringify(data));
  } catch (err) {
    console.warn('Failed to persist active conversation state for dataset:', datasetId, err);
  }
};

export const QueryWorkspace: React.FC<QueryWorkspaceProps> = ({ datasetId, datasetName, tables }) => {
  const [question, setQuestion] = useState('');
  const [conversationId, setConversationId] = useState<string>(() => {
    return loadStoredConversation(datasetId).conversationId;
  });
  const [turns, setTurns] = useState<ConversationTurn[]>(() => {
    return loadStoredConversation(datasetId).turns;
  });
  const [isHistoryOpen, setIsHistoryOpen] = useState<boolean>(false);
  const [healthStatus, setHealthStatus] = useState<AIHealthResponse | null>(null);
  const [schemaTables, setSchemaTables] = useState<DatasetTable[]>(tables || []);

  // Active state for currently processing question or follow-up
  const [isProcessing, setIsProcessing] = useState<boolean>(false);
  const [loadingStage, setLoadingStage] = useState<string>('Understanding question...');
  const [activeFollowupIndex, setActiveFollowupIndex] = useState<number | null>(null);
  const [followupText, setFollowupText] = useState<string>('');

  // Restore conversation state whenever datasetId changes
  useEffect(() => {
    const loaded = loadStoredConversation(datasetId);
    setConversationId(loaded.conversationId);
    setTurns(loaded.turns);
    setQuestion('');
    setFollowupText('');
    setActiveFollowupIndex(null);
  }, [datasetId]);

  // Persist conversation state whenever turns or conversationId updates
  useEffect(() => {
    saveStoredConversation(datasetId, conversationId, turns);
  }, [datasetId, conversationId, turns]);

  useEffect(() => {
    if (tables && tables.length > 0) {
      setSchemaTables(tables);
    } else if (datasetId) {
      datasetService.getDatasetSchema(datasetId)
        .then((data) => setSchemaTables(data.tables || []))
        .catch((err) => console.error('Failed to fetch dataset schema for queries:', err));
    }
  }, [datasetId, tables]);

  // Dynamically generated schema queries
  const samplePrompts = useMemo(() => {
    return generateSchemaQueries(schemaTables);
  }, [schemaTables]);

  useEffect(() => {
    aiService.getAIHealth()
      .then(setHealthStatus)
      .catch(() => {
        setHealthStatus({
          status: 'error',
          configured: false,
          provider: 'Gemini',
          model: 'gemini-3.5-flash-lite',
          message: 'Unable to connect to AI health endpoint.'
        });
      });
  }, []);

  // Reset active conversation thread
  const handleNewConversation = () => {
    const newConvId = generateUUID();
    setConversationId(newConvId);
    setTurns([]);
    setQuestion('');
    setFollowupText('');
    setActiveFollowupIndex(null);
    saveStoredConversation(datasetId, newConvId, []);
  };

  // Helper to execute end-to-end pipeline (Question -> Intent -> SQL -> Security -> Execution -> Insight)
  const processFullPipeline = async (
    userQ: string,
    turnId: string,
    existingIntent?: IntentAnalysis,
    convId: string = conversationId
  ) => {
    setIsProcessing(true);

    try {
      let intentToUse: IntentAnalysis;
      let analysisRes: AIAnalysisResponse;

      if (existingIntent) {
        intentToUse = existingIntent;
      } else {
        // Step 1: Phase 5 Intent Analysis
        setLoadingStage('Understanding question intent...');
        analysisRes = await aiService.analyzeQuestion({
          dataset_id: datasetId,
          question: userQ,
          clarification_round: 1
        });

        if (!analysisRes.success || !analysisRes.analysis) {
          setTurns((prev) =>
            prev.map((t) =>
              t.id === turnId
                ? { ...t, status: 'error', error: analysisRes.error || 'Failed to analyze question intent.' }
                : t
            )
          );
          setIsProcessing(false);
          return;
        }

        intentToUse = analysisRes.analysis;

        // Check if Phase 5 Clarification is required
        if (intentToUse.needs_clarification) {
          setTurns((prev) =>
            prev.map((t) =>
              t.id === turnId
                ? { ...t, status: 'clarifying', response: analysisRes }
                : t
            )
          );
          setIsProcessing(false);
          return;
        }
      }

      // Step 2: Phase 6 Text-to-SQL Generation
      setLoadingStage('Generating SQL query...');
      setTurns((prev) =>
        prev.map((t) => (t.id === turnId ? { ...t, status: 'generating_sql' } : t))
      );

      const sqlRes = await aiService.generateSQL({
        dataset_id: datasetId,
        question: userQ,
        intent: intentToUse
      });

      if (!sqlRes.success || !sqlRes.sql_result) {
        setTurns((prev) =>
          prev.map((t) =>
            t.id === turnId
              ? { ...t, status: 'error', error: sqlRes.error || 'Failed to generate SQL for this intent.' }
              : t
          )
        );
        setIsProcessing(false);
        return;
      }

      const generatedSQL = sqlRes.sql_result.sql;

      // Step 3: Phase 7 SQL Security Validation
      setLoadingStage('Validating query safety (Phase 7)...');
      setTurns((prev) =>
        prev.map((t) =>
          t.id === turnId
            ? { ...t, status: 'validating', sqlResponse: sqlRes }
            : t
        )
      );

      const valRes = await aiService.validateSQL({
        dataset_id: datasetId,
        sql: generatedSQL
      });

      if (!valRes.valid) {
        const errMsg = valRes.errors?.[0]?.message || 'Query failed security validation.';
        setTurns((prev) =>
          prev.map((t) =>
            t.id === turnId
              ? {
                  ...t,
                  status: 'completed',
                  validationResponse: valRes,
                  error: `Security Violation: ${errMsg}`
                }
              : t
          )
        );
        setIsProcessing(false);
        return;
      }

      // Step 4: Phase 8 Safe Execution, Visualizations & Insights
      setLoadingStage('Executing query & generating insights...');
      setTurns((prev) =>
        prev.map((t) => (t.id === turnId ? { ...t, status: 'executing' } : t))
      );

      const fullAnalysis = await aiService.executeFullAnalysis({
        dataset_id: datasetId,
        question: userQ,
        sql: generatedSQL,
        intent: intentToUse,
        conversation_id: convId
      });

      setTurns((prev) =>
        prev.map((t) =>
          t.id === turnId
            ? {
                ...t,
                status: 'completed',
                response: analysisRes || t.response,
                sqlResponse: sqlRes,
                validationResponse: valRes,
                fullAnalysis: fullAnalysis
              }
            : t
        )
      );

      // Non-blocking async insight enhancement if insight is not pre-populated
      if (!fullAnalysis.insight && fullAnalysis.execution?.success && fullAnalysis.execution?.rows?.length > 0) {
        aiService.generateInsight({
          question: userQ,
          columns: fullAnalysis.execution.columns,
          rows: fullAnalysis.execution.rows,
          intent: intentToUse as any
        }).then((insightRes) => {
          if (insightRes) {
            setTurns((prev) =>
              prev.map((t) =>
                t.id === turnId && t.fullAnalysis
                  ? { ...t, fullAnalysis: { ...t.fullAnalysis, insight: insightRes } }
                  : t
              )
            );
          }
        }).catch((err) => console.warn('Async insight loading:', err));
      }
    } catch (err: any) {
      setTurns((prev) =>
        prev.map((t) =>
          t.id === turnId
            ? { ...t, status: 'error', error: err.message || 'An unexpected error occurred.' }
            : t
        )
      );
    } finally {
      setIsProcessing(false);
    }
  };

  // Submit initial question
  const handleSubmitQuestion = async (qToSubmit?: string) => {
    const rawQ = qToSubmit || question;
    const targetQ = typeof rawQ === 'string' ? rawQ.trim() : '';
    if (!targetQ || isProcessing) return;

    const turnId = 'turn_' + Date.now();
    const newTurn: ConversationTurn = {
      id: turnId,
      question: targetQ,
      status: 'analyzing',
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
    };

    setTurns((prev) => [...prev, newTurn]);
    setQuestion('');
    await processFullPipeline(targetQ, turnId);
  };

  // Submit follow-up question attached to a previous turn
  const handleFollowupSubmit = async (turnIndex: number, prevTurn: ConversationTurn) => {
    if (!followupText.trim() || isProcessing) return;

    const fText = followupText.trim();
    setFollowupText('');
    setActiveFollowupIndex(null);

    const newTurnId = 'turn_' + Date.now();
    const newTurn: ConversationTurn = {
      id: newTurnId,
      question: fText,
      status: 'analyzing',
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
    };

    setTurns((prev) => [...prev, newTurn]);
    setIsProcessing(true);
    setLoadingStage('Understanding follow-up intent...');

    try {
      const prevIntentDict = prevTurn.fullAnalysis?.execution?.sql
        ? prevTurn.response?.analysis || null
        : null;

      const followupRes = await aiService.processFollowup({
        dataset_id: datasetId,
        conversation_id: conversationId,
        question: fText,
        previous_intent: prevIntentDict ? (prevIntentDict as any) : undefined,
        previous_question: prevTurn.question
      });

      if (!followupRes.success || !followupRes.analysis) {
        setTurns((prev) =>
          prev.map((t) =>
            t.id === newTurnId
              ? { ...t, status: 'error', error: followupRes.error || 'Could not understand follow-up question.' }
              : t
          )
        );
        setIsProcessing(false);
        return;
      }

      if (followupRes.analysis.needs_clarification) {
        setTurns((prev) =>
          prev.map((t) =>
            t.id === newTurnId
              ? { ...t, status: 'clarifying', response: followupRes }
              : t
          )
        );
        setIsProcessing(false);
        return;
      }

      await processFullPipeline(fText, newTurnId, followupRes.analysis);
    } catch (err: any) {
      setTurns((prev) =>
        prev.map((t) =>
          t.id === newTurnId
            ? { ...t, status: 'error', error: err.message || 'Failed to process follow-up.' }
            : t
        )
      );
      setIsProcessing(false);
    }
  };

  // Submit clarification choice
  const handleClarificationSubmit = async (turnId: string, originalQ: string, answer: string) => {
    setIsProcessing(true);
    setLoadingStage('Refining query intent with clarification...');

    try {
      const clarifyRes = await aiService.submitClarification({
        dataset_id: datasetId,
        original_question: originalQ,
        clarification: answer
      });

      if (!clarifyRes.success || !clarifyRes.analysis) {
        setTurns((prev) =>
          prev.map((t) =>
            t.id === turnId
              ? { ...t, status: 'error', error: clarifyRes.error || 'Clarification processing failed.' }
              : t
          )
        );
        setIsProcessing(false);
        return;
      }

      await processFullPipeline(originalQ, turnId, clarifyRes.analysis);
    } catch (err: any) {
      setTurns((prev) =>
        prev.map((t) =>
          t.id === turnId
            ? { ...t, status: 'error', error: err.message || 'Clarification processing error.' }
            : t
        )
      );
      setIsProcessing(false);
    }
  };

  // Re-run previous query safely through Phase 7 validation & Phase 8 execution
  const handleRerunQuery = async (queryId: string, item: QueryHistoryItem) => {
    setIsHistoryOpen(false);
    setIsProcessing(true);
    setLoadingStage('Re-validating and running stored query safely...');

    const turnId = 'turn_' + Date.now();
    const newTurn: ConversationTurn = {
      id: turnId,
      question: `[Re-run] ${item.user_question}`,
      status: 'executing',
      timestamp: new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
    };

    setTurns((prev) => [...prev, newTurn]);

    try {
      const fullRes = await aiService.rerunQuery(datasetId, queryId);
      setTurns((prev) =>
        prev.map((t) =>
          t.id === turnId
            ? {
                ...t,
                status: 'completed',
                fullAnalysis: fullRes
              }
            : t
        )
      );
    } catch (err: any) {
      setTurns((prev) =>
        prev.map((t) =>
          t.id === turnId
            ? { ...t, status: 'error', error: err.message || 'Failed to re-run query.' }
            : t
        )
      );
    } finally {
      setIsProcessing(false);
    }
  };

  return (
    <div className="flex flex-col h-[calc(100vh-17.5rem)] min-h-[420px] bg-slate-950 dark:bg-[#2C2C2C] text-slate-100 dark:text-[#F2F2F2] rounded-2xl border border-slate-800 dark:border-[#484848] shadow-2xl overflow-hidden relative">
      {/* Workspace Header */}
      <div className="px-5 py-3 border-b border-slate-800 dark:border-[#484848] bg-slate-900/60 dark:bg-[#202020] backdrop-blur-md flex items-center justify-between shrink-0">
        <div className="flex items-center gap-3">
          <div className="p-2 bg-indigo-500/10 dark:bg-[rgba(138,180,248,0.12)] text-brand-600 dark:text-[#8AB4F8] rounded-xl border border-indigo-500/20 dark:border-[rgba(138,180,248,0.35)]">
            <Sparkles className="w-4.5 h-4.5" />
          </div>
          <div>
            <h2 className="font-bold text-base md:text-lg text-slate-900 dark:text-[#F2F2F2] flex items-center gap-2">
              Ask Your Data
              {datasetName && (
                <span className="text-xs px-2.5 py-0.5 rounded-full bg-slate-800 dark:bg-[#383838] text-slate-400 dark:text-[#C7C7C7] font-medium border border-slate-700 dark:border-[#484848]">
                  {datasetName}
                </span>
              )}
            </h2>
            <p className="text-xs text-slate-500 dark:text-[#A3A3A3]">Conversational Database Intelligence Workspace</p>
          </div>
        </div>

        <div className="flex items-center gap-2.5">
          <button
            onClick={handleNewConversation}
            className="flex items-center gap-1.5 text-xs md:text-sm px-3.5 py-2 bg-slate-800 dark:bg-[#383838] hover:bg-slate-700 dark:hover:bg-[#414141] text-slate-200 dark:text-[#F2F2F2] rounded-xl border border-slate-700 dark:border-[#4D4D4D] transition-all font-semibold cursor-pointer"
            title="Start a fresh conversation thread"
          >
            <PlusCircle className="w-4 h-4 text-brand-600 dark:text-[#8AB4F8]" />
            <span>New Conversation</span>
          </button>

          <button
            onClick={() => setIsHistoryOpen(true)}
            className="flex items-center gap-1.5 text-xs md:text-sm px-3.5 py-2 bg-slate-800 dark:bg-[#383838] hover:bg-slate-700 dark:hover:bg-[#414141] text-slate-200 dark:text-[#F2F2F2] rounded-xl border border-slate-700 dark:border-[#4D4D4D] transition-all font-semibold cursor-pointer"
            title="View dataset query history"
          >
            <History className="w-4 h-4 text-brand-600 dark:text-[#8AB4F8]" />
            <span>Recent Queries</span>
          </button>
        </div>
      </div>

      {/* Main Conversational Thread Area */}
      <div className="flex-1 overflow-y-auto p-4 md:p-6 space-y-4">
        {turns.length === 0 ? (
          <div className="max-w-3xl mx-auto h-full flex flex-col items-center justify-center text-center space-y-4 md:space-y-5 py-4">
            <div className="w-16 h-16 rounded-2xl bg-indigo-500/10 dark:bg-[rgba(138,180,248,0.12)] border border-indigo-500/20 dark:border-[rgba(138,180,248,0.35)] flex items-center justify-center text-brand-600 dark:text-[#8AB4F8] shadow-md shrink-0 mb-1">
              <MessageSquare className="w-8 h-8" />
            </div>
            <div className="space-y-2">
              <h3 className="text-2xl md:text-3xl font-bold text-slate-900 dark:text-[#F2F2F2] tracking-tight">Ask anything about your data.</h3>
              <p className="text-sm md:text-base text-slate-500 dark:text-[#C7C7C7] max-w-xl mx-auto leading-relaxed">
                Ask questions in plain English. SQLens will analyze intent, generate read-only SQL, validate security, execute safely, and visualize insights.
              </p>
            </div>

            {/* Sample Prompts */}
            <div className="w-full pt-2 md:pt-3">
              <p className="text-xs md:text-sm font-semibold text-slate-400 dark:text-[#A3A3A3] uppercase tracking-wider mb-3">TRY RELATED QUERIES</p>
              <div className="flex flex-wrap justify-center gap-2.5 max-w-2xl mx-auto">
                {samplePrompts.map((promptText, idx) => (
                  <button
                    key={idx}
                    onClick={() => setQuestion(promptText)}
                    disabled={isProcessing}
                    className="text-xs md:text-sm bg-slate-900/80 dark:bg-[#383838] hover:bg-slate-800 dark:hover:bg-[#414141] border border-slate-800 dark:border-[#4D4D4D] text-slate-300 dark:text-[#F2F2F2] px-4 py-2.5 rounded-xl transition-all font-medium disabled:opacity-50 cursor-pointer shadow-sm"
                  >
                    "{promptText}"
                  </button>
                ))}
              </div>
            </div>
          </div>
        ) : (
          turns.map((turn, index) => (
            <div key={turn.id} className="space-y-4 max-w-5xl mx-auto">
              {/* User Question Card */}
              <div className="flex items-start gap-3 justify-end">
                <div className="bg-slate-800 dark:bg-[#383838] border border-slate-700 dark:border-[#555555] text-slate-100 dark:text-[#F2F2F2] p-4.5 rounded-2xl rounded-tr-sm max-w-2xl shadow-md">
                  <p className="text-sm md:text-base font-medium">{turn.question}</p>
                  <span className="text-[11px] text-slate-400 dark:text-[#A3A3A3] mt-1 block text-right">{turn.timestamp}</span>
                </div>
              </div>

              {/* SQLens Response Card */}
              <div className="flex items-start gap-3">
                <div className="w-9 h-9 rounded-xl bg-slate-900 dark:bg-[#383838] border border-slate-800 dark:border-[#484848] flex items-center justify-center text-brand-600 dark:text-[#8AB4F8] shrink-0 mt-1">
                  <Sparkles className="w-4.5 h-4.5" />
                </div>

                <div className="flex-1 bg-slate-900/70 dark:bg-[#333333] border border-slate-800 dark:border-[#484848] rounded-2xl p-5 md:p-6 space-y-4 shadow-xl">
                  {/* Status Indicator during processing */}
                  {turn.status !== 'completed' && turn.status !== 'clarifying' && turn.status !== 'error' && (
                    <div className="flex items-center gap-3 py-4 text-brand-600 dark:text-[#8AB4F8] text-sm font-medium">
                      <Loader2 className="w-5 h-5 animate-spin text-brand-600 dark:text-[#8AB4F8]" />
                      <span>{loadingStage}</span>
                    </div>
                  )}

                  {/* Error State */}
                  {turn.error && (
                    <div className="p-4 bg-rose-500/10 border border-rose-500/20 rounded-xl text-rose-300 dark:text-[#EF767A] text-sm flex items-start gap-3">
                      <AlertTriangle className="w-5 h-5 text-rose-400 dark:text-[#EF767A] shrink-0 mt-0.5" />
                      <div>
                        <p className="font-semibold text-rose-200 dark:text-[#F2F2F2]">Execution Notice</p>
                        <p className="mt-0.5">{turn.error}</p>
                      </div>
                    </div>
                  )}

                  {/* Phase 5 Clarification Card */}
                  {turn.status === 'clarifying' && turn.response?.analysis?.clarification && (
                    <ClarificationCard
                      clarification={turn.response.analysis.clarification}
                      onSubmitClarification={(ans) => handleClarificationSubmit(turn.id, turn.question, ans)}
                      isLoading={isProcessing}
                    />
                  )}

                  {/* Phase 8 Results, Visualizations & Insights */}
                  {turn.fullAnalysis && turn.fullAnalysis.execution?.success && (
                    <div className="space-y-4">
                      {/* AI Insight Card */}
                      {turn.fullAnalysis.insight && (
                        <ResultInsightCard insight={turn.fullAnalysis.insight} />
                      )}

                      {/* Chart Recommendation Visual */}
                      {turn.fullAnalysis.chart && turn.fullAnalysis.chart.chart_type !== 'none' && (
                        <ResultChart
                          chartId={turn.id}
                          chart={turn.fullAnalysis.chart}
                          columns={turn.fullAnalysis.execution.columns}
                          rows={turn.fullAnalysis.execution.rows}
                        />
                      )}

                      {/* Result Table */}
                      <ResultTable
                        chartId={turn.id}
                        hasChart={Boolean(turn.fullAnalysis.chart && turn.fullAnalysis.chart.chart_type !== 'none')}
                        columns={turn.fullAnalysis.execution.columns}
                        rows={turn.fullAnalysis.execution.rows}
                        rowCount={turn.fullAnalysis.execution.row_count}
                        truncated={turn.fullAnalysis.execution.truncated}
                        executionTimeMs={turn.fullAnalysis.execution.execution_time_ms}
                        question={turn.question}
                        insight={turn.fullAnalysis.insight?.summary_insight}
                      />

                      {/* Execution Metadata & Security Approved Badge */}
                      <div className="flex items-center justify-between text-xs text-slate-400 dark:text-[#C7C7C7] pt-2 border-t border-slate-800/60 dark:border-[#424242]">
                        <div className="flex items-center gap-3">
                          <span className="flex items-center gap-1 font-semibold text-emerald-400 dark:text-[#55D6A6]">
                            <CheckCircle2 className="w-3.5 h-3.5" />
                            ✓ Security Approved
                          </span>
                          <span>{turn.fullAnalysis.execution.row_count} rows returned</span>
                          <span>{turn.fullAnalysis.execution.execution_time_ms} ms</span>
                        </div>
                      </div>

                      {/* Collapsible Read-Only SQL Viewer */}
                      {turn.fullAnalysis.execution.sql && (
                        <SQLViewerCard
                          sqlResult={{
                            sql: turn.fullAnalysis.execution.sql,
                            dialect: 'postgresql',
                            tables_used: [],
                            columns_used: [],
                            explanation: 'Validated read-only SELECT query',
                            confidence: 0.95
                          }}
                          question={turn.question}
                          validationResponse={turn.validationResponse || turn.fullAnalysis.validation}
                        />
                      )}

                      {/* Inline Follow-up Input */}
                      <div className="pt-3 border-t border-slate-800/80 dark:border-[#424242]">
                        {activeFollowupIndex === index ? (
                          <div className="space-y-2">
                            <div className="flex gap-2 items-center">
                              <div className="relative flex-1 flex items-center">
                                <input
                                  type="text"
                                  value={followupText}
                                  onChange={(e) => setFollowupText(e.target.value)}
                                  onKeyDown={(e) => {
                                    if (e.key === 'Enter' && !e.shiftKey) {
                                      e.preventDefault();
                                      handleFollowupSubmit(index, turn);
                                    }
                                  }}
                                  placeholder='Ask a follow-up e.g. "What about only 2026?", "Show top 5 instead"...'
                                  className="w-full bg-slate-950 dark:bg-[#262626] text-slate-100 dark:text-[#F2F2F2] placeholder-slate-500 dark:placeholder-[#858585] pl-4 pr-10 py-2.5 text-xs md:text-sm rounded-xl border border-slate-700 dark:border-[#484848] focus:outline-none focus:ring-1 focus:ring-brand-500 dark:focus:ring-[#8AB4F8]"
                                />
                                <div className="absolute right-2 flex items-center">
                                  <VoiceInputButton
                                    onTranscript={(text) => setFollowupText(text)}
                                    disabled={isProcessing}
                                  />
                                </div>
                              </div>
                              <button
                                onClick={() => handleFollowupSubmit(index, turn)}
                                disabled={!followupText.trim() || isProcessing}
                                className="px-4 py-2.5 bg-brand-600 dark:bg-[#8AB4F8] hover:bg-brand-500 dark:hover:bg-[#A8C7FA] text-white dark:text-[#1B1B1B] rounded-xl text-xs md:text-sm font-semibold transition-colors disabled:opacity-50 flex items-center gap-1.5 cursor-pointer"
                              >
                                <Send className="w-3.5 h-3.5" />
                                Send
                              </button>
                              <button
                                onClick={() => setActiveFollowupIndex(null)}
                                className="px-3 py-2.5 text-slate-400 dark:text-[#C7C7C7] hover:text-slate-200 dark:hover:text-[#F2F2F2] text-xs md:text-sm cursor-pointer"
                              >
                                Cancel
                              </button>
                            </div>
                          </div>
                        ) : (
                          <button
                            onClick={() => setActiveFollowupIndex(index)}
                            disabled={isProcessing}
                            className="text-xs md:text-sm text-brand-600 dark:text-[#8AB4F8] hover:text-brand-500 dark:hover:text-[#A8C7FA] font-semibold flex items-center gap-1.5 transition-colors disabled:opacity-50 cursor-pointer"
                          >
                            <MessageSquare className="w-4 h-4" />
                            Ask Follow-up Question
                          </button>
                        )}
                      </div>
                    </div>
                  )}
                </div>
              </div>
            </div>
          ))
        )}
      </div>

      {/* Footer Query Input Bar */}
      <div className="p-4 md:p-5 border-t border-slate-800 dark:border-[#484848] bg-slate-900/80 dark:bg-[#202020] backdrop-blur-md">
        <form
          onSubmit={(e) => {
            e.preventDefault();
            handleSubmitQuestion();
          }}
          className="flex gap-3 max-w-5xl mx-auto items-center"
        >
          <div className="relative flex-1 flex items-center">
            <input
              type="text"
              value={question}
              onChange={(e) => setQuestion(e.target.value)}
              placeholder="Ask a question about your database in natural language..."
              disabled={isProcessing}
              className="w-full bg-slate-950 dark:bg-[#262626] text-slate-100 dark:text-[#F2F2F2] placeholder-slate-500 dark:placeholder-[#858585] pl-5 pr-12 py-3.5 text-sm md:text-base rounded-xl border border-slate-800 dark:border-[#484848] focus:outline-none focus:ring-2 focus:ring-brand-500 dark:focus:ring-[#8AB4F8] transition-all disabled:opacity-50"
            />
            <div className="absolute right-3 flex items-center">
              <VoiceInputButton
                onTranscript={(text) => setQuestion(text)}
                disabled={isProcessing}
              />
            </div>
          </div>
          <button
            type="submit"
            disabled={!question.trim() || isProcessing}
            className="px-6 py-3.5 bg-brand-600 dark:bg-[#8AB4F8] hover:bg-brand-500 dark:hover:bg-[#A8C7FA] text-white dark:text-[#1B1B1B] font-semibold rounded-xl text-sm md:text-base flex items-center gap-2 transition-all shadow-md disabled:opacity-50 disabled:cursor-not-allowed cursor-pointer"
          >
            {isProcessing ? (
              <Loader2 className="w-4.5 h-4.5 animate-spin" />
            ) : (
              <Send className="w-4.5 h-4.5" />
            )}
            Ask
          </button>
        </form>
      </div>

      {/* Query History Panel Drawer */}
      <QueryHistoryPanel
        datasetId={datasetId}
        isOpen={isHistoryOpen}
        onClose={() => setIsHistoryOpen(false)}
        onSelectQueryToRerun={handleRerunQuery}
        isRerunning={isProcessing}
      />
    </div>
  );
};
