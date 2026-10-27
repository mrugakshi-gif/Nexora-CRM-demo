import React from 'react';

export default function ScoreBar({ score, max = 100 }) {
  const pct = Math.round((score / max) * 100);
  const color = pct >= 70 ? 'var(--success)' : (pct >= 40 ? 'var(--warning)' : 'var(--danger)');
  
  return (
    <div className="score-wrap">
      <div className="score-track">
        <div className="score-fill" style={{ width: `${pct}%`, background: color }}></div>
      </div>
      <span className="score-num">{score}</span>
    </div>
  );
}
