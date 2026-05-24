import { useEffect, useRef, useCallback } from 'react';
import { toast } from 'react-toastify';
import useAppStore from '../store/appStore';

const WS_URL = import.meta.env.VITE_WS_URL || 'ws://localhost:8000';
const MAX_RECONNECT_DELAY = 30000;

export function useWebSocket() {
  const wsRef = useRef(null);
  const reconnectTimeoutRef = useRef(null);
  const reconnectDelayRef = useRef(1000);
  const mountedRef = useRef(true);

  const { setWsConnected, prependAlert, updateZone } = useAppStore();

  const handleMessage = useCallback((event) => {
    try {
      const msg = JSON.parse(event.data);

      switch (msg.type) {
        case 'connected':
          console.log('[WS] Connected to Foresence real-time feed');
          break;

        case 'alert':
          // New deforestation alert received
          prependAlert({
            _id: msg.alert_id,
            zone_name: msg.zone_name,
            severity: msg.severity,
            confidence: msg.confidence,
            change_area_ha: msg.change_area_ha,
            detected_at: msg.detected_at,
            status: 'new',
            notified: true,
          });

          // Show toast notification
          const severityEmoji = {
            critical: '🔴', high: '🟠', medium: '🟡', low: '🔵'
          }[msg.severity] || '⚠️';

          toast.error(
            `${severityEmoji} Deforestation detected in ${msg.zone_name}`,
            {
              toastId: msg.alert_id,
              autoClose: 8000,
              position: 'top-right',
            }
          );
          break;

        case 'health_update':
          updateZone(msg.zone_id, {
            health_score: msg.health_score,
            status: msg.status,
          });
          break;

        case 'scan_complete':
          useAppStore.getState().setLastZoneScan({
            zone_id: msg.zone_id,
            zone_name: msg.zone_name,
            ndvi_mean: msg.ndvi_mean,
            at: Date.now(),
          });
          useAppStore.getState().setLastScanAt(new Date().toISOString());
          console.log(`[WS] Scan complete for zone: ${msg.zone_name}, NDVI: ${msg.ndvi_mean?.toFixed(3)}`);
          break;

        case 'pong':
          break;

        default:
          console.log('[WS] Unknown message type:', msg.type);
      }
    } catch (e) {
      console.error('[WS] Failed to parse message:', e);
    }
  }, [prependAlert, updateZone]);

  const connect = useCallback(() => {
    if (!mountedRef.current) return;

    try {
      const ws = new WebSocket(`${WS_URL}/ws/alerts`);
      wsRef.current = ws;

      ws.onopen = () => {
        if (!mountedRef.current) { ws.close(); return; }
        console.log('[WS] Connection established');
        setWsConnected(true);
        reconnectDelayRef.current = 1000; // Reset backoff on success

        // Start keepalive ping every 30s
        const pingInterval = setInterval(() => {
          if (ws.readyState === WebSocket.OPEN) {
            ws.send(JSON.stringify({ type: 'ping' }));
          } else {
            clearInterval(pingInterval);
          }
        }, 30000);
        ws._pingInterval = pingInterval;
      };

      ws.onmessage = handleMessage;

      ws.onclose = (event) => {
        if (ws._pingInterval) clearInterval(ws._pingInterval);
        setWsConnected(false);
        if (!mountedRef.current) return;

        console.log(`[WS] Disconnected (code ${event.code}). Reconnecting in ${reconnectDelayRef.current}ms…`);

        reconnectTimeoutRef.current = setTimeout(() => {
          reconnectDelayRef.current = Math.min(
            reconnectDelayRef.current * 2,
            MAX_RECONNECT_DELAY
          );
          connect();
        }, reconnectDelayRef.current);
      };

      ws.onerror = (err) => {
        console.error('[WS] Error:', err);
      };
    } catch (e) {
      console.error('[WS] Failed to create WebSocket:', e);
      setWsConnected(false);
    }
  }, [handleMessage, setWsConnected]);

  useEffect(() => {
    mountedRef.current = true;
    connect();

    return () => {
      mountedRef.current = false;
      if (reconnectTimeoutRef.current) clearTimeout(reconnectTimeoutRef.current);
      if (wsRef.current) {
        if (wsRef.current._pingInterval) clearInterval(wsRef.current._pingInterval);
        wsRef.current.close(1000, 'Component unmounted');
      }
      setWsConnected(false);
    };
  }, [connect, setWsConnected]);

  return { connected: useAppStore((s) => s.wsConnected) };
}

export default useWebSocket;
