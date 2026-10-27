import React, { useState, useEffect } from 'react';
import Icon from '../common/Icon';
import SearchInput from '../common/SearchInput';
import { companyService } from '../../services/crmService';

export default function CompanySelector({ companies, selectedCompanies, onSelect, onRemove }) {
  const [searchTerm, setSearchTerm] = useState('');
  const [isOpen, setIsOpen] = useState(false);
  const [searchResults, setSearchResults] = useState([]);
  
  useEffect(() => {
    let active = true;
    
    const fetchSearch = async () => {
      if (!searchTerm) {
        if (active) setSearchResults(companies);
        return;
      }
      try {
        const res = await companyService.getCompanies({ search: searchTerm, limit: 10 });
        if (active) {
          setSearchResults(res.data?.items || res.data?.data || []);
        }
      } catch (e) {
        console.error(e);
        if (active) setSearchResults([]);
      }
    };

    const timer = setTimeout(() => {
      fetchSearch();
    }, 300);

    return () => {
      active = false;
      clearTimeout(timer);
    };
  }, [searchTerm, companies]);

  const filteredCompanies = searchResults.filter(c => 
    c && !selectedCompanies.find(sc => sc && sc.company_id === c.company_id)
  );

  return (
    <div style={{ marginBottom: '24px' }}>
      {selectedCompanies.length < 5 ? (
        <div style={{ position: 'relative', width: '300px' }}>
          <div onClick={() => setIsOpen(true)}>
            <SearchInput 
              value={searchTerm} 
              onChange={(e) => { setSearchTerm(e.target.value); setIsOpen(true); }} 
              placeholder="Select Company to compare..." 
            />
          </div>
          
          {isOpen && (
            <div style={{
              position: 'absolute', top: '100%', left: 0, right: 0, 
              background: 'white', border: '1px solid var(--border)', 
              borderRadius: '6px', marginTop: '4px', zIndex: 10,
              boxShadow: '0 4px 12px rgba(0,0,0,0.1)', maxHeight: '200px', overflowY: 'auto'
            }}>
              {filteredCompanies.length === 0 ? (
                <div style={{ padding: '12px', fontSize: '13px', color: 'var(--ink-mute)', textAlign: 'center' }}>No companies found</div>
              ) : (
                filteredCompanies.slice(0, 10).map(c => (
                  <div 
                    key={c.company_id}
                    onMouseDown={(e) => {
                      e.preventDefault();
                      onSelect(c);
                      setSearchTerm('');
                      setIsOpen(false);
                    }}
                    style={{
                      padding: '8px 12px', fontSize: '13px', cursor: 'pointer',
                      borderBottom: '1px solid var(--border-light)'
                    }}
                    onMouseEnter={(e) => e.target.style.background = 'var(--bg)'}
                    onMouseLeave={(e) => e.target.style.background = 'white'}
                  >
                    {c.company_name}
                  </div>
                ))
              )}
            </div>
          )}
        </div>
      ) : (
        <div style={{ fontSize: '12px', color: 'var(--warning)', marginTop: '8px' }}>
          Maximum of 5 companies can be compared at once.
        </div>
      )}
      
      {isOpen && (
        <div 
          style={{ position: 'fixed', top: 0, left: 0, right: 0, bottom: 0, zIndex: 9 }} 
          onMouseDown={() => setIsOpen(false)}
        />
      )}
    </div>
  );
}
