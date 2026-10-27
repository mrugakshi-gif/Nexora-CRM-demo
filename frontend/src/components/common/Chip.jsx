import React from 'react';
import Icon from './Icon';

export default function Chip({ label, active = false, onClick, className = '' }) {
  return (
    <div 
      className={`chip ${active ? 'active' : ''} ${className}`} 
      onClick={onClick}
    >
      {label}
      <Icon name="chevrondown" size={12} color="var(--ink-mute)" stroke={2} />
    </div>
  );
}
