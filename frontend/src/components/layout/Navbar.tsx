import React, { useEffect, useState } from 'react';
import { Database, Activity, Sparkles } from 'lucide-react';
import { datasetService } from '../../services/api';

export const Navbar: React.FC = () => {
  const [health, setHealth] = useState<'ok' | 'degraded' | 'checking'>('checking');

  useEffect(() => {
    datasetService.checkHealth()
      .then(res => setHealth(res.status === 'ok' ? 'ok' : 'degraded'))
      .catch(() => setHealth('degraded'));
  }, []);

  return (
    <header className="h-16 border-b border-slate-200 dark:border-[#484848] bg-white/90 dark:bg-[#202020] backdrop-blur-md sticky top-0 z-30 px-6 flex items-center justify-between transition-colors">
      <div className="flex items-center space-x-3">
        <div className="h-10 w-10 rounded-xl bg-slate-100 dark:bg-[#383838] border border-slate-300 dark:border-[#484848] flex items-center justify-center">
          <Database className="h-5 w-5 text-brand-600 dark:text-[#8AB4F8]" />
        </div>
        <div>
          <div className="flex items-center space-x-2">
            <span className="font-bold text-lg tracking-tight text-slate-900 dark:text-[#F2F2F2] font-sans">SQLens</span>
            <span className="px-2 py-0.5 text-[10px] font-semibold tracking-wide uppercase rounded-full bg-indigo-500/10 dark:bg-[rgba(138,180,248,0.12)] text-brand-600 dark:text-[#8AB4F8] border border-indigo-500/20 dark:border-[rgba(138,180,248,0.35)]">
              v1.0
            </span>
          </div>
          <p className="text-xs text-slate-500 dark:text-[#A3A3A3] font-normal">Ask Your Data. Get Answers. No SQL Required.</p>
        </div>
      </div>

      <div className="flex items-center space-x-4">
        {/* Backend System Health */}
        <div className="flex items-center space-x-2 px-3 py-1.5 rounded-lg bg-slate-100 dark:bg-[#262626] border border-slate-200 dark:border-[#484848] text-xs">
          <Activity className={`h-3.5 w-3.5 ${health === 'ok' ? 'text-emerald-500 dark:text-[#55D6A6] animate-pulse' : 'text-amber-500 dark:text-[#E8B84A]'}`} />
          <span className="text-slate-500 dark:text-[#C7C7C7]">System:</span>
          <span className={health === 'ok' ? 'text-emerald-600 dark:text-[#55D6A6] font-medium' : 'text-amber-600 dark:text-[#E8B84A] font-medium'}>
            {health === 'ok' ? 'Connected' : health === 'checking' ? 'Checking...' : 'Degraded'}
          </span>
        </div>
      </div>
    </header>
  );
};
