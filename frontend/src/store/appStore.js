import { create } from 'zustand';

const useAppStore = create((set, get) => ({
  // ─── Zones ────────────────────────────────────────────────────────
  zones: [],
  zonesLoading: false,
  zonesError: null,

  setZones: (zones) => set({ zones }),
  setZonesLoading: (loading) => set({ zonesLoading: loading }),
  setZonesError: (error) => set({ zonesError: error }),

  addZone: (zone) => set((state) => ({ zones: [zone, ...state.zones] })),
  updateZone: (id, updates) =>
    set((state) => ({
      zones: state.zones.map((z) => (z._id === id ? { ...z, ...updates } : z)),
    })),
  removeZone: (id) =>
    set((state) => ({ zones: state.zones.filter((z) => z._id !== id) })),

  // ─── Alerts ───────────────────────────────────────────────────────
  alerts: [],
  alertsTotal: 0,
  alertsLoading: false,
  alertsError: null,
  activeAlertFilters: { severity: '', zone_id: '', status: 'new' },

  setAlerts: (alerts, total) => set({ alerts, alertsTotal: total }),
  setAlertsLoading: (loading) => set({ alertsLoading: loading }),
  setAlertsError: (error) => set({ alertsError: error }),
  setAlertFilters: (filters) =>
    set((state) => ({
      activeAlertFilters: { ...state.activeAlertFilters, ...filters },
    })),

  prependAlert: (alert) =>
    set((state) => ({
      alerts: [alert, ...state.alerts],
      alertsTotal: state.alertsTotal + 1,
    })),

  updateAlertStatus: (id, status, notes) =>
    set((state) => ({
      alerts: state.alerts.map((a) =>
        a._id === id ? { ...a, status, notes: notes || a.notes } : a
      ),
    })),

  // ─── Snapshots ────────────────────────────────────────────────────
  snapshots: [],
  snapshotsLoading: false,
  selectedZoneId: null,

  setSnapshots: (snapshots) => set({ snapshots }),
  setSnapshotsLoading: (loading) => set({ snapshotsLoading: loading }),
  setSelectedZoneId: (id) => set({ selectedZoneId: id }),

  // ─── System Health ────────────────────────────────────────────────
  systemHealth: null,
  lastScanAt: null,
  wsConnected: false,

  setSystemHealth: (health) => set({ systemHealth: health }),
  setLastScanAt: (time) => set({ lastScanAt: time }),
  setWsConnected: (connected) => set({ wsConnected: connected }),

  // ─── UI State ─────────────────────────────────────────────────────
  sidebarCollapsed: false,
  setSidebarCollapsed: (collapsed) => set({ sidebarCollapsed: collapsed }),

  // ─── Computed getters ─────────────────────────────────────────────
  getNewAlertsCount: () =>
    get().alerts.filter((a) => a.status === 'new').length,

  getZoneById: (id) => get().zones.find((z) => z._id === id),
}));

export default useAppStore;
