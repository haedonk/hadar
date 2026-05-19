import { useState, useEffect } from 'react';
import StatusBar from '../components/StatusBar.jsx';
import Sidebar from '../components/Sidebar.jsx';
import AnomalyFeed from '../components/AnomalyFeed.jsx';

function useWideLayout() {
  const [wide, setWide] = useState(() => window.matchMedia('(min-width: 900px)').matches);
  useEffect(() => {
    const mq = window.matchMedia('(min-width: 900px)');
    const handler = e => setWide(e.matches);
    mq.addEventListener('change', handler);
    return () => mq.removeEventListener('change', handler);
  }, []);
  return wide;
}

export default function Dashboard() {
  const [activeFilter, setActiveFilter] = useState('open');
  const [expandedId, setExpandedId] = useState(null);
  const showSidebar = useWideLayout();

  function handleToggleExpand(id) {
    setExpandedId(prev => (prev === id ? null : id));
  }

  return (
    <div
      style={{
        display: 'flex',
        flexDirection: 'column',
        height: '100dvh',
        background: 'var(--color-bg-base)',
        overflow: 'hidden',
      }}
    >
      <StatusBar />

      <div
        style={{
          display: 'flex',
          flex: 1,
          minHeight: 0,
          overflow: 'hidden',
        }}
      >
        {showSidebar && <Sidebar />}

        <main
          style={{
            flex: 1,
            minWidth: 0,
            minHeight: 0,
            overflow: 'hidden',
            display: 'flex',
            flexDirection: 'column',
          }}
        >
          <AnomalyFeed
            activeFilter={activeFilter}
            onFilterChange={setActiveFilter}
            expandedId={expandedId}
            onToggleExpand={handleToggleExpand}
          />
        </main>
      </div>
    </div>
  );
}
