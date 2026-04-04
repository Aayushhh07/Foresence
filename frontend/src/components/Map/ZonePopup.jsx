import { useState, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import useAppStore from '../../store/appStore';

const STATUS_COLORS = {
  healthy: '#16a34a',
  warning: '#d97706',
  critical: '#dc2626',
};

function HealthGauge({ score }) {
  const radius = 28;
  const circumference = 2 * Math.PI * radius;
  const offset = circumference - (score / 100) * circumference;
  const color = score > 70 ? '#16a34a' : score >= 40 ? '#d97706' : '#dc2626';

  return (
    <div className="health-gauge w-16 h-16">
      <svg width="64" height="64">
        <circle cx="32" cy="32" r={radius} fill="none" stroke="#e2e8f0" strokeWidth="5" />
        <circle
          cx="32" cy="32" r={radius}
          fill="none" stroke={color} strokeWidth="5"
          strokeDasharray={circumference}
          strokeDashoffset={offset}
          strokeLinecap="round"
          style={{ transform: 'rotate(-90deg)', transformOrigin: '32px 32px', transition: 'stroke-dashoffset 0.5s ease' }}
        />
      </svg>
      <span className="health-gauge-text" style={{ color, fontSize: '12px', fontWeight: 700 }}>{score}</span>
    </div>
  );
}

export default function ZonePopup({ zone, onClose }) {
  const navigate = useNavigate();
  const [latestNdvi, setLatestNdvi] = useState(null);

  const statusColor = STATUS_COLORS[zone.status] || '#64748b';
  const lastScanned = zone.last_scanned_at
    ? new Date(zone.last_scanned_at).toLocaleString()
    : 'Never scanned';

  return (
    <div className="bg-white rounded-xl shadow-2xl w-72 overflow-hidden animate-slide-in">
      {/* Header */}
      <div
        className="p-4 pb-3"
        style={{ background: `linear-gradient(135deg, ${statusColor}15, ${statusColor}08)`, borderBottom: `2px solid ${statusColor}30` }}
      >
        <div className="flex items-start justify-between gap-2">
          <div className="flex-1 min-w-0">
            <h3 className="font-bold text-slate-900 text-sm leading-tight truncate">{zone.name}</h3>
            <p className="text-slate-500 text-xs mt-0.5">{zone.area_ha?.toFixed(1)} ha</p>
          </div>
          <div className="flex items-center gap-2">
            <span
              className={`text-xs font-bold px-2 py-0.5 rounded-full`}
              style={{ background: `${statusColor}20`, color: statusColor, border: `1px solid ${statusColor}40` }}
            >
              {zone.status?.toUpperCase()}
            </span>
            <button onClick={onClose} className="text-slate-400 hover:text-slate-600 transition-colors">
              <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
              </svg>
            </button>
          </div>
        </div>
      </div>

      {/* Body */}
      <div className="p-4 space-y-3">
        {/* Health Score */}
        <div className="flex items-center gap-4">
          <HealthGauge score={zone.health_score || 100} />
          <div>
            <div className="text-xs text-slate-500 uppercase tracking-wide font-semibold">Health Score</div>
            <div className="text-2xl font-bold" style={{ color: statusColor }}>{zone.health_score || 100}</div>
            <div className="text-xs text-slate-400">/100</div>
          </div>
        </div>

        {/* Last scanned */}
        <div className="flex items-center gap-2 text-xs text-slate-500">
          <svg className="w-3.5 h-3.5 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 8v4l3 3m6-3a9 9 0 11-18 0 9 9 0 0118 0z" />
          </svg>
          <span>Scanned: {lastScanned}</span>
        </div>

        {/* Description */}
        {zone.description && (
          <p className="text-xs text-slate-600 bg-slate-50 rounded-lg p-2 leading-relaxed">{zone.description}</p>
        )}

        {/* Thresholds */}
        <div className="grid grid-cols-2 gap-2">
          <div className="bg-slate-50 rounded-lg p-2 text-center">
            <div className="text-xs text-slate-500 font-medium">NDVI Threshold</div>
            <div className="font-bold text-slate-800 text-sm">{zone.ndvi_drop_threshold || 0.15}</div>
          </div>
          <div className="bg-slate-50 rounded-lg p-2 text-center">
            <div className="text-xs text-slate-500 font-medium">Confidence</div>
            <div className="font-bold text-slate-800 text-sm">{Math.round((zone.confidence_threshold || 0.70) * 100)}%</div>
          </div>
        </div>
      </div>

      {/* Actions */}
      <div className="px-4 pb-4 flex gap-2">
        <button
          onClick={() => navigate(`/analytics?zone=${zone._id}`)}
          className="flex-1 btn-primary text-xs justify-center py-2"
        >
          <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
          </svg>
          Analytics
        </button>
        <button
          onClick={() => navigate(`/alerts?zone_id=${zone._id}`)}
          className="flex-1 btn-secondary text-xs justify-center py-2"
        >
          <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3L13.732 4c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z" />
          </svg>
          Alerts
        </button>
      </div>
    </div>
  );
}
