import React from 'react';
import Icon from './Icon';

export default function KpiCard({ label, value, delta, dir = 'up', ctx, icon }) {
  const isUp = dir === 'up';
  return (
    <div className="kpi-card">
      <div className="kpi-top">
        <span className="kpi-label">{label}</span>
        <div className="kpi-icon">
          <Icon name={icon} size={15} color="var(--white)" stroke={1.9} />
        </div>
      </div>
      <div className="kpi-value">{value}</div>
      <div className="kpi-delta-row">
        <span className={`kpi-delta ${isUp ? 'up' : 'down'}`}>
          <Icon name={isUp ? 'arrowup' : 'arrowdown'} size={10} color="currentColor" stroke={2.6} />
          {delta}
        </span>
        <span className="kpi-ctx">{ctx}</span>
      </div>
    </div>
  );
}
