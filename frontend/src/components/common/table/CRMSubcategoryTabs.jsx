import React from 'react';

export default function CRMSubcategoryTabs({ categories, activeCategory, onSelect }) {
  return (
    <div style={{
      display: 'flex',
      gap: '8px',
      overflowX: 'auto',
      paddingBottom: '16px',
      marginBottom: '8px',
      borderBottom: '1px solid var(--border-light)',
      msOverflowStyle: 'none',  // IE and Edge
      scrollbarWidth: 'none'  // Firefox
    }}
    className="hide-scrollbar"
    >
      <style>{`
        .hide-scrollbar::-webkit-scrollbar {
          display: none;
        }
      `}</style>
      {categories.map(cat => {
        const isActive = activeCategory === cat.id;
        return (
          <button
            key={cat.id}
            onClick={() => onSelect(cat.id)}
            style={{
              padding: '6px 14px',
              borderRadius: '20px',
              border: isActive ? '1px solid var(--ink)' : '1px solid var(--gray-200)',
              background: isActive ? 'var(--ink)' : 'var(--white)',
              color: isActive ? 'var(--white)' : 'var(--slate)',
              fontWeight: isActive ? 600 : 500,
              fontSize: '13px',
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              gap: '6px',
              whiteSpace: 'nowrap',
              transition: 'all 0.2s ease',
              boxShadow: isActive ? '0 2px 4px rgba(0,0,0,0.1)' : 'none'
            }}
          >
            {cat.label}
            {cat.count !== undefined && (
              <span style={{
                background: isActive ? 'rgba(255,255,255,0.2)' : 'var(--gray-100)',
                color: isActive ? 'var(--white)' : 'var(--gray-500)',
                padding: '2px 6px',
                borderRadius: '10px',
                fontSize: '11px',
                fontWeight: 600
              }}>
                {cat.count}
              </span>
            )}
          </button>
        );
      })}
    </div>
  );
}
