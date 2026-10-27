import React from 'react';
import SearchInput from '../SearchInput';

export default function FilterBar({ 
  searchPlaceholder = 'Search...',
  searchValue,
  onSearchChange,
  children // Optional filter dropdowns or actions
}) {
  return (
    <div className="toolbar">
      <div className="toolbar-search">
        <SearchInput 
          placeholder={searchPlaceholder} 
          value={searchValue} 
          onChange={(e) => onSearchChange(e.target.value)} 
        />
      </div>
      {children && (
        <div style={{ display: 'flex', gap: '12px', flexWrap: 'wrap' }}>
          {children}
        </div>
      )}
    </div>
  );
}
