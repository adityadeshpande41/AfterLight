/**
 * Hook for triggering and displaying workflow analysis results.
 */

import { useState } from 'react';
import { api, type WorkflowResult } from '@/lib/api';

export function useWorkflowAnalysis() {
  const [result, setResult] = useState<WorkflowResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const analyze = async (incidentId: string) => {
    setLoading(true);
    setError(null);
    try {
      const data = await api.analyzeIncident(incidentId);
      setResult(data);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Analysis failed');
    } finally {
      setLoading(false);
    }
  };

  return { result, loading, error, analyze };
}
