import React, { useState, useEffect } from 'react';
import { Settings, Moon, Sun, Table, Sparkles, Check, Laptop } from 'lucide-react';
import { useTheme } from '../context/ThemeContext';

export const SettingsPage: React.FC = () => {
  const { theme, setTheme } = useTheme();
  
  const [pageSize, setPageSize] = useState<number>(() => {
    const saved = localStorage.getItem('sqlens_page_size');
    return saved ? parseInt(saved, 10) : 15;
  });

  const [animationsEnabled, setAnimationsEnabled] = useState<boolean>(() => {
    const saved = localStorage.getItem('sqlens_animations');
    return saved !== null ? saved === 'true' : true;
  });

  const [savedSuccess, setSavedSuccess] = useState<boolean>(false);

  const handleSaveSettings = () => {
    localStorage.setItem('sqlens_page_size', pageSize.toString());
    localStorage.setItem('sqlens_animations', animationsEnabled.toString());
    setSavedSuccess(true);
    setTimeout(() => setSavedSuccess(false), 2000);
  };

  return (
    <div className="max-w-3xl mx-auto space-y-6 pb-12">
      {/* Header */}
      <div className="flex items-center space-x-3 border-b border-slate-800/80 pb-5">
        <div className="p-2.5 rounded-2xl bg-indigo-600/20 text-indigo-400 border border-indigo-500/30">
          <Settings className="w-6 h-6" />
        </div>
        <div>
          <h1 className="text-2xl font-bold text-white tracking-tight">Application Settings</h1>
          <p className="text-xs text-slate-400">Manage UI appearance, default layout preferences, and display options</p>
        </div>
      </div>

      {/* Settings Sections */}
      <div className="space-y-6">
        {/* Appearance Theme Card */}
        <div className="p-6 rounded-2xl bg-slate-900/90 border border-slate-800/80 space-y-4 shadow-xl">
          <div className="flex items-center space-x-2">
            <Laptop className="w-5 h-5 text-indigo-400" />
            <h2 className="text-base font-bold text-white">Appearance &amp; Theme</h2>
          </div>
          <p className="text-xs text-slate-400">Select your preferred color mode for the SQLens interface.</p>

          <div className="grid grid-cols-2 gap-4 pt-1">
            <button
              type="button"
              onClick={() => setTheme('dark')}
              className={`p-4 rounded-xl border text-left flex items-center space-x-3 transition-all cursor-pointer ${
                theme === 'dark'
                  ? 'bg-indigo-600/20 border-indigo-500 text-white font-semibold shadow-lg'
                  : 'bg-slate-950/60 border-slate-800 text-slate-400 hover:text-slate-200'
              }`}
            >
              <Moon className="w-5 h-5 text-indigo-400" />
              <div>
                <div className="text-xs font-bold">Dark Mode</div>
                <div className="text-[10px] text-slate-400">Slate-950 dark theme (Default)</div>
              </div>
            </button>

            <button
              type="button"
              onClick={() => setTheme('light')}
              className={`p-4 rounded-xl border text-left flex items-center space-x-3 transition-all cursor-pointer ${
                theme === 'light'
                  ? 'bg-indigo-600/20 border-indigo-500 text-white font-semibold shadow-lg'
                  : 'bg-slate-950/60 border-slate-800 text-slate-400 hover:text-slate-200'
              }`}
            >
              <Sun className="w-5 h-5 text-amber-400" />
              <div>
                <div className="text-xs font-bold">Light Mode</div>
                <div className="text-[10px] text-slate-400">Clean light interface</div>
              </div>
            </button>
          </div>
        </div>

        {/* Query Result Workspace Preferences */}
        <div className="p-6 rounded-2xl bg-slate-900/90 border border-slate-800/80 space-y-4 shadow-xl">
          <div className="flex items-center space-x-2">
            <Table className="w-5 h-5 text-indigo-400" />
            <h2 className="text-base font-bold text-white">Result Display Preferences</h2>
          </div>
          <p className="text-xs text-slate-400">Customize how query result tables and micro-animations render.</p>

          <div className="space-y-4 pt-2">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 p-3.5 rounded-xl bg-slate-950/60 border border-slate-800">
              <div>
                <label className="text-xs font-semibold text-slate-200 block">Default Table Page Size</label>
                <span className="text-[11px] text-slate-400">Number of rows displayed per table page in workspace</span>
              </div>

              <select
                value={pageSize}
                onChange={(e) => setPageSize(parseInt(e.target.value, 10))}
                className="bg-slate-900 border border-slate-800 text-slate-200 text-xs rounded-xl px-3 py-1.5 focus:outline-none focus:ring-1 focus:ring-indigo-500"
              >
                <option value={15}>15 rows per page</option>
                <option value={25}>25 rows per page</option>
                <option value={50}>50 rows per page</option>
              </select>
            </div>

            <div className="flex items-center justify-between p-3.5 rounded-xl bg-slate-950/60 border border-slate-800">
              <div className="flex items-center space-x-2">
                <Sparkles className="w-4 h-4 text-indigo-400" />
                <div>
                  <span className="text-xs font-semibold text-slate-200 block">Micro-animations</span>
                  <span className="text-[11px] text-slate-400">Enable smooth card transitions and loaders</span>
                </div>
              </div>

              <input
                type="checkbox"
                checked={animationsEnabled}
                onChange={(e) => setAnimationsEnabled(e.target.checked)}
                className="w-4 h-4 rounded bg-slate-900 border-slate-700 text-indigo-600 focus:ring-indigo-500 cursor-pointer"
              />
            </div>
          </div>
        </div>
      </div>

      {/* Save Button */}
      <div className="flex items-center justify-end space-x-3 pt-4">
        {savedSuccess && (
          <span className="text-xs font-semibold text-emerald-400 flex items-center space-x-1">
            <Check className="w-4 h-4" />
            <span>Preferences saved!</span>
          </span>
        )}
        <button
          type="button"
          onClick={handleSaveSettings}
          className="px-5 py-2.5 rounded-xl bg-indigo-600 hover:bg-indigo-500 text-white font-medium text-xs transition-all shadow-lg active:scale-95 cursor-pointer"
        >
          Save Preferences
        </button>
      </div>
    </div>
  );
};
