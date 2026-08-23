/**
 * API client — fetches from the FastAPI backend via Vite proxy.
 * All calls go to /api/* which Vite proxies to http://localhost:8000.
 */

const BASE = '/api';

async function fetchJSON<T>(path: string): Promise<T> {
  const res = await fetch(`${BASE}${path}`);
  if (!res.ok) {
    throw new Error(`API error ${res.status}: ${res.statusText}`);
  }
  return res.json();
}

async function mutateJSON<T>(path: string, method: string, body: unknown): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    method,
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(body),
  });
  if (!res.ok) {
    throw new Error(`API error ${res.status}: ${res.statusText}`);
  }
  return res.json();
}

// --- Request body types ---

export interface CreateIncidentBody {
  title: string;
  incident_type: string;
  severity?: string;
  location: string;
  occurred_at?: string;
  people?: string[];
  summary: string;
}

export interface UpdateActionBody {
  status?: string;
  proof_description?: string;
}

export interface UpdateEvidenceBody {
  status?: string;
  detail?: string;
}

export interface UploadURLResponse {
  upload_url: string;
  object_key: string;
  expires_in: number;
}

// --- Types matching backend Pydantic schemas ---

export interface VenueDTO {
  id: string;
  name: string;
  slug: string;
  venue_type: string;
  location: string;
  capacity: number;
  created_at: string;
  score: number | null;
  delta: number | null;
  risk: string | null;
  review: string | null;
}

export interface IncidentDTO {
  id: string;
  venue_id: string;
  ref_code: string;
  title: string;
  incident_type: string;
  severity: string;
  status: string;
  location: string;
  occurred_at: string;
  people: string[];
  summary: string;
  evidence_completeness: number;
}

export interface ActionItemDTO {
  id: string;
  incident_id: string;
  title: string;
  owner: string;
  priority: string;
  status: string;
  due: string;
  proof_description: string | null;
  completed_at: string | null;
}

export interface EvidenceItemDTO {
  id: string;
  incident_id: string;
  label: string;
  kind: string;
  status: string;
  detail: string | null;
  object_key: string | null;
  file_hash: string | null;
}

export interface ScoreSnapshotDTO {
  id: string;
  venue_id: string;
  score: number;
  risk_index: number;
  factors: Record<string, number>;
  calculated_at: string;
}

// --- API functions ---

export const api = {
  getVenues: () => fetchJSON<{ venues: VenueDTO[] }>('/venues'),
  getVenue: (id: string) => fetchJSON<VenueDTO>(`/venues/${id}`),
  getVenueIncidents: (venueId: string) =>
    fetchJSON<{ incidents: IncidentDTO[] }>(`/venues/${venueId}/incidents`),
  getIncident: (id: string) => fetchJSON<IncidentDTO>(`/incidents/${id}`),
  getVenueScore: (venueId: string) =>
    fetchJSON<ScoreSnapshotDTO>(`/venues/${venueId}/score`),
  getVenueScoreHistory: (venueId: string) =>
    fetchJSON<{ snapshots: ScoreSnapshotDTO[] }>(`/venues/${venueId}/score/history`),
  getVenueActions: (venueId: string) =>
    fetchJSON<{ actions: ActionItemDTO[] }>(`/venues/${venueId}/actions`),
  getVenueEvidence: (venueId: string) =>
    fetchJSON<{ evidence: EvidenceItemDTO[] }>(`/venues/${venueId}/evidence`),

  // Write operations
  createIncident: (venueId: string, body: CreateIncidentBody) =>
    mutateJSON<IncidentDTO>(`/venues/${venueId}/incidents`, 'POST', body),
  updateAction: (actionId: string, body: UpdateActionBody) =>
    mutateJSON<ActionItemDTO>(`/actions/${actionId}`, 'PATCH', body),
  updateEvidence: (evidenceId: string, body: UpdateEvidenceBody) =>
    mutateJSON<EvidenceItemDTO>(`/evidence/${evidenceId}`, 'PATCH', body),

  // Upload flow
  requestUploadURL: (evidenceId: string, filename: string, contentType: string) =>
    mutateJSON<UploadURLResponse>('/uploads/request-url', 'POST', {
      evidence_id: evidenceId,
      filename,
      content_type: contentType,
    }),
  confirmUpload: (evidenceId: string, objectKey: string, fileHash?: string) =>
    mutateJSON<EvidenceItemDTO>('/uploads/confirm', 'POST', {
      evidence_id: evidenceId,
      object_key: objectKey,
      file_hash: fileHash,
    }),
};
