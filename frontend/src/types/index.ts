export type Persona = 'venue' | 'internal';
export type Theme = 'light' | 'dark' | 'system';
export type RiskLevel = 'Low' | 'Moderate' | 'High';

export interface Venue {
  id: string;
  name: string;
  type: string;
  location: string;
  capacity: number;
  score: number;
  delta: number;
  risk: RiskLevel;
  review: string;
  initials: string;
}

export interface Incident {
  id: string;
  date: string;
  time: string;
  title: string;
  type: string;
  severity: RiskLevel;
  status: string;
  location: string;
  people: string[];
  evidence: number;
  summary: string;
}

export interface ActionItem {
  id: string;
  title: string;
  incident: string;
  owner: string;
  due: string;
  priority: 'Urgent' | 'Important' | 'Routine';
  status: 'Open' | 'In progress' | 'Complete';
  proof: string;
}

export interface EvidenceItem {
  id: string;
  label: string;
  kind: string;
  status: 'Verified' | 'Missing' | 'Pending review';
  detail: string;
  updated: string;
}

export interface ScorePoint {
  month: string;
  score: number;
}