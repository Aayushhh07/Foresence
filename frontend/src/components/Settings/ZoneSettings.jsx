import { useState } from 'react';
import useZones from '../../hooks/useZones';
import useAppStore from '../../store/appStore';
import { toast } from 'react-toastify';

export default function ZoneSettings() {
  const { zones, editZone, deleteZone, triggerScan } = useZones();
  const [editingId, setEditingId] = useState(null);
  const [editForm, setEditForm] = useState({});
  const [scanningId, setScanningId] = useState(null);
  const [deletingId, setDeletingId] = useState(null);

  const startEdit = (zone) => {
    setEditingId(zone._id);
    setEditForm({
      name: zone.name,
      description: zone.description || '',
      ndvi_drop_threshold: zone.ndvi_drop_threshold,
      confidence_threshold: zone.confidence_threshold,
      alert_emails: (zone.alert_emails || []).join(', '),
      webhook_url: zone.webhook_url || '',
      active: zone.active,
    });
  };

  const cancelEdit = () => {
    setEditingId(null);
    setEditForm({});
  };

  const saveEdit = async (zoneId) => {
    try {
      const emails = editForm.alert_emails
        ? editForm.alert_emails.split(',').map((e) => e.trim()).filter(Boolean)
        : [];

      await editZone(zoneId, {
        name: editForm.name,
        description: editForm.description,
        ndvi_drop_threshold: parseFloat(editForm.ndvi_drop_threshold),
        confidence_threshold: parseFloat(editForm.confidence_threshold),
        alert_emails: emails,
        webhook_url: editForm.webhook_url || null,
        active: editForm.active,
      });

      toast.success('Zone settings saved');
      setEditingId(null);
    } catch (err) {
      toast.error(err.message);
    }
  };

  const handleToggleActive = async (zone) => {
    try {
      await editZone(zone._id, { active: !zone.active });
      toast.success(`Zone ${!zone.active ? 'activated' : 'deactivated'}`);
    } catch (err) {
      toast.error(err.message);
    }
  };

  const handleDelete = async (zone) => {
    if (!window.confirm(`Delete zone "${zone.name}"? This will also delete all related alerts.`)) return;
    setDeletingId(zone._id);
    try {
      await deleteZone(zone._id);
      toast.success(`Zone "${zone.name}" deleted`);
    } catch (err) {
      toast.error(err.message);
    } finally {
      setDeletingId(null);
    }
  };

  const handleScan = async (zone) => {
    setScanningId(zone._id);
    try {
      await triggerScan(zone._id);
      toast.info(`Scan triggered for "${zone.name}". Results in a few minutes.`);
    } catch (err) {
      toast.error(err.message);
    } finally {
      setScanningId(null);
    }
  };

  if (zones.length === 0) {
    return (
      <div className="flex flex-col items-center justify-center h-48 text-center text-slate-500">
        <div className="text-4xl mb-3">🗺️</div>
        <div className="font-semibold text-slate-700">No zones configured</div>
        <div className="text-sm mt-1">Go to the Map and draw a polygon to create your first monitoring zone.</div>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      {zones.map((zone) => {
        const isEditing = editingId === zone._id;
        const isScanning = scanningId === zone._id;
        const isDeleting = deletingId === zone._id;

        const statusColor = zone.status === 'healthy' ? '#16a34a'
          : zone.status === 'warning' ? '#d97706' : '#dc2626';

        return (
          <div key={zone._id} className="card p-5">
            {/* Zone header */}
            <div className="flex items-start justify-between gap-3 mb-4">
              <div className="flex items-center gap-3">
                <div
                  className="w-3 h-3 rounded-full flex-shrink-0"
                  style={{ background: statusColor, boxShadow: `0 0 6px ${statusColor}80` }}
                />
                {isEditing ? (
                  <input
                    className="input !py-1 !text-base font-bold"
                    value={editForm.name}
                    onChange={(e) => setEditForm({ ...editForm, name: e.target.value })}
                  />
                ) : (
                  <div>
                    <div className="font-bold text-slate-900">{zone.name}</div>
                    <div className="text-xs text-slate-500">
                      {zone.area_ha?.toFixed(1)} ha · {zone.status} · Health: {zone.health_score}/100
                    </div>
                  </div>
                )}
              </div>

              {/* Actions */}
              <div className="flex items-center gap-2 flex-shrink-0">
                {/* Active toggle */}
                <button
                  onClick={() => handleToggleActive(zone)}
                  className={`relative w-10 h-5 rounded-full transition-colors ${zone.active ? 'bg-forest-600' : 'bg-slate-300'}`}
                  title={zone.active ? 'Deactivate' : 'Activate'}
                >
                  <span
                    className={`absolute top-0.5 w-4 h-4 bg-white rounded-full shadow transition-transform ${zone.active ? 'translate-x-5' : 'translate-x-0.5'}`}
                  />
                </button>

                {/* Scan button */}
                <button
                  onClick={() => handleScan(zone)}
                  disabled={isScanning || !zone.active}
                  className="btn-secondary text-xs py-1 px-2"
                  title="Trigger manual scan"
                >
                  {isScanning ? (
                    <svg className="w-3.5 h-3.5 animate-spin" fill="none" viewBox="0 0 24 24">
                      <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
                      <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
                    </svg>
                  ) : (
                    <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15" />
                    </svg>
                  )}
                  Scan
                </button>

                {/* Edit / Save */}
                {isEditing ? (
                  <>
                    <button onClick={() => saveEdit(zone._id)} className="btn-primary text-xs py-1 px-3">Save</button>
                    <button onClick={cancelEdit} className="btn-secondary text-xs py-1 px-2">Cancel</button>
                  </>
                ) : (
                  <button onClick={() => startEdit(zone)} className="btn-secondary text-xs py-1 px-2">
                    <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M11 5H6a2 2 0 00-2 2v11a2 2 0 002 2h11a2 2 0 002-2v-5m-1.414-9.414a2 2 0 112.828 2.828L11.828 15H9v-2.828l8.586-8.586z" />
                    </svg>
                    Edit
                  </button>
                )}

                {/* Delete */}
                <button
                  onClick={() => handleDelete(zone)}
                  disabled={isDeleting}
                  className="btn-danger text-xs py-1 px-2"
                >
                  {isDeleting ? '…' : (
                    <svg className="w-3.5 h-3.5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16" />
                    </svg>
                  )}
                </button>
              </div>
            </div>

            {/* Edit form */}
            {isEditing && (
              <div className="space-y-3 pt-3 border-t border-slate-100">
                <div>
                  <label className="label">Description</label>
                  <input className="input text-sm" value={editForm.description}
                    onChange={(e) => setEditForm({ ...editForm, description: e.target.value })} />
                </div>
                <div className="grid grid-cols-2 gap-3">
                  <div>
                    <label className="label">NDVI Drop Threshold</label>
                    <div className="flex items-center gap-2">
                      <input type="range" min="0.05" max="0.40" step="0.01"
                        value={editForm.ndvi_drop_threshold}
                        onChange={(e) => setEditForm({ ...editForm, ndvi_drop_threshold: e.target.value })}
                        className="flex-1 accent-forest-600"
                      />
                      <span className="text-sm font-bold w-10 text-forest-700">
                        {parseFloat(editForm.ndvi_drop_threshold).toFixed(2)}
                      </span>
                    </div>
                  </div>
                  <div>
                    <label className="label">Confidence Threshold</label>
                    <div className="flex items-center gap-2">
                      <input type="range" min="0.10" max="1.00" step="0.05"
                        value={editForm.confidence_threshold}
                        onChange={(e) => setEditForm({ ...editForm, confidence_threshold: e.target.value })}
                        className="flex-1 accent-forest-600"
                      />
                      <span className="text-sm font-bold w-10 text-forest-700">
                        {Math.round(editForm.confidence_threshold * 100)}%
                      </span>
                    </div>
                  </div>
                </div>
                <div>
                  <label className="label">Alert Emails (comma-separated)</label>
                  <input className="input text-sm" value={editForm.alert_emails}
                    onChange={(e) => setEditForm({ ...editForm, alert_emails: e.target.value })}
                    placeholder="email1@example.com, email2@example.com"
                  />
                </div>
                <div>
                  <label className="label">Webhook URL</label>
                  <input className="input text-sm" value={editForm.webhook_url}
                    onChange={(e) => setEditForm({ ...editForm, webhook_url: e.target.value })}
                    placeholder="https://hooks.yourapp.com/..."
                  />
                </div>
              </div>
            )}

            {/* Stats row (non-editing) */}
            {!isEditing && (
              <div className="flex gap-4 text-xs text-slate-500">
                <span>NDVI threshold: <strong className="text-slate-700">{zone.ndvi_drop_threshold}</strong></span>
                <span>Confidence: <strong className="text-slate-700">{Math.round(zone.confidence_threshold * 100)}%</strong></span>
                <span>Emails: <strong className="text-slate-700">{zone.alert_emails?.length || 0}</strong></span>
                <span>Scanned: <strong className="text-slate-700">{zone.last_scanned_at ? new Date(zone.last_scanned_at).toLocaleDateString() : 'Never'}</strong></span>
              </div>
            )}
          </div>
        );
      })}
    </div>
  );
}
