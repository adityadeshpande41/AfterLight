/**
 * React Query hooks for the Afterlight API.
 * These replace the localStorage-based useDemoData hook.
 */

import { useQuery } from '@tanstack/react-query';
import { api } from '@/lib/api';

export function useVenues() {
  return useQuery({
    queryKey: ['venues'],
    queryFn: () => api.getVenues(),
    select: (data) => data.venues,
  });
}

export function useVenue(id: string) {
  return useQuery({
    queryKey: ['venue', id],
    queryFn: () => api.getVenue(id),
    enabled: !!id,
  });
}

export function useVenueIncidents(venueId: string) {
  return useQuery({
    queryKey: ['incidents', venueId],
    queryFn: () => api.getVenueIncidents(venueId),
    select: (data) => data.incidents,
    enabled: !!venueId,
  });
}

export function useIncident(id: string) {
  return useQuery({
    queryKey: ['incident', id],
    queryFn: () => api.getIncident(id),
    enabled: !!id,
  });
}

export function useVenueScore(venueId: string) {
  return useQuery({
    queryKey: ['score', venueId],
    queryFn: () => api.getVenueScore(venueId),
    enabled: !!venueId,
  });
}

export function useVenueScoreHistory(venueId: string) {
  return useQuery({
    queryKey: ['scoreHistory', venueId],
    queryFn: () => api.getVenueScoreHistory(venueId),
    select: (data) => data.snapshots,
    enabled: !!venueId,
  });
}

export function useVenueActions(venueId: string) {
  return useQuery({
    queryKey: ['actions', venueId],
    queryFn: () => api.getVenueActions(venueId),
    select: (data) => data.actions,
    enabled: !!venueId,
  });
}

export function useVenueEvidence(venueId: string) {
  return useQuery({
    queryKey: ['evidence', venueId],
    queryFn: () => api.getVenueEvidence(venueId),
    select: (data) => data.evidence,
    enabled: !!venueId,
  });
}
