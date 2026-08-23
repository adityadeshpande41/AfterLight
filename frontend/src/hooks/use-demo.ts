import { useCallback, useEffect, useState } from 'react';
import { apiClient } from '@/lib/apiClient';
import type { ActionItem, EvidenceItem, Incident } from '@/types';

export function useDemoData() {
  const [state, setState] = useState(apiClient.getState);
  useEffect(() => { const onStorage = () => setState(apiClient.getState()); window.addEventListener('storage', onStorage); return () => window.removeEventListener('storage', onStorage); }, []);
  const refresh = useCallback(() => setState({ ...apiClient.getState() }), []);
  const updateAction = useCallback((id: string, patch: Partial<ActionItem>) => { apiClient.updateAction(id, patch); refresh(); }, [refresh]);
  const updateEvidence = useCallback((id: string, patch: Partial<EvidenceItem>) => { apiClient.updateEvidence(id, patch); refresh(); }, [refresh]);
  const addIncident = useCallback((incident: Incident) => { apiClient.addIncident(incident); refresh(); }, [refresh]);
  return { ...state, refresh, updateAction, updateEvidence, addIncident };
}