import React from 'react';
import DataTable from '../common/DataTable';
import Badge from '../common/Badge';

export default function CustomerComparisonTable({ selectedCustomers, metrics }) {
  if (selectedCustomers.length < 2) {
    return (
      <div style={{ padding: '40px 20px', textAlign: 'center', background: 'var(--bg-light)', borderRadius: '8px', border: '1px dashed var(--border)' }}>
        <p style={{ color: 'var(--ink-mute)', fontSize: '14px' }}>Select at least 2 customers to compare.</p>
      </div>
    );
  }

  const formatCurrency = (val) => {
    if (!val) return '₹0';
    return new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR', maximumFractionDigits: 0 }).format(val);
  };
  const formatDate = (dateStr) => {
    if (!dateStr) return '—';
    return new Date(dateStr).toLocaleDateString('en-US', { year: 'numeric', month: 'short', day: 'numeric' });
  };

  const headers = [
    'CUSTOMER',
    'STATUS',
    'TIER & CONTRACT',
    'DATES',
    'TOTAL SPEND',
    'ORDERS',
    'SUPPORT CASES',
    'CSM'
  ];

  const rows = selectedCustomers.map(c => {
    const m = metrics[c.customer_id] || {};

    const customerCell = (
      <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
        <div style={{
          width: '32px', height: '32px', borderRadius: '50%',
          background: 'var(--accent-primary)', color: '#ffffff',
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          fontWeight: 700, fontSize: '13px', flexShrink: 0
        }}>
          {(m.customer_name || 'C').substring(0, 1).toUpperCase()}
        </div>
        <div>
          <div style={{ fontSize: '14px', fontWeight: 700, color: 'var(--heading-primary)', lineHeight: '1.2' }}>
            {m.customer_name || 'Unknown'}
          </div>
        </div>
      </div>
    );

    const statusCell = (() => {
      const val = m.customer_status;
      if (val === 'Active') return <Badge text="Active" color="success" />;
      if (val === 'Paused') return <Badge text="Paused" color="warning" />;
      if (val === 'At Risk') return <Badge text="At Risk" color="danger" />;
      return <Badge text={val || 'Unknown'} color="neutral" />;
    })();

    const tierCell = (
      <div>
        <div style={{ fontSize: '13px', fontWeight: 600, color: 'var(--heading-primary)' }}>{m.customer_tier || '—'}</div>
        <div style={{ fontSize: '11px', color: 'var(--ink-mute)' }}>{m.contract_type || '—'}</div>
      </div>
    );

    const datesCell = (
      <div>
        <div style={{ fontSize: '12px', color: 'var(--ink-dark)' }}>Since: {formatDate(m.customer_since)}</div>
        <div style={{ fontSize: '11px', color: 'var(--ink-mute)', marginTop: '2px' }}>Renews: {formatDate(m.renewal_date)}</div>
      </div>
    );

    const spendCell = (
      <div style={{ fontSize: '14px', fontWeight: 700, color: 'var(--success)' }}>
        {formatCurrency(m.total_revenue)}
      </div>
    );
    
    const ordersCell = <div style={{ fontWeight: 600 }}>{m.total_orders || 0}</div>;
    const casesCell = <div style={{ fontWeight: 600 }}>{m.support_cases || 0}</div>;
    
    const csmCell = <div style={{ fontSize: '13px', color: 'var(--ink-dark)' }}>{m.csm_name || '—'}</div>;

    return [
      customerCell, statusCell, tierCell, datesCell, spendCell, ordersCell, casesCell, csmCell
    ];
  });

  return (
    <div style={{ overflowX: 'auto', margin: '0 -20px', padding: '0 20px' }}>
      <DataTable headers={headers} rows={rows} rightCols={[4, 5, 6]} />
    </div>
  );
}
