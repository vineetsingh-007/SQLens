import React from 'react';
import { UploadZone } from '../components/common/UploadZone';
import { UploadCloud } from 'lucide-react';

export const UploadPage: React.FC = () => {
  return (
    <div className="space-y-6 max-w-4xl mx-auto pb-12">
      <div className="border-b border-slate-800 pb-4">
        <h1 className="text-2xl font-bold text-white flex items-center space-x-2.5">
          <UploadCloud className="h-6 w-6 text-brand-400" />
          <span>Upload Dataset</span>
        </h1>
        <p className="text-xs text-slate-400 mt-1">
          Select or drop your CSV, Excel, or SQLite database file to ingest it into SQLens.
        </p>
      </div>

      <div className="bg-slate-900/40 border border-slate-800/80 rounded-3xl p-6 md:p-8 space-y-6 shadow-2xl">
        <UploadZone />
      </div>
    </div>
  );
};
