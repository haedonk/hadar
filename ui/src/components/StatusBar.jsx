import { api } from '../api.js';
import { useFetch } from '../hooks/useFetch.js';

function MetricCard({ label, value, tone = 'default', detail }) {
  const toneStyles = {
    default:  { bg: 'var(--color-bg-raised)', border: 'var(--color-border-subtle)', color: 'var(--color-text-primary)' },
    critical: { bg: 'var(--color-critical-bg)', border: 'var(--color-critical)', color: 'var(--color-critical-text)' },
    warning:  { bg: 'var(--color-warning-bg)', border: 'var(--color-warning)', color: 'var(--color-warning-text)' },
    nominal:  { bg: 'var(--color-nominal-bg)', border: 'var(--color-nominal)', color: 'var(--color-nominal-text)' },
  };
  const style = toneStyles[tone] ?? toneStyles.default;

  return (
    <div style={{
      minWidth: 132,
      flex: '1 1 132px',
      padding: 'var(--space-3) var(--space-4)',
      border: `1px solid ${style.border}`,
      borderRadius: 'var(--radius-md)',
      background: style.bg,
    }}>
      <div style={{
        color: 'var(--color-text-muted)',
        fontSize: 'var(--text-xs)',
        fontWeight: 600,
        letterSpacing: '0.06em',
        lineHeight: 1.3,
        textTransform: 'uppercase',
      }}>
        {label}
      </div>
      <div style={{ color: style.color, fontSize: 'var(--text-2xl)', fontWeight: 600, lineHeight: 1.15, marginTop: 4 }}>
        {value}
      </div>
      {detail && (
        <div style={{ color: 'var(--color-text-secondary)', fontSize: 'var(--text-xs)', lineHeight: 1.4, marginTop: 2 }}>
          {detail}
        </div>
      )}
    </div>
  );
}

function SystemPill({ loading, error, summary }) {
  let label = 'Checking API';
  let color = 'var(--color-warning-text)';
  let bg = 'var(--color-warning-bg)';

  if (error) {
    label = 'API unavailable';
    color = 'var(--color-critical-text)';
    bg = 'var(--color-critical-bg)';
  } else if (!loading && summary) {
    label = 'Live monitoring';
    color = 'var(--color-nominal-text)';
    bg = 'var(--color-nominal-bg)';
  }

  return (
    <span style={{
      display: 'inline-flex',
      alignItems: 'center',
      gap: 'var(--space-2)',
      padding: '5px var(--space-3)',
      borderRadius: '999px',
      background: bg,
      color,
      fontSize: 'var(--text-xs)',
      fontWeight: 700,
      letterSpacing: '0.04em',
      lineHeight: 1.2,
      textTransform: 'uppercase',
      whiteSpace: 'nowrap',
    }}>
      <span aria-hidden="true" style={{ width: 7, height: 7, borderRadius: 99, background: color }} />
      {label}
    </span>
  );
}

export default function StatusBar() {
  const { data: summary, loading, error } = useFetch(() => api.summary(), []);

  const openCount = summary?.open_anomaly_count ?? 0;
  const affectedCount = summary?.affected_device_count ?? 0;
  const windowHours = summary?.window_hours ?? 24;

  return (
    <header style={{
      flexShrink: 0,
      background: 'linear-gradient(180deg, var(--color-bg-surface), var(--color-bg-base))',
      borderBottom: '1px solid var(--color-border-subtle)',
      padding: 'var(--space-6) var(--space-6) var(--space-5)',
      boxShadow: 'var(--shadow-soft)',
    }}>
      <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', gap: 'var(--space-4)', flexWrap: 'wrap' }}>
        <div style={{ minWidth: 240 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-3)', flexWrap: 'wrap' }}>
            <h1 style={{ color: 'var(--color-text-primary)', fontSize: 'var(--text-2xl)', fontWeight: 700, letterSpacing: 0, lineHeight: 1.05 }}>
              Hadar
            </h1>
            <SystemPill loading={loading} error={error} summary={summary} />
          </div>
          <p style={{ color: 'var(--color-text-secondary)', fontSize: 'var(--text-base)', lineHeight: 1.45, marginTop: 'var(--space-2)', maxWidth: 660 }}>
            Smart home anomaly monitoring across temperature sensors, model scoring, and persisted events.
          </p>
        </div>
        <div style={{ color: 'var(--color-text-muted)', fontFamily: 'var(--font-mono)', fontSize: 'var(--text-xs)', lineHeight: 1.5, textAlign: 'right' }}>
          <div>Dashboard: 30080</div>
          <div>API: 30800</div>
        </div>
      </div>

      <div style={{ display: 'flex', gap: 'var(--space-3)', flexWrap: 'wrap', marginTop: 'var(--space-5)' }}>
        <MetricCard
          label="Open anomalies"
          value={loading ? '-' : openCount}
          tone={openCount > 0 ? 'critical' : 'nominal'}
          detail={`last ${windowHours} hours`}
        />
        <MetricCard
          label="Affected devices"
          value={loading ? '-' : affectedCount}
          tone={affectedCount > 0 ? 'warning' : 'nominal'}
          detail="currently flagged"
        />
        <MetricCard label="Critical" value={loading ? '-' : (summary?.critical_count ?? 0)} tone="critical" detail="highest severity" />
        <MetricCard label="Warning" value={loading ? '-' : (summary?.warning_count ?? 0)} tone="warning" detail="needs review" />
        <MetricCard label="Low" value={loading ? '-' : (summary?.low_count ?? 0)} tone="default" detail="watch list" />
      </div>

      {error && (
        <div style={{ color: 'var(--color-critical-text)', fontSize: 'var(--text-sm)', marginTop: 'var(--space-3)' }}>
          Unable to load system summary from the API.
        </div>
      )}
    </header>
  );
}
