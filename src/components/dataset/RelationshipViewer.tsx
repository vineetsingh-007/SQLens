import React from 'react';
import { Relationship } from '../../types/dataset';
import { Network, ArrowRight, ShieldCheck, HelpCircle } from 'lucide-react';

interface RelationshipViewerProps {
  relationships: Relationship[];
}

export const RelationshipViewer: React.FC<RelationshipViewerProps> = ({ relationships }) => {
  if (!relationships || relationships.length === 0) {
    return (
      <div className="py-16 text-center space-y-3 bg-slate-900/40 rounded-2xl border border-slate-800">
        <Network className="h-10 w-10 text-slate-600 mx-auto" />
        <div className="space-y-1">
          <h3 className="text-base font-semibold text-slate-200">No Relationships Detected</h3>
          <p className="text-xs text-slate-400 max-w-md mx-auto">
            This dataset contains single or unlinked tables with no matching primary/foreign key connections.
          </p>
        </div>
      </div>
    );
  }

  const confirmedRels = relationships.filter((r) => r.is_confirmed);
  const inferredRels = relationships.filter((r) => !r.is_confirmed);

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between text-xs text-slate-400">
        <p>
          Discovered <span className="font-semibold text-slate-200">{relationships.length}</span> relationship(s) across tables.
        </p>
        <div className="flex items-center space-x-4">
          <span className="flex items-center space-x-1.5 text-emerald-400">
            <ShieldCheck className="h-3.5 w-3.5" />
            <span>Confirmed FK ({confirmedRels.length})</span>
          </span>
          <span className="flex items-center space-x-1.5 text-sky-400">
            <HelpCircle className="h-3.5 w-3.5" />
            <span>Inferred ({inferredRels.length})</span>
          </span>
        </div>
      </div>

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
        {relationships.map((rel, idx) => (
          <div
            key={idx}
            className="p-4 rounded-2xl bg-slate-900/60 border border-slate-800 space-y-3 hover:border-slate-700 transition-all shadow-md"
          >
            <div className="flex items-center justify-between">
              <span className="text-[10px] font-semibold uppercase tracking-wider text-slate-400 font-mono">
                {rel.relationship_type.replace('_', ' ')}
              </span>

              {rel.is_confirmed ? (
                <span className="inline-flex items-center space-x-1 px-2.5 py-0.5 rounded-full text-[10px] font-semibold bg-emerald-500/10 text-emerald-400 border border-emerald-500/20">
                  <ShieldCheck className="h-3 w-3" />
                  <span>Confirmed FK</span>
                </span>
              ) : (
                <span className="inline-flex items-center space-x-1 px-2.5 py-0.5 rounded-full text-[10px] font-semibold bg-sky-500/10 text-sky-400 border border-sky-500/20">
                  <HelpCircle className="h-3 w-3" />
                  <span>Possible Relationship</span>
                </span>
              )}
            </div>

            {/* Connection Visual */}
            <div className="flex items-center justify-between bg-slate-950/80 p-3 rounded-xl border border-slate-800/80 font-mono text-xs">
              <div className="space-y-0.5">
                <div className="font-bold text-slate-200">{rel.source_table}</div>
                <div className="text-[11px] text-brand-400">{rel.source_column}</div>
              </div>

              <div className="h-8 w-8 rounded-full bg-slate-800 border border-slate-700 flex items-center justify-center shrink-0">
                <ArrowRight className="h-4 w-4 text-slate-400" />
              </div>

              <div className="space-y-0.5 text-right">
                <div className="font-bold text-slate-200">{rel.target_table}</div>
                <div className="text-[11px] text-emerald-400">{rel.target_column}</div>
              </div>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
};
