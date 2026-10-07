import React, { useState } from 'react';
import { Sparkles, Database, ArrowRight, Loader2, Play, CheckCircle2, ShieldCheck, Zap } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { datasetService } from '../services/api';

export const DemoPage: React.FC = () => {
  const navigate = useNavigate();
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  const handleStartDemo = async () => {
    setIsLoading(true);
    setError(null);
    try {
      const res = await datasetService.loadSampleDataset();
      navigate(`/datasets/${res.dataset_id}`);
    } catch (err: any) {
      console.error('Failed to load demo dataset:', err);
      setError(err.response?.data?.detail || 'Failed to initialize sample dataset.');
    } finally {
      setIsLoading(false);
    }
  };

  const demoFeatures = [
    { title: 'Dataset Ingestion', desc: 'Pre-loaded e-commerce sales dataset with customers, orders, and products.' },
    { title: 'Smart Intent Clarification', desc: 'Analyzes natural language questions and clarifies ambiguities automatically.' },
    { title: 'Read-Only Text-to-SQL', desc: 'Generates read-only SELECT statements with strict SQLGlot security validation.' },
    { title: 'Interactive Insights & Charts', desc: 'Executes safely and auto-recommends visual charts and key business takeaways.' }
  ];

  return (
    <div className="max-w-4xl mx-auto space-y-8 py-8">
      {/* Hero Header */}
      <div className="text-center space-y-4">
        <div className="inline-flex items-center space-x-2 px-3.5 py-1.5 rounded-full bg-indigo-500/10 border border-indigo-500/20 text-indigo-400 text-xs font-semibold">
          <Sparkles className="w-4 h-4 text-indigo-400" />
          <span>Interactive Live Demo</span>
        </div>

        <h1 className="text-3xl md:text-4xl font-extrabold tracking-tight text-white font-sans">
          Experience SQLens with Sample Data
        </h1>

        <p className="text-sm text-slate-400 max-w-xl mx-auto leading-relaxed">
          Test SQLens immediately without uploading your own files. Explore natural language database querying with pre-populated schema tables and sample records.
        </p>

        <div className="pt-2">
          <button
            onClick={handleStartDemo}
            disabled={isLoading}
            className="inline-flex items-center space-x-2 px-6 py-3 rounded-2xl bg-indigo-600 hover:bg-indigo-500 text-white font-medium text-sm transition-all shadow-xl shadow-indigo-600/20 disabled:opacity-50 active:scale-95 cursor-pointer"
          >
            {isLoading ? (
              <Loader2 className="w-4 h-4 animate-spin text-white" />
            ) : (
              <Play className="w-4 h-4 text-white fill-current" />
            )}
            <span>{isLoading ? 'Loading Sample Dataset...' : 'Launch Interactive Demo'}</span>
          </button>
        </div>

        {error && (
          <p className="text-xs text-rose-400 pt-2 font-medium">{error}</p>
        )}
      </div>

      {/* Feature Highlights Grid */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4 pt-4">
        {demoFeatures.map((feat, idx) => (
          <div key={idx} className="p-5 rounded-2xl bg-slate-900/80 border border-slate-800/80 space-y-2 shadow-lg">
            <div className="flex items-center space-x-2 text-indigo-400 font-semibold text-sm">
              <CheckCircle2 className="w-4 h-4 text-indigo-400 shrink-0" />
              <span>{feat.title}</span>
            </div>
            <p className="text-xs text-slate-400 leading-relaxed pl-6">{feat.desc}</p>
          </div>
        ))}
      </div>
    </div>
  );
};
