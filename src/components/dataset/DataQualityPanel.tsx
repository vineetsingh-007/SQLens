import React, { useEffect, useState } from 'react';
import { TableStatistics } from '../../types/dataset';
import { datasetService } from '../../services/api';
import { Loader2, AlertCircle, Hash, Table, CheckCircle, HelpCircle } from 'lucide-react';

interface DataQualityPanelProps {
  datasetId: string;
  tableName: string;
}

export const DataQualityPanel: React.FC<DataQualityPanelProps> = ({ datasetId, tableName }) => {
  const [stats, setStats] = useState<TableStatistics | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    let isMounted = true;
    setLoading(true);
    setError(null);

    datasetService
      .getTableStatistics(datasetId, tableName)
      .then((data) => {
        if (isMounted) {
          setStats(data);
          setLoading(false);
        }
      })
      .catch((err) => {
        if (isMounted) {
          setError(err.response?.data?.detail || 'Failed to calculate table statistics.');
          setLoading(false);
        }
      });

    return () => {
      isMounted = false;
    };
  }, [datasetId, tableName]);

  if (loading) {
    return (
      <div className="py-16 text-center space-y-3 bg-slate-900/40 rounded-2xl border border-slate-800">
        <Loader2 className="h-8 w-8 text-brand-400 animate-spin mx-auto" />
        <p className="text-sm text-slate-400">Calculating data quality &amp; statistics...</p>
      </div>
    );
  }

  if (error || !stats) {
    return (
      <div className="p-4 rounded-xl bg-rose-500/10 border border-rose-500/20 text-rose-300 text-sm">
        {error || 'Unable to load statistics for this table.'}
      </div>
    );
  }

  return (
    <div className="space-y-6">
      {/* Summary Cards */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <div className="bg-slate-900/60 p-4 rounded-2xl border border-slate-800 text-center space-y-1">
          <div className="text-xs text-slate-400 flex items-center justify-center space-x-1.5">
            <Table className="h-4 w-4 text-emerald-400" />
            <span>Total Rows</span>
          </div>
          <div className="text-2xl font-bold text-white">{stats.total_rows.toLocaleString()}</div>
        </div>

        <div className="bg-slate-900/60 p-4 rounded-2xl border border-slate-800 text-center space-y-1">
          <div className="text-xs text-slate-400 flex items-center justify-center space-x-1.5">
            <Hash className="h-4 w-4 text-sky-400" />
            <span>Total Columns</span>
          </div>
          <div className="text-2xl font-bold text-white">{stats.total_columns}</div>
        </div>

        <div className="bg-slate-900/60 p-4 rounded-2xl border border-slate-800 text-center space-y-1">
          <div className="text-xs text-slate-400 flex items-center justify-center space-x-1.5">
            {stats.total_missing_values > 0 ? (
              <AlertCircle className="h-4 w-4 text-amber-400" />
            ) : (
              <CheckCircle className="h-4 w-4 text-emerald-400" />
            )}
            <span>Missing / Null Values</span>
          </div>
          <div
            className={`text-2xl font-bold ${
              stats.total_missing_values > 0 ? 'text-amber-400' : 'text-emerald-400'
            }`}
          >
            {stats.total_missing_values.toLocaleString()}
          </div>
        </div>
      </div>

      {/* Column Statistics Breakdown */}
      <div className="bg-slate-900/60 border border-slate-800 rounded-2xl p-5 space-y-4">
        <h3 className="text-sm font-bold text-slate-200">Column Data Analysis</h3>

        <div className="overflow-x-auto rounded-xl border border-slate-800 bg-slate-950/60">
          <table className="w-full text-left text-xs font-mono">
            <thead>
              <tr className="bg-slate-900 border-b border-slate-800 text-slate-400">
                <th className="py-3 px-4 font-semibold">Column</th>
                <th className="py-3 px-4 font-semibold">Type</th>
                <th className="py-3 px-4 font-semibold">Nulls</th>
                <th className="py-3 px-4 font-semibold">Distinct / Range / Summary</th>
                <th className="py-3 px-4 font-semibold">Sample Values</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-800/40">
              {stats.columns_stats.map((col, idx) => (
                <tr key={idx} className="hover:bg-slate-900/40">
                  <td className="py-3 px-4 text-slate-200 font-bold">{col.display_name || col.column_name}</td>
                  <td className="py-3 px-4 text-sky-400">{col.data_type}</td>
                  <td className="py-3 px-4">
                    {col.null_count > 0 ? (
                      <span className="text-amber-400 font-semibold">{col.null_count} missing</span>
                    ) : (
                      <span className="text-emerald-400 font-normal">0 missing</span>
                    )}
                  </td>
                  <td className="py-3 px-4 text-slate-300">
                    {col.data_type === 'Integer' || col.data_type === 'Decimal' ? (
                      <div>
                        Min: <span className="text-white">{col.min_value ?? 'N/A'}</span> • Max:{' '}
                        <span className="text-white">{col.max_value ?? 'N/A'}</span> • Avg:{' '}
                        <span className="text-white">{col.avg_value ?? 'N/A'}</span>
                      </div>
                    ) : col.data_type === 'Date' || col.data_type === 'DateTime' ? (
                      <div>
                        Earliest: <span className="text-white">{col.min_value ?? 'N/A'}</span> • Latest:{' '}
                        <span className="text-white">{col.max_value ?? 'N/A'}</span>
                      </div>
                    ) : col.data_type === 'Boolean' ? (
                      <div>
                        True: <span className="text-emerald-400">{col.true_count ?? 0}</span> • False:{' '}
                        <span className="text-rose-400">{col.false_count ?? 0}</span>
                      </div>
                    ) : (
                      <div>
                        Distinct values: <span className="text-white">{col.distinct_count ?? 'N/A'}</span>
                      </div>
                    )}
                  </td>
                  <td className="py-3 px-4 text-slate-400 max-w-xs truncate">
                    {col.sample_values && col.sample_values.length > 0
                      ? col.sample_values.join(', ')
                      : 'N/A'}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};
