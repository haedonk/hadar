import { useState } from 'react';

const SEVERITY_META = {
  high:   { label: 'Critical', bg: 'var(--color-critical-bg)',  text: 'var(--color-critical-text)' },
  medium: { label: 'Warning',  bg: 'var(--color-warning-bg)',   text: 'var(--color-warning-text)'  },
  low:    { label: 'Low',      bg: 'var(--color-nominal-bg)',   text: 'var(--color-nominal-text)'  },
};

function SeverityBadge({ severity }) {
  const meta = SEVERITY_META[severity] ?? { label: 'Nominal', bg: 'var(--color-nominal-bg)', text: 'var(--color-nominal-text)' };
  return (
    <span style={{
      display: 'inline-flex',
      alignItems: 'center',
      padding: '2px var(--space-2)',
      borderRadius: 'var(--radius-sm)',
      background: meta.bg,
      color: meta.text,
      fontSize: 'var(--text-xs)',
      fontWeight: 600,
      letterSpacing: '0.04em',
      textTransform: 'uppercase',
      flexShrink: 0,
      minWidth: '62px',
      justifyContent: 'center',
    }}>
      {meta.label}
    </span>
  );
}

function formatAbsoluteTs(isoString) {
  const d = new Date(isoString);
  const pad2 = n => String(n).padStart(2, '0');
  const year  = d.getFullYear();
  const month = pad2(d.getMonth() + 1);
  const day   = pad2(d.getDate());
  const hours = pad2(d.getHours());
  const mins  = pad2(d.getMinutes());
  return `${year}-${month}-${day} ${hours}:${mins}`;
}

function EventRow({ event }) {
  const [hovered, setHovered] = useState(false);

  return (
    <div
      onMouseEnter={() => setHovered(true)}
      onMouseLeave={() => setHovered(false)}
      style={{
        display: 'flex',
        alignItems: 'center',
        gap: 'var(--space-3)',
        minHeight: '44px',
        padding: '0 var(--space-4)',
        borderBottom: '1px solid var(--color-border-subtle)',
        background: hovered ? 'var(--color-bg-hover)' : 'transparent',
        transition: 'background var(--transition-fast)',
      }}
    >
      <SeverityBadge severity={event.event_severity} />

      <span style={{
        fontFamily: 'var(--font-mono)',
        fontSize: 'var(--text-sm)',
        color: 'var(--color-text-secondary)',
        flexShrink: 0,
        minWidth: '130px',
      }}>
        {formatAbsoluteTs(event.scored_at)}
      </span>

      <span style={{
        fontFamily: 'var(--font-mono)',
        fontSize: 'var(--text-sm)',
        color: 'var(--color-text-primary)',
        flexShrink: 0,
      }}>
        {event.anomaly_score >= 0
          ? `+${event.anomaly_score.toFixed(2)}`
          : `−${Math.abs(event.anomaly_score).toFixed(2)}`}
      </span>

      <span style={{
        fontSize: 'var(--text-xs)',
        color: 'var(--color-text-muted)',
        textTransform: 'lowercase',
        marginLeft: 'auto',
        flexShrink: 0,
      }}>
        {event.event_status}
      </span>
    </div>
  );
}

export default function AnomalyEventList({ events }) {
  const sorted = [...events].sort((a, b) => new Date(b.scored_at) - new Date(a.scored_at));

  return (
    <section>
      <div style={{
        padding: 'var(--space-4) var(--space-4) var(--space-3)',
        fontSize: 'var(--text-sm)',
        color: 'var(--color-text-secondary)',
        textTransform: 'uppercase',
        letterSpacing: '0.08em',
        fontWeight: 500,
        borderBottom: '1px solid var(--color-border-subtle)',
      }}>
        Anomaly history
      </div>

      {sorted.length === 0 ? (
        <div style={{
          padding: 'var(--space-8) var(--space-4)',
          textAlign: 'center',
          color: 'var(--color-text-muted)',
          fontSize: 'var(--text-base)',
        }}>
          No anomaly events recorded for this device.
        </div>
      ) : (
        sorted.map(event => <EventRow key={event.id} event={event} />)
      )}
    </section>
  );
}
