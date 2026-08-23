/**
 * useDemoData — provides data to all pages.
 *
 * This now fetches from the real API via React Query.
 * Falls back to the local fixtures if the API is unreachable
 * (so the frontend still works standalone for demo purposes).
 */

import { useQuery } from '@tanstack/react-query';
import { api } from '@/lib/api';
import { venues as seedVenues, incidents as seedIncidents, actions as seedActions, evidence as seedEvidence, scoreHistory as seedScoreHistory } from '@/data/fixtures';
import type { ActionItem, EvidenceItem, Incident, ScorePoint, Venue } from '@/types';

// Map API DTOs to the frontend types the pages expect
function mapVenues(data: Awaited<ReturnType<typeof api.getVenues>>): Venue[] {
  return data.venues.map((v) => ({
    id: v.slug,
    name: v.name,
    type: v.venue_type,
    location: v.location,
    capacity: v.capacity,
    score: v.score ?? 0,
    delta: v.delta ?? 0,
    risk: (v.risk as Venue['risk']) ?? 'Low',
    review: v.review ?? 'Healthy',
    initials: v.name.split(' ').map((w) => w[0]).join('').slice(0, 2).toUpperCase(),
  }));
}

function mapIncidents(data: Awaited<ReturnType<typeof api.getVenueIncidents>>): Incident[] {
  return data.incidents.map((i) => ({
    id: i.ref_code,
    date: new Date(i.occurred_at).toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' }),
    time: new Date(i.occurred_at).toLocaleTimeString('en-US', { hour: 'numeric', minute: '2-digit', hour12: true }),
    title: i.title,
    type: i.incident_type,
    severity: i.severity as Incident['severity'],
    status: i.status,
    location: i.location,
    people: i.people,
    evidence: i.evidence_completeness,
    summary: i.summary,
  }));
}

function mapActions(data: Awaited<ReturnType<typeof api.getVenueActions>>): ActionItem[] {
  return data.actions.map((a) => ({
    id: a.id.slice(0, 8),
    title: a.title,
    incident: 'INC-1042', // simplified for now
    owner: a.owner,
    due: a.due,
    priority: a.priority as ActionItem['priority'],
    status: a.status as ActionItem['status'],
    proof: a.proof_description ?? '',
  }));
}

function mapEvidence(data: Awaited<ReturnType<typeof api.getVenueEvidence>>): EvidenceItem[] {
  return data.evidence.map((e) => ({
    id: e.id.slice(0, 8),
    label: e.label,
    kind: e.kind,
    status: e.status as EvidenceItem['status'],
    detail: e.detail ?? '',
    updated: 'From database',
  }));
}

function mapScoreHistory(data: Awaited<ReturnType<typeof api.getVenueScoreHistory>>): ScorePoint[] {
  const months = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec'];
  return data.snapshots.map((s) => ({
    month: months[new Date(s.calculated_at).getMonth()],
    score: s.score,
  }));
}

export function useDemoData() {
  const venuesQuery = useQuery({
    queryKey: ['venues'],
    queryFn: () => api.getVenues(),
    retry: 1,
    staleTime: 30_000,
  });

  const incidentsQuery = useQuery({
    queryKey: ['incidents', 'moonlight'],
    queryFn: () => api.getVenueIncidents('moonlight'),
    retry: 1,
    staleTime: 30_000,
  });

  const actionsQuery = useQuery({
    queryKey: ['actions', 'moonlight'],
    queryFn: () => api.getVenueActions('moonlight'),
    retry: 1,
    staleTime: 30_000,
  });

  const evidenceQuery = useQuery({
    queryKey: ['evidence', 'moonlight'],
    queryFn: () => api.getVenueEvidence('moonlight'),
    retry: 1,
    staleTime: 30_000,
  });

  const scoreQuery = useQuery({
    queryKey: ['scoreHistory', 'moonlight'],
    queryFn: () => api.getVenueScoreHistory('moonlight'),
    retry: 1,
    staleTime: 30_000,
  });

  // Use API data if available, fall back to local fixtures
  const venues = venuesQuery.data ? mapVenues(venuesQuery.data) : seedVenues;
  const incidents = incidentsQuery.data ? mapIncidents(incidentsQuery.data) : seedIncidents;
  const actions = actionsQuery.data ? mapActions(actionsQuery.data) : seedActions;
  const evidence = evidenceQuery.data ? mapEvidence(evidenceQuery.data) : seedEvidence;
  const scoreHistory = scoreQuery.data ? mapScoreHistory(scoreQuery.data) : seedScoreHistory;

  // Keep the mutation functions as no-ops for now (Step 2 will add real mutations)
  const updateAction = (_id: string, _patch: Partial<ActionItem>) => {};
  const updateEvidence = (_id: string, _patch: Partial<EvidenceItem>) => {};
  const addIncident = (_incident: Incident) => {};

  return { venues, incidents, actions, evidence, scoreHistory, updateAction, updateEvidence, addIncident };
}
