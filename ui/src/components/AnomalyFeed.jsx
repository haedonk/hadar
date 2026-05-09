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
  return score < 0 ? `−${s}` : `+${s}`;
}

function severityConfig(severity) {
  switch (severity) {
    case 'high':   return { label: 'Critical', bg: 'var(--color-critical-bg)', text: 'var(--color-critical-text)' };
    case 'medium': return { label: 'Warning',  bg: 'var(--color-warning-bg)',  text: 'var(--color-warning-text)'  };
    case 'low':    return { label: 'Low',       bg: 'var(--color-nominal-bg)', text: 'var(--color-nominal-text)'  };
    default:       return { label: 'Unknown',  bg: 'var(--color-bg-raised)',   text: 'var(--color-text-muted)'    };
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
  { key: 'all',          label: 'All'           },
  { key: 'acknowledged', label: 'Acknowledged'  },
  { key: 'resolved',     label: 'Resolved'      },
];

// hours window per filter — broader for non-open views
const FILTER_HOURS = { open: 24, all: 720, acknowledged: 720, resolved: 720 };

function SkeletonRow() {
  return (
    <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-3)', padding: '0 var(--space-4)', minHeight: 48, borderBottom: '1px solid var(--color-border-subtle)' }}>
      <div style={{ width: 64, height: 20, borderRadius: 'var(--radius-sm)', background: 'var(--color-bg-raised)' }} />
      <div style={{ flex: 1, height: 14, borderRadius: 'var(--radius-sm)', background: 'var(--color-bg-raised)', maxWidth: 160 }} />
      <div style={{ width: 48, height: 14, borderRadius: 'var(--radius-sm)', background: 'var(--color-bg-raised)' }} />
      <div style={{ width: 52, height: 14, borderRadius: 'var(--radius-sm)', background: 'var(--color-bg-raised)', marginLeft: 'auto' }} />
    </div>
  );
}

function ExpandedDetail({ event }) {
  const sc = statusConfig(event.event_status);
  return (
    <div style={{
      padding: 'var(--space-3) var(--space-4) var(--space-3) calc(var(--space-4) + 64px + var(--space-3))',
      background: 'var(--color-bg-raised)',
      borderBottom: '1px solid var(--color-border-subtle)',
      display: 'flex', flexWrap: 'wrap', gap: 'var(--space-3) var(--space-6)',
      fontSize: 'var(--text-sm)', color: 'var(--color-text-secondary)',
    }}>
      {[
        { label: 'Detected', value: new Date(event.scored_at).toLocaleString() },
        { label: 'Reason', value: event.anomaly_reason, mono: true },
        { label: 'Model', value: event.model_config_name, mono: true },
      ].map(({ label, value, mono }) => (
        <div key={label} style={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
          <span style={{ fontSize: 'var(--text-xs)', color: 'var(--color-text-muted)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>{label}</span>
          <span style={{ color: 'var(--color-text-primary)', lineHeight: 1.4, fontFamily: mono ? 'var(--font-mono)' : undefined }}>{value}</span>
        </div>
      ))}
      <div style={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
        <span style={{ fontSize: 'var(--text-xs)', color: 'var(--color-text-muted)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>Status</span>
        <span style={{ display: 'inline-block', padding: '1px var(--space-2)', borderRadius: 'var(--radius-sm)', background: sc.bg, color: sc.color, fontSize: 'var(--text-xs)', fontWeight: 600, lineHeight: 1.6 }}>
          {sc.label}
        </span>
      </div>
      <div style={{ display: 'flex', alignItems: 'flex-end', marginLeft: 'auto' }}>
        <Link to={`/device/${event.device_id}`}
          style={{ fontSize: 'var(--text-sm)', color: 'var(--color-warning-text)', fontWeight: 500, lineHeight: 1.4, transition: 'color var(--transition-fast)' }}
          onMouseEnter={e => { e.currentTarget.style.color = 'var(--color-warning)'; }}
          onMouseLeave={e => { e.currentTarget.style.color = 'var(--color-warning-text)'; }}>
          View device →
        </Link>
      </div>
    </div>
  );
}

function FeedRow({ event, isExpanded, onToggle }) {
  const sv = severityConfig(event.event_severity);
  return (
    <>
      <button onClick={onToggle} aria-expanded={isExpanded} style={{
        display: 'flex', alignItems: 'center', gap: 'var(--space-3)',
        width: '100%', minHeight: 48, padding: '0 var(--space-4)',
        background: isExpanded ? 'var(--color-bg-active)' : 'transparent',
        borderBottom: isExpanded ? 'none' : '1px solid var(--color-border-subtle)',
        textAlign: 'left', cursor: 'pointer', transition: 'background var(--transition-fast)',
      }}
        onMouseEnter={e => { if (!isExpanded) e.currentTarget.style.background = 'var(--color-bg-hover)'; }}
        onMouseLeave={e => { if (!isExpanded) e.currentTarget.style.background = 'transparent'; }}
      >
        <span style={{ display: 'inline-flex', alignItems: 'center', justifyContent: 'center', minWidth: 64, padding: '2px var(--space-2)', borderRadius: 'var(--radius-sm)', background: sv.bg, color: sv.text, fontSize: 'var(--text-xs)', fontWeight: 600, lineHeight: 1.6, flexShrink: 0 }}>
          {sv.label}
        </span>
        <span style={{ flex: 1, fontWeight: 600, fontSize: 'var(--text-base)', color: 'var(--color-text-primary)', lineHeight: 1.4, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
          {event.device_label}
        </span>
        <span style={{ fontFamily: 'var(--font-mono)', fontSize: 'var(--text-sm)', color: 'var(--color-text-secondary)', lineHeight: 1.4, flexShrink: 0 }}>
          {formatScore(event.anomaly_score)}
        </span>
        <span title={new Date(event.scored_at).toLocaleString()} style={{ fontSize: 'var(--text-sm)', color: 'var(--color-text-muted)', lineHeight: 1.4, flexShrink: 0, minWidth: 60, textAlign: 'right' }}>
          {relativeTime(event.scored_at)}
        </span>
      </button>
      {isExpanded && <ExpandedDetail event={event} />}
    </>
  );
}

export default function AnomalyFeed({ activeFilter, onFilterChange, expandedId, onToggleExpand }) {
  const [internalFilter, setInternalFilter] = useState('open');
  const [internalExpanded, setInternalExpanded] = useState(null);

  const filter      = activeFilter   !== undefined ? activeFilter   : internalFilter;
  const setFilter   = onFilterChange !== undefined ? onFilterChange : setInternalFilter;
  const expanded    = expandedId     !== undefined ? expandedId     : internalExpanded;
  const toggleExpand = onToggleExpand !== undefined ? onToggleExpand : (id) => setInternalExpanded(p => p === id ? null : id);

  const [events, setEvents]   = useState([]);
  const [total, setTotal]     = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError]     = useState(null);

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
    <div style={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
      {/* Filter tabs */}
      <div style={{ display: 'flex', gap: 'var(--space-1)', padding: 'var(--space-3) var(--space-4)', borderBottom: '1px solid var(--color-border-subtle)', flexShrink: 0 }}>
        {FILTERS.map(f => (
          <button key={f.key} onClick={() => setFilter(f.key)} style={{
            padding: 'var(--space-1) var(--space-3)', fontSize: 'var(--text-sm)',
            fontWeight: filter === f.key ? 600 : 400,
            color: filter === f.key ? 'var(--color-text-primary)' : 'var(--color-text-muted)',
            background: 'transparent', borderRadius: 'var(--radius-sm)', transition: 'color var(--transition-fast)', lineHeight: 1.4,
          }}
            onMouseEnter={e => { if (filter !== f.key) e.currentTarget.style.color = 'var(--color-text-secondary)'; }}
            onMouseLeave={e => { if (filter !== f.key) e.currentTarget.style.color = 'var(--color-text-muted)'; }}
          >
            {f.label}
          </button>
        ))}
        {!loading && !error && total > 0 && (
          <span style={{ marginLeft: 'auto', fontSize: 'var(--text-xs)', color: 'var(--color-text-muted)', fontFamily: 'var(--font-mono)', alignSelf: 'center' }}>
            {total}
          </span>
        )}
      </div>

      {/* Feed */}
      <div style={{ flex: 1, overflowY: 'auto' }}>
        {loading && Array.from({ length: 6 }, (_, i) => <SkeletonRow key={i} />)}
        {error && (
          <div style={{ padding: 'var(--space-12)', color: 'var(--color-text-muted)', fontSize: 'var(--text-base)', textAlign: 'center' }}>
            Could not load anomaly events.
          </div>
        )}
        {!loading && !error && events.length === 0 && (
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', padding: 'var(--space-12)', color: 'var(--color-text-muted)', fontSize: 'var(--text-base)', textAlign: 'center' }}>
            No anomalies match this filter.
          </div>
        )}
        {!loading && !error && events.map(ev => (
          <FeedRow key={ev.id} event={ev} isExpanded={expanded === ev.id} onToggle={() => toggleExpand(ev.id)} />
        ))}
      </div>
    </div>
  );
}
