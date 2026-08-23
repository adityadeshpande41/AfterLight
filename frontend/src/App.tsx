import { type ReactNode } from 'react';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { ErrorBoundary } from '@/components/error-boundary';
import { Toaster } from '@/components/ui/toaster';
import { TooltipProvider } from '@/components/ui/tooltip';
import NotFound from '@/pages/not-found';
import { Architecture, Auth, Landing } from '@/pages/Public';
import { ActionBoard, Copilot, EvidenceRoom, IncidentDetail, IncidentList, ReportWizard, ScorePage, VenueDashboard, VenueGuard } from '@/pages/Venue';
import { AgentRuns, CaseReview, Cases, ConsoleDashboard, InternalGuard, Playbooks, Portfolio, Underwriting, UnderwritingDetail, VenueProfile } from '@/pages/Console';
import { Route, Switch, useLocation } from 'wouter';

const queryClient = new QueryClient();

function Home() {
  return <Landing />;
}

function Guard({ persona, children }: { persona: 'venue' | 'internal'; children: ReactNode }) {
  const current = localStorage.getItem('afterlight-persona');
  if (current !== persona) return persona === 'venue' ? <VenueGuard /> : <InternalGuard />;
  return <>{children}</>;
}

function AppRouter() {
  return (
    <RoutedErrorBoundary>
      <Switch>
        <Route path="/" component={Home} />
        <Route path="/architecture" component={Architecture} />
        <Route path="/login" component={Auth} />
        <Route path="/login/venue" component={Auth} />
        <Route path="/login/internal" component={Auth} />
        <Route path="/venue/dashboard"><Guard persona="venue"><VenueDashboard /></Guard></Route>
        <Route path="/venue/incidents"><Guard persona="venue"><IncidentList /></Guard></Route>
        <Route path="/venue/incidents/report"><Guard persona="venue"><ReportWizard /></Guard></Route>
        <Route path="/venue/incidents/:id"><Guard persona="venue"><IncidentDetail /></Guard></Route>
        <Route path="/venue/actions"><Guard persona="venue"><ActionBoard /></Guard></Route>
        <Route path="/venue/evidence"><Guard persona="venue"><EvidenceRoom /></Guard></Route>
        <Route path="/venue/score"><Guard persona="venue"><ScorePage /></Guard></Route>
        <Route path="/venue/copilot"><Guard persona="venue"><Copilot /></Guard></Route>
        <Route path="/console/dashboard"><Guard persona="internal"><ConsoleDashboard /></Guard></Route>
        <Route path="/console/portfolio"><Guard persona="internal"><Portfolio /></Guard></Route>
        <Route path="/console/cases"><Guard persona="internal"><Cases /></Guard></Route>
        <Route path="/console/cases/:id"><Guard persona="internal"><CaseReview /></Guard></Route>
        <Route path="/console/venues/:id"><Guard persona="internal"><VenueProfile /></Guard></Route>
        <Route path="/console/underwriting"><Guard persona="internal"><Underwriting /></Guard></Route>
        <Route path="/console/underwriting/:venueId"><Guard persona="internal"><UnderwritingDetail /></Guard></Route>
        <Route path="/console/playbooks"><Guard persona="internal"><Playbooks /></Guard></Route>
        <Route path="/console/agent-runs"><Guard persona="internal"><AgentRuns /></Guard></Route>
        <Route component={NotFound} />
      </Switch>
    </RoutedErrorBoundary>
  );
}

function RoutedErrorBoundary({ children }: { children: ReactNode }) {
  const [location] = useLocation();
  return <ErrorBoundary resetKey={location}>{children}</ErrorBoundary>;
}

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <TooltipProvider>
        <AppRouter />
        <Toaster />
      </TooltipProvider>
    </QueryClientProvider>
  );
}

export default App;
