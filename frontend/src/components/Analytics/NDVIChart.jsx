import {
  LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip,
  ResponsiveContainer, ReferenceLine, Area, ComposedChart,
} from 'recharts';
import { format } from 'date-fns';

function CustomTooltip({ active, payload, label }) {
  if (!active || !payload?.length) return null;
  return (
    <div className="bg-white border border-slate-200 rounded-xl shadow-lg p-3 text-xs">
      <div className="font-semibold text-slate-700 mb-2">{label}</div>
      {payload.map((entry) => (
        <div key={entry.dataKey} className="flex items-center gap-2">
          <span className="w-2 h-2 rounded-full" style={{ background: entry.color }} />
          <span className="text-slate-600">{entry.name}:</span>
          <span className="font-bold" style={{ color: entry.color }}>
            {typeof entry.value === 'number' ? entry.value.toFixed(3) : entry.value}
          </span>
        </div>
      ))}
    </div>
  );
}

export default function NDVIChart({ snapshots }) {
  if (!snapshots || snapshots.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center h-64 text-center">
        <div className="text-3xl mb-2">📊</div>
        <div className="text-slate-500 text-sm">No snapshot data available yet.</div>
        <div className="text-slate-400 text-xs mt-1">Trigger a manual scan in Settings to get started.</div>
      </div>
    );
  }

  const data = [...snapshots]
    .sort((a, b) => new Date(a.timestamp) - new Date(b.timestamp))
    .map((s) => ({
      date: format(new Date(s.timestamp), 'MMM d'),
      ndvi: parseFloat(s.ndvi_mean?.toFixed(3) ?? 0),
      ndvi_min: parseFloat(s.ndvi_min?.toFixed(3) ?? 0),
      ndvi_max: parseFloat(s.ndvi_max?.toFixed(3) ?? 0),
      evi: parseFloat(s.evi_mean?.toFixed(3) ?? 0),
      cloud: parseFloat(s.cloud_cover_pct?.toFixed(1) ?? 0),
    }));

  const avgNdvi = data.reduce((sum, d) => sum + d.ndvi, 0) / data.length;

  return (
    <div>
      {/* Chart */}
      <ResponsiveContainer width="100%" height={280}>
        <ComposedChart data={data} margin={{ top: 8, right: 16, left: 0, bottom: 0 }}>
          <defs>
            <linearGradient id="ndviGradient" x1="0" y1="0" x2="0" y2="1">
              <stop offset="5%" stopColor="#16a34a" stopOpacity={0.12} />
              <stop offset="95%" stopColor="#16a34a" stopOpacity={0} />
            </linearGradient>
          </defs>
          <CartesianGrid strokeDasharray="3 3" stroke="#f1f5f9" />
          <XAxis
            dataKey="date"
            tick={{ fontSize: 11, fill: '#94a3b8' }}
            axisLine={false}
            tickLine={false}
          />
          <YAxis
            domain={[-0.1, 1]}
            tick={{ fontSize: 11, fill: '#94a3b8' }}
            axisLine={false}
            tickLine={false}
            width={40}
          />
          <Tooltip content={<CustomTooltip />} />

          {/* Min/Max confidence band */}
          <Area
            type="monotone"
            dataKey="ndvi_max"
            stroke="none"
            fill="#16a34a"
            fillOpacity={0.06}
            name="NDVI Max"
          />
          <Area
            type="monotone"
            dataKey="ndvi_min"
            stroke="none"
            fill="#f8fafc"
            fillOpacity={1}
            name="NDVI Min"
          />

          {/* NDVI Mean line */}
          <Line
            type="monotone"
            dataKey="ndvi"
            stroke="#16a34a"
            strokeWidth={2.5}
            dot={{ r: 3, fill: '#16a34a', strokeWidth: 0 }}
            activeDot={{ r: 5, fill: '#16a34a' }}
            name="NDVI Mean"
          />

          {/* EVI line */}
          <Line
            type="monotone"
            dataKey="evi"
            stroke="#0ea5e9"
            strokeWidth={1.5}
            strokeDasharray="4 2"
            dot={false}
            name="EVI Mean"
          />

          {/* Average reference line */}
          <ReferenceLine
            y={avgNdvi}
            stroke="#64748b"
            strokeDasharray="6 3"
            strokeWidth={1}
            label={{ value: `Avg ${avgNdvi.toFixed(3)}`, position: 'right', fontSize: 10, fill: '#64748b' }}
          />
        </ComposedChart>
      </ResponsiveContainer>

      {/* Legend */}
      <div className="flex items-center gap-5 mt-3 text-xs text-slate-500">
        <div className="flex items-center gap-1.5">
          <div className="w-4 h-0.5 bg-forest-600 rounded" />
          <span>NDVI Mean</span>
        </div>
        <div className="flex items-center gap-1.5">
          <div className="w-4 h-0.5 bg-sky-500 rounded" style={{ borderTop: '2px dashed' }} />
          <span>EVI Mean</span>
        </div>
        <div className="flex items-center gap-1.5">
          <div className="w-4 h-2 rounded" style={{ background: 'rgba(22,163,74,0.12)' }} />
          <span>NDVI Range (min–max)</span>
        </div>
      </div>
    </div>
  );
}
