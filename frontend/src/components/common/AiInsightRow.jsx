import React from 'react';
import Icon from './Icon';

export default function AiInsightRow({ icon, color, title, desc }) {
  return (
    <div className="ai-insight-row">
      <div className="ai-ic" style={{ background: `${color}22` }}>
        <Icon name={icon} size={16} color={color} stroke={2} />
      </div>
      <div>
        <div style={{ fontSize: '12.5px', fontWeight: 700, color: 'var(--heading-primary)' }}>{title}</div>
        <div style={{ fontSize: '11.3px', color: 'var(--ink-soft)', marginTop: '2px', lineHeight: 1.5 }}>
          {desc}
        </div>
      </div>
    </div>
  );
}
