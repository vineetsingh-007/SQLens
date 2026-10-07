import React, { useState } from 'react';
import { HelpCircle, Send, Sparkles, CheckCircle2 } from 'lucide-react';
import { ClarificationDetails } from '../../types/ai';

interface ClarificationCardProps {
  clarification: ClarificationDetails;
  onSubmitClarification: (clarificationText: string) => void;
  isLoading: boolean;
  clarificationRound?: number;
}

export const ClarificationCard: React.FC<ClarificationCardProps> = ({
  clarification,
  onSubmitClarification,
  isLoading,
  clarificationRound = 1
}) => {
  const [selectedOption, setSelectedOption] = useState<string | null>(null);
  const [customInput, setCustomInput] = useState('');
  const [showCustomInput, setShowCustomInput] = useState(false);

  const handleOptionClick = (label: string) => {
    setSelectedOption(label);
    setShowCustomInput(false);
    onSubmitClarification(label);
  };

  const handleCustomSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (!customInput.trim() || isLoading) return;
    onSubmitClarification(customInput.trim());
  };

  return (
    <div className="my-6 p-6 rounded-2xl bg-amber-500/10 border border-amber-500/30 backdrop-blur-md shadow-xl animate-fade-in">
      <div className="flex items-start justify-between gap-4 mb-4">
        <div className="flex items-start space-x-3">
          <div className="p-2.5 rounded-xl bg-amber-500/20 text-amber-400 border border-amber-500/30 shrink-0">
            <HelpCircle className="w-6 h-6 animate-pulse" />
          </div>
          <div>
            <span className="text-xs font-semibold tracking-wider text-amber-400 uppercase">
              SQLens Needs Clarification
            </span>
            <h3 className="text-lg font-bold text-slate-100 mt-0.5">
              {clarification.question}
            </h3>
            <p className="text-sm text-slate-300 mt-1">
              Please choose an interpretation backed by your dataset schema so SQLens can analyze your question accurately:
            </p>
          </div>
        </div>

        <span className="px-3 py-1 rounded-full bg-amber-500/20 text-amber-300 border border-amber-500/40 text-xs font-mono font-semibold shrink-0">
          Step {clarificationRound} of 3
        </span>
      </div>


      <div className="space-y-3 mt-4">
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
          {clarification.options.map((option) => {
            const isSelected = selectedOption === option.label;
            return (
              <button
                key={option.id}
                onClick={() => handleOptionClick(option.label)}
                disabled={isLoading}
                className={`flex items-center justify-between p-4 rounded-xl text-left transition-all duration-200 border ${
                  isSelected
                    ? 'bg-amber-500/30 border-amber-400 text-amber-100 ring-2 ring-amber-400/50 shadow-lg'
                    : 'bg-slate-800/80 hover:bg-slate-700/80 border-slate-700 text-slate-200 hover:border-amber-500/50'
                } ${isLoading ? 'opacity-50 cursor-not-allowed' : 'cursor-pointer'}`}
              >
                <div>
                  <div className="font-semibold text-sm">{option.label}</div>
                  {option.description && (
                    <div className="text-xs text-slate-400 mt-1">{option.description}</div>
                  )}
                </div>
                {isSelected ? (
                  <CheckCircle2 className="w-5 h-5 text-amber-400 shrink-0 ml-2" />
                ) : (
                  <Sparkles className="w-4 h-4 text-slate-500 group-hover:text-amber-400 shrink-0 ml-2" />
                )}
              </button>
            );
          })}
        </div>

        {/* Custom / Other option toggle */}
        {!showCustomInput ? (
          <button
            onClick={() => setShowCustomInput(true)}
            disabled={isLoading}
            className="text-xs text-amber-400/90 hover:text-amber-300 underline font-medium cursor-pointer pt-2 inline-block"
          >
            + Other / Type custom clarification...
          </button>
        ) : (
          <form onSubmit={handleCustomSubmit} className="mt-3 flex items-center space-x-2">
            <input
              type="text"
              value={customInput}
              onChange={(e) => setCustomInput(e.target.value)}
              placeholder="e.g., Customers who buy most frequently..."
              disabled={isLoading}
              className="flex-1 bg-slate-900 border border-amber-500/40 rounded-xl px-4 py-2.5 text-sm text-slate-100 placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-amber-500/50"
            />
            <button
              type="submit"
              disabled={!customInput.trim() || isLoading}
              className="px-4 py-2.5 rounded-xl bg-amber-500 hover:bg-amber-400 disabled:opacity-50 text-slate-950 font-semibold text-sm flex items-center space-x-1.5 transition-all shadow-md cursor-pointer"
            >
              <span>Send</span>
              <Send className="w-3.5 h-3.5" />
            </button>
          </form>
        )}
      </div>
    </div>
  );
};
