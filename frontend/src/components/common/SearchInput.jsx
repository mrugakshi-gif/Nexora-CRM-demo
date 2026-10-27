import React from 'react';
import Icon from './Icon';

export default function SearchInput({ value, onChange, placeholder = 'Search...' }) {
  return (
    <div className="search-wrap" style={{ position: 'relative' }}>
      <input 
        type="text" 
        value={value} 
        onChange={onChange} 
        placeholder={placeholder} 
        autoComplete="off" 
      />
      {value ? (
        <button
          onClick={() => onChange({ target: { value: '' } })}
          aria-label="Clear search"
          style={{
            position: 'absolute',
            right: '8px',
            top: '50%',
            transform: 'translateY(-50%)',
            background: 'none',
            border: 'none',
            cursor: 'pointer',
            padding: '2px',
            color: 'var(--ink-mute)',
            display: 'flex',
            alignItems: 'center',
            lineHeight: 1,
          }}
        >
          <Icon name="x" size={14} stroke={2} />
        </button>
      ) : (
        <span className="icon">
          <Icon name="search" size={15} color="var(--ink-mute)" stroke={1.8} />
        </span>
      )}
    </div>
  );
}
