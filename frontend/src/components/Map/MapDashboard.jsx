import { useEffect, useState, useRef } from 'react';
import { MapContainer, TileLayer, GeoJSON, useMap } from 'react-leaflet';
import L from 'leaflet';
import 'leaflet/dist/leaflet.css';
import useZones from '../../hooks/useZones';
import useAppStore from '../../store/appStore';
import ZoneDrawer from './ZoneDrawer';
import ZonePopup from './ZonePopup';

// Fix Leaflet default icon
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

// ─── Drawing Control Component ──────────────────────────────────────
function DrawControl({ onPolygonDrawn }) {
  const map = useMap();
  const drawnItemsRef = useRef(new L.FeatureGroup());

  useEffect(() => {
    map.addLayer(drawnItemsRef.current);

    // Lazy-load leaflet-draw
    import('leaflet-draw').then(() => {
      const drawControl = new L.Control.Draw({
        position: 'topright',
        draw: {
          polygon: {
            allowIntersection: false,
            shapeOptions: { color: '#16a34a', fillOpacity: 0.15, weight: 2 },
            showArea: true,
          },
          polyline: false,
          rectangle: false,
          circle: false,
          marker: false,
          circlemarker: false,
        },
        edit: { featureGroup: drawnItemsRef.current, edit: false, remove: false },
      });
      map.addControl(drawControl);

      map.on(L.Draw.Event.CREATED, (e) => {
        const layer = e.layer;
        drawnItemsRef.current.clearLayers();
        drawnItemsRef.current.addLayer(layer);
        const geojson = layer.toGeoJSON().geometry;
        onPolygonDrawn(geojson);
      });
    });

    return () => {
      map.removeLayer(drawnItemsRef.current);
    };
  }, [map, onPolygonDrawn]);

  return null;
}

// ─── Zone Layer Component ───────────────────────────────────────────
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

// ─── Map Dashboard ──────────────────────────────────────────────────
export default function MapDashboard() {
  const { zones, zonesLoading, fetchZones } = useZones();
  const [drawnGeojson, setDrawnGeojson] = useState(null);
  const [selectedZone, setSelectedZone] = useState(null);
  const [popupPosition, setPopupPosition] = useState({ top: 64, left: 64 });

  useEffect(() => {
    fetchZones();
  }, [fetchZones]);

  const handlePolygonDrawn = (geojson) => {
    setDrawnGeojson(geojson);
  };

  const handleZoneClick = (zone) => {
    setSelectedZone(zone);
  };

  const handleZoneCreated = (zone) => {
    setDrawnGeojson(null);
    fetchZones();
  };

  const totalZones = zones.length;
  const criticalCount = zones.filter((z) => z.status === 'critical').length;
  const warningCount = zones.filter((z) => z.status === 'warning').length;
  const healthyCount = zones.filter((z) => z.status === 'healthy').length;

  return (
    <div className="flex flex-col h-full relative">
      {/* Stats bar */}
      <div className="flex items-center gap-4 px-4 py-2 bg-white border-b border-slate-200">
        <div className="flex items-center gap-2 text-sm">
          <span className="text-slate-500">Zones:</span>
          <span className="font-bold text-slate-800">{totalZones}</span>
        </div>
        {healthyCount > 0 && (
          <div className="flex items-center gap-1.5 text-sm">
            <span className="status-dot healthy" />
            <span className="text-green-700 font-medium">{healthyCount} Healthy</span>
          </div>
        )}
        {warningCount > 0 && (
          <div className="flex items-center gap-1.5 text-sm">
            <span className="status-dot warning" />
            <span className="text-yellow-700 font-medium">{warningCount} Warning</span>
          </div>
        )}
        {criticalCount > 0 && (
          <div className="flex items-center gap-1.5 text-sm">
            <span className="status-dot critical" />
            <span className="text-red-700 font-medium">{criticalCount} Critical</span>
          </div>
        )}
        <div className="ml-auto flex items-center gap-2 text-xs text-slate-500">
          <svg className="w-3.5 h-3.5 text-forest-600" fill="none" stroke="currentColor" viewBox="0 0 24 24">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15.232 5.232l3.536 3.536m-2.036-5.036a2.5 2.5 0 113.536 3.536L6.5 21.036H3v-3.572L16.732 3.732z" />
          </svg>
          Use the polygon tool (top-right) to draw a new monitoring zone
        </div>
      </div>

      {/* Map */}
      <div className="flex-1 relative">
        {zonesLoading && (
          <div className="absolute top-3 left-1/2 -translate-x-1/2 z-[1000] bg-white shadow-lg rounded-full px-4 py-2 text-sm text-slate-600 flex items-center gap-2">
            <svg className="w-4 h-4 animate-spin text-forest-600" fill="none" viewBox="0 0 24 24">
              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
              <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4z" />
            </svg>
            Loading zones…
          </div>
        )}

        <MapContainer
          center={[20.5937, 78.9629]}
          zoom={5}
          className="w-full h-full"
          style={{ zIndex: 0 }}
        >
          <TileLayer
            attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
            url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
            maxZoom={18}
          />

          <ZoneLayers zones={zones} onZoneClick={handleZoneClick} />
          <DrawControl onPolygonDrawn={handlePolygonDrawn} />
        </MapContainer>

        {/* Zone popup (custom, not Leaflet popup) */}
        {selectedZone && (
          <div className="absolute top-4 right-4 z-[1000]">
            <ZonePopup
              zone={selectedZone}
              onClose={() => setSelectedZone(null)}
            />
          </div>
        )}

        {/* Empty state */}
        {zones.length === 0 && !zonesLoading && (
          <div className="absolute bottom-8 left-1/2 -translate-x-1/2 z-[500] pointer-events-none">
            <div className="bg-white/95 rounded-xl shadow-lg px-5 py-4 text-center border border-slate-200">
              <div className="text-2xl mb-1">🌳</div>
              <div className="font-semibold text-slate-800 text-sm">No zones yet</div>
              <div className="text-slate-500 text-xs mt-1">Use the polygon tool to draw your first monitoring zone</div>
            </div>
          </div>
        )}
      </div>

      {/* Zone creation modal */}
      {drawnGeojson && (
        <ZoneDrawer
          geojson={drawnGeojson}
          onClose={() => setDrawnGeojson(null)}
          onSuccess={handleZoneCreated}
        />
      )}
    </div>
  );
}
