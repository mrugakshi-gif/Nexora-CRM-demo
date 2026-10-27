import React from 'react';

export default function PageHeader({ title, desc, actions }) {
  return (
    <div className="page-header">
      <div>
        <h1 className="page-title">{title}</h1>
        <p className="page-desc">{desc}</p>
      </div>
      {actions && <div className="page-actions">{actions}</div>}
    </div>
  );
}
