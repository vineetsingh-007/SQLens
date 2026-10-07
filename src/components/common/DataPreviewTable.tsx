import React, { useEffect, useState } from 'react';
import { ColumnInfo } from '../../types/dataset';
import { datasetService } from '../../services/api';
import { Loader2, ChevronLeft, ChevronRight, Table as TableIcon } from 'lucide-react';

interface DataPreviewTableProps {
  datasetId: string;
  tableName: string;
}

export const DataPreviewTable: React.FC<DataPreviewTableProps> = ({ datasetId, tableName }) => {
  const [loading, setLoading] = useState<boolean>(true);
  const [error, setError] = useState<string | null>(null);
  const [columns, setColumns] = useState<ColumnInfo[]>([]);
  const [rows, setRows] = useState<Record<string, any>[]>([]);
  const [totalRows, setTotalRows] = useState<number>(0);
  const [totalPages, setTotalPages] = useState<number>(1);
  const [page, setPage] = useState<number>(1);
  const [pageSize, setPageSize] = useState<number>(20);

  useEffect(() => {
    let isMounted = true;
    setLoading(true);
    setError(null);

    datasetService
      .getTablePreview(datasetId, tableName, page, pageSize)
      .then((data) => {
        if (isMounted) {
          setColumns(data.columns);
          setRows(data.rows);
          setTotalRows(data.total_rows);
          setTotalPages(data.total_pages);
          setLoading(false);
        }
      })
      .catch((err) => {
        if (isMounted) {
          setError(err.response?.data?.detail || 'Failed to load preview rows.');
          setLoading(false);
        }
      });

    return () => {
      isMounted = false;
    };
  }, [datasetId, tableName, page, pageSize]);

  if (loading) {
    return (
      <div className="py-16 text-center space-y-3 bg-slate-900/40 rounded-2xl border border-slate-800">
        <Loader2 className="h-8 w-8 text-brand-400 animate-spin mx-auto" />
        <p className="text-sm text-slate-400">Loading table data preview...</p>
      </div>
    );
  }

  if (error) {
    return (
      <div className="p-4 rounded-xl bg-rose-500/10 border border-rose-500/20 text-rose-300 text-sm">
        {error}
      </div>
    );
  }

  if (rows.length === 0) {
    return (
      <div className="py-12 text-center space-y-2 bg-slate-900/40 rounded-2xl border border-slate-800">
        <TableIcon className="h-8 w-8 text-slate-600 mx-auto" />
        <p className="text-sm font-semibold text-slate-300">Table is empty</p>
        <p className="text-xs text-slate-500">No rows exist in this table.</p>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {/* Table Header Control Bar */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 text-xs text-slate-400">
        <div>
          Showing rows <span className="font-bold text-slate-200">{(page - 1) * pageSize + 1}</span> to{' '}
          <span className="font-bold text-slate-200">{Math.min(page * pageSize, totalRows)}</span> of{' '}
          <span className="font-bold text-slate-200">{totalRows.toLocaleString()}</span>
        </div>

        {/* Page Size & Pagination Controls */}
        <div className="flex items-center space-x-4">
          <div className="flex items-center space-x-2">
            <span className="text-slate-400">Rows per page:</span>
            <select
              value={pageSize}
              onChange={(e) => {
                setPageSize(Number(e.target.value));
                setPage(1);
              }}
              className="bg-slate-900 border border-slate-800 text-slate-200 rounded-lg px-2 py-1 text-xs focus:outline-none focus:border-brand-500"
            >
              <option value={20}>20</option>
              <option value={50}>50</option>
              <option value={100}>100</option>
            </select>
          </div>

          <div className="flex items-center space-x-2">
            <button
              onClick={() => setPage((p) => Math.max(1, p - 1))}
              disabled={page === 1}
              className="p-1.5 rounded-lg border border-slate-800 bg-slate-900 text-slate-400 hover:text-white disabled:opacity-40 disabled:cursor-not-allowed text-xs flex items-center space-x-1"
            >
              <ChevronLeft className="h-4 w-4" />
              <span>Prev</span>
            </button>

            <span className="text-xs text-slate-300 font-medium">
              Page {page} of {totalPages}
            </span>

            <button
              onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
              disabled={page >= totalPages}
              className="p-1.5 rounded-lg border border-slate-800 bg-slate-900 text-slate-400 hover:text-white disabled:opacity-40 disabled:cursor-not-allowed text-xs flex items-center space-x-1"
            >
              <span>Next</span>
              <ChevronRight className="h-4 w-4" />
            </button>
          </div>
        </div>
      </div>

      {/* Scrollable Data Table */}
      <div className="overflow-x-auto rounded-2xl border border-slate-800 bg-slate-900/60 shadow-xl">
        <table className="w-full text-left border-collapse text-xs">
          <thead>
            <tr className="bg-slate-900 border-b border-slate-800 sticky top-0 z-10">
              {columns.map((col) => (
                <th key={col.name} className="py-3 px-4 font-semibold text-slate-200 whitespace-nowrap">
                  <div className="flex flex-col space-y-0.5">
                    <span>{col.display_name || col.name}</span>
                    <span className="text-[10px] font-mono uppercase text-sky-400 font-normal">
                      {col.type}
                    </span>
                  </div>
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-800/60">
            {rows.map((row, rowIdx) => (
              <tr key={rowIdx} className="hover:bg-slate-800/40 transition-colors">
                {columns.map((col) => {
                  const val = row[col.name];
                  const isNull = val === null || val === undefined;

                  return (
                    <td key={col.name} className="py-2.5 px-4 font-mono text-slate-300 max-w-xs truncate">
                      {isNull ? (
                        <span className="text-[10px] text-slate-500 font-semibold bg-slate-950 px-1.5 py-0.5 rounded border border-slate-800">
                          NULL
                        </span>
                      ) : typeof val === 'object' ? (
                        JSON.stringify(val)
                      ) : (
                        String(val)
                      )}
                    </td>
                  );
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
};
