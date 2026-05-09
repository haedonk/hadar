import { api } from '../api.js';
import { useFetch } from '../hooks/useFetch.js';

function SeverityBadge({ count, bgColor, textColor, label }) {
  if (!count) return null;
  return (
    <span style={{
      display: 'inline-flex',
      alignItems: 'center',
      gap: 'var(--space-1)',
      padding: '1px var(--space-2)',
      borderRadius: 'var(--radius-sm)',
      background: bgColor,
      color: textColor,
      fontFamily: 'var(--font-mono)',
      fontSize: 'var(--text-xs)',
      fontWeight: 600,
      lineHeight: 1.6,
    }}>
      {count} {label}
    </span>
  );
}

export default function StatusBar() {
  const { data: summary, loading, error } = useFetch(() => api.summary(), []);

  return (
    <div style={{
      position: 'sticky',
      top: 0,
      zIndex: 10,
      backgroundColor: 'var(--color-bg-surface)',
      borderBottom: '1px solid var(--color-border-subtle)',
      padding: 'var(--space-2) var(--space-4)',
      display: 'flex',
      alignItems: 'center',
      gap: 'var(--space-3)',
      flexWrap: 'wrap',
      minHeight: '36px',
    }}>
      {loading && (
        <span style={{ color: 'var(--color-text-muted)', fontSize: 'var(--text-sm)' }}>
          Loading…
        </span>
      )}
      {error && (
        <span style={{ color: 'var(--color-critical-text)', fontSize: 'var(--text-sm)' }}>
          Unable to load status
        </span>
      )}
      {summary && summary.open_anomaly_count === 0 && (
        <span style={{ color: 'var(--color-text-secondary)', fontSize: 'var(--text-sm)', lineHeight: 1.4 }}>
          No open anomalies in the last {summary.window_hours} hours
        </span>
      )}
      {summary && summary.open_anomaly_count > 0 && (
        <>
          <span style={{ color: 'var(--color-text-secondary)', fontSize: 'var(--text-sm)', lineHeight: 1.4 }}>
            {summary.open_anomaly_count} open {summary.open_anomaly_count === 1 ? 'anomaly' : 'anomalies'} across{' '}
            {summary.affected_device_count} {summary.affected_device_count === 1 ? 'device' : 'devices'} in the last{' '}
            {summary.window_hours} hours
          </span>
          <SeverityBadge count={summary.critical_count} bgColor="var(--color-critical-bg)" textColor="var(--color-critical-text)" label="critical" />
          <SeverityBadge count={summary.warning_count}  bgColor="var(--color-warning-bg)"  textColor="var(--color-warning-text)"  label="warning"  />
          <SeverityBadge count={summary.low_count}      bgColor="var(--color-nominal-bg)"  textColor="var(--color-nominal-text)"  label="low"      />
        </>
      )}
    </div>
  );
}
