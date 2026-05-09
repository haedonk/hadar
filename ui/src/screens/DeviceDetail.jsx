import { useEffect, useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import { api } from '../api.js';
import ReadingChart from '../components/ReadingChart.jsx';
import AnomalyEventList from '../components/AnomalyEventList.jsx';

const SEVERITY_META = {
  high:   { label: 'Critical', bg: 'var(--color-critical-bg)',  text: 'var(--color-critical-text)' },
  medium: { label: 'Warning',  bg: 'var(--color-warning-bg)',   text: 'var(--color-warning-text)'  },
  low:    { label: 'Low',      bg: 'var(--color-nominal-bg)',   text: 'var(--color-nominal-text)'  },
};

function SeverityBadge({ severity }) {
  const meta = severity
    ? SEVERITY_META[severity] ?? { label: 'Nominal', bg: 'var(--color-nominal-bg)', text: 'var(--color-nominal-text)' }
    : { label: 'Nominal', bg: 'var(--color-nominal-bg)', text: 'var(--color-nominal-text)' };
  return (
    <span style={{ display: 'inline-flex', alignItems: 'center', padding: '3px var(--space-2)', borderRadius: 'var(--radius-sm)', background: meta.bg, color: meta.text, fontSize: 'var(--text-xs)', fontWeight: 600, letterSpacing: '0.04em', textTransform: 'uppercase' }}>
      {meta.label}
    </span>
  );
}

function TypeBadge({ type }) {
  const label = type === 'temperature' ? 'Temperature' : type === 'plug' ? 'Energy' : type;
  return (
    <span style={{ display: 'inline-flex', alignItems: 'center', padding: '3px var(--space-2)', borderRadius: 'var(--radius-sm)', background: 'var(--color-bg-raised)', color: 'var(--color-text-secondary)', fontSize: 'var(--text-xs)', fontWeight: 500 }}>
      {label}
    </span>
  );
}

function BackLink() {
  return (
    <Link to="/" style={{ color: 'var(--color-text-secondary)', fontSize: 'var(--text-base)', textDecoration: 'none', display: 'inline-flex', alignItems: 'center', gap: 'var(--space-1)', transition: 'color var(--transition-fast)', flexShrink: 0 }}
      onMouseEnter={e => { e.currentTarget.style.color = 'var(--color-text-primary)'; }}
      onMouseLeave={e => { e.currentTarget.style.color = 'var(--color-text-secondary)'; }}>
      ← Back
    </Link>
  );
}

function HeaderSkeleton() {
  return (
    <header style={{ background: 'var(--color-bg-surface)', borderBottom: '1px solid var(--color-border-subtle)', padding: 'var(--space-4) var(--space-6)', display: 'flex', alignItems: 'center', gap: 'var(--space-4)' }}>
      <BackLink />
      <div style={{ height: 18, width: 160, background: 'var(--color-bg-raised)', borderRadius: 'var(--radius-sm)' }} />
    </header>
  );
}

export default function DeviceDetail() {
  const { id } = useParams();

  const [device,   setDevice]   = useState(null);
  const [readings, setReadings] = useState(null);
  const [events,   setEvents]   = useState([]);
  const [loading,  setLoading]  = useState(true);
  const [error,    setError]    = useState(null);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);

    Promise.all([
      api.device(id),
      api.deviceReadings(id).catch(() => null),
      api.deviceAnomalyEvents(id),
    ]).then(([dev, rdg, evs]) => {
      if (cancelled) return;
      setDevice(dev);
      setReadings(rdg);
      setEvents(evs ?? []);
      setLoading(false);
    }).catch(e => {
      if (!cancelled) { setError(e.message); setLoading(false); }
    });

    return () => { cancelled = true; };
  }, [id]);

  if (loading) return (
    <div style={{ display: 'flex', flexDirection: 'column', minHeight: '100dvh', background: 'var(--color-bg-base)', fontFamily: 'var(--font-sans)' }}>
      <HeaderSkeleton />
    </div>
  );

  if (error) return (
    <div style={{ display: 'flex', flexDirection: 'column', minHeight: '100dvh', background: 'var(--color-bg-base)', fontFamily: 'var(--font-sans)', padding: 'var(--space-8)' }}>
      <BackLink />
      <p style={{ color: 'var(--color-critical-text)', marginTop: 'var(--space-4)', fontSize: 'var(--text-base)' }}>
        {error.includes('404') || error.toLowerCase().includes('not found') ? 'Device not found.' : `Error: ${error}`}
      </p>
    </div>
  );

  const chartType = readings?.type ?? (device.type === 'plug' ? 'energy' : 'temperature');

  return (
    <div style={{ display: 'flex', flexDirection: 'column', minHeight: '100dvh', background: 'var(--color-bg-base)', fontFamily: 'var(--font-sans)' }}>
      <header style={{ background: 'var(--color-bg-surface)', borderBottom: '1px solid var(--color-border-subtle)', padding: 'var(--space-4) var(--space-6)', display: 'flex', alignItems: 'center', gap: 'var(--space-4)', flexWrap: 'wrap' }}>
        <BackLink />
        <h1 style={{ fontSize: 'var(--text-xl)', fontWeight: 600, color: 'var(--color-text-primary)', lineHeight: 1.2 }}>
          {device.label}
        </h1>
        <TypeBadge type={device.type} />
        <SeverityBadge severity={device.current_severity} />
        {device.description && (
          <span style={{ fontSize: 'var(--text-sm)', color: 'var(--color-text-muted)', marginLeft: 'auto' }}>
            {device.description}
          </span>
        )}
      </header>

      <main style={{ flex: 1, overflowY: 'auto', padding: 'var(--space-6)', display: 'flex', flexDirection: 'column', gap: 'var(--space-4)', maxWidth: '1100px', width: '100%', margin: '0 auto' }}>
        {readings ? (
          <section style={{ background: 'var(--color-bg-surface)', borderRadius: 'var(--radius-md)', border: '1px solid var(--color-border-subtle)', overflow: 'hidden' }}>
            <ReadingChart readings={readings.readings} type={chartType} anomalyEvents={events} />
          </section>
        ) : (
          <p style={{ fontSize: 'var(--text-base)', color: 'var(--color-text-muted)' }}>
            No readings available for this device.
          </p>
        )}

        <section style={{ background: 'var(--color-bg-surface)', borderRadius: 'var(--radius-md)', border: '1px solid var(--color-border-subtle)', overflow: 'hidden' }}>
          <AnomalyEventList events={events} deviceLabel={device.label} />
        </section>
      </main>
    </div>
  );
}
