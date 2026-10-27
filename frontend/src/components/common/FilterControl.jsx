import React from 'react';
import Chip from './Chip';
import Icon from './Icon';
import SearchInput from './SearchInput';

export default function FilterControl({ searchValue, onSearchChange, searchPlaceholder, chips = [] }) {
  return (
    <div className="toolbar">
      <div className="toolbar-search">
        <SearchInput value={searchValue} onChange={onSearchChange} placeholder={searchPlaceholder} />
      </div>
      <div className="chip-row">
        {chips.map((chip, idx) => (
          <Chip key={idx} label={chip.label} active={chip.active} onClick={chip.onClick} />
        ))}
      </div>
    </div>
  );
}
