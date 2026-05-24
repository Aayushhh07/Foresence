import { useEffect, useState } from 'react';
import { toast } from 'react-toastify';
import useZones from '../../hooks/useZones';
import { notificationsApi } from '../../services/api';

export default function EmailReportPanel() {
  const { zones } = useZones();
  const [selected, setSelected] = useState({});
  const [recipients, setRecipients] = useState('');
  const [sending, setSending] = useState(false);
  const [emailStatus, setEmailStatus] = useState(null);

  useEffect(() => {
    const initial = {};
    zones.forEach((z) => {
      initial[z._id] = true;
    });
    setSelected(initial);
  }, [zones]);

  useEffect(() => {
    notificationsApi
      .emailStatus()
      .then((res) => {
        const data = res.data?.data;
        setEmailStatus(data);
        if (data?.global_recipients?.length && !recipients) {
          setRecipients(data.global_recipients.join(', '));
        }
      })
      .catch(() => setEmailStatus({ configured: false }));
  }, []);

  const toggleZone = (id) => {
    setSelected((prev) => ({ ...prev, [id]: !prev[id] }));
  };

  const toggleAll = (checked) => {
    const next = {};
    zones.forEach((z) => {
      next[z._id] = checked;
    });
    setSelected(next);
  };

  const selectedIds = zones.filter((z) => selected[z._id]).map((z) => z._id);

  const handleSend = async () => {
    if (!selectedIds.length) {
      toast.warn('Select at least one zone.');
      return;
    }
    const emails = recipients
      .split(',')
      .map((e) => e.trim())
      .filter(Boolean);
    if (!emails.length) {
      toast.warn('Enter at least one recipient email.');
      return;
    }

    setSending(true);
    try {
      const res = await notificationsApi.sendZoneReport({
        zone_ids: selectedIds,
        recipients: emails,
      });
      toast.success(res.data?.message || 'Report sent successfully');
    } catch (err) {
      toast.error(err.message || 'Failed to send report');
    } finally {
      setSending(false);
    }
  };

  return (
    <div className="card p-4 sm:p-5 space-y-4">
      <div>
        <h3 className="font-bold text-slate-800">Email health report</h3>
        <p className="text-xs text-slate-500 mt-1 leading-relaxed">
          Send a summary for selected forests: health score, status, latest NDVI, new alerts, and
          last scan image. Deforestation alerts are also emailed automatically when detected.
        </p>
      </div>

      <div
        className={`rounded-lg px-3 py-2 text-xs ${
          emailStatus?.configured
            ? 'bg-green-50 text-green-800 border border-green-200'
            : 'bg-amber-50 text-amber-900 border border-amber-200'
        }`}
      >
        {emailStatus?.configured ? (
          <>
            <strong>Email ready</strong> via {emailStatus.provider || 'resend'}. Auto-alerts:{' '}
            {emailStatus.auto_email_on_alert ? 'enabled' : 'disabled'}.
          </>
        ) : (
          <>
            <strong>Email not configured.</strong> Add <code className="bg-white/60 px-1 rounded">RESEND_API_KEY</code> and{' '}
            <code className="bg-white/60 px-1 rounded">ALERT_FROM_EMAIL</code> to backend .env
            (free at <a href="https://resend.com" className="underline" target="_blank" rel="noreferrer">resend.com</a>).
          </>
        )}
      </div>

      <div>
        <label className="label">Recipients (comma-separated)</label>
        <input
          type="text"
          className="input"
          placeholder="ranger@forest.gov, analyst@org.in"
          value={recipients}
          onChange={(e) => setRecipients(e.target.value)}
        />
        <p className="text-[11px] text-slate-400 mt-1">
          Also set <code>GLOBAL_ALERT_EMAILS</code> on the server for default recipients on auto-alerts.
        </p>
      </div>

      <div>
        <div className="flex items-center justify-between mb-2">
          <label className="label mb-0">Zones to include</label>
          <div className="flex gap-2 text-xs">
            <button type="button" className="text-forest-700 font-semibold" onClick={() => toggleAll(true)}>
              All
            </button>
            <span className="text-slate-300">|</span>
            <button type="button" className="text-slate-600 font-semibold" onClick={() => toggleAll(false)}>
              None
            </button>
          </div>
        </div>
        <div className="max-h-48 overflow-y-auto rounded-lg border border-slate-200 divide-y divide-slate-100">
          {zones.map((zone) => (
            <label
              key={zone._id}
              className="flex items-center gap-3 px-3 py-2.5 hover:bg-slate-50 cursor-pointer text-sm"
            >
              <input
                type="checkbox"
                checked={!!selected[zone._id]}
                onChange={() => toggleZone(zone._id)}
                className="rounded border-slate-300 text-forest-600 focus:ring-forest-500"
              />
              <span className="flex-1 min-w-0">
                <span className="font-medium text-slate-800 truncate block">{zone.name}</span>
                <span className="text-xs text-slate-500">
                  Health {zone.health_score ?? '—'} · {zone.status} · {zone.area_ha?.toFixed?.(0) ?? '—'} ha
                </span>
              </span>
            </label>
          ))}
        </div>
        <p className="text-xs text-slate-500 mt-2">{selectedIds.length} zone(s) selected</p>
      </div>

      <button
        type="button"
        className="btn-primary w-full sm:w-auto justify-center"
        disabled={sending || !emailStatus?.configured || !selectedIds.length}
        onClick={handleSend}
      >
        {sending ? 'Sending report…' : `📧 Email report for ${selectedIds.length} zone(s)`}
      </button>
    </div>
  );
}
