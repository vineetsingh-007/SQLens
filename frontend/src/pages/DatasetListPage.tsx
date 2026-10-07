import React, { useEffect, useState } from 'react';
import { DatasetCard } from '../components/dataset/DatasetCard';
import { DeleteConfirmModal } from '../components/common/DeleteConfirmModal';
import { Dataset } from '../types/dataset';
import { datasetService } from '../services/api';
import { Database, Plus, Loader2 } from 'lucide-react';
import { useNavigate } from 'react-router-dom';

export const DatasetListPage: React.FC = () => {
  const navigate = useNavigate();
  const [datasets, setDatasets] = useState<Dataset[]>([]);
  const [loading, setLoading] = useState<boolean>(true);
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
    <div className="space-y-6 pb-12">
      {/* Header */}
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-slate-800">
        <div>
          <h1 className="text-2xl font-bold text-white flex items-center space-x-2.5">
            <Database className="h-6 w-6 text-brand-400" />
            <span>My Datasets</span>
          </h1>
          <p className="text-xs text-slate-400 mt-1">
            Manage your ingested datasets, inspect schemas, and preview database tables.
          </p>
        </div>

        <button
          onClick={() => navigate('/upload')}
          className="inline-flex items-center space-x-2 px-4 py-2.5 rounded-xl bg-brand-600 hover:bg-brand-500 text-white text-sm font-semibold transition-colors shadow-lg shadow-brand-600/20 self-start sm:self-auto"
        >
          <Plus className="h-4 w-4" />
          <span>Upload Dataset</span>
        </button>
      </div>

      {/* Content */}
      {loading ? (
        <div className="py-20 text-center text-slate-400 space-y-3">
          <Loader2 className="h-8 w-8 text-brand-400 animate-spin mx-auto" />
          <p className="text-sm">Loading your datasets...</p>
        </div>
      ) : datasets.length === 0 ? (
        <div className="p-12 text-center rounded-3xl bg-slate-900/40 border border-slate-800 space-y-4 max-w-lg mx-auto my-12">
          <div className="h-16 w-16 rounded-2xl bg-slate-800/80 border border-slate-700 flex items-center justify-center text-slate-500 mx-auto">
            <Database className="h-8 w-8" />
          </div>
          <div className="space-y-1">
            <h2 className="text-lg font-bold text-white">No datasets yet</h2>
            <p className="text-xs text-slate-400 leading-relaxed">
              Upload a CSV, Excel, or SQLite file to start exploring your data.
            </p>
          </div>
          <button
            onClick={() => navigate('/upload')}
            className="inline-flex items-center space-x-2 px-5 py-2.5 rounded-xl bg-brand-600 hover:bg-brand-500 text-white font-semibold text-sm transition-colors shadow-lg shadow-brand-600/20"
          >
            <Plus className="h-4 w-4" />
            <span>Upload Data</span>
          </button>
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
          {datasets.map((ds) => (
            <DatasetCard key={ds.id} dataset={ds} onDeleteClick={(d) => setDeleteTarget(d)} />
          ))}
        </div>
      )}

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
