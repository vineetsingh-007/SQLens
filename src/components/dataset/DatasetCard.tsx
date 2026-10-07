import React from 'react';
import { Dataset } from '../../types/dataset';
import { FileCode, FileSpreadsheet, Database as DbIcon, Trash2, ChevronRight, Layers, Table, Hash } from 'lucide-react';
import { useNavigate } from 'react-router-dom';

interface DatasetCardProps {
  dataset: Dataset;
  onDeleteClick: (dataset: Dataset) => void;
}

export const DatasetCard: React.FC<DatasetCardProps> = ({ dataset, onDeleteClick }) => {
  const navigate = useNavigate();

  const getFormatIcon = () => {
    switch (dataset.file_type) {
      case 'csv':
        return <FileCode className="h-5 w-5 text-sky-400" />;
      case 'excel':
        return <FileSpreadsheet className="h-5 w-5 text-emerald-400" />;
      case 'sqlite':
        return <DbIcon className="h-5 w-5 text-indigo-400" />;
      default:
        return <FileCode className="h-5 w-5 text-slate-400" />;
    }
  };

  const getStatusBadge = () => {
    switch (dataset.status) {
      case 'READY':
        return (
          <span className="px-2.5 py-1 text-xs font-semibold rounded-full bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
            ✓ Ready
          </span>
        );
      case 'PROCESSING':
        return (
          <span className="px-2.5 py-1 text-xs font-semibold rounded-full bg-sky-500/10 text-sky-400 border border-sky-500/20 animate-pulse">
            Processing...
          </span>
        );
      case 'FAILED':
        return (
          <span className="px-2.5 py-1 text-xs font-semibold rounded-full bg-rose-500/10 text-rose-400 border border-rose-500/20">
            ✕ Failed
          </span>
        );
      default:
        return null;
    }
  };

  const formattedDate = new Date(dataset.created_at).toLocaleDateString(undefined, {
    month: 'short',
    day: 'numeric',
    year: 'numeric'
  });

  return (
    <div className="bg-slate-900/60 border border-slate-800 hover:border-slate-700 rounded-2xl p-5 md:p-5.5 transition-all duration-200 hover:shadow-xl space-y-4 flex flex-col justify-between group">
      <div className="space-y-3">
        <div className="flex items-start justify-between">
          <div className="flex items-center space-x-3.5">
            <div className="h-11 w-11 rounded-xl bg-slate-800 border border-slate-700/80 flex items-center justify-center shrink-0">
              {getFormatIcon()}
            </div>
            <div>
              <h3 className="font-bold text-slate-100 text-base md:text-[1.05rem] group-hover:text-brand-400 transition-colors line-clamp-1">
                {dataset.original_filename}
              </h3>
              <p className="text-xs text-slate-400 capitalize">{dataset.file_type} dataset • {formattedDate}</p>
            </div>
          </div>
          {getStatusBadge()}
        </div>

        {/* Metadata summary cards */}
        <div className="grid grid-cols-3 gap-2.5 pt-2 text-center">
          <div className="bg-slate-950/60 p-2.5 rounded-xl border border-slate-800/80">
            <div className="text-xs text-slate-400 flex items-center justify-center space-x-1">
              <Layers className="h-3.5 w-3.5 text-slate-400" />
              <span>Tables</span>
            </div>
            <div className="text-base font-extrabold text-slate-200 mt-0.5">{dataset.number_of_tables}</div>
          </div>

          <div className="bg-slate-950/60 p-2.5 rounded-xl border border-slate-800/80">
            <div className="text-xs text-slate-400 flex items-center justify-center space-x-1">
              <Table className="h-3.5 w-3.5 text-slate-400" />
              <span>Rows</span>
            </div>
            <div className="text-base font-extrabold text-slate-200 mt-0.5">
              {dataset.total_rows.toLocaleString()}
            </div>
          </div>

          <div className="bg-slate-950/60 p-2.5 rounded-xl border border-slate-800/80">
            <div className="text-xs text-slate-400 flex items-center justify-center space-x-1">
              <Hash className="h-3.5 w-3.5 text-slate-400" />
              <span>Cols</span>
            </div>
            <div className="text-base font-extrabold text-slate-200 mt-0.5">{dataset.total_columns}</div>
          </div>
        </div>
      </div>

      {/* Footer buttons */}
      <div className="pt-2.5 border-t border-slate-800/60 flex items-center justify-between">
        <button
          onClick={() => onDeleteClick(dataset)}
          className="p-2 rounded-lg text-slate-500 hover:text-rose-400 hover:bg-rose-500/10 transition-colors"
          title="Delete dataset"
        >
          <Trash2 className="h-4.5 w-4.5" />
        </button>

        <button
          onClick={() => navigate(`/datasets/${dataset.id}`)}
          className="inline-flex items-center space-x-1.5 px-4 py-2 rounded-xl bg-slate-800 hover:bg-brand-600 text-slate-200 hover:text-white text-xs md:text-sm font-semibold transition-colors"
        >
          <span>View Dataset</span>
          <ChevronRight className="h-4 w-4" />
        </button>
      </div>
    </div>
  );
};
