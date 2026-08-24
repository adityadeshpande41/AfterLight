import { useEffect, useMemo, useState, type ReactNode } from 'react';
import { Link, useLocation } from 'wouter';
import { Activity, Archive, ArrowLeftRight, BadgeCheck, BarChart3, BookOpen, Boxes, ClipboardCheck, FileText, HelpCircle, LayoutDashboard, LogOut, Menu, Moon, MoreHorizontal, Radio, RotateCcw, Search, Settings2, Shield, Sun, Target, Upload, Users, X } from 'lucide-react';
import type { Persona, Theme, Venue } from '@/types';
import { apiClient } from '@/lib/apiClient';

export const demoVenue: Venue = apiClient.getState().venues[0];

const venueNav = [
  { href: '/venue/dashboard', label: 'Overview', icon: LayoutDashboard },
  { href: '/venue/incidents', label: 'Incidents', icon: FileText },
  { href: '/venue/actions', label: 'Corrective actions', icon: ClipboardCheck },
  { href: '/venue/evidence', label: 'Evidence room', icon: Archive },
  { href: '/venue/score', label: 'Savings Score', icon: BarChart3 },
  { href: '/venue/copilot', label: 'AfterLight guide', icon: Radio },
];
const internalNav = [
  { href: '/console/dashboard', label: 'Portfolio overview', icon: LayoutDashboard },
  { href: '/console/portfolio', label: 'Venues', icon: Boxes },
  { href: '/console/cases', label: 'Review queue', icon: ClipboardCheck },
  { href: '/console/underwriting', label: 'Underwriting', icon: Shield },
  { href: '/console/playbooks', label: 'Playbooks', icon: BookOpen },
  { href: '/console/agent-runs', label: 'Agent runs', icon: Activity },
];

function Logo() {
  return <Link href="/" data-testid="link-logo" className="flex items-center gap-3 focus-ring rounded-lg w-fit">
    <span className="grid size-9 place-items-center rounded-xl bg-[hsl(var(--accent))] text-[hsl(var(--primary))] shadow-sm"><Shield size={18} strokeWidth={2.5} /></span>
    <span className="font-display text-xl tracking-tight">AfterLight</span>
  </Link>;
}

export function DemoBadge() {
  return null;
}

export function ThemeControl() {
  const [theme, setTheme] = useState<Theme>(() => (localStorage.getItem('afterlight-theme') as Theme) || 'light');
  useEffect(() => {
    const isDark = theme === 'dark' || (theme === 'system' && window.matchMedia('(prefers-color-scheme: dark)').matches);
    document.documentElement.classList.toggle('dark', isDark);
    localStorage.setItem('afterlight-theme', theme);
  }, [theme]);
  return <div className="flex items-center gap-1 rounded-full border border-[hsl(var(--border))] bg-[hsl(var(--card)/.7)] p-1" aria-label="Theme controls">
    {([['light', Sun], ['dark', Moon], ['system', MoreHorizontal]] as const).map(([value, Icon]) => <button key={value} data-testid={`button-theme-${value}`} onClick={() => setTheme(value)} className={`focus-ring rounded-full p-1.5 ${theme === value ? 'bg-[hsl(var(--primary))] text-[hsl(var(--primary-foreground))]' : 'text-[hsl(var(--muted-foreground))] hover:bg-[hsl(var(--muted))]'}`} aria-label={`Use ${value} theme`}><Icon size={14} /></button>)}
  </div>;
}

export function AppShell({ children, persona = 'venue' }: { children: ReactNode; persona?: Persona }) {
  const [location, setLocation] = useLocation();
  const [open, setOpen] = useState(false);
  const [venueMenu, setVenueMenu] = useState(false);
  const nav = persona === 'venue' ? venueNav : internalNav;
  const activeVenue = useMemo(() => apiClient.getState().venues[0], []);
  const logout = () => { localStorage.removeItem('afterlight-persona'); setLocation('/'); };
  return <div className="min-h-[100dvh] bg-[hsl(var(--background))]">
    <DemoBadge />
    <aside className={`fixed inset-y-0 left-0 z-40 flex w-[255px] flex-col border-r border-[hsl(var(--sidebar-border))] bg-[hsl(var(--sidebar))] px-4 py-5 text-[hsl(var(--sidebar-foreground))] transition-transform md:translate-x-0 ${open ? 'translate-x-0' : '-translate-x-full'}`}>
      <div className="flex items-center justify-between px-2"><Logo /><button data-testid="button-close-menu" onClick={() => setOpen(false)} className="focus-ring rounded-md p-1 md:hidden"><X size={18} /></button></div>
      <div className="mt-8 border-b border-[hsl(var(--sidebar-border))] pb-5">
        <button data-testid="button-select-venue" onClick={() => setVenueMenu(!venueMenu)} className="focus-ring flex w-full items-center gap-3 rounded-xl p-2 text-left hover:bg-[hsl(var(--sidebar-accent))]">
          <span className="grid size-9 place-items-center rounded-lg bg-[hsl(var(--accent)/.16)] text-sm font-bold text-[hsl(var(--accent))]">{activeVenue.initials}</span>
          <span className="min-w-0 flex-1"><span className="block truncate text-sm font-semibold">{activeVenue.name}</span><span className="block truncate text-[11px] text-[hsl(var(--sidebar-foreground)/.58)]">{persona === 'venue' ? 'Venue workspace' : 'All venues'}</span></span>
          <MoreHorizontal size={16} className="text-[hsl(var(--sidebar-foreground)/.55)]" />
        </button>
        {venueMenu && <div className="mt-2 rounded-xl border border-[hsl(var(--sidebar-border))] bg-[hsl(var(--sidebar-accent))] p-1.5 text-xs">
          {apiClient.getState().venues.filter((v) => v.id === 'moonlight').map((venue) => <button key={venue.id} data-testid={`button-venue-${venue.id}`} onClick={() => { setVenueMenu(false); }} className="flex w-full items-center gap-2 rounded-lg px-2 py-2 text-left hover:bg-[hsl(var(--sidebar))]"><span className="font-mono-ui text-[10px] text-[hsl(var(--accent))]">{venue.initials}</span>{venue.name}<span className="ml-auto text-[9px] text-[hsl(var(--accent))]">active</span></button>)}
          {persona === 'internal' && <Link href="/console/portfolio" data-testid="link-all-venues" className="mt-1 flex items-center gap-2 rounded-lg px-2 py-2 text-[hsl(var(--accent))] hover:bg-[hsl(var(--sidebar))]">View portfolio <ArrowLeftRight size={12} /></Link>}
        </div>}
      </div>
      <nav className="mt-5 flex-1 space-y-1" aria-label="Primary navigation">
        <p className="mb-3 px-3 text-[10px] font-mono-ui uppercase tracking-[.18em] text-[hsl(var(--sidebar-foreground)/.45)]">{persona === 'venue' ? 'Operations' : 'Risk console'}</p>
        {nav.map(({ href, label, icon: Icon }) => <Link key={href} href={href} data-testid={`link-nav-${label.toLowerCase().replaceAll(' ', '-')}`} onClick={() => setOpen(false)} className={`focus-ring group flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm transition-colors ${location === href || (location.startsWith(href + '/')) ? 'bg-[hsl(var(--sidebar-accent))] font-semibold text-[hsl(var(--accent))]' : 'text-[hsl(var(--sidebar-foreground)/.72)] hover:bg-[hsl(var(--sidebar-accent))] hover:text-[hsl(var(--sidebar-foreground))]'}`}><Icon size={17} strokeWidth={1.8} /><span>{label}</span>{label === 'Review queue' && <span className="ml-auto rounded-full bg-[hsl(var(--destructive))] px-1.5 py-0.5 text-[10px] text-white">3</span>}</Link>)}
      </nav>
      <div className="space-y-1 border-t border-[hsl(var(--sidebar-border))] pt-4">
        {persona === 'venue' && <Link href="/architecture" data-testid="link-architecture" className="flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm text-[hsl(var(--sidebar-foreground)/.65)] hover:bg-[hsl(var(--sidebar-accent))]"><Target size={17} />How AfterLight works</Link>}
        <button data-testid="button-logout" onClick={logout} className="flex w-full items-center gap-3 rounded-xl px-3 py-2.5 text-sm text-[hsl(var(--sidebar-foreground)/.65)] hover:bg-[hsl(var(--sidebar-accent))]"><LogOut size={17} />Sign out</button>
      </div>
    </aside>
    <div className="md:pl-[255px]">
      <header className="sticky top-0 z-30 flex h-[68px] items-center justify-between border-b border-[hsl(var(--border))] bg-[hsl(var(--background)/.92)] px-4 backdrop-blur-md md:px-8">
        <button data-testid="button-open-menu" onClick={() => setOpen(true)} className="focus-ring rounded-lg p-2 md:hidden"><Menu size={20} /></button>
        <div className="hidden items-center gap-2 text-xs text-[hsl(var(--muted-foreground))] md:flex"><span className="size-2 rounded-full bg-[hsl(var(--accent))]" />Last synced 2 min ago</div>
        <div className="ml-auto flex items-center gap-3"><ThemeControl /><span className="grid size-8 place-items-center rounded-full bg-[hsl(var(--primary))] text-xs font-bold text-[hsl(var(--primary-foreground))]">{persona === 'venue' ? 'MC' : 'AR'}</span></div>
      </header>
      <main className="mx-auto max-w-[1500px] px-4 py-7 pb-24 md:px-8 lg:px-10">{children}</main>
    </div>
  </div>;
}

export function PageHeader({ eyebrow, title, description, action }: { eyebrow: string; title: string; description?: string; action?: ReactNode }) {
  return <div className="mb-7 flex flex-col justify-between gap-5 md:flex-row md:items-end"><div><p className="mb-2 font-mono-ui text-[10px] uppercase tracking-[.2em] text-[hsl(var(--muted-foreground))]">{eyebrow}</p><h1 className="font-display text-4xl leading-none tracking-tight md:text-5xl">{title}</h1>{description && <p className="mt-3 max-w-2xl text-sm leading-6 text-[hsl(var(--muted-foreground))]">{description}</p>}</div>{action}</div>;
}

export function Pill({ children, tone = 'neutral' }: { children: ReactNode; tone?: 'neutral' | 'good' | 'warn' | 'bad' | 'accent' }) {
  const tones = { neutral: 'bg-[hsl(var(--muted))] text-[hsl(var(--muted-foreground))]', good: 'bg-[hsl(161_31%_43%/.13)] text-[hsl(161_31%_34%)] dark:text-[hsl(161_45%_64%)]', warn: 'bg-[hsl(38_79%_62%/.2)] text-[hsl(28_58%_31%)] dark:text-[hsl(38_79%_72%)]', bad: 'bg-[hsl(3_62%_50%/.13)] text-[hsl(3_62%_42%)] dark:text-[hsl(3_72%_68%)]', accent: 'bg-[hsl(var(--primary)/.1)] text-[hsl(var(--primary))]' };
  return <span data-testid="status-pill" className={`inline-flex items-center rounded-full px-2.5 py-1 text-[10px] font-bold uppercase tracking-wider ${tones[tone]}`}>{children}</span>;
}

export function Metric({ label, value, detail, tone = 'neutral' }: { label: string; value: string; detail: string; tone?: 'neutral' | 'good' | 'warn' | 'bad' }) {
  return <div data-testid={`metric-${label.toLowerCase().replaceAll(' ', '-')}`} className="rounded-2xl border border-[hsl(var(--border))] bg-[hsl(var(--card))] p-5 shadow-[0_1px_0_hsl(var(--border))]"><p className="text-xs text-[hsl(var(--muted-foreground))]">{label}</p><p className="mt-3 text-3xl font-semibold tracking-tight">{value}</p><p className={`mt-2 text-xs ${tone === 'bad' ? 'text-[hsl(var(--destructive))]' : tone === 'good' ? 'text-[hsl(161_31%_36%)] dark:text-[hsl(161_45%_64%)]' : 'text-[hsl(var(--muted-foreground))]'}`}>{detail}</p></div>;
}

export function Restricted({ internal = false }: { internal?: boolean }) {
  const [, setLocation] = useLocation();
  return <div className="mx-auto max-w-lg py-20 text-center"><div className="mx-auto grid size-16 place-items-center rounded-2xl bg-[hsl(var(--muted))] text-[hsl(var(--primary))]"><Settings2 size={28} /></div><h1 className="mt-6 font-display text-4xl">Restricted room</h1><p className="mt-3 text-sm leading-6 text-[hsl(var(--muted-foreground))]">This view belongs to the {internal ? 'internal risk team' : 'venue operations'} workspace. Switch demo personas to continue.</p><button data-testid="button-go-login" onClick={() => setLocation('/login')} className="mt-7 rounded-xl bg-[hsl(var(--primary))] px-5 py-3 text-sm font-semibold text-[hsl(var(--primary-foreground))]">Switch workspace</button></div>;
}