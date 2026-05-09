import { useNavigate, useParams } from 'react-router-dom';
import { api } from '../api.js';
import { useFetch } from '../hooks/useFetch.js';

function relativeTime(isoString) {
  if (!isoString) return '—';
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
    case 'high':   return { label: 'Critical', color: 'var(--color-critical)' };
    case 'medium': return { label: 'Warning',  color: 'var(--color-warning)'  };
    case 'low':    return { label: 'Low',      color: 'var(--color-nominal)'  };
    default:       return { label: '—',        color: 'var(--color-text-muted)' };
  }
}

function SkeletonRow() {
  return (
    <div style={{ padding: 'var(--space-3) var(--space-4)', borderTop: '1px solid var(--color-border-subtle)' }}>
      <div style={{ height: 12, width: '70%', background: 'var(--color-bg-raised)', borderRadius: 'var(--radius-sm)', marginBottom: 'var(--space-2)' }} />
      <div style={{ height: 10, width: '40%', background: 'var(--color-bg-raised)', borderRadius: 'var(--radius-sm)' }} />
    </div>
  );
}

function DeviceRow({ device, isActive, onClick }) {
  const { label, color } = severityConfig(device.current_severity);
  return (
    <button
      onClick={onClick}
      title={device.description}
      style={{
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'flex-start',
        gap: 'var(--space-1)',
        width: '100%',
        padding: 'var(--space-3) var(--space-4)',
        background: isActive ? 'var(--color-bg-active)' : 'transparent',
        borderTop: '1px solid var(--color-border-subtle)',
        textAlign: 'left',
        cursor: 'pointer',
        transition: 'background var(--transition-fast)',
      }}
      onMouseEnter={e => { if (!isActive) e.currentTarget.style.background = 'var(--color-bg-hover)'; }}
      onMouseLeave={e => { if (!isActive) e.currentTarget.style.background = 'transparent'; }}
    >
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', width: '100%', gap: 'var(--space-2)' }}>
        <span style={{
          fontSize: 'var(--text-base)', fontWeight: isActive ? 600 : 400,
          color: 'var(--color-text-primary)', lineHeight: 1.4,
          overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap', flex: 1, minWidth: 0,
        }}>
          {device.label}
        </span>
        {device.open_anomaly_count > 0 && (
          <span style={{
            fontSize: 'var(--text-xs)', fontFamily: 'var(--font-mono)', fontWeight: 600,
            color: device.current_severity === 'high' ? 'var(--color-critical-text)'
                 : device.current_severity === 'medium' ? 'var(--color-warning-text)'
                 : 'var(--color-nominal-text)',
            background: device.current_severity === 'high' ? 'var(--color-critical-bg)'
                      : device.current_severity === 'medium' ? 'var(--color-warning-bg)'
                      : 'var(--color-nominal-bg)',
            padding: '1px 5px', borderRadius: 'var(--radius-sm)', flexShrink: 0, lineHeight: 1.6,
          }}>
            {device.open_anomaly_count}
          </span>
        )}
      </div>
      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', width: '100%' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 'var(--space-1)' }}>
          <span aria-hidden="true" style={{ display: 'inline-block', width: 6, height: 6, borderRadius: '1px', background: color, flexShrink: 0 }} />
          <span style={{ fontSize: 'var(--text-xs)', color, lineHeight: 1.4 }}>{label}</span>
        </div>
        <span style={{ fontSize: 'var(--text-xs)', color: 'var(--color-text-muted)', lineHeight: 1.4 }}
              title={device.last_seen ? new Date(device.last_seen).toLocaleString() : ''}>
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

  return (
    <aside style={{
      width: 'var(--sidebar-width)', flexShrink: 0,
      background: 'var(--color-bg-surface)',
      borderRight: '1px solid var(--color-border-subtle)',
      display: 'flex', flexDirection: 'column',
      overflowY: 'auto', height: '100%',
    }}>
      <div style={{
        padding: 'var(--space-4) var(--space-4) var(--space-2)',
        fontSize: 'var(--text-xs)', color: 'var(--color-text-muted)',
        textTransform: 'uppercase', letterSpacing: '0.06em', fontWeight: 500, lineHeight: 1.4,
      }}>
        Devices
      </div>
      <nav style={{ flex: 1 }}>
        {loading && Array.from({ length: 6 }, (_, i) => <SkeletonRow key={i} />)}
        {error && (
          <div style={{ padding: 'var(--space-4)', fontSize: 'var(--text-sm)', color: 'var(--color-text-muted)' }}>
            Could not load devices.
          </div>
        )}
        {devices && devices.map(device => (
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
