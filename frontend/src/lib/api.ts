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

export interface WorkflowToolCall {
  tool_name: string;
  arguments: Record<string, unknown>;
  result_summary: string;
  duration_ms: number;
}

export interface WorkflowStep {
  agent_name: string;
  duration_ms: number;
  tool_calls: WorkflowToolCall[];
  output_summary: string;
  error: string | null;
}

export interface WorkflowTrace {
  workflow_id: string;
  incident_id: string;
  total_duration_ms: number;
  total_tool_calls: number;
  total_llm_calls: number;
  steps: WorkflowStep[];
}

export interface WorkflowFinding {
  status: string;
  title: string;
  cite: string;
  urgency: string | null;
}

export interface WorkflowAction {
  title: string;
  owner: string;
  priority: string;
  due_description: string;
  required_proof: string;
  citation: string;
}

export interface WorkflowResult {
  status: string;
  incident_id: string;
  findings: WorkflowFinding[];
  action_plan_draft: WorkflowAction[];
  evidence_assessment: Record<string, unknown> | null;
  pattern_analysis: Record<string, unknown> | null;
  playbook_citations: Record<string, unknown>[];
  validation_result: Record<string, unknown> | null;
  is_valid: boolean;
  needs_human_review: boolean;
  errors: string[];
  trace: WorkflowTrace | null;
}

export interface ChatCitation {
  source: string;
  section: string | null;
  content_preview: string | null;
}

export interface ChatSuggestedAction {
  title: string;
  link: string | null;
}

export interface ChatResponseDTO {
  answer: string;
  citations: ChatCitation[];
  suggested_actions: ChatSuggestedAction[];
  is_cached: boolean;
  guardrail_triggered: boolean;
  guardrail_reason: string | null;
}

export interface UnderwritingResult {
  venue: Record<string, unknown> | null;
  historical_risk: Record<string, unknown> | null;
  control_status: Record<string, unknown> | null;
  guidelines: Record<string, unknown>[];
  draft: Record<string, unknown> | null;
  posture: string | null;
  forced_referral: boolean;
  referral_reasons: string[];
  errors: string[];
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

  // Workflow
  analyzeIncident: (incidentId: string) =>
    mutateJSON<WorkflowResult>(`/workflows/incidents/${incidentId}/analyze`, 'POST', {}),

  // Decisions (human-in-the-loop)
  createDecision: (body: { incident_id: string; decision: string; reviewer: string; note?: string; action_plan?: WorkflowAction[] }) =>
    mutateJSON<{ id: string; decision: string }>('/decisions', 'POST', body),

  // Chat (Risk Copilot)
  chat: (message: string, venueId: string = 'moonlight') =>
    mutateJSON<ChatResponseDTO>('/chat', 'POST', { message, venue_id: venueId }),

  // Underwriting
  generateUnderwriting: (venueId: string) =>
    mutateJSON<UnderwritingResult>(`/underwriting/venues/${venueId}/generate`, 'POST', {}),
};
