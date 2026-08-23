import { actions as seedActions, evidence as seedEvidence, incidents as seedIncidents, scoreHistory as seedScoreHistory, venues as seedVenues } from '@/data/fixtures';
import type { ActionItem, EvidenceItem, Incident, ScorePoint, Venue } from '@/types';

const key = 'afterlight-demo-state';
type State = { venues: Venue[]; incidents: Incident[]; actions: ActionItem[]; evidence: EvidenceItem[]; scoreHistory: ScorePoint[]; };

const initial = (): State => ({ venues: structuredClone(seedVenues), incidents: structuredClone(seedIncidents), actions: structuredClone(seedActions), evidence: structuredClone(seedEvidence), scoreHistory: structuredClone(seedScoreHistory) });

let memory: State | null = null;
const read = (): State => {
  if (memory) return memory;
  try { const saved = localStorage.getItem(key); memory = saved ? JSON.parse(saved) as State : initial(); } catch { memory = initial(); }
  return memory;
};
const write = (state: State) => { memory = state; try { localStorage.setItem(key, JSON.stringify(state)); } catch { /* demo continues in memory */ } };

export const apiClient = {
  getState: (): State => read(),
  reset: () => { write(initial()); return read(); },
  updateAction: (id: string, patch: Partial<ActionItem>) => { const state = read(); state.actions = state.actions.map((item) => item.id === id ? { ...item, ...patch } : item); write(state); return state.actions.find((item) => item.id === id); },
  addIncident: (incident: Incident) => { const state = read(); state.incidents = [incident, ...state.incidents]; write(state); return incident; },
  updateEvidence: (id: string, patch: Partial<EvidenceItem>) => { const state = read(); state.evidence = state.evidence.map((item) => item.id === id ? { ...item, ...patch } : item); write(state); return state.evidence.find((item) => item.id === id); },
};