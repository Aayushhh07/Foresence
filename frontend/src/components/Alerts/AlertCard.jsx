import { useState } from 'react';
import { format } from 'date-fns';
import { alertsApi } from '../../services/api';
import useAppStore from '../../store/appStore';
import { toast } from 'react-toastify';

const SEVERITY_CONFIG = {
  critical: { label: 'Critical', class: 'badge-critical', dot: 'bg-red-500', textColor: 'text-red-700' },
  high:     { label: 'High',     class: 'badge-high',     dot: 'bg-orange-500', textColor: 'text-orange-700' },
  medium:   { label: 'Medium',   class: 'badge-medium',   dot: 'bg-yellow-500', textColor: 'text-yellow-700' },
  low:      { label: 'Low',      class: 'badge-low',      dot: 'bg-blue-500',   textColor: 'text-blue-700' },
};

const STATUS_CONFIG = {
  new:          { label: 'New',          class: 'bg-red-100 text-red-700 border-red-200' },
  acknowledged: { label: 'Acknowledged', class: 'bg-yellow-100 text-yellow-700 border-yellow-200' },
  resolved:     { label: 'Resolved',     class: 'bg-green-100 text-green-700 border-green-200' },
};

function ImageModal({ src, onClose }) {
  return (
    <div
      className="fixed inset-0 z-[9999] bg-black/80 flex items-center justify-center"
      onClick={onClose}
    >
      <div className="relative max-w-4xl mx-4">
        <button
          onClick={onClose}
          className="absolute -top-10 right-0 text-white hover:text-slate-300 transition-colors"
        >
          <svg className="w-8 h-8" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
          </svg>
        </button>
        <img
          src={src}
          alt="Change detection map"
          className="rounded-xl max-h-[80vh] object-contain"
          onClick={(e) => e.stopPropagation()}
        />
      </div>
    </div>
  );
}

export default function AlertCard({ alert, onStatusChanged }) {
  const { updateAlertStatus } = useAppStore();
  const [updating, setUpdating] = useState(false);
  const [imageModalSrc, setImageModalSrc] = useState(null);

  const sev = SEVERITY_CONFIG[alert.severity] || SEVERITY_CONFIG.low;
  const statusCfg = STATUS_CONFIG[alert.status] || STATUS_CONFIG.new;
  const ndviDelta = alert.ndvi_delta ?? (alert.ndvi_after - alert.ndvi_before);
  const isDropping = ndviDelta < 0;

  const handleStatus = async (newStatus) => {
    setUpdating(true);
    try {
      await alertsApi.updateStatus(alert._id, newStatus);
      updateAlertStatus(alert._id, newStatus);
      toast.success(`Alert ${newStatus}`);
      onStatusChanged?.();
    } catch (err) {
      toast.error(err.message);
    } finally {
      setUpdating(false);
    }
  };

  return (
    <>
      <div className="card card-hover p-5 animate-slide-in">
        {/* Header row */}
        <div className="flex items-start justify-between gap-3 mb-4">
          <div className="flex items-start gap-3">
            <div className={`w-2.5 h-2.5 rounded-full mt-1.5 flex-shrink-0 ${sev.dot} animate-pulse`} />
            <div>
              <div className="font-bold text-slate-900 text-sm">{alert.zone_name}</div>
              <div className="text-slate-500 text-xs mt-0.5">
                {alert.detected_at
                  ? format(new Date(alert.detected_at), "MMM d, yyyy · HH:mm 'UTC'")
                  : 'Unknown time'
                }
              </div>
            </div>
          </div>
          <div className="flex items-center gap-2 flex-shrink-0">
            <span className={`text-xs font-bold px-2.5 py-1 rounded-full border ${sev.class}`}>
              {sev.label}
            </span>
            <span className={`text-xs font-semibold px-2.5 py-1 rounded-full border ${statusCfg.class}`}>
              {statusCfg.label}
            </span>
          </div>
        </div>

        {/* Stats grid */}
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 mb-4">
          {/* NDVI Before */}
          <div className="bg-slate-50 rounded-lg p-3">
            <div className="text-xs text-slate-500 font-medium mb-1">NDVI Before</div>
            <div className="font-bold text-green-700 text-lg">
              {(alert.ndvi_before ?? 0).toFixed(3)}
            </div>
          </div>

          {/* NDVI After */}
          <div className="bg-slate-50 rounded-lg p-3">
            <div className="text-xs text-slate-500 font-medium mb-1">NDVI After</div>
            <div className={`font-bold text-lg ${isDropping ? 'text-red-600' : 'text-green-700'}`}>
              {(alert.ndvi_after ?? 0).toFixed(3)}
            </div>
          </div>

          {/* Delta */}
          <div className="bg-slate-50 rounded-lg p-3">
            <div className="text-xs text-slate-500 font-medium mb-1">NDVI Δ</div>
            <div className={`font-bold text-lg ${isDropping ? 'text-red-600' : 'text-green-700'}`}>
              {isDropping ? '▼' : '▲'} {Math.abs(ndviDelta).toFixed(3)}
            </div>
          </div>

          {/* Area */}
          <div className="bg-slate-50 rounded-lg p-3">
            <div className="text-xs text-slate-500 font-medium mb-1">Area Affected</div>
            <div className="font-bold text-slate-800 text-lg">
              {(alert.change_area_ha ?? 0).toFixed(1)}
              <span className="text-xs font-normal text-slate-500 ml-1">ha</span>
            </div>
          </div>
        </div>

        {/* Confidence bar */}
        <div className="mb-4">
          <div className="flex justify-between items-center text-xs mb-1.5">
            <span className="text-slate-500 font-medium">Confidence Score</span>
            <span className={`font-bold ${sev.textColor}`}>
              {Math.round((alert.confidence ?? 0) * 100)}%
            </span>
          </div>
          <div className="w-full h-2 bg-slate-100 rounded-full overflow-hidden">
            <div
              className="h-full rounded-full transition-all duration-500"
              style={{
                width: `${Math.round((alert.confidence ?? 0) * 100)}%`,
                background: alert.severity === 'critical' ? '#dc2626'
                  : alert.severity === 'high' ? '#ea580c'
                  : alert.severity === 'medium' ? '#d97706'
                  : '#2563eb',
              }}
            />
          </div>
        </div>

        {/* Change map thumbnail */}
        {alert.change_map_url && (
          <div className="mb-4">
            <div className="text-xs text-slate-500 font-medium mb-2">Change Detection Map</div>
            <img
              src={alert.change_map_url}
              alt="Change map"
              className="w-full h-32 object-cover rounded-lg border border-slate-200 cursor-zoom-in hover:opacity-90 transition-opacity"
              onClick={() => setImageModalSrc(alert.change_map_url)}
              onError={(e) => { e.target.style.display = 'none'; }}
            />
          </div>
        )}

        {/* Notes */}
        {alert.notes && (
          <div className="mb-3 text-xs text-slate-600 bg-slate-50 rounded-lg p-2.5 italic">
            {alert.notes}
          </div>
        )}

        {/* Action buttons */}
        {alert.status === 'new' && (
          <div className="flex gap-2">
            <button
              onClick={() => handleStatus('acknowledged')}
              disabled={updating}
              className="btn-secondary flex-1 text-xs justify-center py-2"
            >
              {updating ? '…' : 'Acknowledge'}
            </button>
            <button
              onClick={() => handleStatus('resolved')}
              disabled={updating}
              className="btn-primary flex-1 text-xs justify-center py-2"
            >
              {updating ? '…' : 'Resolve'}
            </button>
          </div>
        )}
        {alert.status === 'acknowledged' && (
          <div className="flex gap-2">
            <button
              onClick={() => handleStatus('resolved')}
              disabled={updating}
              className="btn-primary w-full text-xs justify-center py-2"
            >
              {updating ? '…' : '✓ Mark Resolved'}
            </button>
          </div>
        )}
      </div>

      {imageModalSrc && (
        <ImageModal src={imageModalSrc} onClose={() => setImageModalSrc(null)} />
      )}
    </>
  );
}
