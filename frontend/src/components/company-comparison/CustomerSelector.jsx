import React, { useState, useEffect, useRef } from 'react';
import Icon from '../common/Icon';
import { customerService } from '../../services/crmService';
import useDebounce from '../../hooks/useDebounce';

export default function CustomerSelector({ customers, selectedCustomers, onSelect }) {
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
    async function searchCustomers() {
      if (!debouncedSearch || debouncedSearch.trim().length < 2) {
        if (active) setResults([]);
        return;
      }
      
      setIsLoading(true);
      try {
        const res = await customerService.getCustomers({ search: debouncedSearch.trim(), limit: 8 });
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
    
    searchCustomers();
    return () => { active = false; };
  }, [debouncedSearch]);

  const handleSelect = (customer) => {
    onSelect(customer);
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
          placeholder="Search customers to compare..."
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
          {results.map(c => {
            const isSelected = selectedCustomers.some(sc => sc.customer_id === c.customer_id);
            return (
              <div
                key={c.customer_id}
                onClick={() => !isSelected && handleSelect(c)}
                style={{ padding: '12px 16px', borderBottom: '1px solid var(--border-soft)', cursor: isSelected ? 'not-allowed' : 'pointer', opacity: isSelected ? 0.5 : 1, display: 'flex', justifyContent: 'space-between', alignItems: 'center', background: isSelected ? 'var(--bg-light)' : 'transparent' }}
                onMouseEnter={(e) => { if (!isSelected) e.currentTarget.style.background = 'var(--bg-light)'; }}
                onMouseLeave={(e) => { if (!isSelected) e.currentTarget.style.background = 'transparent'; }}
              >
                <div>
                  <div style={{ fontWeight: 600, color: 'var(--ink-dark)' }}>{c.company?.company_name || c.customer_id}</div>
                  <div style={{ fontSize: '12px', color: 'var(--ink-mute)' }}>Tier: {c.customer_tier || 'N/A'} • {c.customer_status}</div>
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
