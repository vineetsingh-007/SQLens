import React, { useEffect, useState } from 'react';
import {
  History,
  Search,
  Database,
  Play,
  CheckCircle2,
  Table as TableIcon,
  BarChart2,
  Clock,
  Loader2,
  Trash2,
  ArrowRight
} from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { datasetService, aiService } from '../services/api';
import { Dataset } from '../types/dataset';
import { QueryHistoryItem, QueryHistoryListResponse } from '../types/ai';

export const QueryHistoryPage: React.FC = () => {
  const navigate = useNavigate();
  const [datasets, setDatasets] = useState<Dataset[]>([]);
  const [selectedDatasetId, setSelectedDatasetId] = useState<string>('');
  const [historyData, setHistoryData] = useState<QueryHistoryListResponse | null>(null);
  const [page, setPage] = useState<number>(1);
  const [search, setSearch] = useState<string>('');
  const [isLoading, setIsLoading] = useState<boolean>(true);
  const [deletingId, setDeletingId] = useState<string | null>(null);

  useEffect(() => {
    datasetService.getDatasets()
      .then((data) => {
        setDatasets(data);
        if (data.length > 0) {
          setSelectedDatasetId(data[0].id);
        } else {
          setIsLoading(false);
        }
      })
      .catch((err) => {
        console.error('Failed to load datasets for history:', err);
        setIsLoading(false);
      });
  }, []);

  const fetchHistory = async () => {
    if (!selectedDatasetId) {
      setIsLoading(false);
      return;
    }
    setIsLoading(true);
    try {
      const res = await aiService.getQueryHistory(selectedDatasetId, page, 15, search);
      setHistoryData(res);
    } catch (err) {
      console.error('Failed to load query history:', err);
    } finally {
      setIsLoading(false);
    }
  };

  useEffect(() => {
    if (selectedDatasetId) {
      fetchHistory();
    }
  }, [selectedDatasetId, page, search]);

  const handleDelete = async (queryId: string) => {
    if (!selectedDatasetId) return;
    setDeletingId(queryId);
    try {
      await aiService.deleteQueryHistoryItem(selectedDatasetId, queryId);
      await fetchHistory();
    } catch (err) {
      console.error('Failed to delete query history item:', err);
    } finally {
      setDeletingId(null);
    }
  };

  const handleRunAgain = (datasetId: string) => {
    navigate(`/datasets/${datasetId}`);
  };

  return (
    <div className="space-y-6 pb-12">
      {/* Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 border-b border-slate-800/80 pb-5">
        <div className="flex items-center space-x-3">
          <div className="p-2.5 rounded-2xl bg-indigo-600/20 text-indigo-400 border border-indigo-500/30">
            <History className="w-6 h-6" />
          </div>
          <div>
            <h1 className="text-2xl font-bold text-white tracking-tight">Query History</h1>
            <p className="text-xs text-slate-400">View and re-run your previous natural-language SQL queries</p>
          </div>
        </div>

        {/* Dataset Selector Dropdown */}
        {datasets.length > 0 && (
          <div className="flex items-center space-x-2">
            <Database className="w-4 h-4 text-indigo-400" />
            <select
              value={selectedDatasetId}
              onChange={(e) => {
                setSelectedDatasetId(e.target.value);
                setPage(1);
              }}
              className="bg-slate-900 text-slate-200 border border-slate-800 text-xs rounded-xl px-3 py-2 focus:outline-none focus:ring-2 focus:ring-indigo-500/50"
            >
              {datasets.map((ds) => (
                <option key={ds.id} value={ds.id}>
                  {ds.original_filename} ({ds.total_rows || 0} rows)
                </option>
              ))}
            </select>
          </div>
        )}
      </div>

      {/* Search Input Bar */}
      <div className="flex items-center justify-between gap-4">
        <div className="relative flex-1 max-w-md">
          <Search className="w-4 h-4 text-slate-400 absolute left-3.5 top-1/2 -translate-y-1/2" />
          <input
            type="text"
            value={search}
            onChange={(e) => {
              setSearch(e.target.value);
              setPage(1);
            }}
            placeholder="Search questions or SQL..."
            className="w-full bg-slate-900/90 border border-slate-800 text-slate-200 placeholder-slate-500 text-xs rounded-xl pl-9 pr-4 py-2.5 focus:outline-none focus:ring-2 focus:ring-indigo-500/50"
          />
        </div>
      </div>

      {/* Main Query History Table / Card List */}
      {isLoading ? (
        <div className="py-20 text-center space-y-3">
          <Loader2 className="w-8 h-8 text-indigo-400 animate-spin mx-auto" />
          <p className="text-xs text-slate-400">Loading query history...</p>
        </div>
      ) : datasets.length === 0 ? (
        <div className="p-12 text-center rounded-2xl bg-slate-900/50 border border-slate-800 space-y-3">
          <Database className="w-12 h-12 text-slate-600 mx-auto" />
          <h3 className="text-base font-bold text-slate-200">No Datasets Available</h3>
          <p className="text-xs text-slate-400 max-w-md mx-auto">
            Upload a dataset or try sample data on the Dashboard to execute queries and record history.
          </p>
          <button
            onClick={() => navigate('/')}
            className="inline-flex items-center space-x-2 px-4 py-2 rounded-xl bg-indigo-600 text-white text-xs font-medium hover:bg-indigo-500 transition-colors"
          >
            <span>Go to Dashboard</span>
            <ArrowRight className="w-3.5 h-3.5" />
          </button>
        </div>
      ) : !historyData || historyData.items.length === 0 ? (
        <div className="p-12 text-center rounded-2xl bg-slate-900/50 border border-slate-800 space-y-3">
          <History className="w-12 h-12 text-slate-600 mx-auto" />
          <h3 className="text-base font-bold text-slate-200">No Recorded Queries</h3>
          <p className="text-xs text-slate-400 max-w-md mx-auto">
            Ask questions in the Ask Your Data workspace to build query history for this dataset.
          </p>
          {selectedDatasetId && (
            <button
              onClick={() => navigate(`/datasets/${selectedDatasetId}`)}
              className="inline-flex items-center space-x-2 px-4 py-2 rounded-xl bg-indigo-600 text-white text-xs font-medium hover:bg-indigo-500 transition-colors"
            >
              <span>Open Query Workspace</span>
              <ArrowRight className="w-3.5 h-3.5" />
            </button>
          )}
        </div>
      ) : (
        <div className="space-y-3">
          {historyData.items.map((item: QueryHistoryItem) => (
            <div
              key={item.id}
              className="p-5 rounded-2xl bg-slate-900/80 border border-slate-800/80 hover:border-indigo-500/30 transition-all space-y-3 shadow-xl"
            >
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
                <div className="flex items-center space-x-2">
                  <span className="px-2.5 py-0.5 rounded-full text-[10px] font-bold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20 flex items-center space-x-1">
                    <CheckCircle2 className="w-3 h-3" />
                    <span>{item.execution_status}</span>
                  </span>
                  <span className="text-xs font-semibold text-slate-100">{item.user_question}</span>
                </div>

                <div className="flex items-center space-x-2">
                  <button
                    onClick={() => handleRunAgain(item.dataset_id)}
                    className="px-3 py-1.5 rounded-xl bg-indigo-600/20 hover:bg-indigo-600/30 text-indigo-300 border border-indigo-500/30 text-xs font-medium flex items-center space-x-1.5 transition-all"
                  >
                    <Play className="w-3.5 h-3.5 text-indigo-400" />
                    <span>Run in Workspace</span>
                  </button>

                  <button
                    onClick={() => handleDelete(item.id)}
                    disabled={deletingId === item.id}
                    className="p-1.5 rounded-xl bg-slate-800 text-slate-400 hover:text-rose-400 hover:bg-rose-500/10 transition-colors disabled:opacity-50"
                    title="Delete history item"
                  >
                    <Trash2 className="w-4 h-4" />
                  </button>
                </div>
              </div>

              {item.generated_sql && (
                <div className="p-3 rounded-xl bg-slate-950 border border-slate-800/80 font-mono text-xs text-cyan-300 overflow-x-auto">
                  <code>{item.generated_sql}</code>
                </div>
              )}

              {item.insight_summary && (
                <p className="text-xs text-slate-400 italic bg-slate-950/60 p-2.5 rounded-xl border border-slate-800/50">
                  "{item.insight_summary}"
                </p>
              )}

              <div className="flex items-center space-x-4 text-[11px] text-slate-500 pt-1 border-t border-slate-800/60">
                <span className="flex items-center space-x-1">
                  <TableIcon className="w-3.5 h-3.5 text-slate-400" />
                  <span>{item.row_count} rows</span>
                </span>
                {item.chart_type !== 'none' && (
                  <span className="flex items-center space-x-1 text-indigo-400 uppercase font-semibold">
                    <BarChart2 className="w-3.5 h-3.5" />
                    <span>{item.chart_type} chart</span>
                  </span>
                )}
                <span className="flex items-center space-x-1">
                  <Clock className="w-3.5 h-3.5" />
                  <span>{new Date(item.created_at).toLocaleString()}</span>
                </span>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  );
};
