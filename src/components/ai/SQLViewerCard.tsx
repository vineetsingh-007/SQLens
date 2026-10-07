import React, { useState } from 'react';
import { Code, Copy, Check, ChevronDown, ChevronRight } from 'lucide-react';
import { SQLGenerationResult, SQLValidationResponse } from '../../types/ai';

interface SQLViewerCardProps {
  sqlResult: SQLGenerationResult;
  question?: string;
  generationTimeMs?: number | null;
  validationResponse?: SQLValidationResponse | null;
  isValidating?: boolean;
}

export const SQLViewerCard: React.FC<SQLViewerCardProps> = ({ sqlResult }) => {
  const [isExpanded, setIsExpanded] = useState<boolean>(false);
  const [isCopied, setIsCopied] = useState<boolean>(false);

  const handleCopy = async () => {
    if (!sqlResult.sql) return;
    try {
      await navigator.clipboard.writeText(sqlResult.sql);
      setIsCopied(true);
      setTimeout(() => setIsCopied(false), 2000);
    } catch (err) {
      console.error('Failed to copy SQL to clipboard:', err);
    }
  };

  return (
    <div className="rounded-xl bg-slate-900/90 border border-slate-800 shadow-lg overflow-hidden transition-all text-xs">
      {/* Compact Minimal Header Bar */}
      <div className="px-4 py-3 bg-slate-900/90 dark:bg-[#333333] flex items-center justify-between gap-3">
        <div className="flex items-center space-x-2">
          <span className="px-2.5 py-0.5 rounded-full text-[11px] font-bold bg-indigo-500/10 dark:bg-[rgba(138,180,248,0.12)] text-brand-600 dark:text-[#8AB4F8] border border-indigo-500/20 dark:border-[rgba(138,180,248,0.35)]">
            PostgreSQL
          </span>
        </div>

        <button
          type="button"
          onClick={() => setIsExpanded(!isExpanded)}
          className="px-3 py-1.5 rounded-xl bg-slate-800 dark:bg-[#383838] hover:bg-slate-700 dark:hover:bg-[#414141] border border-slate-700 dark:border-[#4D4D4D] text-slate-300 dark:text-[#F2F2F2] hover:text-white font-medium flex items-center space-x-1.5 transition-all cursor-pointer"
        >
          {isExpanded ? (
            <>
              <ChevronDown className="w-3.5 h-3.5 text-slate-400 dark:text-[#A3A3A3]" />
              <span>Hide Generated SQL</span>
            </>
          ) : (
            <>
              <ChevronRight className="w-3.5 h-3.5 text-slate-400 dark:text-[#A3A3A3]" />
              <span>▸ View Generated SQL</span>
            </>
          )}
        </button>
      </div>

      {/* Expanded SQL View */}
      {isExpanded && (
        <div className="p-4 border-t border-slate-800/80 dark:border-[#484848] bg-slate-950 dark:bg-[#262626] space-y-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-2 text-slate-300 dark:text-[#F2F2F2] font-semibold text-xs">
              <Code className="w-4 h-4 text-brand-600 dark:text-[#8AB4F8]" />
              <span>Generated PostgreSQL Query</span>
            </div>

            <button
              type="button"
              onClick={handleCopy}
              className="px-3 py-1.5 rounded-lg bg-slate-800 dark:bg-[#383838] hover:bg-slate-700 dark:hover:bg-[#414141] border border-slate-700 dark:border-[#4D4D4D] text-xs font-medium text-slate-200 dark:text-[#F2F2F2] flex items-center space-x-1.5 transition-all cursor-pointer active:scale-95"
              title="Copy SQL to clipboard"
            >
              {isCopied ? (
                <>
                  <Check className="w-3.5 h-3.5 text-emerald-400 dark:text-[#55D6A6]" />
                  <span className="text-emerald-400 dark:text-[#55D6A6] font-bold">Copied!</span>
                </>
              ) : (
                <>
                  <Copy className="w-3.5 h-3.5 text-slate-400 dark:text-[#A3A3A3]" />
                  <span>Copy SQL</span>
                </>
              )}
            </button>
          </div>

          <div className="rounded-xl border border-slate-800 dark:border-[#484848] bg-slate-900/90 dark:bg-[#242424] overflow-hidden">
            <pre className="p-4 text-xs font-mono text-slate-100 dark:text-[#E5E5E5] bg-slate-900/90 dark:bg-[#242424] overflow-x-auto leading-relaxed">
              <code>{sqlResult.sql}</code>
            </pre>
          </div>
        </div>
      )}
    </div>
  );
};
