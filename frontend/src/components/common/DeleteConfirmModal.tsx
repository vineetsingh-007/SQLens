import React from 'react';
import { AlertTriangle, Loader2 } from 'lucide-react';

interface DeleteConfirmModalProps {
  isOpen: boolean;
  datasetName: string;
  isDeleting: boolean;
  onConfirm: () => void;
  onCancel: () => void;
}

export const DeleteConfirmModal: React.FC<DeleteConfirmModalProps> = ({
  isOpen,
  datasetName,
  isDeleting,
  onConfirm,
  onCancel
}) => {
  if (!isOpen) return null;

  return (
    <div className="fixed inset-0 z-50 bg-slate-950/80 backdrop-blur-sm flex items-center justify-center p-4">
      <div className="bg-slate-900 border border-slate-800 rounded-2xl p-6 max-w-md w-full shadow-2xl space-y-5 animate-in fade-in zoom-in-95 duration-150">
        <div className="flex items-center space-x-3 text-rose-400">
          <div className="h-10 w-10 rounded-xl bg-rose-500/10 border border-rose-500/20 flex items-center justify-center">
            <AlertTriangle className="h-5 w-5 text-rose-400" />
          </div>
          <div>
            <h3 className="text-lg font-bold text-white">Delete this dataset?</h3>
            <p className="text-xs text-slate-400">This action cannot be undone.</p>
          </div>
        </div>

        <p className="text-sm text-slate-300 leading-relaxed">
          Are you sure you want to delete <span className="font-semibold text-white">"{datasetName}"</span>?
          This will drop its isolated database schema, tables, and stored source file.
        </p>

        <div className="flex items-center justify-end space-x-3 pt-2">
          <button
            type="button"
            onClick={onCancel}
            disabled={isDeleting}
            className="px-4 py-2 rounded-xl text-sm font-medium text-slate-300 hover:text-white bg-slate-800 hover:bg-slate-700 transition-colors"
          >
            Cancel
          </button>
          <button
            type="button"
            onClick={onConfirm}
            disabled={isDeleting}
            className="px-4 py-2 rounded-xl text-sm font-semibold text-white bg-rose-600 hover:bg-rose-500 transition-colors shadow-lg shadow-rose-600/20 flex items-center space-x-2"
          >
            {isDeleting ? (
              <>
                <Loader2 className="h-4 w-4 animate-spin" />
                <span>Deleting...</span>
              </>
            ) : (
              <span>Delete</span>
            )}
          </button>
        </div>
      </div>
    </div>
  );
};
