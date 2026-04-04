import { Routes, Route, Navigate } from 'react-router-dom';
import { useEffect } from 'react';
import { ToastContainer } from 'react-toastify';
import 'react-toastify/dist/ReactToastify.css';

import Sidebar from './components/Layout/Sidebar';
import Header from './components/Layout/Header';
import StatusBar from './components/Layout/StatusBar';
import MapDashboard from './components/Map/MapDashboard';
import AlertCenter from './components/Alerts/AlertCenter';
import AnalyticsPage from './pages/AnalyticsPage';
import SettingsPage from './pages/SettingsPage';

import useWebSocket from './hooks/useWebSocket';
import { useZones } from './hooks/useZones';
import { alertsApi, healthApi } from './services/api';
import useAppStore from './store/appStore';

function AppContent() {
  const { fetchZones } = useZones();
  const { setAlerts, setSystemHealth, setLastScanAt } = useAppStore();

  // Initialize WebSocket connection
  useWebSocket();

  // Load initial data on mount
  useEffect(() => {
    fetchZones();

    // Load recent alerts
    alertsApi.list({ limit: 50 })
      .then((res) => {
        const data = res.data.data;
        setAlerts(data?.alerts || [], data?.total || 0);
      })
      .catch((err) => console.error('Initial alerts load failed:', err.message));

    // Load system health
    healthApi.check()
      .then((res) => {
        const data = res.data.data;
        setSystemHealth(data);
        if (data?.last_scan_at) setLastScanAt(data.last_scan_at);
      })
      .catch((err) => console.error('Health check failed:', err.message));
  }, []);

  return (
    <div className="flex h-screen overflow-hidden bg-slate-50">
      {/* Sidebar */}
      <Sidebar />

      {/* Main content */}
      <div className="flex-1 flex flex-col min-w-0 overflow-hidden">
        <Header />

        <main className="flex-1 overflow-hidden">
          <Routes>
            <Route path="/" element={<MapDashboard />} />
            <Route path="/alerts" element={<AlertCenter />} />
            <Route path="/analytics" element={<AnalyticsPage />} />
            <Route path="/settings" element={<SettingsPage />} />
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </main>

        <StatusBar />
      </div>

      {/* Toast notifications */}
      <ToastContainer
        position="top-right"
        autoClose={5000}
        hideProgressBar={false}
        newestOnTop
        closeOnClick
        rtl={false}
        pauseOnFocusLoss
        draggable
        pauseOnHover
        theme="light"
      />
    </div>
  );
}

export default function App() {
  return <AppContent />;
}
