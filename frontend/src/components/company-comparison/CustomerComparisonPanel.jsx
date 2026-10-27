import React, { useState, useEffect } from 'react';
import CustomerSelector from './CustomerSelector';
import CustomerComparisonTable from './CustomerComparisonTable';
import Icon from '../common/Icon';
import api from '../../api';

export default function CustomerComparisonPanel({ customers }) {
  const [selectedCustomers, setSelectedCustomers] = useState([]);
  const [metrics, setMetrics] = useState({});
  const [isLoading, setIsLoading] = useState(false);
  const [hasError, setHasError] = useState(false);
  const [initialized, setInitialized] = useState(false);

  useEffect(() => {
    let active = true;
    async function initDefaults() {
      if (initialized) return;
      try {
        const res = await api.get('/api/analytics/revenue/top-customers?limit=3');
        const tops = res.data || [];
        if (active && tops.length > 0) {
          setSelectedCustomers(tops.map(t => ({
            customer_id: t.customer_id,
            company: { company_name: t.company_name }
          })));
          setInitialized(true);
        }
      } catch (err) {
        console.warn("Failed to fetch top customers", err);
      }
    }
    initDefaults();
    return () => { active = false; };
  }, [initialized]);

  const handleSelect = (customer) => {
    if (selectedCustomers.length < 3 && !selectedCustomers.some(c => c.customer_id === customer.customer_id)) {
      setSelectedCustomers([...selectedCustomers, customer]);
    }
  };

  const handleRemove = (id) => {
    setSelectedCustomers(selectedCustomers.filter(c => c.customer_id !== id));
  };

  useEffect(() => {
    let active = true;
    const fetchMetrics = async () => {
      if (selectedCustomers.length === 0) {
        if (active) setMetrics({});
        return;
      }
      setIsLoading(true);
      setHasError(false);
      try {
        const ids = selectedCustomers.map(c => c.customer_id).join(',');
        const res = await api.get(`/api/compare/customers?ids=${ids}`);
        if (active) {
          setMetrics(res.data);
        }
      } catch (e) {
        console.error("Error fetching customer comparison metrics:", e);
        if (active) setHasError(true);
      } finally {
        if (active) setIsLoading(false);
      }
    };
    fetchMetrics();
    return () => { active = false; };
  }, [selectedCustomers]);

  return (
    <div className="card" style={{ padding: '24px 32px' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '20px', flexWrap: 'wrap', gap: '12px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          <Icon name="users" size={28} color="var(--accent-primary)" stroke={2} />
          <div>
            <h2 className="section-title" style={{ fontSize: '22px', marginBottom: '4px', color: 'var(--heading-primary)' }}>Customer Comparison</h2>
            <p style={{ color: 'var(--ink-mute)', fontSize: '14px', margin: 0 }}>Compare active customers, spend, and support metrics</p>
          </div>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <div style={{ padding: '6px 12px', background: 'var(--accent-primary)', border: '1px solid var(--border-soft)', borderRadius: '8px', fontSize: '14px', fontWeight: 600, color: '#ffffff', display: 'flex', alignItems: 'center', gap: '8px' }}>
            <Icon name="layers" size={16} /> {selectedCustomers.length} selected
          </div>
          <span style={{ fontSize: '13px', color: 'var(--ink-soft)' }}>(Max 3)</span>
        </div>
      </div>

      <div style={{ display: 'flex', flexWrap: 'wrap', gap: '12px', marginBottom: '16px' }}>
        {selectedCustomers.map(customer => (
          <div key={customer.customer_id} style={{
            display: 'flex', alignItems: 'center', gap: '8px',
            padding: '6px 12px', background: 'var(--bg-subtle)',
            border: '1px solid var(--border)', borderRadius: '6px',
            fontSize: '14px', fontWeight: 700, color: 'var(--heading-primary)',
            boxShadow: '0 1px 2px rgba(0,0,0,0.05)'
          }}>
            <strong>{customer.company?.company_name || customer.customer_id}</strong>
            <button
              onClick={() => handleRemove(customer.customer_id)}
              style={{ background: 'none', border: 'none', cursor: 'pointer', display: 'flex', alignItems: 'center', padding: '2px', color: 'var(--ink-soft)' }}
            >
              <Icon name="x" size={16} />
            </button>
          </div>
        ))}
      </div>

      <div style={{ marginBottom: '24px' }}>
        <CustomerSelector selectedCustomers={selectedCustomers} onSelect={handleSelect} />
      </div>

      {hasError ? (
        <div style={{ padding: '40px 20px', textAlign: 'center', background: 'var(--bg-light)', borderRadius: '8px', border: '1px dashed var(--border)' }}>
          <p style={{ color: 'var(--danger)', fontSize: '14px', fontWeight: 500 }}>Unable to load customer comparison data.</p>
        </div>
      ) : isLoading ? (
        <div style={{ padding: '40px 20px', textAlign: 'center', color: 'var(--ink-mute)', fontSize: '14px' }}>
          Loading metrics...
        </div>
      ) : (
        <div style={{ marginBottom: '24px' }}>
          <CustomerComparisonTable selectedCustomers={selectedCustomers} metrics={metrics} />
        </div>
      )}
    </div>
  );
}
