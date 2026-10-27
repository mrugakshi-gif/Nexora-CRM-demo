import React from 'react';

export default function Badge({ text, kind = 'neutral', className = '' }) {
  return (
    <span className={`badge ${kind} ${className}`}>
      <span className="dotb"></span>
      {text}
    </span>
  );
}
