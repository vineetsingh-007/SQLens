import React, { useState, useEffect } from 'react';
import {
  History,
  Search,
  Play,
  Trash2,
  ChevronLeft,
  ChevronRight,
  Clock,
  Database,
  BarChart2,
  Table as TableIcon,
  CheckCircle2,
  AlertCircle,
  Loader2,
  X
} from 'lucide-react';
import { aiService } from '../../services/api';
import { QueryHistoryItem, QueryHistoryListResponse, FullQueryAnalysisResponse } from '../../types/ai';

interface QueryHistoryPanelProps {
  datasetId: string;
  isOpen: boolean;
  onClose: () => void;
  onSelectQueryToRerun: (queryId: string, item: QueryHistoryItem) => void;
  isRerunning?: boolean;
}

export const QueryHistoryPanel: React.FC<QueryHistoryPanelProps> = ({
  datasetId,
  isOpen,
  onClose,
  onSelectQueryToRerun,
  isRerunning = false
}) => {
  const [historyData, setHistoryData] = useState<QueryHistoryListResponse | null>(null);
  const [page, setPage] = useState<number>(1);
  const [search, setSearch] = useState<string>('');
  const [isLoading, setIsLoading] = useState<boolean>(false);
  const [deleteConfirmId, setDeleteConfirmId] = useState<string | null>(null);
  const [deletingId, setDeletingId] = useState<string | null>(null);

  const fetchHistory = async () => {
    if (!datasetId) return;
    setIsLoading(true);
    try {
      const data = await aiService.getQueryHistory(datasetId, page, 10, search);
      setHistoryData(data);
    } catch (err) {
      console.error('Failed to load query history:', err);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    if (isOpen) {
      fetchHistory();
    }
  }, [datasetId, page, search, isOpen]);

  const handleDelete = async (queryId: string) => {
    setDeletingId(queryId);
    try {
      await aiService.deleteQueryHistoryItem(datasetId, queryId);
      setDeleteConfirmId(null);
      fetchHistory();
    } catch (err) {
      console.error('Failed to delete query history item:', err);
    } finally {
      setDeletingId(null);
    }
  };

  if (!isOpen) return null;

  return (
    <div className="fixed inset-y-0 right-0 w-full max-w-md bg-slate-900 border-l border-slate-800 shadow-2xl z-50 flex flex-col transition-all duration-300">
      {/* Header */}
      <div className="p-4 border-b border-slate-800 flex items-center justify-between bg-slate-950/60 backdrop-blur-md">
        <div className="flex items-center gap-2.5">
          <History className="w-5 h-5 text-indigo-400" />
          <h3 className="font-semibold text-white text-lg">Recent Query History</h3>
        </div>
        <button
          onClick={onClose}
          className="p-1 text-slate-400 hover:text-white rounded-lg hover:bg-slate-800 transition-colors"
        >
          <X className="w-5 h-5" />
        </button>
      </div>

      {/* Search Input */}
      <div className="p-4 border-b border-slate-800/80 bg-slate-900/50">
        <div className="relative">
          <Search className="w-4 h-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
          <input
            type="text"
            value={search}
            onChange={(e) => {
              setSearch(e.target.value);
              setPage(1);
            }}
            placeholder="Search query history..."
            className="w-full bg-slate-950 text-slate-100 placeholder-slate-500 pl-9 pr-4 py-2 text-sm rounded-xl border border-slate-800 focus:outline-none focus:ring-2 focus:ring-indigo-500/50 focus:border-indigo-500 transition-all"
          />
        </div>
      </div>

      {/* History Items List */}
      <div className="flex-1 overflow-y-auto p-4 space-y-3">
        {isLoading ? (
          <div className="flex flex-col items-center justify-center py-16 text-slate-400 gap-3">
            <Loader2 className="w-8 h-8 animate-spin text-indigo-400" />
            <p className="text-sm">Loading dataset query history...</p>
          </div>
        ) : !historyData || historyData.items.length === 0 ? (
          <div className="flex flex-col items-center justify-center py-16 text-slate-400 gap-3 text-center px-4">
            <Database className="w-10 h-10 text-slate-600 mb-1" />
            <p className="font-medium text-slate-300">No queries yet.</p>
            <p className="text-xs text-slate-500">Ask questions in the workspace to build query history.</p>
          </div>
        ) : (
          historyData.items.map((item) => (
            <div
              key={item.id}
              className="bg-slate-950/70 border border-slate-800/90 hover:border-slate-700/80 rounded-xl p-3.5 space-y-2.5 transition-all group"
            >
              <div className="flex items-start justify-between gap-2">
                <p className="text-sm font-medium text-slate-200 line-clamp-2">{item.user_question}</p>
                <span className="shrink-0 flex items-center gap-1 text-[10px] font-semibold px-2 py-0.5 rounded-full bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                  <CheckCircle2 className="w-3 h-3" />
                  {item.execution_status}
                </span>
              </div>

              {item.insight_summary && (
                <p className="text-xs text-slate-400 bg-slate-900/60 rounded-lg p-2 border border-slate-800/50 italic line-clamp-2">
                  "{item.insight_summary}"
                </p>
              )}

              <div className="flex items-center justify-between text-xs text-slate-500 pt-1 border-t border-slate-900">
                <div className="flex items-center gap-3">
                  <span className="flex items-center gap-1">
                    <TableIcon className="w-3.5 h-3.5 text-slate-400" />
                    {item.row_count} rows
                  </span>
                  {item.chart_type !== 'none' && (
                    <span className="flex items-center gap-1 text-indigo-400 uppercase font-semibold text-[10px]">
                      <BarChart2 className="w-3.5 h-3.5" />
                      {item.chart_type}
                    </span>
                  )}
                  <span className="flex items-center gap-1">
                    <Clock className="w-3.5 h-3.5" />
                    {new Date(item.created_at).toLocaleDateString([], { month: 'short', day: 'numeric', hour: '2-digit', minute: '2-digit' })}
                  </span>
                </div>

                <div className="flex items-center gap-1.5">
                  <button
                    onClick={() => onSelectQueryToRerun(item.id, item)}
                    disabled={isRerunning}
                    className="flex items-center gap-1 text-xs px-2.5 py-1 bg-indigo-600/20 text-indigo-300 hover:bg-indigo-600/40 hover:text-white rounded-lg border border-indigo-500/30 transition-all font-medium disabled:opacity-50"
                    title="Safely re-run with Phase 7 validation"
                  >
                    <Play className="w-3 h-3" />
                    Run Again
                  </button>

                  {deleteConfirmId === item.id ? (
                    <div className="flex items-center gap-1">
                      <button
                        onClick={() => handleDelete(item.id)}
                        disabled={deletingId === item.id}
                        className="text-[10px] px-2 py-1 bg-rose-600 text-white rounded-lg hover:bg-rose-500 transition-colors font-medium"
                      >
                        {deletingId === item.id ? 'Deleting...' : 'Confirm'}
                      </button>
                      <button
                        onClick={() => setDeleteConfirmId(null)}
                        className="text-[10px] px-1.5 py-1 bg-slate-800 text-slate-300 rounded-lg hover:text-white"
                      >
                        Cancel
                      </button>
                    </div>
                  ) : (
                    <button
                      onClick={() => setDeleteConfirmId(item.id)}
                      className="p-1 text-slate-500 hover:text-rose-400 rounded-lg hover:bg-slate-900 transition-colors"
                      title="Delete history item"
                    >
                      <Trash2 className="w-3.5 h-3.5" />
                    </button>
                  )}
                </div>
              </div>
            </div>
          ))
        )}
      </div>

      {/* Pagination Footer */}
      {historyData && historyData.total_pages > 1 && (
        <div className="p-3 border-t border-slate-800 bg-slate-950/80 flex items-center justify-between text-xs text-slate-400">
          <span>
            Page {historyData.page} of {historyData.total_pages} ({historyData.total} items)
          </span>
          <div className="flex items-center gap-2">
            <button
              onClick={() => setPage((p) => Math.max(1, p - 1))}
              disabled={page === 1}
              className="p-1 bg-slate-900 border border-slate-800 rounded-lg hover:bg-slate-800 disabled:opacity-40 text-slate-300"
            >
              <ChevronLeft className="w-4 h-4" />
            </button>
            <button
              onClick={() => setPage((p) => Math.min(historyData.total_pages, p + 1))}
              disabled={page >= historyData.total_pages}
              className="p-1 bg-slate-900 border border-slate-800 rounded-lg hover:bg-slate-800 disabled:opacity-40 text-slate-300"
            >
              <ChevronRight className="w-4 h-4" />
            </button>
          </div>
        </div>
      )}
    </div>
  );
};
