import React from 'react';

export default function TabNav({ tabs = [], currentTab, onTabChange }) {
  return (
    <div className="tabbar">
      {tabs.map((t) => (
        <div 
          key={t}
          className={`tab ${t === currentTab ? 'active' : ''}`}
          onClick={() => onTabChange && onTabChange(t)}
        >
          {t}
        </div>
      ))}
    </div>
  );
}
