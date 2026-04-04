import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer, Cell,
} from 'recharts';
import { format } from 'date-fns';

const SEVERITY_COLORS = {
  critical: '#dc2626',
  high: '#ea580c',
  medium: '#d97706',
  low: '#2563eb',
};

function CustomTooltip({ active, payload, label }) {
  if (!active || !payload?.length) return null;
  const d = payload[0];
  return (
    <div className="bg-white border border-slate-200 rounded-xl shadow-lg p-3 text-xs">
      <div className="font-semibold text-slate-700 mb-1">{label}</div>
      <div className="flex items-center gap-2">
        <span className="w-2 h-2 rounded-full" style={{ background: d.fill }} />
        <span className="text-slate-600">Area Affected:</span>
        <span className="font-bold text-slate-800">{d.value?.toFixed(1)} ha</span>
      </div>
    </div>
  );
}

export default function ChangeAreaChart({ alerts }) {
  if (!alerts || alerts.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center h-48 text-center">
        <div className="text-3xl mb-2">📉</div>
        <div className="text-slate-500 text-sm">No change events recorded yet.</div>
      </div>
    );
  }

  const data = [...alerts]
    .sort((a, b) => new Date(a.detected_at) - new Date(b.detected_at))
    .slice(-30)
    .map((a) => ({
      date: format(new Date(a.detected_at), 'MMM d'),
      area: parseFloat((a.change_area_ha ?? 0).toFixed(1)),
      severity: a.severity,
    }));

  return (
    <ResponsiveContainer width="100%" height={200}>
      <BarChart data={data} margin={{ top: 4, right: 8, left: 0, bottom: 0 }}>
        <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" vertical={false} />
        <XAxis
          dataKey="date"
          tick={{ fontSize: 11, fill: '#94a3b8' }}
          axisLine={false}
          tickLine={false}
        />
        <YAxis
          tick={{ fontSize: 11, fill: '#94a3b8' }}
          axisLine={false}
          tickLine={false}
          width={40}
          unit=" ha"
        />
        <Tooltip content={<CustomTooltip />} cursor={{ fill: '#f1f5f9' }} />
        <Bar dataKey="area" radius={[4, 4, 0, 0]} name="Area Affected (ha)">
          {data.map((entry, index) => (
            <Cell
              key={index}
              fill={SEVERITY_COLORS[entry.severity] || '#64748b'}
            />
          ))}
        </Bar>
      </BarChart>
    </ResponsiveContainer>
  );
}
