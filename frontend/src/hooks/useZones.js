import { useCallback } from 'react';
import { zonesApi } from '../services/api';
import useAppStore from '../store/appStore';

export function useZones() {
  const {
    zones, zonesLoading, zonesError,
    setZones, setZonesLoading, setZonesError,
    addZone, updateZone, removeZone,
  } = useAppStore();

  const fetchZones = useCallback(async () => {
    setZonesLoading(true);
    setZonesError(null);
    try {
      const res = await zonesApi.list();
      setZones(res.data.data || []);
    } catch (err) {
      setZonesError(err.message);
    } finally {
      setZonesLoading(false);
    }
  }, [setZones, setZonesLoading, setZonesError]);

  const createZone = useCallback(async (zoneData) => {
    const res = await zonesApi.create(zoneData);
    const zone = res.data.data;
    addZone(zone);
    return zone;
  }, [addZone]);

  const editZone = useCallback(async (id, updates) => {
    const res = await zonesApi.update(id, updates);
    const zone = res.data.data;
    updateZone(id, zone);
    return zone;
  }, [updateZone]);

  const deleteZone = useCallback(async (id) => {
    await zonesApi.delete(id);
    removeZone(id);
  }, [removeZone]);

  const triggerScan = useCallback(async (id) => {
    const res = await zonesApi.scan(id);
    return res.data;
  }, []);

  return {
    zones, zonesLoading, zonesError,
    fetchZones, createZone, editZone, deleteZone, triggerScan,
  };
}

export default useZones;
