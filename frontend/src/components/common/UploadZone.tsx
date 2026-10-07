import React, { useState, useRef } from 'react';
import { Upload, FileSpreadsheet, Database as DbIcon, FileCode, CheckCircle2, AlertCircle, Loader2 } from 'lucide-react';
import { useNavigate } from 'react-router-dom';
import { datasetService } from '../../services/api';

const MAX_SIZE_MB = 50;
const ALLOWED_EXTENSIONS = ['.csv', '.xlsx', '.xls', '.sqlite', '.db'];

type IngestionState = 'idle' | 'uploading' | 'validating' | 'processing' | 'ready' | 'error';

export const UploadZone: React.FC = () => {
  const navigate = useNavigate();
  const fileInputRef = useRef<HTMLInputElement>(null);

  const [dragActive, setDragActive] = useState(false);
  const [selectedFile, setSelectedFile] = useState<File | null>(null);
  const [statusState, setStatusState] = useState<IngestionState>('idle');
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [uploadProgress, setUploadProgress] = useState<number>(0);

  const validateFile = (file: File): string | null => {
    const ext = '.' + file.name.split('.').pop()?.toLowerCase();
    if (!ALLOWED_EXTENSIONS.includes(ext)) {
      return `Unsupported file format '${ext}'. Please upload CSV, Excel (.xlsx, .xls), or SQLite (.db, .sqlite).`;
    }
    if (file.size > MAX_SIZE_MB * 1024 * 1024) {
      return `File is too large (${(file.size / (1024 * 1024)).toFixed(1)} MB). Maximum allowed size is ${MAX_SIZE_MB} MB.`;
    }
    return null;
  };

  const handleFile = async (file: File) => {
    const error = validateFile(file);
    if (error) {
      setErrorMessage(error);
      setStatusState('error');
      return;
    }

    setSelectedFile(file);
    setErrorMessage(null);
    setStatusState('uploading');
    setUploadProgress(10);

    try {
      setStatusState('uploading');
      setUploadProgress(40);

      // Trigger backend ingestion
      setStatusState('processing');
      const response = await datasetService.uploadDataset(file, (progressEvent) => {
        if (progressEvent.total) {
          const pct = Math.round((progressEvent.loaded * 100) / progressEvent.total);
          setUploadProgress(pct);
        }
      });

      setStatusState('ready');
      setUploadProgress(100);

      // Redirect after a brief success indicator
      setTimeout(() => {
        navigate(`/datasets/${response.dataset_id}`);
      }, 800);

    } catch (err: any) {
      console.error('Upload error:', err);
      let msg = 'Unable to process this file. Please check that the file is valid.';
      if (err.response) {
        if (typeof err.response.data?.detail === 'string') {
          msg = err.response.data.detail;
        } else if (Array.isArray(err.response.data?.detail)) {
          msg = err.response.data.detail.map((d: any) => d.msg || JSON.stringify(d)).join(', ');
        } else if (err.response.data?.message) {
          msg = err.response.data.message;
        }
      } else if (err.message) {
        msg = `Network Error (${err.message}). Please ensure the SQLens backend server is running on http://localhost:8000.`;
      }
      setErrorMessage(msg);
      setStatusState('error');
    }
  };

  const handleDrag = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    if (e.type === 'dragenter' || e.type === 'dragover') {
      setDragActive(true);
    } else if (e.type === 'dragleave') {
      setDragActive(false);
    }
  };

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault();
    e.stopPropagation();
    setDragActive(false);
    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      handleFile(e.dataTransfer.files[0]);
    }
  };

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      handleFile(e.target.files[0]);
    }
  };

  return (
    <div className="w-full space-y-6">
      {/* Drag & Drop Area */}
      <div
        onDragEnter={handleDrag}
        onDragOver={handleDrag}
        onDragLeave={handleDrag}
        onDrop={handleDrop}
        onClick={() => statusState === 'idle' && fileInputRef.current?.click()}
        className={`relative border-2 border-dashed rounded-2xl p-5 md:p-6 text-center transition-all cursor-pointer ${
          dragActive
            ? 'border-brand-500 dark:border-[#8AB4F8] bg-brand-500/10 dark:bg-[rgba(138,180,248,0.12)] scale-[1.01]'
            : 'border-slate-300 dark:border-[#484848] bg-slate-50 dark:bg-[#303030] hover:bg-slate-100 dark:hover:bg-[#383838]'
        }`}
      >
        <input
          ref={fileInputRef}
          type="file"
          accept=".csv, .xlsx, .xls, .sqlite, .db"
          onChange={handleInputChange}
          className="hidden"
          disabled={statusState === 'uploading' || statusState === 'processing'}
        />

        <div className="flex flex-col items-center justify-center space-y-2.5">
          {statusState === 'idle' && (
            <>
              <div className="h-12 w-12 rounded-xl bg-slate-100 dark:bg-[#383838] border border-slate-300 dark:border-[#484848] flex items-center justify-center text-slate-700 dark:text-[#F2F2F2] group-hover:scale-105 transition-transform">
                <Upload className="h-6 w-6 text-brand-600 dark:text-[#8AB4F8]" />
              </div>

              <div className="space-y-0.5">
                <p className="text-base font-bold text-slate-900 dark:text-[#F2F2F2]">
                  Drag &amp; drop your file here
                </p>
                <p className="text-xs md:text-sm text-slate-500 dark:text-[#C7C7C7]">or click to browse from your computer</p>
              </div>

              <button
                type="button"
                className="mt-1 inline-flex items-center px-4.5 py-2.5 rounded-xl bg-brand-600 dark:bg-[#8AB4F8] text-white dark:text-[#1B1B1B] hover:bg-brand-500 dark:hover:bg-[#A8C7FA] font-semibold text-xs md:text-sm transition-colors shadow-md"
              >
                Browse Files
              </button>

              <div className="pt-2.5 border-t border-slate-800/80 w-full max-w-sm flex items-center justify-center space-x-6 text-xs text-slate-400">
                <div className="flex items-center space-x-1.5">
                  <FileCode className="h-4 w-4 text-sky-400" />
                  <span>CSV</span>
                </div>
                <div className="flex items-center space-x-1.5">
                  <FileSpreadsheet className="h-4 w-4 text-emerald-400" />
                  <span>Excel (.xlsx, .xls)</span>
                </div>
                <div className="flex items-center space-x-1.5">
                  <DbIcon className="h-4 w-4 text-indigo-400" />
                  <span>SQLite (.db, .sqlite)</span>
                </div>
              </div>

              <p className="text-xs text-slate-500">Maximum allowed file size: {MAX_SIZE_MB} MB</p>
            </>
          )}

          {(statusState === 'uploading' || statusState === 'processing') && (
            <div className="py-6 space-y-4 w-full max-w-md">
              <Loader2 className="h-10 w-10 text-brand-400 animate-spin mx-auto" />
              <div className="space-y-2 text-center">
                <p className="text-sm font-medium text-slate-200">
                  {statusState === 'uploading' ? 'Uploading file...' : 'Processing dataset...'}
                </p>
                <p className="text-xs text-slate-400">{selectedFile?.name}</p>
              </div>

              {/* Progress bar */}
              <div className="w-full bg-slate-800 h-2 rounded-full overflow-hidden">
                <div
                  className="bg-brand-500 h-full transition-all duration-300 rounded-full"
                  style={{ width: `${uploadProgress}%` }}
                />
              </div>
            </div>
          )}

          {statusState === 'ready' && (
            <div className="py-6 space-y-3 text-center">
              <CheckCircle2 className="h-12 w-12 text-emerald-400 mx-auto" />
              <p className="text-base font-semibold text-emerald-400">✓ Dataset ready!</p>
              <p className="text-xs text-slate-400">Redirecting to dataset overview...</p>
            </div>
          )}
        </div>
      </div>

      {/* Error Message Alert */}
      {statusState === 'error' && errorMessage && (
        <div className="p-4 rounded-xl bg-rose-500/10 border border-rose-500/20 text-rose-300 flex items-start space-x-3 text-sm">
          <AlertCircle className="h-5 w-5 text-rose-400 shrink-0 mt-0.5" />
          <div className="flex-1 space-y-1">
            <p className="font-semibold text-rose-200">Ingestion Error</p>
            <p className="text-xs text-rose-300/90 leading-relaxed">{errorMessage}</p>
          </div>
          <button
            onClick={() => { setStatusState('idle'); setErrorMessage(null); }}
            className="text-xs text-rose-400 hover:text-rose-200 font-medium underline"
          >
            Try Again
          </button>
        </div>
      )}
    </div>
  );
};
