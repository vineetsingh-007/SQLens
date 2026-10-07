import React, { useState } from 'react';
import {
  Table,
  Search,
  Zap,
  Info,
  ChevronLeft,
  ChevronRight,
  Database
} from 'lucide-react';
import { QueryResultColumn } from '../../types/ai';
import { ExportControl } from './ExportControl';

interface ResultTableProps {
  columns: QueryResultColumn[];
  rows: Array<Record<string, any>>;
  rowCount: number;
  truncated?: boolean;
  executionTimeMs?: number;
  question?: string;
  insight?: string;
  chartId?: string;
  hasChart?: boolean;
}

export const ResultTable: React.FC<ResultTableProps> = ({
  columns,
  rows,
  rowCount,
  truncated,
  executionTimeMs,
  question,
  insight,
  chartId,
  hasChart = false
}) => {
  const [searchTerm, setSearchTerm] = useState('');
  const [page, setPage] = useState(1);
  const pageSize = 15;

  if (!rows || rows.length === 0) {
    return (
      <div className="p-8 rounded-2xl bg-slate-900/80 border border-slate-800 text-center space-y-2">
        <Database className="w-8 h-8 text-slate-500 mx-auto" />
        <h4 className="text-sm font-bold text-slate-300">No Results Found</h4>
        <p className="text-xs text-slate-400">
          The query was valid and executed successfully, but no records matched the conditions.
        </p>
      </div>
    );
  }

  // Filter rows by search term
  const filteredRows = rows.filter((row) =>
    Object.values(row).some((val) =>
      val !== null && val !== undefined && String(val).toLowerCase().includes(searchTerm.toLowerCase())
    )
  );

  const totalPages = Math.ceil(filteredRows.length / pageSize) || 1;
  const paginatedRows = filteredRows.slice((page - 1) * pageSize, page * pageSize);

  const formatCellValue = (val: any, type: string) => {
    if (val === null || val === undefined) {
      return <span className="text-slate-500 italic">null</span>;
    }
    if (type === 'numeric' || typeof val === 'number') {
      return <span className="font-mono text-slate-900 dark:text-[#F2F2F2]">{val.toLocaleString()}</span>;
    }
    if (type === 'boolean' || typeof val === 'boolean') {
      return (
        <span className={`px-2 py-0.5 rounded text-[10px] font-bold ${val ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/30' : 'bg-rose-500/10 text-rose-400 border border-rose-500/30'}`}>
          {val ? 'TRUE' : 'FALSE'}
        </span>
      );
    }
    return String(val);
  };

  return (
    <div className="p-6 rounded-2xl bg-slate-900/90 dark:bg-[#333333] border border-slate-800 dark:border-[#484848] shadow-xl space-y-4">
      {/* Table Header Controls */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 pb-2 border-b border-slate-800/80 dark:border-[#484848]">
        <div className="flex items-center space-x-2">
          <Table className="w-5 h-5 text-brand-600 dark:text-[#8AB4F8]" />
          <h3 className="text-base font-bold text-slate-100 dark:text-[#F2F2F2]">Query Result Table</h3>
          <span className="px-2.5 py-0.5 rounded-full text-xs font-mono bg-slate-800 dark:bg-[#383838] text-slate-300 dark:text-[#C7C7C7] border border-slate-700 dark:border-[#484848]">
            {rowCount} {rowCount === 1 ? 'row' : 'rows'}
          </span>
        </div>

        <div className="flex items-center space-x-3">
          {/* Quick Filter Input */}
          <div className="relative">
            <input
              type="text"
              value={searchTerm}
              onChange={(e) => {
                setSearchTerm(e.target.value);
                setPage(1);
              }}
              placeholder="Search results..."
              className="bg-slate-950 dark:bg-[#262626] border border-slate-800 dark:border-[#484848] rounded-xl pl-8 pr-3 py-1.5 text-xs text-slate-200 dark:text-[#F2F2F2] placeholder-slate-500 dark:placeholder-[#858585] focus:outline-none focus:ring-1 focus:ring-brand-500 dark:focus:ring-[#8AB4F8]"
            />
            <Search className="w-3.5 h-3.5 text-slate-500 dark:text-[#858585] absolute left-2.5 top-1/2 -translate-y-1/2" />
          </div>

          {/* Execution Time */}
          {executionTimeMs !== undefined && (
            <span className="text-[11px] font-mono text-slate-400 flex items-center space-x-1 shrink-0">
              <Zap className="w-3.5 h-3.5 text-amber-400" />
              <span>{executionTimeMs} ms</span>
            </span>
          )}

          {/* Result Export & Copy Controls */}
          <ExportControl
            columns={columns.map((c) => c.name)}
            rows={rows}
            question={question}
            insight={insight}
            truncated={truncated}
            chartId={chartId}
            hasChart={hasChart}
          />
        </div>
      </div>

      {/* Truncation Warning Banner */}
      {truncated && (
        <div className="p-3 rounded-xl bg-amber-500/10 border border-amber-500/30 text-amber-200 text-xs flex items-center space-x-2">
          <Info className="w-4 h-4 text-amber-400 shrink-0" />
          <span>Results truncated: Displaying the first 1,000 rows.</span>
        </div>
      )}

      {/* Responsive Table Grid */}
      <div className="overflow-x-auto rounded-xl border border-slate-800 bg-slate-950">
        <table className="w-full text-left text-xs md:text-sm">
          <thead className="bg-slate-900/90 text-slate-400 uppercase tracking-wider font-semibold border-b border-slate-800">
            <tr>
              {columns.map((col) => (
                <th key={col.name} className="px-4.5 py-3.5 font-mono">
                  <div className="flex items-center space-x-1.5">
                    <span>{col.name}</span>
                    <span className="text-[10px] px-1.5 py-0.5 rounded bg-slate-800 text-slate-400 font-sans font-normal lowercase">
                      {col.type}
                    </span>
                  </div>
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-800/60 text-slate-200 font-medium">
            {paginatedRows.map((row, rIdx) => (
              <tr key={rIdx} className="hover:bg-slate-900/50 transition-colors">
                {columns.map((col) => (
                  <td key={col.name} className="px-4.5 py-3.5 whitespace-nowrap">
                    {formatCellValue(row[col.name], col.type)}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {/* Table Pagination Footer */}
      {totalPages > 1 && (
        <div className="flex items-center justify-between pt-2 text-xs text-slate-400">
          <span>
            Showing {(page - 1) * pageSize + 1} - {Math.min(page * pageSize, filteredRows.length)} of {filteredRows.length} rows
          </span>
          <div className="flex items-center space-x-2">
            <button
              onClick={() => setPage((p) => Math.max(1, p - 1))}
              disabled={page === 1}
              className="p-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 disabled:opacity-40 text-slate-200 cursor-pointer"
            >
              <ChevronLeft className="w-4 h-4" />
            </button>
            <span className="font-mono text-slate-300">
              Page {page} of {totalPages}
            </span>
            <button
              onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
              disabled={page === totalPages}
              className="p-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 disabled:opacity-40 text-slate-200 cursor-pointer"
            >
              <ChevronRight className="w-4 h-4" />
            </button>
          </div>
        </div>
      )}
    </div>
  );
};
