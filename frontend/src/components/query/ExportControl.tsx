import React, { useState, useRef, useEffect } from 'react';
import {
  Copy,
  Download,
  ChevronDown,
  Check,
  FileSpreadsheet,
  FileText,
  FileCode,
  File,
  Loader2,
  AlertCircle
} from 'lucide-react';
import {
  copyResultsToClipboard,
  exportCSV,
  exportExcel,
  exportDocx,
  exportPDF,
  captureChartImage,
  ExportRequestPayload
} from '../../services/exportService';

interface ExportControlProps {
  columns: string[];
  rows: Array<Record<string, any>>;
  question?: string;
  insight?: string;
  truncated?: boolean;
  chartId?: string;
  hasChart?: boolean;
}

type ExportFormat = 'pdf' | 'docx' | 'excel' | 'csv';

export const ExportControl: React.FC<ExportControlProps> = ({
  columns,
  rows,
  question,
  insight,
  truncated,
  chartId,
  hasChart = false
}) => {
  const [isOpen, setIsOpen] = useState(false);
  const [copied, setCopied] = useState(false);
  const [isExporting, setIsExporting] = useState(false);
  const [selectedFormat, setSelectedFormat] = useState<ExportFormat>('pdf');
  const [includeViz, setIncludeViz] = useState<boolean>(hasChart);
  const [toastMessage, setToastMessage] = useState<{ text: string; type: 'success' | 'error' } | null>(null);

  const menuRef = useRef<HTMLDivElement>(null);

  // Sync includeViz with hasChart status when dropdown opens or hasChart changes
  useEffect(() => {
    if (hasChart && selectedFormat !== 'csv' && selectedFormat !== 'excel') {
      setIncludeViz(true);
    } else {
      setIncludeViz(false);
    }
  }, [hasChart, selectedFormat]);

  // Close dropdown when clicking outside
  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (menuRef.current && !menuRef.current.contains(e.target as Node)) {
        setIsOpen(false);
      }
    };
    document.addEventListener('mousedown', handleClickOutside);
    return () => document.removeEventListener('mousedown', handleClickOutside);
  }, []);

  const showToast = (text: string, type: 'success' | 'error' = 'success') => {
    setToastMessage({ text, type });
    setTimeout(() => {
      setToastMessage((prev) => (prev?.text === text ? null : prev));
    }, 3500);
  };

  const handleCopy = async () => {
    if (!rows || rows.length === 0) {
      showToast('Nothing to copy.', 'error');
      return;
    }

    const res = await copyResultsToClipboard(columns, rows);
    if (res.success) {
      setCopied(true);
      showToast(res.message, 'success');
      setTimeout(() => setCopied(false), 2000);
    } else {
      showToast(res.message, 'error');
    }
  };

  const isVizSupported = selectedFormat === 'pdf' || selectedFormat === 'docx';

  const handleExportSubmit = async () => {
    if (!rows || rows.length === 0) {
      showToast('Nothing to export.', 'error');
      return;
    }

    setIsOpen(false);
    setIsExporting(true);

    try {
      // 1. CSV table-only export
      if (selectedFormat === 'csv') {
        const res = exportCSV(columns, rows, 'results.csv');
        if (res.success) {
          showToast('CSV downloaded successfully.', 'success');
        } else {
          showToast(res.message || 'Failed to generate CSV file.', 'error');
        }
        return;
      }

      // 2. Capture high-resolution static image of rendered UI chart if PDF/Word and visualization requested
      let chartImageBase64: string | undefined = undefined;

      if (isVizSupported && includeViz && hasChart) {
        let chartElem: HTMLElement | null = null;

        // Try locating chart by exact chartId
        if (chartId) {
          chartElem = document.getElementById(`sqlens-chart-${chartId}`);
        }

        // Fallback: search closest turn container
        if (!chartElem && menuRef.current) {
          const parentTurn = menuRef.current.closest('.space-y-4');
          chartElem = parentTurn?.querySelector('[data-sqlens-chart-container]') as HTMLElement | null;
        }

        // Global fallback: any active chart container on screen
        if (!chartElem) {
          chartElem = document.querySelector('[data-sqlens-chart-container]') as HTMLElement | null;
        }

        if (chartElem) {
          const capturedImg = await captureChartImage(chartElem);
          if (capturedImg) {
            chartImageBase64 = capturedImg;
          }
        }
      }

      const payload: ExportRequestPayload = {
        columns,
        rows,
        question,
        insight,
        truncated,
        total_rows: rows.length,
        include_visualization: Boolean(chartImageBase64),
        chart_image_base64: chartImageBase64
      };

      let res: { success: boolean; message?: string };
      if (selectedFormat === 'excel') {
        res = await exportExcel(payload);
      } else if (selectedFormat === 'docx') {
        res = await exportDocx(payload);
      } else {
        res = await exportPDF(payload);
      }

      if (res.success) {
        showToast(`${selectedFormat.toUpperCase()} file downloaded.`, 'success');
      } else {
        showToast(res.message || `Failed to generate ${selectedFormat.toUpperCase()} file.`, 'error');
      }
    } catch (err) {
      console.error('Export error:', err);
      showToast(`Failed to generate ${selectedFormat.toUpperCase()} file.`, 'error');
    } finally {
      setIsExporting(false);
    }
  };

  return (
    <div className="relative inline-flex items-center space-x-2" ref={menuRef}>
      {/* Toast Notification Banner */}
      {toastMessage && (
        <div
          className={`absolute right-0 -top-11 z-50 px-3 py-1.5 rounded-xl text-xs font-medium flex items-center space-x-1.5 shadow-2xl transition-all duration-200 animate-in fade-in slide-in-from-bottom-2 ${
            toastMessage.type === 'error'
              ? 'bg-rose-900/90 text-rose-200 border border-rose-700'
              : 'bg-emerald-900/90 text-emerald-200 border border-emerald-700'
          }`}
        >
          {toastMessage.type === 'error' ? (
            <AlertCircle className="w-3.5 h-3.5 text-rose-400 shrink-0" />
          ) : (
            <Check className="w-3.5 h-3.5 text-emerald-400 shrink-0" />
          )}
          <span>{toastMessage.text}</span>
        </div>
      )}

      {/* Copy Button */}
      <button
        type="button"
        onClick={handleCopy}
        className="px-3 py-1.5 rounded-xl bg-slate-800 dark:bg-[#383838] hover:bg-slate-700 dark:hover:bg-[#414141] text-slate-200 dark:text-[#F2F2F2] border border-slate-700 dark:border-[#4D4D4D] text-xs font-medium flex items-center space-x-1.5 transition-all cursor-pointer active:scale-95"
        title="Copy result table as TSV to clipboard"
      >
        {copied ? (
          <>
            <Check className="w-3.5 h-3.5 text-emerald-400 dark:text-[#55D6A6]" />
            <span className="text-emerald-400 dark:text-[#55D6A6]">Copied</span>
          </>
        ) : (
          <>
            <Copy className="w-3.5 h-3.5 text-brand-600 dark:text-[#8AB4F8]" />
            <span>Copy</span>
          </>
        )}
      </button>

      {/* Export Dropdown Trigger */}
      <div className="relative">
        <button
          type="button"
          onClick={() => setIsOpen((prev) => !prev)}
          disabled={isExporting}
          className="px-3 py-1.5 rounded-xl bg-slate-800 dark:bg-[#383838] hover:bg-slate-700 dark:hover:bg-[#414141] text-slate-200 dark:text-[#F2F2F2] border border-slate-700 dark:border-[#4D4D4D] text-xs font-medium flex items-center space-x-1.5 transition-all cursor-pointer disabled:opacity-50 active:scale-95"
          title="Export query results"
        >
          {isExporting ? (
            <Loader2 className="w-3.5 h-3.5 animate-spin text-brand-600 dark:text-[#8AB4F8]" />
          ) : (
            <Download className="w-3.5 h-3.5 text-brand-600 dark:text-[#8AB4F8]" />
          )}
          <span>{isExporting ? 'Exporting...' : 'Export'}</span>
          <ChevronDown className={`w-3.5 h-3.5 transition-transform duration-200 ${isOpen ? 'rotate-180' : ''}`} />
        </button>

        {/* Export Options Modal / Popover Menu */}
        {isOpen && (
          <div className="absolute right-0 mt-2 w-64 rounded-2xl bg-slate-900 dark:bg-[#202020] border border-slate-800 dark:border-[#484848] shadow-2xl z-50 overflow-hidden text-slate-200 dark:text-[#F2F2F2] animate-in fade-in zoom-in-95 duration-100">
            {/* Header */}
            <div className="px-3.5 py-2.5 font-bold text-xs text-slate-200 dark:text-[#F2F2F2] border-b border-slate-800 dark:border-[#484848]">
              Export Results
            </div>

            {/* Checkbox for Visualization */}
            <div className="p-3.5 border-b border-slate-800 dark:border-[#484848] space-y-1.5">
              <label
                className={`flex items-center space-x-2.5 text-xs font-medium ${
                  !isVizSupported || !hasChart
                    ? 'opacity-50 cursor-not-allowed text-slate-500 dark:text-[#707070]'
                    : 'cursor-pointer text-slate-200 dark:text-[#F2F2F2]'
                }`}
              >
                <input
                  type="checkbox"
                  checked={includeViz && isVizSupported && hasChart}
                  onChange={(e) => {
                    if (!isVizSupported || !hasChart) return;
                    setIncludeViz(e.target.checked);
                  }}
                  disabled={!isVizSupported || !hasChart}
                  className="w-4 h-4 rounded border-slate-700 bg-slate-800 text-brand-600 focus:ring-brand-500 cursor-pointer accent-[#8AB4F8]"
                />
                <span>Include visualization</span>
              </label>

              {!isVizSupported ? (
                <p className="text-[11px] text-amber-400 dark:text-[#F6AD55] leading-snug pl-6 font-normal">
                  Visualization is available only for PDF and Word exports.
                </p>
              ) : !hasChart ? (
                <p className="text-[11px] text-slate-400 dark:text-[#9A9A9A] leading-snug pl-6 font-normal">
                  No visualization available for this result.
                </p>
              ) : null}
            </div>

            {/* Format Selection Dropdown */}
            <div className="p-3.5 space-y-2 border-b border-slate-800 dark:border-[#484848]">
              <label className="block text-[11px] uppercase font-semibold text-slate-400 dark:text-[#9A9A9A] tracking-wider">
                Format:
              </label>
              <select
                value={selectedFormat}
                onChange={(e) => {
                  const fmt = e.target.value as ExportFormat;
                  setSelectedFormat(fmt);
                  if (fmt === 'csv' || fmt === 'excel') {
                    setIncludeViz(false);
                  } else if (hasChart) {
                    setIncludeViz(true);
                  }
                }}
                className="w-full bg-slate-950 dark:bg-[#262626] border border-slate-800 dark:border-[#4D4D4D] text-slate-200 dark:text-[#F2F2F2] rounded-xl px-3 py-2 text-xs focus:outline-none focus:ring-1 focus:ring-[#8AB4F8]"
              >
                <option value="pdf">PDF</option>
                <option value="docx">Word (.docx)</option>
                <option value="excel">Excel (.xlsx)</option>
                <option value="csv">CSV</option>
              </select>
            </div>

            {/* Submit Export Button */}
            <div className="p-3">
              <button
                type="button"
                onClick={handleExportSubmit}
                disabled={isExporting}
                className="w-full py-2 px-3 rounded-xl bg-brand-600 dark:bg-[#8AB4F8] hover:bg-brand-700 dark:hover:bg-[#76A0E4] text-white dark:text-[#1F1F1F] font-bold text-xs transition-all flex items-center justify-center space-x-1.5 cursor-pointer disabled:opacity-50 active:scale-95"
              >
                {isExporting ? (
                  <>
                    <Loader2 className="w-3.5 h-3.5 animate-spin" />
                    <span>Exporting...</span>
                  </>
                ) : (
                  <>
                    <Download className="w-3.5 h-3.5" />
                    <span>Export</span>
                  </>
                )}
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
};
