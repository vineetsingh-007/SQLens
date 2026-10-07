import React from 'react';
import {
  BarChart,
  Bar,
  LineChart,
  Line,
  AreaChart,
  Area,
  PieChart,
  Pie,
  Cell,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ResponsiveContainer
} from 'recharts';
import { BarChart3, TrendingUp, Award, PieChart as PieIcon, Layers } from 'lucide-react';
import { ChartRecommendation, QueryResultColumn } from '../../types/ai';

interface ResultChartProps {
  chart: ChartRecommendation;
  columns: QueryResultColumn[];
  rows: Array<Record<string, any>>;
  chartId?: string;
  isExporting?: boolean;
}

const PIE_COLORS = ['#8AB4F8', '#55D6A6', '#F6AD55', '#F687B3', '#9F7AEA', '#4FD1C5', '#F56565'];

export const ResultChart: React.FC<ResultChartProps> = ({
  chart,
  columns,
  rows,
  chartId,
  isExporting = false
}) => {
  if (!chart || chart.chart_type === 'none' || !rows || rows.length === 0) {
    return null;
  }

  const { chart_type, x_axis, y_axis, title } = chart;

  // Custom Tooltip formatter matching dark theme
  const CustomTooltip = ({ active, payload, label }: any) => {
    if (active && payload && payload.length) {
      return (
        <div className="p-3 bg-slate-900 dark:bg-[#202020] border border-slate-700 dark:border-[#4D4D4D] rounded-xl shadow-xl text-xs space-y-1 z-50">
          <div className="font-bold text-slate-200 dark:text-[#F2F2F2]">{label}</div>
          {payload.map((entry: any, index: number) => (
            <div key={index} className="text-brand-400 dark:text-[#8AB4F8] font-mono flex items-center space-x-2">
              <span className="w-2 h-2 rounded-full bg-brand-500 dark:bg-[#8AB4F8]" />
              <span>
                {entry.name}: {typeof entry.value === 'number' ? entry.value.toLocaleString() : entry.value}
              </span>
            </div>
          ))}
        </div>
      );
    }
    return null;
  };

  const containerId = chartId ? `sqlens-chart-${chartId}` : undefined;

  // Render KPI Card
  if (chart_type === 'kpi' && y_axis) {
    const kpiVal = rows[0]?.[y_axis];
    return (
      <div
        id={containerId}
        data-sqlens-chart-container="true"
        className="p-6 rounded-2xl bg-slate-900/90 dark:bg-[#333333] border border-slate-800 dark:border-[#484848] shadow-2xl flex items-center space-x-4"
      >
        <div className="p-4 rounded-2xl bg-indigo-500/10 dark:bg-[rgba(138,180,248,0.12)] text-brand-600 dark:text-[#8AB4F8] border border-indigo-500/30 dark:border-[rgba(138,180,248,0.35)]">
          <Award className="w-8 h-8" />
        </div>
        <div>
          <div className="text-xs font-semibold uppercase tracking-wider text-slate-400 dark:text-[#C7C7C7]">
            {title || y_axis.replace(/_/g, ' ').toUpperCase()}
          </div>
          <div className="text-3xl font-extrabold text-slate-100 dark:text-[#F2F2F2] font-mono mt-1">
            {typeof kpiVal === 'number' ? kpiVal.toLocaleString() : String(kpiVal ?? 'N/A')}
          </div>
        </div>
      </div>
    );
  }

  // Ensure x_axis and y_axis are valid keys
  const xAxisKey = x_axis || columns[0]?.name;
  const yAxisKey = y_axis || columns.find((c) => c.name !== xAxisKey)?.name || columns[1]?.name;

  if (!xAxisKey || !yAxisKey) return null;

  const renderChartIcon = () => {
    switch (chart_type) {
      case 'line':
        return <TrendingUp className="w-5 h-5 text-brand-600 dark:text-[#8AB4F8]" />;
      case 'area':
        return <Layers className="w-5 h-5 text-brand-600 dark:text-[#8AB4F8]" />;
      case 'pie':
        return <PieIcon className="w-5 h-5 text-brand-600 dark:text-[#8AB4F8]" />;
      default:
        return <BarChart3 className="w-5 h-5 text-brand-600 dark:text-[#8AB4F8]" />;
    }
  };

  return (
    <div
      id={containerId}
      data-sqlens-chart-container="true"
      className="p-6 rounded-2xl bg-slate-900/90 dark:bg-[#333333] border border-slate-800 dark:border-[#484848] shadow-2xl space-y-4"
    >
      <div className="flex items-center justify-between border-b border-slate-800/80 dark:border-[#484848] pb-3">
        <div className="flex items-center space-x-2">
          {renderChartIcon()}
          <h3 className="text-base font-bold text-slate-100 dark:text-[#F2F2F2]">
            {title || `${yAxisKey.replace(/_/g, ' ')} by ${xAxisKey.replace(/_/g, ' ')}`}
          </h3>
        </div>
        <span className="px-2.5 py-0.5 rounded-full text-[11px] font-bold bg-indigo-500/10 dark:bg-[rgba(138,180,248,0.12)] text-brand-600 dark:text-[#8AB4F8] border border-indigo-500/30 dark:border-[rgba(138,180,248,0.35)] uppercase">
          {chart_type} Chart
        </span>
      </div>

      <div className="h-72 w-full pt-2">
        <ResponsiveContainer width="100%" height="100%">
          {chart_type === 'line' ? (
            <LineChart data={rows} margin={{ top: 10, right: 30, left: 10, bottom: 25 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#484848" />
              <XAxis dataKey={xAxisKey} stroke="#C7C7C7" tick={{ fontSize: 11 }} dy={10} />
              <YAxis stroke="#C7C7C7" tick={{ fontSize: 11 }} />
              <Tooltip content={<CustomTooltip />} />
              <Line
                type="monotone"
                dataKey={yAxisKey}
                stroke="#8AB4F8"
                strokeWidth={3}
                dot={{ r: 4, fill: '#8AB4F8' }}
                activeDot={{ r: 6 }}
                isAnimationActive={!isExporting}
              />
            </LineChart>
          ) : chart_type === 'area' ? (
            <AreaChart data={rows} margin={{ top: 10, right: 30, left: 10, bottom: 25 }}>
              <defs>
                <linearGradient id="areaGradient" x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor="#8AB4F8" stopOpacity={0.4} />
                  <stop offset="95%" stopColor="#8AB4F8" stopOpacity={0.0} />
                </linearGradient>
              </defs>
              <CartesianGrid strokeDasharray="3 3" stroke="#484848" />
              <XAxis dataKey={xAxisKey} stroke="#C7C7C7" tick={{ fontSize: 11 }} dy={10} />
              <YAxis stroke="#C7C7C7" tick={{ fontSize: 11 }} />
              <Tooltip content={<CustomTooltip />} />
              <Area
                type="monotone"
                dataKey={yAxisKey}
                stroke="#8AB4F8"
                strokeWidth={3}
                fillOpacity={1}
                fill="url(#areaGradient)"
                isAnimationActive={!isExporting}
              />
            </AreaChart>
          ) : chart_type === 'pie' ? (
            <PieChart margin={{ top: 10, right: 30, left: 10, bottom: 10 }}>
              <Tooltip content={<CustomTooltip />} />
              <Pie
                data={rows}
                dataKey={yAxisKey}
                nameKey={xAxisKey}
                cx="50%"
                cy="50%"
                outerRadius={90}
                fill="#8AB4F8"
                label={({ name }) => String(name)}
                isAnimationActive={!isExporting}
              >
                {rows.map((_, index) => (
                  <Cell key={`cell-${index}`} fill={PIE_COLORS[index % PIE_COLORS.length]} />
                ))}
              </Pie>
            </PieChart>
          ) : (
            <BarChart data={rows} margin={{ top: 10, right: 30, left: 10, bottom: 25 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#484848" />
              <XAxis dataKey={xAxisKey} stroke="#C7C7C7" tick={{ fontSize: 11 }} dy={10} />
              <YAxis stroke="#C7C7C7" tick={{ fontSize: 11 }} />
              <Tooltip content={<CustomTooltip />} />
              <Bar dataKey={yAxisKey} fill="#8AB4F8" radius={[6, 6, 0, 0]} isAnimationActive={!isExporting} />
            </BarChart>
          )}
        </ResponsiveContainer>
      </div>
    </div>
  );
};
