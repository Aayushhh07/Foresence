import { useState } from 'react';
import useZones from '../../hooks/useZones';
import { toast } from 'react-toastify';

export default function ZoneDrawer({ geojson, onClose, onSuccess }) {
  const { createZone } = useZones();
  const [loading, setLoading] = useState(false);
  const [form, setForm] = useState({
    name: '',
    description: '',
    ndvi_drop_threshold: 0.15,
    confidence_threshold: 0.70,
    alert_emails: '',
    webhook_url: '',
  });

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!form.name.trim()) { toast.error('Zone name is required'); return; }

    setLoading(true);
    try {
      const emails = form.alert_emails
        ? form.alert_emails.split(',').map((e) => e.trim()).filter(Boolean)
        : [];

      const zone = await createZone({
        name: form.name.trim(),
        description: form.description.trim(),
        geojson,
        ndvi_drop_threshold: parseFloat(form.ndvi_drop_threshold),
        confidence_threshold: parseFloat(form.confidence_threshold),
        alert_emails: emails,
        webhook_url: form.webhook_url.trim() || null,
      });

      toast.success(`Zone "${zone.name}" created successfully!`);
      onSuccess?.(zone);
      onClose?.();
    } catch (err) {
      toast.error(err.message || 'Failed to create zone');
    } finally {
      setLoading(false);
    }
  };

  return (
    <div className="fixed inset-0 z-[9999] flex items-center justify-center bg-black/40 backdrop-blur-sm animate-fade-in">
      <div className="bg-white rounded-2xl shadow-2xl w-full max-w-md mx-4 overflow-hidden">
        {/* Header */}
        <div className="flex items-center justify-between px-6 py-4 border-b border-slate-200" style={{ background: 'linear-gradient(135deg, #f0fdf4, #dcfce7)' }}>
          <div>
            <h2 className="font-bold text-slate-900 text-lg">New Forest Zone</h2>
            <p className="text-slate-500 text-sm">Configure your monitoring zone</p>
          </div>
          <button onClick={onClose} className="btn-ghost p-1">
            <svg className="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        </div>

        <form onSubmit={handleSubmit} className="p-6 space-y-4">
          {/* Zone Name */}
          <div>
            <label className="label">Zone Name *</label>
            <input
              type="text"
              className="input"
              placeholder="e.g. Western Amazon Sector A"
              value={form.name}
              onChange={(e) => setForm({ ...form, name: e.target.value })}
              required
            />
          </div>

          {/* Description */}
          <div>
            <label className="label">Description</label>
            <textarea
              className="input resize-none"
              rows={2}
              placeholder="Brief description of this monitoring zone…"
              value={form.description}
              onChange={(e) => setForm({ ...form, description: e.target.value })}
            />
          </div>

          {/* Thresholds */}
          <div className="grid grid-cols-2 gap-3">
            <div>
              <label className="label">NDVI Drop Threshold</label>
              <div className="flex items-center gap-2">
                <input
                  type="range" min="0.05" max="0.40" step="0.01"
                  value={form.ndvi_drop_threshold}
                  onChange={(e) => setForm({ ...form, ndvi_drop_threshold: e.target.value })}
                  className="flex-1 accent-forest-600"
                />
                <span className="text-sm font-bold text-forest-700 w-10 text-right">
                  {parseFloat(form.ndvi_drop_threshold).toFixed(2)}
                </span>
              </div>
            </div>
            <div>
              <label className="label">Confidence Threshold</label>
              <div className="flex items-center gap-2">
                <input
                  type="range" min="0.10" max="1.00" step="0.05"
                  value={form.confidence_threshold}
                  onChange={(e) => setForm({ ...form, confidence_threshold: e.target.value })}
                  className="flex-1 accent-forest-600"
                />
                <span className="text-sm font-bold text-forest-700 w-10 text-right">
                  {Math.round(form.confidence_threshold * 100)}%
                </span>
              </div>
            </div>
          </div>

          {/* Alert Emails */}
          <div>
            <label className="label">Alert Emails (comma-separated)</label>
            <input
              type="text"
              className="input"
              placeholder="alert@example.com, team@org.com"
              value={form.alert_emails}
              onChange={(e) => setForm({ ...form, alert_emails: e.target.value })}
            />
          </div>

          {/* Webhook */}
          <div>
            <label className="label">Webhook URL (optional)</label>
            <input
              type="url"
              className="input"
              placeholder="https://hooks.yourapp.com/deforestation"
              value={form.webhook_url}
              onChange={(e) => setForm({ ...form, webhook_url: e.target.value })}
            />
          </div>

          {/* GeoJSON preview */}
          <div className="bg-slate-50 rounded-lg p-3 text-xs text-slate-500">
            <span className="font-semibold text-slate-700">Polygon: </span>
            {geojson?.coordinates?.[0]?.length} vertices drawn
          </div>

          {/* Actions */}
          <div className="flex gap-3 pt-2">
            <button type="button" onClick={onClose} className="btn-secondary flex-1 justify-center">
              Cancel
            </button>
            <button type="submit" className="btn-primary flex-1 justify-center" disabled={loading}>
              {loading ? (
                <svg className="w-4 h-4 animate-spin" fill="none" viewBox="0 0 24 24">
                  <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                  <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                </svg>
              ) : (
                <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                </svg>
              )}
              {loading ? 'Creating…' : 'Create Zone'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}
