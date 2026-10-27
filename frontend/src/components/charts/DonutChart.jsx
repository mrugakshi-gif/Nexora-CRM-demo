import React from 'react';

// Basic wrapper for future Recharts integration
export default function DonutChartWrapper({ data = [], size = 120 }) {
  return (
    <div style={{ width: size, height: size, borderRadius: '50%', background: 'var(--white)', border: '1px dashed var(--border)', display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'var(--ink-mute)', fontSize: '11px', textAlign: 'center' }}>
      DonutChart (F1)
    </div>
  );
}
