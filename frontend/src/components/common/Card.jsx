import React from 'react';

export default function Card({ children, className = '', style = {} }) {
  return (
    <div className={`card ${className}`} style={{ padding: '18px 20px', ...style }}>
      {children}
    </div>
  );
}
