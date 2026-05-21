import { useEffect, useState } from 'react';
import { MapContainer, TileLayer, GeoJSON, useMap } from 'react-leaflet';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';
import useZones from '../../hooks/useZones';
import ZonePopup from './ZonePopup';
import { healthApi } from '../../services/api';
import { toast } from 'react-toastify';
import { INDIA_CENTER, INDIA_ZOOM, INDIA_MAX_BOUNDS } from '../../constants/map';

delete L.Icon.Default.prototype._getIconUrl;
L.Icon.Default.mergeOptions({
  iconRetinaUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-icon-2x.png',
  iconUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-icon.png',
  shadowUrl: 'https://cdnjs.cloudflare.com/ajax/libs/leaflet/1.9.4/images/marker-shadow.png',
});

const STATUS_COLORS = {
  healthy: '#16a34a',
  warning: '#d97706',
  critical: '#dc2626',
};

function ZoneLayers({ zones, onZoneClick }) {
  return zones.map((zone) => {
    const color = STATUS_COLORS[zone.status] || '#64748b';
    return (
      <GeoJSON
        key={zone._id}
        data={zone.geojson}
        style={() => ({
          color,
          fillColor: color,
          fillOpacity: 0.18,
          weight: 2.5,
          opacity: 1,
        })}
        onEachFeature={(feature, layer) => {
          layer.on({
            click: () => onZoneClick(zone),
            mouseover: (e) => {
              e.target.setStyle({ fillOpacity: 0.35, weight: 3.5 });
            },
            mouseout: (e) => {
              e.target.setStyle({ fillOpacity: 0.18, weight: 2.5 });
            },
          });
        }}
      />
    );
  });
}

/** Initial view: centered on India */
function MapIndiaDefault() {
  const map = useMap();
  useEffect(() => {
    map.setView(INDIA_CENTER, INDIA_ZOOM, { animate: false });
    map.setMaxBounds(INDIA_MAX_BOUNDS);
  }, [map]);
  return null;
}

/** Fit all zones; fallback to India if empty */
function MapAutoFit({ zones }) {
  const map = useMap();

  useEffect(() => {
    if (!zones.length) {
      map.setView(INDIA_CENTER, INDIA_ZOOM);
      return;
    }

    const bounds = L.latLngBounds([]);
    zones.forEach((zone) => {
      const ring = zone?.geojson?.coordinates?.[0];
      if (!Array.isArray(ring)) return;
      ring.forEach(([lng, lat]) => {
        if (typeof lat === 'number' && typeof lng === 'number') {
          bounds.extend([lat, lng]);
        }
      });
    });

    if (bounds.isValid()) {
      map.fitBounds(bounds, { padding: [40, 40], maxZoom: 10 });
    } else {
      map.setView(INDIA_CENTER, INDIA_ZOOM);
    }
  }, [map, zones]);

  return null;
}

export default function MapDashboard() {
  const { zones, zonesLoading, fetchZones } = useZones();
  const [selectedZone, setSelectedZone] = useState(null);
  const [connectivityLoading, setConnectivityLoading] = useState(false);
  const [connectivityResult, setConnectivityResult] = useState(null);

  useEffect(() => {
    fetchZones();
  }, [fetchZones]);

  const totalZones = zones.length;
  const criticalCount = zones.filter((z) => z.status === 'critical').length;
  const warningCount = zones.filter((z) => z.status === 'warning').length;
  const healthyCount = zones.filter((z) => z.status === 'healthy').length;

  const handleConnectivityCheck = async () => {
    const kukrail = zones.find((z) => z.name?.includes('Kukrail')) || zones[0];
    if (!kukrail) {
      toast.warn('No zones available to test connectivity.');
      return;
    }

    setConnectivityLoading(true);
    try {
      const res = await healthApi.satelliteCheck({
        geojson: kukrail.geojson,
        lookback_days: 30,
        require_copernicus_auth: true,
      });
      const result = res.data?.data || null;
      setConnectivityResult(result);
      if (result?.has_recent_scene) {
        toast.success('Satellite connectivity is healthy.');
      } else {
        toast.warn('Connectivity works, but no recent scene found.');
      }
    } catch (err) {
      setConnectivityResult(null);
      toast.error(err.message || 'Satellite connectivity check failed');
    } finally {
      setConnectivityLoading(false);
    }
  };

  return (
    <div className="flex flex-col h-full min-h-0 relative">
      <div className="flex flex-wrap items-center gap-2 sm:gap-4 px-3 sm:px-4 py-2 bg-white border-b border-slate-200 shrink-0">
        <div className="flex items-center gap-2 text-xs sm:text-sm">
          <span className="text-slate-500">Zones</span>
          <span className="font-bold text-slate-800">{totalZones}</span>
        </div>
        {healthyCount > 0 && (
          <div className="flex items-center gap-1.5 text-xs sm:text-sm">
            <span className="status-dot healthy" />
            <span className="text-green-700 font-medium">{healthyCount} OK</span>
          </div>
        )}
        {warningCount > 0 && (
          <div className="flex items-center gap-1.5 text-xs sm:text-sm">
            <span className="status-dot warning" />
            <span className="text-yellow-700 font-medium">{warningCount} Warn</span>
          </div>
        )}
        {criticalCount > 0 && (
          <div className="flex items-center gap-1.5 text-xs sm:text-sm">
            <span className="status-dot critical" />
            <span className="text-red-700 font-medium">{criticalCount} Critical</span>
          </div>
        )}
        <div className="w-full sm:w-auto sm:ml-auto flex">
          <button
            type="button"
            className="btn-secondary w-full sm:w-auto text-xs py-1.5"
            onClick={handleConnectivityCheck}
            disabled={connectivityLoading || zonesLoading || zones.length === 0}
          >
            {connectivityLoading ? 'Checking…' : 'Satellite check'}
          </button>
        </div>
      </div>

      {connectivityResult && (
        <div className="px-3 sm:px-4 py-2 bg-slate-100 border-b border-slate-200 text-[10px] sm:text-xs text-slate-700 shrink-0 overflow-x-auto">
          STAC: {connectivityResult.stac?.reachable ? 'OK' : 'fail'} · Copernicus:{' '}
          {connectivityResult.copernicus?.auth_ok ? 'OK' : 'fail'} · Scene:{' '}
          {connectivityResult.has_recent_scene ? 'yes' : 'no'}
        </div>
      )}

      <div className="flex-1 min-h-[240px] relative">
        {zonesLoading && (
          <div className="absolute top-3 left-1/2 -translate-x-1/2 z-[1000] bg-white shadow-lg rounded-full px-3 sm:px-4 py-2 text-xs sm:text-sm text-slate-600 flex items-center gap-2 max-w-[90vw]">
            <svg className="w-4 h-4 animate-spin text-forest-600 shrink-0" fill="none" viewBox="0 0 24 24">
              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
              <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
            </svg>
            Loading zones…
          </div>
        )}

        <MapContainer
          center={INDIA_CENTER}
          zoom={INDIA_ZOOM}
          className="w-full h-full min-h-[240px]"
          style={{ zIndex: 0 }}
          maxBounds={INDIA_MAX_BOUNDS}
          maxBoundsViscosity={0.85}
        >
          <TileLayer
            attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a>'
            url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
            maxZoom={18}
          />
          <MapIndiaDefault />
          <ZoneLayers zones={zones} onZoneClick={setSelectedZone} />
          <MapAutoFit zones={zones} />
        </MapContainer>

        {selectedZone && (
          <div className="absolute z-[1000] inset-x-3 bottom-3 sm:inset-auto sm:top-4 sm:right-4 sm:left-auto sm:bottom-auto sm:max-w-[min(100%,20rem)]">
            <ZonePopup zone={selectedZone} onClose={() => setSelectedZone(null)} />
          </div>
        )}

        {zones.length === 0 && !zonesLoading && (
          <div className="absolute bottom-20 sm:bottom-8 left-1/2 -translate-x-1/2 z-[500] pointer-events-none px-3 w-full max-w-sm">
            <div className="bg-white/95 rounded-xl shadow-lg px-4 py-3 text-center border border-slate-200">
              <div className="text-xl mb-1">🌳</div>
              <div className="font-semibold text-slate-800 text-sm">No zones yet</div>
              <div className="text-slate-500 text-xs mt-1">Restart API or enable predefined zones</div>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
