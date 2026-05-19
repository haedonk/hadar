import { useNavigate, useParams } from 'react-router-dom';
import { api } from '../api.js';
import { useFetch } from '../hooks/useFetch.js';

function relativeTime(isoString) {
  if (!isoString) return '-';
  const diffMs = Date.now() - new Date(isoString).getTime();
  const diffMin = Math.round(diffMs / 60_000);
  if (diffMin < 1) return 'just now';
  if (diffMin < 60) return `${diffMin}m ago`;
  const diffHr = Math.round(diffMin / 60);
  if (diffHr < 24) return `${diffHr}h ago`;
  return `${Math.round(diffHr / 24)}d ago`;
}

function severityConfig(severity) {
  switch (severity) {
    case 'high':   return { label: 'Critical', color: 'var(--color-critical)', text: 'var(--color-critical-text)', bg: 'var(--color-critical-bg)' };
    case 'medium': return { label: 'Warning',  color: 'var(--color-warning)',  text: 'var(--color-warning-text)',  bg: 'var(--color-warning-bg)'  };
    case 'low':    return { label: 'Low',      color: 'var(--color-nominal)',  text: 'var(--color-nominal-text)',  bg: 'var(--color-nominal-bg)'  };
    default:       return { label: 'Nominal',  color: 'var(--color-text-muted)', text: 'var(--color-text-muted)', bg: 'var(--color-bg-raised)' };
  }
}

function startsWithNumber(label) {
  return /^[0-9]/.test((label ?? '').trim());
}

function sortDevices(a, b) {
  const aNumeric = startsWithNumber(a.label);
  const bNumeric = startsWithNumber(b.label);

  if (aNumeric !== bNumeric) return aNumeric ? 1 : -1;

  return (a.label ?? a.id).localeCompare(b.label ?? b.id, undefined, {
    numeric: true,
    sensitivity: 'base',
  });
}

function SkeletonRow() {
  return (
    <div style={{ padding: 'var(--space-3) var(--space-4)', borderTop: '1px solid var(--color-border-subtle)' }}>
      <div style={{ height: 14, width: '75%', background: 'var(--color-bg-raised)', borderRadius: 'var(--radius-sm)', marginBottom: 'var(--space-2)' }} />
      <div style={{ height: 11, width: '48%', background: 'var(--color-bg-raised)', borderRadius: 'var(--radius-sm)' }} />
    </div>
  );
}

function DeviceRow({ device, isActive, onClick }) {
  const meta = severityConfig(device.current_severity);
  const hasAnomaly = device.open_anomaly_count > 0;

  return (
    <button
      onClick={onClick}
      title={device.description}
      style={{
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'stretch',
        gap: 'var(--space-2)',
        width: '100%',
        padding: 'var(--space-3) var(--space-4)',
        background: isActive ? 'var(--color-bg-active)' : 'transparent',
        borderTop: '1px solid var(--color-border-subtle)',
        borderLeft: `3px solid ${hasAnomaly ? meta.color : 'transparent'}`,
        textAlign: 'left',
        cursor: 'pointer',
        transition: 'background var(--transition-fast), border-color var(--transition-fast)',
      }}
      onMouseEnter={e => { if (!isActive) e.currentTarget.style.background = 'var(--color-bg-hover)'; }}
      onMouseLeave={e => { if (!isActive) e.currentTarget.style.background = 'transparent'; }}
    >
      <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', gap: 'var(--space-2)' }}>
        <span style={{
          fontSize: 'var(--text-base)',
          fontWeight: isActive ? 700 : 600,
          color: 'var(--color-text-primary)',
          lineHeight: 1.3,
          overflow: 'hidden',
          textOverflow: 'ellipsis',
          whiteSpace: 'nowrap',
          flex: 1,
          minWidth: 0,
        }}>
          {device.label}
        </span>
        {hasAnomaly && (
          <span style={{
            fontSize: 'var(--text-xs)',
            fontFamily: 'var(--font-mono)',
            fontWeight: 700,
            color: meta.text,
            background: meta.bg,
            padding: '2px 6px',
            borderRadius: 'var(--radius-sm)',
            flexShrink: 0,
            lineHeight: 1.4,
          }}>
            {device.open_anomaly_count}
          </span>
        )}
      </div>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 'var(--space-2)' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-2)', minWidth: 0 }}>
          <span aria-hidden="true" style={{ display: 'inline-block', width: 7, height: 7, borderRadius: 99, background: meta.color, flexShrink: 0 }} />
          <span style={{ fontSize: 'var(--text-xs)', color: hasAnomaly ? meta.text : 'var(--color-text-muted)', lineHeight: 1.4, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
            {meta.label}
          </span>
        </div>
        <span style={{ fontSize: 'var(--text-xs)', color: 'var(--color-text-muted)', lineHeight: 1.4, flexShrink: 0 }} title={device.last_seen ? new Date(device.last_seen).toLocaleString() : ''}>
          {relativeTime(device.last_seen)}
        </span>
      </div>
    </button>
  );
}

export default function Sidebar() {
  const navigate = useNavigate();
  const { id: activeId } = useParams();
  const { data: devices, loading, error } = useFetch(() => api.devices(), []);

  const temperatureDevices = (devices ?? [])
    .filter(device => device.type === 'temperature')
    .sort(sortDevices);
  const totalDevices = temperatureDevices.length;
  const activeDevices = temperatureDevices.filter(device => device.open_anomaly_count > 0).length;

  return (
    <aside style={{
      width: 'var(--sidebar-width)',
      flexShrink: 0,
      background: 'var(--color-bg-surface)',
      borderRight: '1px solid var(--color-border-subtle)',
      display: 'flex',
      flexDirection: 'column',
      overflowY: 'auto',
      height: '100%',
    }}>
      <div style={{ padding: 'var(--space-5) var(--space-4) var(--space-3)' }}>
        <div style={{ color: 'var(--color-text-primary)', fontSize: 'var(--text-md)', fontWeight: 700, lineHeight: 1.2 }}>
          Devices
        </div>
        <div style={{ color: 'var(--color-text-muted)', fontSize: 'var(--text-xs)', fontFamily: 'var(--font-mono)', lineHeight: 1.5, marginTop: 4 }}>
          {loading ? 'Loading' : `${totalDevices} total / ${activeDevices} flagged`}
        </div>
      </div>
      <nav style={{ flex: 1 }}>
        {loading && Array.from({ length: 6 }, (_, i) => <SkeletonRow key={i} />)}
        {error && (
          <div style={{ padding: 'var(--space-4)', fontSize: 'var(--text-sm)', color: 'var(--color-critical-text)', lineHeight: 1.4 }}>
            Could not load devices.
          </div>
        )}
        {!loading && !error && devices && temperatureDevices.length === 0 && (
          <div style={{ padding: 'var(--space-4)', fontSize: 'var(--text-sm)', color: 'var(--color-text-muted)', lineHeight: 1.4 }}>
            No temperature devices found.
          </div>
        )}
        {temperatureDevices.map(device => (
          <DeviceRow
            key={device.id}
            device={device}
            isActive={device.id === activeId}
            onClick={() => navigate(`/device/${device.id}`)}
          />
        ))}
      </nav>
    </aside>
  );
}
