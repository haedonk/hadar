import {
  ResponsiveContainer,
  LineChart,
  Line,
  XAxis,
  YAxis,
  Tooltip,
  ReferenceLine,
} from 'recharts';

function formatTickDate(ts) {
  const d = new Date(ts);
  const pad2 = n => String(n).padStart(2, '0');
  return `${pad2(d.getMonth() + 1)}/${pad2(d.getDate())} ${pad2(d.getHours())}:${pad2(d.getMinutes())}`;
}

function CustomTooltip({ active, payload, label, unit, dataKey }) {
  if (!active || !payload || payload.length === 0) return null;
  const value = payload[0]?.value;
  return (
    <div style={{
      background: 'var(--color-bg-raised)',
      border: '1px solid var(--color-border)',
      borderRadius: 'var(--radius-md)',
      padding: 'var(--space-2) var(--space-3)',
      fontFamily: 'var(--font-mono)',
      fontSize: 'var(--text-sm)',
      color: 'var(--color-text-primary)',
      lineHeight: 1.6,
      pointerEvents: 'none',
    }}>
      <div style={{ color: 'var(--color-text-secondary)', marginBottom: '2px' }}>
        {formatTickDate(label)}
      </div>
      <div>
        {value != null ? `${value}${unit}` : '—'}
      </div>
    </div>
  );
}

export default function ReadingChart({ readings, type, anomalyEvents }) {
  const isTemperature = type === 'temperature';
  const dataKey = isTemperature ? 'temperature' : 'power_watts';
  const unit    = isTemperature ? '°C' : 'W';
  const title   = isTemperature ? 'Temperature (°C)' : 'Power (W)';

  // Convert ts to numeric timestamp for time-scale axis
  const chartData = readings.map(r => ({
    ...r,
    ts: new Date(r.ts).getTime(),
  }));

  // Filter anomaly events to only those with a severity we display
  const markers = (anomalyEvents ?? []).filter(
    e => e.event_severity === 'high' || e.event_severity === 'medium' || e.event_severity === 'low'
  );

  return (
    <div style={{ padding: 'var(--space-4) var(--space-4) var(--space-4)' }}>
      <div style={{
        fontSize: 'var(--text-sm)',
        color: 'var(--color-text-secondary)',
        marginBottom: 'var(--space-3)',
      }}>
        {title}
      </div>
      <div style={{ background: 'var(--color-bg-base)', borderRadius: 'var(--radius-md)' }}>
        <ResponsiveContainer width="100%" height={300}>
          <LineChart
            data={chartData}
            margin={{ top: 8, right: 16, bottom: 4, left: 8 }}
          >
            <XAxis
              dataKey="ts"
              type="number"
              scale="time"
              domain={['dataMin', 'dataMax']}
              tickFormatter={formatTickDate}
              stroke="var(--color-text-muted)"
              tick={{ fill: 'var(--color-text-muted)', fontSize: 11 }}
              tickLine={false}
              axisLine={{ stroke: 'var(--color-border-subtle)' }}
              minTickGap={80}
            />
            <YAxis
              tickFormatter={v => `${v}${unit}`}
              stroke="var(--color-text-muted)"
              tick={{ fill: 'var(--color-text-muted)', fontSize: 11 }}
              tickLine={false}
              axisLine={{ stroke: 'var(--color-border-subtle)' }}
              width={isTemperature ? 52 : 62}
            />
            <Tooltip
              content={<CustomTooltip unit={unit} dataKey={dataKey} />}
              cursor={{ stroke: 'var(--color-border)', strokeWidth: 1 }}
            />
            {markers.map(ev => (
              <ReferenceLine
                key={ev.id}
                x={new Date(ev.scored_at).getTime()}
                stroke={ev.event_severity === 'high' ? 'var(--color-critical)' : 'var(--color-warning)'}
                strokeDasharray="3 3"
                strokeWidth={1}
              />
            ))}
            <Line
              type="monotone"
              dataKey={dataKey}
              stroke="var(--color-nominal)"
              strokeWidth={1.5}
              dot={false}
              isAnimationActive={false}
            />
          </LineChart>
        </ResponsiveContainer>
      </div>
    </div>
  );
}
