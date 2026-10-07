import React from 'react';
import { Lightbulb, CheckCircle2 } from 'lucide-react';
import { AIInsightResult } from '../../types/ai';

interface ResultInsightCardProps {
  insight?: AIInsightResult | null;
}

export const ResultInsightCard: React.FC<ResultInsightCardProps> = ({ insight }) => {
  if (!insight || (!insight.summary_insight && (!insight.key_highlights || insight.key_highlights.length === 0))) {
    return null;
  }

  return (
    <div className="p-5 md:p-6 rounded-2xl bg-slate-900 dark:bg-[#333333] border border-slate-800 dark:border-[#484848] shadow-xl relative overflow-hidden space-y-3 animate-fade-in">
      {/* Header */}
      <div className="flex items-center space-x-2.5">
        <div className="p-1.5 rounded-lg bg-indigo-500/10 dark:bg-[rgba(138,180,248,0.12)] border border-indigo-500/20 dark:border-[rgba(138,180,248,0.35)] shrink-0">
          <Lightbulb className="w-4 h-4 text-brand-600 dark:text-[#8AB4F8]" />
        </div>
        <h4 className="text-xs font-bold uppercase tracking-wider text-brand-600 dark:text-[#8AB4F8]">
          AI Data Insights
        </h4>
      </div>

      {/* Summary Insight */}
      {insight.summary_insight && (
        <p className="text-sm font-medium text-slate-900 dark:text-[#F2F2F2] leading-relaxed">
          "{insight.summary_insight}"
        </p>
      )}

      {/* Key Highlight Bullets */}
      {insight.key_highlights && insight.key_highlights.length > 0 && (
        <div className="pt-1 flex flex-wrap gap-2">
          {insight.key_highlights.map((highlight, idx) => (
            <div
              key={idx}
              className="px-3 py-1.5 rounded-xl bg-slate-950/60 dark:bg-[#262626] border border-slate-800 dark:border-[#484848] text-xs text-slate-700 dark:text-[#C7C7C7] flex items-center space-x-1.5 shadow-sm"
            >
              <CheckCircle2 className="w-3.5 h-3.5 text-brand-600 dark:text-[#8AB4F8] shrink-0" />
              <span>{highlight}</span>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};
