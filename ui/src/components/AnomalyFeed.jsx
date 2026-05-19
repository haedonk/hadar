import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { api } from '../api.js';

function relativeTime(isoString) {
  const diffMs = Date.now() - new Date(isoString).getTime();
  const diffMin = Math.round(diffMs / 60_000);
  if (diffMin < 1) return 'just now';
  if (diffMin < 60) return `${diffMin}m ago`;
  const diffHr = Math.round(diffMin / 60);
  if (diffHr < 24) return `${diffHr}h ago`;
  return `${Math.round(diffHr / 24)}d ago`;
}

function formatScore(score) {
  const s = Math.abs(score).toFixed(2);
  return score < 0 ? `-${s}` : `+${s}`;
}

function severityConfig(severity) {
  switch (severity) {
    case 'high':   return { label: 'Critical', bg: 'var(--color-critical-bg)', text: 'var(--color-critical-text)', bar: 'var(--color-critical)' };
    case 'medium': return { label: 'Warning',  bg: 'var(--color-warning-bg)',  text: 'var(--color-warning-text)',  bar: 'var(--color-warning)'  };
    case 'low':    return { label: 'Low',      bg: 'var(--color-nominal-bg)',  text: 'var(--color-nominal-text)',  bar: 'var(--color-nominal)'  };
    default:       return { label: 'Unknown',  bg: 'var(--color-bg-raised)',   text: 'var(--color-text-muted)',    bar: 'var(--color-border)'   };
  }
}

function statusConfig(status) {
  switch (status) {
    case 'open':         return { label: 'Open',         color: 'var(--color-critical-text)', bg: 'var(--color-critical-bg)' };
    case 'acknowledged': return { label: 'Acknowledged', color: 'var(--color-warning-text)',  bg: 'var(--color-warning-bg)'  };
    case 'resolved':     return { label: 'Resolved',     color: 'var(--color-nominal-text)',  bg: 'var(--color-nominal-bg)'  };
    default:             return { label: status,         color: 'var(--color-text-muted)',    bg: 'var(--color-bg-raised)'   };
  }
}

const FILTERS = [
  { key: 'open',         label: 'Open'         },
  { key: 'all',          label: 'All'          },
  { key: 'acknowledged', label: 'Acknowledged' },
  { key: 'resolved',     label: 'Resolved'     },
];

const FILTER_HOURS = { open: 24, all: 720, acknowledged: 720, resolved: 720 };

function SkeletonRow() {
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-3)', padding: 'var(--space-4)', borderBottom: '1px solid var(--color-border-subtle)' }}>
      <div style={{ width: 5, height: 52, borderRadius: 99, background: 'var(--color-bg-raised)' }} />
      <div style={{ flex: 1 }}>
        <div style={{ height: 14, width: '40%', borderRadius: 'var(--radius-sm)', background: 'var(--color-bg-raised)', marginBottom: 'var(--space-2)' }} />
        <div style={{ height: 12, width: '70%', borderRadius: 'var(--radius-sm)', background: 'var(--color-bg-raised)' }} />
      </div>
      <div style={{ width: 74, height: 24, borderRadius: 'var(--radius-sm)', background: 'var(--color-bg-raised)' }} />
    </div>
  );
}

function ExpandedDetail({ event }) {
  const sc = statusConfig(event.event_status);
  return (
    <div style={{
      margin: '0 var(--space-4) var(--space-4) calc(var(--space-4) + 14px)',
      padding: 'var(--space-4)',
      background: 'var(--color-bg-raised)',
      border: '1px solid var(--color-border-subtle)',
      borderRadius: 'var(--radius-md)',
      display: 'flex',
      flexWrap: 'wrap',
      gap: 'var(--space-4) var(--space-6)',
      fontSize: 'var(--text-sm)',
      color: 'var(--color-text-secondary)',
    }}>
      {[
        { label: 'Detected', value: new Date(event.scored_at).toLocaleString() },
        { label: 'Reason', value: event.anomaly_reason, mono: true },
        { label: 'Model', value: event.model_config_name, mono: true },
      ].map(({ label, value, mono }) => (
        <div key={label} style={{ display: 'flex', flexDirection: 'column', gap: 3, minWidth: 150 }}>
          <span style={{ fontSize: 'var(--text-xs)', color: 'var(--color-text-muted)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>{label}</span>
          <span style={{ color: 'var(--color-text-primary)', lineHeight: 1.4, fontFamily: mono ? 'var(--font-mono)' : undefined }}>{value}</span>
        </div>
      ))}
      <div style={{ display: 'flex', flexDirection: 'column', gap: 3 }}>
        <span style={{ fontSize: 'var(--text-xs)', color: 'var(--color-text-muted)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>Status</span>
        <span style={{ display: 'inline-block', padding: '2px var(--space-2)', borderRadius: 'var(--radius-sm)', background: sc.bg, color: sc.color, fontSize: 'var(--text-xs)', fontWeight: 700, lineHeight: 1.6 }}>
          {sc.label}
        </span>
      </div>
      <div style={{ display: 'flex', alignItems: 'flex-end', marginLeft: 'auto' }}>
        <Link to={`/device/${event.device_id}`} style={{ fontSize: 'var(--text-sm)', color: 'var(--color-accent)', fontWeight: 700, lineHeight: 1.4 }}>
          View device
        </Link>
      </div>
    </div>
  );
}

function FeedRow({ event, isExpanded, onToggle }) {
  const sv = severityConfig(event.event_severity);
  return (
    <div style={{ borderBottom: '1px solid var(--color-border-subtle)' }}>
      <button onClick={onToggle} aria-expanded={isExpanded} style={{
        display: 'grid',
        gridTemplateColumns: '5px minmax(0, 1fr) auto auto',
        alignItems: 'center',
        columnGap: 'var(--space-4)',
        width: '100%',
        minHeight: 74,
        padding: 'var(--space-3) var(--space-4)',
        background: isExpanded ? 'var(--color-bg-active)' : 'transparent',
        textAlign: 'left',
        cursor: 'pointer',
        transition: 'background var(--transition-fast)',
      }}
        onMouseEnter={e => { if (!isExpanded) e.currentTarget.style.background = 'var(--color-bg-hover)'; }}
        onMouseLeave={e => { if (!isExpanded) e.currentTarget.style.background = 'transparent'; }}
      >
        <span aria-hidden="true" style={{ width: 5, height: 46, borderRadius: 99, background: sv.bar }} />
        <span style={{ display: 'flex', flexDirection: 'column', gap: 5, minWidth: 0 }}>
          <span style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-2)', minWidth: 0 }}>
            <span style={{ display: 'inline-flex', alignItems: 'center', justifyContent: 'center', padding: '2px var(--space-2)', borderRadius: 'var(--radius-sm)', background: sv.bg, color: sv.text, fontSize: 'var(--text-xs)', fontWeight: 700, lineHeight: 1.5, flexShrink: 0 }}>
              {sv.label}
            </span>
            <span style={{ color: 'var(--color-text-muted)', fontSize: 'var(--text-xs)', fontFamily: 'var(--font-mono)', lineHeight: 1.4 }}>
              {relativeTime(event.scored_at)}
            </span>
          </span>
          <span style={{ color: 'var(--color-text-primary)', fontSize: 'var(--text-md)', fontWeight: 650, lineHeight: 1.25, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
            {event.device_label}
          </span>
          <span style={{ color: 'var(--color-text-secondary)', fontSize: 'var(--text-sm)', lineHeight: 1.35, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
            {event.anomaly_reason || 'Model flagged this reading as outside the learned baseline.'}
          </span>
        </span>
        <span style={{ color: 'var(--color-text-secondary)', fontFamily: 'var(--font-mono)', fontSize: 'var(--text-md)', fontWeight: 700, lineHeight: 1.4, whiteSpace: 'nowrap' }}>
          {formatScore(event.anomaly_score)}
        </span>
        <span title={new Date(event.scored_at).toLocaleString()} style={{ color: 'var(--color-text-muted)', fontSize: 'var(--text-sm)', lineHeight: 1.4, minWidth: 66, textAlign: 'right', whiteSpace: 'nowrap' }}>
          {new Date(event.scored_at).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
        </span>
      </button>
      {isExpanded && <ExpandedDetail event={event} />}
    </div>
  );
}

function EmptyState({ filter }) {
  return (
    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', minHeight: 260, padding: 'var(--space-12)', textAlign: 'center' }}>
      <div style={{ maxWidth: 360 }}>
        <div style={{ color: 'var(--color-nominal-text)', fontSize: 'var(--text-lg)', fontWeight: 700, lineHeight: 1.3 }}>
          No matching anomalies
        </div>
        <p style={{ color: 'var(--color-text-muted)', fontSize: 'var(--text-base)', lineHeight: 1.5, marginTop: 'var(--space-2)' }}>
          {filter === 'open' ? 'The current monitoring window is clear.' : 'Try another status filter or widen the review window.'}
        </p>
      </div>
    </div>
  );
}

export default function AnomalyFeed({ activeFilter, onFilterChange, expandedId, onToggleExpand }) {
  const [internalFilter, setInternalFilter] = useState('open');
  const [internalExpanded, setInternalExpanded] = useState(null);

  const filter = activeFilter !== undefined ? activeFilter : internalFilter;
  const setFilter = onFilterChange !== undefined ? onFilterChange : setInternalFilter;
  const expanded = expandedId !== undefined ? expandedId : internalExpanded;
  const toggleExpand = onToggleExpand !== undefined ? onToggleExpand : (id) => setInternalExpanded(p => p === id ? null : id);

  const [events, setEvents] = useState([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    let cancelled = false;
    setLoading(true);
    setError(null);
    api.anomalyEvents({ status: filter, hours: FILTER_HOURS[filter] ?? 24 })
      .then(res => {
        if (!cancelled) {
          setEvents(res.events ?? []);
          setTotal(res.total ?? 0);
          setLoading(false);
        }
      })
      .catch(e => { if (!cancelled) { setError(e.message); setLoading(false); } });
    return () => { cancelled = true; };
  }, [filter]);

  return (
    <section style={{ display: 'flex', flexDirection: 'column', minHeight: '100%', padding: 'var(--space-6)', gap: 'var(--space-4)' }}>
      <div style={{ display: 'flex', alignItems: 'flex-end', justifyContent: 'space-between', gap: 'var(--space-4)', flexWrap: 'wrap' }}>
        <div>
          <h2 style={{ color: 'var(--color-text-primary)', fontSize: 'var(--text-xl)', fontWeight: 700, lineHeight: 1.2 }}>
            Anomaly review
          </h2>
          <p style={{ color: 'var(--color-text-secondary)', fontSize: 'var(--text-sm)', lineHeight: 1.45, marginTop: 4 }}>
            Recent model events sorted by detection time.
          </p>
        </div>
        {!loading && !error && (
          <div style={{ color: 'var(--color-text-muted)', fontFamily: 'var(--font-mono)', fontSize: 'var(--text-xs)', lineHeight: 1.4 }}>
            {total} {total === 1 ? 'event' : 'events'}
          </div>
        )}
      </div>

      <div style={{ background: 'var(--color-bg-surface)', border: '1px solid var(--color-border-subtle)', borderRadius: 'var(--radius-md)', overflow: 'hidden', boxShadow: 'var(--shadow-soft)' }}>
        <div style={{ display: 'flex', gap: 'var(--space-1)', padding: 'var(--space-3) var(--space-4)', borderBottom: '1px solid var(--color-border-subtle)', flexWrap: 'wrap' }}>
          {FILTERS.map(f => (
            <button key={f.key} onClick={() => setFilter(f.key)} style={{
              padding: 'var(--space-2) var(--space-3)',
              fontSize: 'var(--text-sm)',
              fontWeight: filter === f.key ? 700 : 500,
              color: filter === f.key ? 'var(--color-text-primary)' : 'var(--color-text-muted)',
              background: filter === f.key ? 'var(--color-bg-active)' : 'transparent',
              borderRadius: 'var(--radius-sm)',
              lineHeight: 1.2,
            }}>
              {f.label}
            </button>
          ))}
        </div>

        <div>
          {loading && Array.from({ length: 5 }, (_, i) => <SkeletonRow key={i} />)}
          {error && (
            <div style={{ padding: 'var(--space-12)', color: 'var(--color-critical-text)', fontSize: 'var(--text-base)', textAlign: 'center' }}>
              Could not load anomaly events from the API.
            </div>
          )}
          {!loading && !error && events.length === 0 && <EmptyState filter={filter} />}
          {!loading && !error && events.map(ev => (
            <FeedRow key={ev.id} event={ev} isExpanded={expanded === ev.id} onToggle={() => toggleExpand(ev.id)} />
          ))}
        </div>
      </div>
    </section>
  );
}
