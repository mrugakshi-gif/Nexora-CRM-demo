import React from 'react';
import Button from '../Button';

export default function TableEmptyState({ title = 'No Data Found', description, actionLabel, onAction }) {
  return (
    <div className="empty-state">
      <div className="empty-ic">
        <svg width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="var(--ink-mute)" strokeWidth="2" strokeLinecap="round" strokeLinejoin="round">
          <circle cx="11" cy="11" r="8"></circle>
          <line x1="21" y1="21" x2="16.65" y2="16.65"></line>
        </svg>
      </div>
      <div className="empty-title">{title}</div>
      {description && <div className="empty-desc">{description}</div>}
      {actionLabel && onAction && (
        <Button variant="secondary" onClick={onAction} style={{ marginTop: '12px' }}>
          {actionLabel}
        </Button>
      )}
    </div>
  );
}
