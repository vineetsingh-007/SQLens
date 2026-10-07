import React, { useState } from 'react';
import { DatasetTable } from '../../types/dataset';
import { Search, Key, Link2, Table as TableIcon } from 'lucide-react';

interface SchemaViewerProps {
  tables: DatasetTable[];
}

export const SchemaViewer: React.FC<SchemaViewerProps> = ({ tables }) => {
  const [tableSearch, setTableSearch] = useState<string>('');
  const [columnSearch, setColumnSearch] = useState<string>('');

  const filteredTables = tables.filter((table) => {
    const matchesTableName =
      table.table_name.toLowerCase().includes(tableSearch.toLowerCase()) ||
      table.display_name.toLowerCase().includes(tableSearch.toLowerCase());

    if (!columnSearch.trim()) {
      return matchesTableName;
    }

    const matchesColumn = table.columns_json.some(
      (col) =>
        col.name.toLowerCase().includes(columnSearch.toLowerCase()) ||
        col.display_name.toLowerCase().includes(columnSearch.toLowerCase())
    );

    return matchesTableName || matchesColumn;
  });

  return (
    <div className="space-y-6">
      {/* Search Filters Bar */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        <div className="relative">
          <Search className="h-4 w-4 text-slate-500 absolute left-3.5 top-3" />
          <input
            type="text"
            placeholder="Search tables..."
            value={tableSearch}
            onChange={(e) => setTableSearch(e.target.value)}
            className="w-full bg-slate-900 border border-slate-800 rounded-xl pl-10 pr-4 py-2 text-xs text-slate-200 placeholder-slate-500 focus:outline-none focus:border-brand-500"
          />
        </div>

        <div className="relative">
          <Search className="h-4 w-4 text-slate-500 absolute left-3.5 top-3" />
          <input
            type="text"
            placeholder="Search columns..."
            value={columnSearch}
            onChange={(e) => setColumnSearch(e.target.value)}
            className="w-full bg-slate-900 border border-slate-800 rounded-xl pl-10 pr-4 py-2 text-xs text-slate-200 placeholder-slate-500 focus:outline-none focus:border-brand-500"
          />
        </div>
      </div>

      {/* Table Tree View */}
      {filteredTables.length === 0 ? (
        <div className="py-12 text-center text-sm text-slate-400 bg-slate-900/40 rounded-2xl border border-slate-800 space-y-2">
          <TableIcon className="h-8 w-8 text-slate-600 mx-auto" />
          <p className="text-slate-300 font-semibold">No matching tables or columns found</p>
          <p className="text-xs text-slate-500">Try adjusting your search filters.</p>
        </div>
      ) : (
        filteredTables.map((table) => {
          const displayCols = columnSearch.trim()
            ? table.columns_json.filter(
                (col) =>
                  col.name.toLowerCase().includes(columnSearch.toLowerCase()) ||
                  col.display_name.toLowerCase().includes(columnSearch.toLowerCase())
              )
            : table.columns_json;

          return (
            <div key={table.id} className="bg-slate-900/60 border border-slate-800 rounded-2xl p-5 space-y-4">
              <div className="flex items-center justify-between">
                <div>
                  <h4 className="font-bold text-slate-100 text-sm tracking-wide font-mono flex items-center space-x-2">
                    <TableIcon className="h-4 w-4 text-brand-400" />
                    <span>{table.table_name}</span>
                  </h4>
                  <p className="text-xs text-slate-400 mt-0.5">
                    Display: {table.display_name} • {table.row_count.toLocaleString()} rows •{' '}
                    {table.column_count} columns
                  </p>
                </div>
              </div>

              {/* Columns Table */}
              <div className="overflow-x-auto rounded-xl border border-slate-800/80 bg-slate-950/60">
                <table className="w-full text-left text-xs font-mono">
                  <thead>
                    <tr className="bg-slate-900/80 border-b border-slate-800 text-slate-400">
                      <th className="py-2.5 px-4 font-semibold">Column Name</th>
                      <th className="py-2.5 px-4 font-semibold">Type</th>
                      <th className="py-2.5 px-4 font-semibold">Nullable</th>
                      <th className="py-2.5 px-4 font-semibold">Key Constraints</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-800/40">
                    {displayCols.map((col, idx) => (
                      <tr key={idx} className="hover:bg-slate-900/40">
                        <td className="py-2.5 px-4 text-brand-300 font-bold flex items-center space-x-2">
                          <span>{col.name}</span>
                          {col.display_name !== col.name && (
                            <span className="text-[10px] text-slate-500 font-sans font-normal">
                              ({col.display_name})
                            </span>
                          )}
                        </td>
                        <td className="py-2.5 px-4 text-amber-400 font-semibold">{col.type}</td>
                        <td className="py-2.5 px-4 text-slate-400">
                          {col.nullable === false ? (
                            <span className="text-slate-300 font-semibold">NOT NULL</span>
                          ) : (
                            <span className="text-slate-500">NULLABLE</span>
                          )}
                        </td>
                        <td className="py-2.5 px-4">
                          <div className="flex items-center space-x-2">
                            {col.is_primary_key && (
                              <span className="inline-flex items-center space-x-1 px-2 py-0.5 rounded text-[10px] font-bold bg-amber-500/10 text-amber-400 border border-amber-500/20">
                                <Key className="h-3 w-3" />
                                <span>PK</span>
                              </span>
                            )}
                            {col.is_foreign_key && (
                              <span className="inline-flex items-center space-x-1 px-2 py-0.5 rounded text-[10px] font-bold bg-sky-500/10 text-sky-400 border border-sky-500/20">
                                <Link2 className="h-3 w-3" />
                                <span>
                                  FK ➔ {col.referenced_table}.{col.referenced_column}
                                </span>
                              </span>
                            )}
                            {!col.is_primary_key && !col.is_foreign_key && (
                              <span className="text-slate-600">—</span>
                            )}
                          </div>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          );
        })
      )}
    </div>
  );
};
