import { format } from 'date-fns';
import { resolveImageUrl } from '../../utils/imageUrl';

export default function RecentScanImages({ snapshots, loading, onRefresh }) {
  const recent = (snapshots || [])
    .filter((s) => s?.image_url)
    .sort((a, b) => new Date(b.timestamp) - new Date(a.timestamp))
    .slice(0, 2);

  return (
    <div className="card p-4 sm:p-5">
      <div className="flex flex-wrap items-start justify-between gap-2 mb-4">
        <div>
          <h2 className="font-bold text-slate-800">Recent satellite scans</h2>
          <p className="text-xs text-slate-500 mt-0.5">
            Latest 2 NDVI maps for this zone — updates after each scan
          </p>
        </div>
        {onRefresh && (
          <button type="button" className="btn-ghost text-xs" onClick={onRefresh} disabled={loading}>
            {loading ? 'Refreshing…' : '↻ Refresh'}
          </button>
        )}
      </div>

      {loading && !recent.length ? (
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <div className="skeleton h-44 w-full rounded-lg" />
          <div className="skeleton h-44 w-full rounded-lg" />
        </div>
      ) : recent.length === 0 ? (
        <div className="text-center py-10 px-4 rounded-lg bg-slate-50 border border-dashed border-slate-200">
          <div className="text-3xl mb-2">🛰️</div>
          <p className="text-sm font-medium text-slate-700">No scan images yet</p>
          <p className="text-xs text-slate-500 mt-1">
            Run a scan from the map or wait for the scheduled pass. Images appear here automatically.
          </p>
        </div>
      ) : (
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          {recent.map((snap, index) => {
            const src = resolveImageUrl(snap.image_url);
            const label = index === 0 ? 'Latest scan' : 'Previous scan';
            const ts = snap.timestamp ? new Date(snap.timestamp) : null;
            return (
              <div
                key={snap.scan_id || snap.timestamp || index}
                className="rounded-xl border border-slate-200 overflow-hidden bg-slate-50"
              >
                <div className="px-3 py-2 bg-white border-b border-slate-100 flex justify-between items-center gap-2">
                  <span className="text-xs font-bold text-slate-700 uppercase tracking-wide">{label}</span>
                  <span className="text-[10px] text-slate-500 tabular-nums">
                    {ts && !Number.isNaN(ts.getTime())
                      ? format(ts, 'MMM d, yyyy HH:mm')
                      : '—'}
                  </span>
                </div>
                <a href={src} target="_blank" rel="noopener noreferrer" className="block">
                  <img
                    src={src}
                    alt={`NDVI ${label}`}
                    className="w-full h-44 sm:h-52 object-cover bg-slate-200"
                    loading="lazy"
                  />
                </a>
                <div className="px-3 py-2 flex justify-between text-xs text-slate-600 bg-white">
                  <span>
                    NDVI: <strong className="text-slate-900">{snap.ndvi_mean?.toFixed(3) ?? '—'}</strong>
                  </span>
                  <span>Cloud: {snap.cloud_cover_pct != null ? `${snap.cloud_cover_pct.toFixed(0)}%` : '—'}</span>
                </div>
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
