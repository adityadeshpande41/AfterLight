import type { ActionItem, EvidenceItem, Incident, ScorePoint, Venue } from '@/types';

export const venues: Venue[] = [
  { id: 'moonlight', name: 'Moonlight Club', type: 'Nightclub', location: 'Williamsburg, Brooklyn', capacity: 650, score: 58, delta: -14, risk: 'High', review: 'Urgent review', initials: 'MC' },
  { id: 'harbor', name: 'Harbor Rooftop', type: 'Live venue', location: 'Long Island City, Queens', capacity: 420, score: 78, delta: 6, risk: 'Moderate', review: 'Monitoring', initials: 'HR' },
  { id: 'junction', name: 'The Junction Hall', type: 'Event hall', location: 'Gowanus, Brooklyn', capacity: 1100, score: 86, delta: 3, risk: 'Low', review: 'Healthy', initials: 'JH' },
];

export const incidents: Incident[] = [
  { id: 'INC-1042', date: 'Aug 23, 2026', time: '1:20 AM', title: 'Slip-and-fall near main entrance', type: 'Injury', severity: 'High', status: 'Ready for review', location: 'Main entrance · Camera 3', people: ['Emergency services', 'Security'], evidence: 67, summary: 'Guest slipped on pooled water at the main entrance during peak egress. Security responded within two minutes and EMS assessed the guest on site.' },
  { id: 'INC-1027', date: 'Aug 09, 2026', time: '12:44 AM', title: 'Guest injury at entrance mat', type: 'Injury', severity: 'Moderate', status: 'Action plan active', location: 'Main entrance', people: ['Security'], evidence: 82, summary: 'A guest reported ankle pain after the edge of the entrance mat lifted during the late-night rush.' },
  { id: 'INC-1010', date: 'Jul 28, 2026', time: '1:56 AM', title: 'Crowd surge at front doors', type: 'Crowd management', severity: 'Moderate', status: 'Closed', location: 'Main entrance', people: ['Security', 'Manager'], evidence: 94, summary: 'A short crowd surge formed during last call. Door staffing was adjusted and the entry lane was re-marked.' },
];

export const actions: ActionItem[] = [
  { id: 'act-1', title: 'Preserve Camera 3 footage', incident: 'INC-1042', owner: 'Maya Chen', due: 'Due today', priority: 'Urgent', status: 'Open', proof: 'Video export required' },
  { id: 'act-2', title: 'Collect witness statement from door team', incident: 'INC-1042', owner: 'Jordan Lee', due: 'Due tomorrow', priority: 'Urgent', status: 'In progress', proof: '1 of 2 statements' },
  { id: 'act-3', title: 'Replace and anchor entrance mat', incident: 'INC-1027', owner: 'Facilities', due: 'Sep 02', priority: 'Important', status: 'Complete', proof: 'Photo uploaded Aug 12' },
  { id: 'act-4', title: 'Add wet-floor response checkpoint', incident: 'INC-1042', owner: 'Maya Chen', due: 'Sep 05', priority: 'Important', status: 'Open', proof: 'Checklist not started' },
];

export const evidence: EvidenceItem[] = [
  { id: 'ev-1', label: 'Camera 3 preservation confirmation', kind: 'Video · 01:05:00–01:35:00', status: 'Missing', detail: 'Main entrance camera. Retention window closes in 18 hours.', updated: 'Not yet added' },
  { id: 'ev-2', label: 'Witness statement · Door lead', kind: 'Statement', status: 'Pending review', detail: 'Uploaded by Jordan Lee. Signature is still outstanding.', updated: 'Aug 23 · 02:18 AM' },
  { id: 'ev-3', label: 'EMS response record', kind: 'Document', status: 'Verified', detail: 'Incident number and arrival time match the report.', updated: 'Aug 23 · 03:04 AM' },
  { id: 'ev-4', label: 'Entrance condition photo', kind: 'Photo · 3 files', status: 'Verified', detail: 'Timestamped images show pooled water near the threshold.', updated: 'Aug 23 · 01:42 AM' },
];

export const scoreHistory: ScorePoint[] = [
  { month: 'Mar', score: 74 }, { month: 'Apr', score: 73 }, { month: 'May', score: 71 }, { month: 'Jun', score: 69 }, { month: 'Jul', score: 66 }, { month: 'Aug', score: 58 },
];