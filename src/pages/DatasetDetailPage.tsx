import React, { useEffect, useState } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { DatasetSchemaResponse } from '../types/dataset';
import { datasetService } from '../services/api';
import { DataPreviewTable } from '../components/common/DataPreviewTable';
import { SchemaViewer } from '../components/dataset/SchemaViewer';
import { RelationshipViewer } from '../components/dataset/RelationshipViewer';
import { DataQualityPanel } from '../components/dataset/DataQualityPanel';
import { DeleteConfirmModal } from '../components/common/DeleteConfirmModal';
import { QueryWorkspace } from '../components/ai/QueryWorkspace';
import {
  FileCode,
  FileSpreadsheet,
  Database,
  Layers,
  Table,
  Hash,
  Trash2,
  ArrowLeft,
  Loader2,
  Code,
  Eye,
  Network,
  BarChart3,
  RefreshCw,
  Sparkles
} from 'lucide-react';


export const DatasetDetailPage: React.FC = () => {
  const { datasetId } = useParams<{ datasetId: string }>();
  const navigate = useNavigate();

  const [schemaData, setSchemaData] = useState<DatasetSchemaResponse | null>(null);
  const [loading, setLoading] = useState<boolean>(true);
  const [refreshing, setRefreshing] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);

  const [selectedTable, setSelectedTable] = useState<string | null>(null);
  const [activeTab, setActiveTab] = useState<'ask' | 'preview' | 'schema' | 'relationships' | 'quality'>('ask');


  const [deleteModalOpen, setDeleteModalOpen] = useState<boolean>(false);
  const [isDeleting, setIsDeleting] = useState<boolean>(false);

  const fetchSchema = async () => {
    if (!datasetId) return;
    try {
      const data = await datasetService.getDatasetSchema(datasetId);
      setSchemaData(data);
      if (data.tables && data.tables.length > 0 && !selectedTable) {
        setSelectedTable(data.tables[0].table_name);
      }
    } catch (err: any) {
      setError(err.response?.data?.detail || 'Dataset schema not found.');
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchSchema();
  }, [datasetId]);

  const handleRefreshSchema = async () => {
    if (!datasetId) return;
    setRefreshing(true);
    try {
      const updated = await datasetService.refreshSchema(datasetId);
      setSchemaData(updated);
    } catch (err: any) {
      console.error('Refresh schema failed:', err);
    } finally {
      setRefreshing(false);
    }
  };

  const handleDeleteConfirm = async () => {
    if (!datasetId) return;
    setIsDeleting(true);
    try {
      await datasetService.deleteDataset(datasetId);
      navigate('/datasets');
    } catch (err) {
      console.error('Failed to delete dataset:', err);
      setIsDeleting(false);
    }
  };

  if (loading) {
    return (
      <div className="py-24 text-center space-y-3">
        <Loader2 className="h-8 w-8 text-brand-400 animate-spin mx-auto" />
        <p className="text-sm text-slate-400">Analyzing database structure &amp; relationships...</p>
      </div>
    );
  }

  if (error || !schemaData) {
    return (
      <div className="py-12 space-y-4 max-w-lg mx-auto text-center">
        <div className="p-6 rounded-2xl bg-rose-500/10 border border-rose-500/20 text-rose-300 text-sm">
          {error || 'Unable to load dataset details.'}
        </div>
        <button
          onClick={() => navigate('/datasets')}
          className="inline-flex items-center space-x-2 text-xs font-semibold text-brand-400 hover:text-brand-300"
        >
          <ArrowLeft className="h-4 w-4" />
          <span>Back to My Datasets</span>
        </button>
      </div>
    );
  }

  return (
    <div className="space-y-4 pb-4">
      {/* Back Button */}
      <button
        onClick={() => navigate('/datasets')}
        className="inline-flex items-center space-x-2 text-xs font-medium text-slate-400 hover:text-slate-200 transition-colors"
      >
        <ArrowLeft className="h-4 w-4" />
        <span>Back to Datasets</span>
      </button>

      {/* Dataset Overview Header Card */}
      <div className="bg-slate-900/60 border border-slate-800 rounded-2xl p-3.5 md:p-4 space-y-2.5 shadow-xl">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-3">
          <div className="flex items-center space-x-3.5">
            <div className="h-11 w-11 rounded-xl bg-slate-800 border border-slate-700 flex items-center justify-center shrink-0 text-brand-400">
              <Database className="h-5.5 w-5.5" />
            </div>
            <div>
              <div className="flex items-center space-x-2.5">
                <h1 className="text-lg md:text-xl font-bold text-white tracking-tight">{schemaData.original_filename}</h1>
                <span className="px-2.5 py-0.5 text-xs font-semibold rounded-full bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                  ✓ Ready
                </span>
              </div>
              <p className="text-xs text-slate-400 font-mono mt-0.5">
                Isolated Schema: <span className="text-slate-200">{schemaData.schema_name}</span>
              </p>
            </div>
          </div>

          <div className="flex items-center space-x-2.5 self-start md:self-auto">
            <button
              onClick={handleRefreshSchema}
              disabled={refreshing}
              className="inline-flex items-center space-x-2 px-3.5 py-1.5 rounded-xl bg-slate-800 hover:bg-slate-700 text-slate-200 text-xs md:text-sm font-semibold transition-colors border border-slate-700/80 cursor-pointer"
              title="Re-inspect schema and update metadata"
            >
              <RefreshCw className={`h-3.5 w-3.5 ${refreshing ? 'animate-spin text-brand-400' : 'text-slate-400'}`} />
              <span>{refreshing ? 'Refreshing...' : 'Refresh Schema'}</span>
            </button>

            <button
              onClick={() => setDeleteModalOpen(true)}
              className="inline-flex items-center space-x-2 px-3.5 py-1.5 rounded-xl text-rose-400 hover:bg-rose-500/10 border border-rose-500/20 text-xs md:text-sm font-semibold transition-colors cursor-pointer"
            >
              <Trash2 className="h-3.5 w-3.5" />
              <span>Delete</span>
            </button>
          </div>
        </div>

        {/* Overview Metric Summary Cards */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3 pt-2.5 border-t border-slate-800/80">
          <div className="bg-slate-950/60 p-2 md:p-2.5 rounded-xl border border-slate-800/80 text-center">
            <div className="text-xs text-slate-400 flex items-center justify-center space-x-1.5 mb-0.5">
              <Layers className="h-3.5 w-3.5 text-brand-400" />
              <span>Tables</span>
            </div>
            <div className="text-lg md:text-xl font-extrabold text-white">{schemaData.number_of_tables}</div>
          </div>

          <div className="bg-slate-950/60 p-2 md:p-2.5 rounded-xl border border-slate-800/80 text-center">
            <div className="text-xs text-slate-400 flex items-center justify-center space-x-1.5 mb-0.5">
              <Table className="h-3.5 w-3.5 text-emerald-400" />
              <span>Total Rows</span>
            </div>
            <div className="text-lg md:text-xl font-extrabold text-white">{schemaData.total_rows.toLocaleString()}</div>
          </div>

          <div className="bg-slate-950/60 p-2 md:p-2.5 rounded-xl border border-slate-800/80 text-center">
            <div className="text-xs text-slate-400 flex items-center justify-center space-x-1.5 mb-0.5">
              <Hash className="h-3.5 w-3.5 text-sky-400" />
              <span>Total Columns</span>
            </div>
            <div className="text-lg md:text-xl font-extrabold text-white">{schemaData.total_columns}</div>
          </div>

          <div className="bg-slate-950/60 p-2 md:p-2.5 rounded-xl border border-slate-800/80 text-center">
            <div className="text-xs text-slate-400 flex items-center justify-center space-x-1.5 mb-0.5">
              <Network className="h-3.5 w-3.5 text-indigo-400" />
              <span>Relationships</span>
            </div>
            <div className="text-lg md:text-xl font-extrabold text-white">{schemaData.relationships?.length || 0}</div>
          </div>
        </div>
      </div>

      {/* Main Content Workspace: Navigation Tabs + Active View */}
      <div className="space-y-3">
        {/* Navigation Tabs */}
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3 border-b border-slate-800 pb-2">
          <div className="flex flex-wrap items-center gap-3 md:gap-3.5 pb-1 sm:pb-0">
            <button
              onClick={() => setActiveTab('ask')}
              className={`inline-flex items-center space-x-2 px-4.5 py-2.5 rounded-xl text-xs md:text-sm font-semibold transition-all shrink-0 ${
                activeTab === 'ask'
                  ? 'bg-brand-600/20 dark:bg-[#414141] text-brand-600 dark:text-[#F2F2F2] border border-brand-500/30 dark:border-[#555555]'
                  : 'text-slate-500 dark:text-[#AFAFAF] hover:text-slate-900 dark:hover:text-[#F2F2F2] hover:bg-slate-100 dark:hover:bg-[#383838]'
              }`}
            >
              <Sparkles className={`h-4.5 w-4.5 ${activeTab === 'ask' ? 'text-brand-600 dark:text-[#8AB4F8]' : 'text-slate-400 dark:text-[#B8B8B8]'}`} />
              <span>Ask Your Data (AI)</span>
            </button>

            <button
              onClick={() => setActiveTab('preview')}
              className={`inline-flex items-center space-x-2 px-4.5 py-2.5 rounded-xl text-xs md:text-sm font-semibold transition-all shrink-0 ${
                activeTab === 'preview'
                  ? 'bg-brand-600/20 dark:bg-[#414141] text-brand-600 dark:text-[#F2F2F2] border border-brand-500/30 dark:border-[#555555]'
                  : 'text-slate-500 dark:text-[#AFAFAF] hover:text-slate-900 dark:hover:text-[#F2F2F2] hover:bg-slate-100 dark:hover:bg-[#383838]'
              }`}
            >
              <Eye className={`h-4.5 w-4.5 ${activeTab === 'preview' ? 'text-brand-600 dark:text-[#8AB4F8]' : 'text-slate-400 dark:text-[#B8B8B8]'}`} />
              <span>Data Preview</span>
            </button>

            <button
              onClick={() => setActiveTab('schema')}
              className={`inline-flex items-center space-x-2 px-4.5 py-2.5 rounded-xl text-xs md:text-sm font-semibold transition-all shrink-0 ${
                activeTab === 'schema'
                  ? 'bg-brand-600/20 dark:bg-[#414141] text-brand-600 dark:text-[#F2F2F2] border border-brand-500/30 dark:border-[#555555]'
                  : 'text-slate-500 dark:text-[#AFAFAF] hover:text-slate-900 dark:hover:text-[#F2F2F2] hover:bg-slate-100 dark:hover:bg-[#383838]'
              }`}
            >
              <Code className={`h-4.5 w-4.5 ${activeTab === 'schema' ? 'text-brand-600 dark:text-[#8AB4F8]' : 'text-slate-400 dark:text-[#B8B8B8]'}`} />
              <span>Schema Explorer</span>
            </button>

            <button
              onClick={() => setActiveTab('relationships')}
              className={`inline-flex items-center space-x-2 px-4.5 py-2.5 rounded-xl text-xs md:text-sm font-semibold transition-all shrink-0 ${
                activeTab === 'relationships'
                  ? 'bg-brand-600/20 dark:bg-[#414141] text-brand-600 dark:text-[#F2F2F2] border border-brand-500/30 dark:border-[#555555]'
                  : 'text-slate-500 dark:text-[#AFAFAF] hover:text-slate-900 dark:hover:text-[#F2F2F2] hover:bg-slate-100 dark:hover:bg-[#383838]'
              }`}
            >
              <Network className={`h-4.5 w-4.5 ${activeTab === 'relationships' ? 'text-brand-600 dark:text-[#8AB4F8]' : 'text-slate-400 dark:text-[#B8B8B8]'}`} />
              <span>Relationships ({schemaData.relationships?.length || 0})</span>
            </button>

            <button
              onClick={() => setActiveTab('quality')}
              className={`inline-flex items-center space-x-2 px-4.5 py-2.5 rounded-xl text-xs md:text-sm font-semibold transition-all shrink-0 ${
                activeTab === 'quality'
                  ? 'bg-brand-600/20 dark:bg-[#414141] text-brand-600 dark:text-[#F2F2F2] border border-brand-500/30 dark:border-[#555555]'
                  : 'text-slate-500 dark:text-[#AFAFAF] hover:text-slate-900 dark:hover:text-[#F2F2F2] hover:bg-slate-100 dark:hover:bg-[#383838]'
              }`}
            >
              <BarChart3 className={`h-4.5 w-4.5 ${activeTab === 'quality' ? 'text-brand-600 dark:text-[#8AB4F8]' : 'text-slate-400 dark:text-[#B8B8B8]'}`} />
              <span>Data Quality &amp; Stats</span>
            </button>
          </div>

          {/* Table Pills selector for Preview / Quality tabs */}
          {(activeTab === 'preview' || activeTab === 'quality') &&
            schemaData.tables &&
            schemaData.tables.length > 0 && (
              <div className="flex items-center gap-2 overflow-x-auto">
                <span className="text-xs font-medium text-slate-400 shrink-0">Table:</span>
                {schemaData.tables.map((t) => (
                  <button
                    key={t.id}
                    onClick={() => setSelectedTable(t.table_name)}
                    className={`px-3 py-1.5 rounded-xl text-xs font-mono font-semibold transition-all shrink-0 ${
                      selectedTable === t.table_name
                        ? 'bg-brand-600 text-white shadow-md shadow-brand-600/20'
                        : 'bg-slate-900 text-slate-400 hover:text-slate-200 border border-slate-800'
                    }`}
                  >
                    {t.display_name || t.table_name} ({t.row_count.toLocaleString()})
                  </button>
                ))}
              </div>
            )}
        </div>

        {/* Tab Views */}
        {activeTab === 'ask' && (
          <QueryWorkspace
            datasetId={schemaData.dataset_id}
            datasetName={schemaData.original_filename}
            tables={schemaData.tables}
          />
        )}

        {activeTab === 'preview' && (
          selectedTable ? (
            <DataPreviewTable datasetId={schemaData.dataset_id} tableName={selectedTable} />
          ) : (
            <div className="py-12 text-center text-sm text-slate-400">No table selected.</div>
          )
        )}


        {activeTab === 'schema' && <SchemaViewer tables={schemaData.tables || []} />}

        {activeTab === 'relationships' && (
          <RelationshipViewer relationships={schemaData.relationships || []} />
        )}

        {activeTab === 'quality' && (
          selectedTable ? (
            <DataQualityPanel datasetId={schemaData.dataset_id} tableName={selectedTable} />
          ) : (
            <div className="py-12 text-center text-sm text-slate-400">No table selected.</div>
          )
        )}
      </div>

      {/* Delete Confirmation Modal */}
      <DeleteConfirmModal
        isOpen={deleteModalOpen}
        datasetName={schemaData.original_filename}
        isDeleting={isDeleting}
        onConfirm={handleDeleteConfirm}
        onCancel={() => setDeleteModalOpen(false)}
      />
    </div>
  );
};
