import React from 'react';
import Icon from './Icon';

export default function Modal({ isOpen, onClose, title, children, footer, maxWidth = 420 }) {
  if (!isOpen) return null;

  return (
    <div id="modal-backdrop" onClick={(e) => e.target.id === 'modal-backdrop' && onClose()}>
      <div className="modal" style={{ maxWidth }} role="dialog" aria-modal="true">
        <div className="modal-header">
          <span className="modal-title">{title}</span>
          <span className="modal-close" onClick={onClose}><Icon name="x" size={16} color="var(--ink-mute)" stroke={2} /></span>
        </div>
        <div className="modal-body">
          {children}
        </div>
        {footer && <div className="modal-footer">{footer}</div>}
      </div>
    </div>
  );
}
