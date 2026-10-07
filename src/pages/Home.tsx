import React, { useEffect, useState } from 'react';
import { UploadZone } from '../components/common/UploadZone';
import { DatasetCard } from '../components/dataset/DatasetCard';
import { DeleteConfirmModal } from '../components/common/DeleteConfirmModal';
import { Dataset } from '../types/dataset';
import { datasetService } from '../services/api';
import { Sparkles, Database, ArrowRight, Loader2 } from 'lucide-react';
import { useNavigate } from 'react-router-dom';

export const Home: React.FC = () => {
  const navigate = useNavigate();
  const [datasets, setDatasets] = useState<Dataset[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
  const [loadingSample, setLoadingSample] = useState<boolean>(false);
  const [deleteTarget, setDeleteTarget] = useState<Dataset | null>(null);
  const [isDeleting, setIsDeleting] = useState<boolean>(false);

  const fetchDatasets = async () => {
    try {
      const data = await datasetService.getDatasets();
      setDatasets(data);
    } catch (err) {
      console.error('Failed to fetch datasets:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchDatasets();
  }, []);

  const handleTrySampleData = async () => {
    setLoadingSample(true);
    try {
      const res = await datasetService.loadSampleDataset();
      navigate(`/datasets/${res.dataset_id}`);
    } catch (err) {
      console.error('Failed to load sample dataset:', err);
    } finally {
      setLoadingSample(false);
    }
  };

  const handleDeleteConfirm = async () => {
    if (!deleteTarget) return;
    const targetId = deleteTarget.id;
    setIsDeleting(true);
    try {
      await datasetService.deleteDataset(targetId);
      setDatasets((prev) => prev.filter((d) => d.id !== targetId));
      setDeleteTarget(null);
      await fetchDatasets();
    } catch (err: any) {
      console.error('Failed to delete dataset:', err);
      alert(err.response?.data?.detail || 'Failed to delete dataset.');
    } finally {
      setIsDeleting(false);
    }
  };

  return (
    <div className="space-y-5 pb-6">
      {/* Hero Header Banner */}
      <div className="text-center space-y-3 max-w-4xl mx-auto pt-1">
        <div className="inline-flex items-center space-x-2 px-3.5 py-1 rounded-full bg-brand-500/10 border border-brand-500/20 text-brand-400 text-xs font-semibold">
          <Sparkles className="h-4 w-4 text-brand-400" />
          <span>Conversational Database Intelligence System</span>
        </div>

        <h1 className="text-3xl md:text-[2.5rem] font-extrabold tracking-tight font-sans leading-tight">
          <span className="fluid-hero-tagline inline-block pb-0.5">
            Ask Your Data. Get Answers. No SQL Required.
          </span>
        </h1>

        <p className="text-xs md:text-sm lg:text-base text-slate-400 max-w-3xl mx-auto leading-relaxed">
          Upload your CSV, Excel, or SQLite data and prepare it for natural-language analysis. Fast, secure, and dataset-isolated.
        </p>

        <div className="pt-1 flex items-center justify-center space-x-4">
          <button
            onClick={handleTrySampleData}
            disabled={loadingSample}
            className="inline-flex items-center space-x-2 px-4.5 py-2.5 rounded-xl bg-slate-900 hover:bg-slate-800 text-slate-200 border border-slate-800 font-semibold text-xs md:text-sm transition-all shadow-md shadow-black/20"
          >
            {loadingSample ? (
              <Loader2 className="h-4 w-4 animate-spin text-brand-400" />
            ) : (
              <Database className="h-4 w-4 text-brand-400" />
            )}
            <span>Try Sample Dataset</span>
          </button>
        </div>
      </div>

      {/* Main Upload Zone Section */}
      <section className="bg-slate-900/40 border border-slate-800/80 rounded-2xl p-4 md:p-5 space-y-3 shadow-xl">
        <div className="flex items-center justify-between">
          <div>
            <h2 className="text-base md:text-lg font-bold text-white">Upload Your Data</h2>
            <p className="text-xs text-slate-400">Supported formats: CSV, Excel (.xlsx, .xls), SQLite (.db, .sqlite)</p>
          </div>
        </div>

        <UploadZone />
      </section>

      {/* Recent Datasets Section */}
      <section className="space-y-3">
        <div className="flex items-center justify-between">
          <h2 className="text-base md:text-lg font-bold text-white flex items-center space-x-2">
            <Database className="h-4.5 w-4.5 text-brand-400" />
            <span>Recent Datasets</span>
          </h2>

          {datasets.length > 0 && (
            <button
              onClick={() => navigate('/datasets')}
              className="text-xs md:text-sm font-semibold text-brand-400 hover:text-brand-300 flex items-center space-x-1"
            >
              <span>View all datasets ({datasets.length})</span>
              <ArrowRight className="h-4 w-4" />
            </button>
          )}
        </div>

        {loading ? (
          <div className="py-12 text-center text-sm text-slate-400 space-y-2">
            <Loader2 className="h-6 w-6 text-brand-400 animate-spin mx-auto" />
            <p>Loading datasets...</p>
          </div>
        ) : datasets.length === 0 ? (
          <div className="p-8 text-center rounded-2xl bg-slate-900/40 border border-slate-800 space-y-3">
            <Database className="h-10 w-10 text-slate-600 mx-auto" />
            <div className="space-y-1">
              <h3 className="text-sm font-semibold text-slate-200">No datasets yet</h3>
              <p className="text-xs text-slate-400">Upload a CSV, Excel, or SQLite file to start exploring your data.</p>
            </div>
          </div>
        ) : (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-5">
            {datasets.slice(0, 3).map((ds) => (
              <DatasetCard key={ds.id} dataset={ds} onDeleteClick={(d) => setDeleteTarget(d)} />
            ))}
          </div>
        )}
      </section>

      {/* Delete Confirmation Modal */}
      <DeleteConfirmModal
        isOpen={Boolean(deleteTarget)}
        datasetName={deleteTarget?.original_filename || ''}
        isDeleting={isDeleting}
        onConfirm={handleDeleteConfirm}
        onCancel={() => setDeleteTarget(null)}
      />
    </div>
  );
};
