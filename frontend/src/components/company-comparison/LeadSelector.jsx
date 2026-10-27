import React, { useState, useEffect, useRef } from 'react';
import Icon from '../common/Icon';
import { leadService } from '../../services/crmService';
import useDebounce from '../../hooks/useDebounce';

export default function LeadSelector({ selectedLeads, onSelect }) {
  const [searchTerm, setSearchTerm] = useState('');
  const [isFocused, setIsFocused] = useState(false);
  const [results, setResults] = useState([]);
  const [isLoading, setIsLoading] = useState(false);
  const wrapperRef = useRef(null);
  const debouncedSearch = useDebounce(searchTerm, 300);

  useEffect(() => {
    function handleClickOutside(event) {
      if (wrapperRef.current && !wrapperRef.current.contains(event.target)) {
        setIsFocused(false);
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  useEffect(() => {
    let active = true;
    async function searchLeads() {
      if (!debouncedSearch || debouncedSearch.trim().length < 2) {
        if (active) setResults([]);
        return;
      }
      setIsLoading(true);
      try {
        const res = await leadService.getLeads({ search: debouncedSearch.trim(), limit: 8 });
        if (active) {
          const items = res.data?.items || res.data || [];
          setResults(items);
        }
      } catch (err) {
        console.warn("Search failed", err);
      } finally {
        if (active) setIsLoading(false);
      }
    }
    searchLeads();
    return () => { active = false; };
  }, [debouncedSearch]);

  const handleSelect = (lead) => {
    onSelect(lead);
    setSearchTerm('');
    setResults([]);
    setIsFocused(false);
  };

  return (
    <div ref={wrapperRef} style={{ position: 'relative', width: '100%', maxWidth: '500px' }}>
      <div style={{ position: 'relative' }}>
        <div style={{ position: 'absolute', left: '14px', top: '50%', transform: 'translateY(-50%)', color: 'var(--ink-mute)', pointerEvents: 'none' }}>
          <Icon name="search" size={18} />
        </div>
        <input
          type="text"
          placeholder="Search leads to compare..."
          value={searchTerm}
          onChange={(e) => setSearchTerm(e.target.value)}
          onFocus={() => setIsFocused(true)}
          style={{ width: '100%', padding: '12px 14px 12px 42px', fontSize: '15px', border: '1px solid var(--border)', borderRadius: '8px', background: 'var(--bg-light)', outline: 'none' }}
        />
        {isLoading && (
          <div style={{ position: 'absolute', right: '14px', top: '50%', transform: 'translateY(-50%)', color: 'var(--ink-mute)' }}>
            <span style={{ fontSize: '12px' }}>Loading...</span>
          </div>
        )}
      </div>

      {isFocused && searchTerm.trim().length >= 2 && results.length > 0 && (
        <div style={{ position: 'absolute', top: 'calc(100% + 8px)', left: 0, right: 0, background: 'var(--white)', border: '1px solid var(--border)', borderRadius: '8px', boxShadow: '0 4px 12px rgba(0,0,0,0.1)', zIndex: 10, maxHeight: '300px', overflowY: 'auto' }}>
          {results.map(l => {
            const isSelected = selectedLeads.some(sl => sl.lead_id === l.lead_id);
            const title = l.contact?.full_name || l.company?.company_name || l.lead_id;
            return (
              <div
                key={l.lead_id}
                onClick={() => !isSelected && handleSelect(l)}
                style={{ padding: '12px 16px', borderBottom: '1px solid var(--border-soft)', cursor: isSelected ? 'not-allowed' : 'pointer', opacity: isSelected ? 0.5 : 1, display: 'flex', justifyContent: 'space-between', alignItems: 'center', background: isSelected ? 'var(--bg-light)' : 'transparent' }}
                onMouseEnter={(e) => { if (!isSelected) e.currentTarget.style.background = 'var(--bg-light)'; }}
                onMouseLeave={(e) => { if (!isSelected) e.currentTarget.style.background = 'transparent'; }}
              >
                <div>
                  <div style={{ fontWeight: 600, color: 'var(--ink-dark)' }}>{title}</div>
                  <div style={{ fontSize: '12px', color: 'var(--ink-mute)' }}>Status: {l.lead_status}</div>
                </div>
                {isSelected && (
                  <span style={{ fontSize: '12px', fontWeight: 600, color: 'var(--ink-soft)' }}>Selected</span>
                )}
              </div>
            );
          })}
        </div>
      )}
    </div>
  );
}
