import React from 'react';

export default function Avatar({ name, size = 30, bg = 'var(--brown)', className = '', style = {} }) {
  const initials = (name || '').trim().split(/\s+/).slice(0, 2).map(p => p[0]).join('').toUpperCase();
  const fontSize = Math.round(size * 0.38);

  return (
    <div 
      className={`avatar ${className}`} 
      style={{ width: size, height: size, fontSize, background: bg, ...style }}
    >
      {initials}
    </div>
  );
}
