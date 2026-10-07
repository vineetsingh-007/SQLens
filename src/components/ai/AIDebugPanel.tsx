import React, { useState } from 'react';
import { Terminal, ChevronDown, ChevronUp, Code2, Clock, ShieldCheck, Database, Layers } from 'lucide-react';
import { IntentAnalysis } from '../../types/ai';

interface AIDebugPanelProps {
  question: string;
  analysis: IntentAnalysis;
  debugInfo?: {
    processing_time_ms: number;
    relevant_tables: string[];
    tokens_matched_tables: string[];
    detected_metrics: string[];
    detected_filters: string[];
    needs_clarification: boolean;
    confidence: number;
  } | null;
}

export const AIDebugPanel: React.FC<AIDebugPanelProps> = ({
  question,
  analysis,
  debugInfo
}) => {
  const [isOpen, setIsOpen] = useState(false);

  return (
    <div className="mt-6 rounded-2xl bg-slate-900/90 border border-slate-800 overflow-hidden text-xs font-mono shadow-xl">
      <button
        onClick={() => setIsOpen(!isOpen)}
        className="w-full flex items-center justify-between px-5 py-3 bg-slate-800/60 hover:bg-slate-800 transition-colors text-slate-300 font-sans cursor-pointer"
      >
        <div className="flex items-center space-x-2">
          <Terminal className="w-4 h-4 text-cyan-400" />
          <span className="font-semibold text-slate-200">Developer AI Debug Panel</span>
          <span className="px-2 py-0.5 rounded-full bg-cyan-500/10 text-cyan-400 text-[10px] border border-cyan-500/20 font-mono">
            Phase 4 Intent Inspector
          </span>
        </div>
        <div className="flex items-center space-x-3 text-slate-400">
          {debugInfo?.processing_time_ms && (
            <span className="flex items-center space-x-1">
              <Clock className="w-3 h-3 text-slate-500" />
              <span>{debugInfo.processing_time_ms}ms</span>
            </span>
          )}
          {isOpen ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
        </div>
      </button>

      {isOpen && (
        <div className="p-5 space-y-4 border-t border-slate-800 text-slate-300">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
            {/* Question & Intent */}
            <div className="space-y-2 bg-slate-950/60 p-3.5 rounded-xl border border-slate-800">
              <div className="text-slate-400 font-semibold uppercase text-[10px] tracking-wider flex items-center space-x-1.5">
                <Code2 className="w-3.5 h-3.5 text-cyan-400" />
                <span>Question & Intent</span>
              </div>
              <div className="text-slate-100 font-sans font-medium text-sm">{question}</div>
              <div className="pt-2 text-cyan-300 font-mono text-xs">
                Intent: <span className="font-bold text-cyan-200">{analysis.intent}</span>
              </div>
              <div className="text-slate-400 font-sans text-xs">{analysis.summary}</div>
            </div>

            {/* Relevant Tables & Schema Context */}
            <div className="space-y-2 bg-slate-950/60 p-3.5 rounded-xl border border-slate-800">
              <div className="text-slate-400 font-semibold uppercase text-[10px] tracking-wider flex items-center space-x-1.5">
                <Database className="w-3.5 h-3.5 text-emerald-400" />
                <span>Selected Relevant Schema</span>
              </div>
              <div className="flex flex-wrap gap-1.5 pt-1">
                {analysis.relevant_tables.map((t) => (
                  <span key={t} className="px-2 py-1 rounded bg-emerald-500/10 text-emerald-300 border border-emerald-500/30 text-xs">
                    table: {t}
                  </span>
                ))}
              </div>
              {analysis.relevant_columns.length > 0 && (
                <div className="text-[11px] text-slate-400 pt-1">
                  Columns: {analysis.relevant_columns.join(', ')}
                </div>
              )}
            </div>
          </div>

          {/* Metrics, Filters, Groupings */}
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-3">
            <div className="bg-slate-950/60 p-3 rounded-xl border border-slate-800">
              <div className="text-slate-400 font-semibold uppercase text-[10px]">Detected Metrics</div>
              {analysis.metrics.length > 0 ? (
                <div className="space-y-1 mt-1.5 text-slate-200">
                  {analysis.metrics.map((m, idx) => (
                    <div key={idx} className="text-xs">
                      • {m.name} {m.aggregation && `(${m.aggregation})`} {m.matched_column && `→ ${m.matched_column}`}
                    </div>
                  ))}
                </div>
              ) : (
                <div className="text-slate-500 text-xs italic mt-1">None</div>
              )}
            </div>

            <div className="bg-slate-950/60 p-3 rounded-xl border border-slate-800">
              <div className="text-slate-400 font-semibold uppercase text-[10px]">Detected Filters</div>
              {analysis.filters.length > 0 ? (
                <div className="space-y-1 mt-1.5 text-slate-200">
                  {analysis.filters.map((f, idx) => (
                    <div key={idx} className="text-xs">
                      • {f.column} {f.operator} {JSON.stringify(f.value)}
                    </div>
                  ))}
                </div>
              ) : (
                <div className="text-slate-500 text-xs italic mt-1">None</div>
              )}
            </div>

            <div className="bg-slate-950/60 p-3 rounded-xl border border-slate-800">
              <div className="text-slate-400 font-semibold uppercase text-[10px]">Group & Sort</div>
              <div className="space-y-1 mt-1.5 text-slate-200">
                {analysis.grouping.length > 0 && (
                  <div>Group: {analysis.grouping.map((g) => g.column).join(', ')}</div>
                )}
                {analysis.sorting && (
                  <div>Sort: {analysis.sorting.column} ({analysis.sorting.direction})</div>
                )}
                {!analysis.grouping.length && !analysis.sorting && (
                  <div className="text-slate-500 text-xs italic">None</div>
                )}
              </div>
            </div>
          </div>

          {/* Raw JSON Structure */}
          <div className="bg-slate-950 p-3 rounded-xl border border-slate-800 overflow-x-auto">
            <div className="text-slate-400 font-semibold uppercase text-[10px] mb-1">Parsed Pydantic Structure</div>
            <pre className="text-[11px] text-cyan-300/90 leading-relaxed font-mono">
              {JSON.stringify(analysis, null, 2)}
            </pre>
          </div>
        </div>
      )}
    </div>
  );
};
