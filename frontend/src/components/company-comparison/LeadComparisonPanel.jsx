import React, { useState, useEffect } from 'react';
import LeadSelector from './LeadSelector';
import LeadComparisonTable from './LeadComparisonTable';
import Icon from '../common/Icon';
import api from '../../api';

export default function LeadComparisonPanel({ leads }) {
  const [selectedLeads, setSelectedLeads] = useState([]);
  const [metrics, setMetrics] = useState({});
  const [isLoading, setIsLoading] = useState(false);
  const [hasError, setHasError] = useState(false);
  const [initialized, setInitialized] = useState(false);

  useEffect(() => {
    let active = true;
    async function initDefaults() {
      if (initialized) return;
      try {
        const res = await api.get('/api/compare/top-leads');
        const tops = res.data || [];
        if (active && tops.length > 0) {
          setSelectedLeads(tops);
          setInitialized(true);
        }
      } catch (err) {
        console.warn("Failed to fetch top leads", err);
      }
    }
    initDefaults();
    return () => { active = false; };
  }, [initialized]);

  const handleSelect = (lead) => {
    if (selectedLeads.length < 3 && !selectedLeads.some(l => l.lead_id === lead.lead_id)) {
      setSelectedLeads([...selectedLeads, lead]);
    }
  };

  const handleRemove = (id) => {
    setSelectedLeads(selectedLeads.filter(l => l.lead_id !== id));
  };

  useEffect(() => {
    let active = true;
    const fetchMetrics = async () => {
      if (selectedLeads.length === 0) {
        if (active) setMetrics({});
        return;
      }
      setIsLoading(true);
      setHasError(false);
      try {
        const ids = selectedLeads.map(l => l.lead_id).join(',');
        const res = await api.get(`/api/compare/leads?ids=${ids}`);
        if (active) {
          setMetrics(res.data);
        }
      } catch (e) {
        console.error("Error fetching lead comparison metrics:", e);
        if (active) setHasError(true);
      } finally {
        if (active) setIsLoading(false);
      }
    };
    fetchMetrics();
    return () => { active = false; };
  }, [selectedLeads]);

  return (
    <div className="card" style={{ padding: '24px 32px' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '20px', flexWrap: 'wrap', gap: '12px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          <Icon name="target" size={28} color="var(--accent-primary)" stroke={2} />
          <div>
            <h2 className="section-title" style={{ fontSize: '22px', marginBottom: '4px', color: 'var(--heading-primary)' }}>Lead Comparison</h2>
            <p style={{ color: 'var(--ink-mute)', fontSize: '14px', margin: 0 }}>Compare pipeline prospects and their engagement</p>
          </div>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <div style={{ padding: '6px 12px', background: 'var(--accent-primary)', border: '1px solid var(--border-soft)', borderRadius: '8px', fontSize: '14px', fontWeight: 600, color: '#ffffff', display: 'flex', alignItems: 'center', gap: '8px' }}>
            <Icon name="layers" size={16} /> {selectedLeads.length} selected
          </div>
          <span style={{ fontSize: '13px', color: 'var(--ink-soft)' }}>(Max 3)</span>
        </div>
      </div>

      <div style={{ display: 'flex', flexWrap: 'wrap', gap: '12px', marginBottom: '16px' }}>
        {selectedLeads.map(lead => (
          <div key={lead.lead_id} style={{
            display: 'flex', alignItems: 'center', gap: '8px',
            padding: '6px 12px', background: 'var(--bg-subtle)',
            border: '1px solid var(--border)', borderRadius: '6px',
            fontSize: '14px', fontWeight: 700, color: 'var(--heading-primary)',
            boxShadow: '0 1px 2px rgba(0,0,0,0.05)'
          }}>
            <strong>{lead.contact?.full_name || lead.company?.company_name || lead.lead_id}</strong>
            <button
              onClick={() => handleRemove(lead.lead_id)}
              style={{ background: 'none', border: 'none', cursor: 'pointer', display: 'flex', alignItems: 'center', padding: '2px', color: 'var(--ink-soft)' }}
            >
              <Icon name="x" size={16} />
            </button>
          </div>
        ))}
      </div>

      <div style={{ marginBottom: '24px' }}>
        <LeadSelector selectedLeads={selectedLeads} onSelect={handleSelect} />
      </div>

      {hasError ? (
        <div style={{ padding: '40px 20px', textAlign: 'center', background: 'var(--bg-light)', borderRadius: '8px', border: '1px dashed var(--border)' }}>
          <p style={{ color: 'var(--danger)', fontSize: '14px', fontWeight: 500 }}>Unable to load lead comparison data.</p>
        </div>
      ) : isLoading ? (
        <div style={{ padding: '40px 20px', textAlign: 'center', color: 'var(--ink-mute)', fontSize: '14px' }}>
          Loading metrics...
        </div>
      ) : (
        <div style={{ marginBottom: '24px' }}>
          <LeadComparisonTable selectedLeads={selectedLeads} metrics={metrics} />
        </div>
      )}
    </div>
  );
}
