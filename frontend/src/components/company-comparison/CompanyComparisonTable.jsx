import React from 'react';
import DataTable from '../common/DataTable';
import Badge from '../common/Badge';
import Icon from '../common/Icon';

export default function CompanyComparisonTable({ selectedCompanies, metrics }) {
  if (selectedCompanies.length < 2) {
    return (
      <div style={{ padding: '40px 20px', textAlign: 'center', background: 'var(--bg-light)', borderRadius: '8px', border: '1px dashed var(--border)' }}>
        <p style={{ color: 'var(--ink-mute)', fontSize: '14px' }}>Select at least 2 companies to compare.</p>
      </div>
    );
  }

  const formatCurrency = (val) => {
    if (val === 0 || !val) return '₹0';
    return new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR', maximumFractionDigits: 0 }).format(val);
  };

  const headers = [
    'COMPANY NAME',
    'INDUSTRY & DETAILS',
    'LOCATION & TYPE',
    'STATUS',
    'WON PIPELINE',
    'TOTAL REVENUE',
    'ORDERS & AOV',
    'TIER',
    'CHURN RISK'
  ];

  const rows = selectedCompanies.map(c => {
    const m = metrics[c.company_id] || {};

    // 1. Company Column
    const companyCell = (
      <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
        <div style={{
          width: '32px', height: '32px', borderRadius: '50%',
          background: 'var(--accent-primary)', color: '#ffffff',
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          fontWeight: 700, fontSize: '13px', flexShrink: 0
        }}>
          {(c.company_name || c.company_id || 'C').substring(0, 1).toUpperCase()}
        </div>
        <div>
          <div style={{ fontSize: '14px', fontWeight: 700, color: 'var(--heading-primary)', lineHeight: '1.2' }}>
            {c.company_name || c.company_id || 'Unnamed Company'}
          </div>
          {m.founded_year && m.founded_year !== '—' && (
            <span style={{ fontSize: '11px', color: 'var(--ink-mute)' }}>Est. {m.founded_year}</span>
          )}
        </div>
      </div>
    );

    // 2. Industry & Details
    const industryCell = (
      <div>
        <div style={{ fontSize: '13px', fontWeight: 600, color: 'var(--heading-primary)' }}>
          {m.industry || '—'}
        </div>
        <div style={{ display: 'flex', gap: '6px', marginTop: '4px', flexWrap: 'wrap' }}>
          {m.sub_industry && m.sub_industry !== '—' && (
            <span style={{ fontSize: '11px', background: 'var(--accent-tint)', color: 'var(--accent-primary)', padding: '2px 6px', borderRadius: '4px', fontWeight: 600 }}>
              {m.sub_industry}
            </span>
          )}
          {m.company_size && m.company_size !== '—' && (
            <span style={{ fontSize: '11px', background: 'var(--bg-subtle)', border: '1px solid var(--border-soft)', color: 'var(--ink-soft)', padding: '2px 6px', borderRadius: '4px', fontWeight: 500 }}>
              {m.company_size}
            </span>
          )}
        </div>
      </div>
    );

    // 3. Location & Type
    const locationCell = (
      <div>
        <div style={{ fontSize: '13px', color: 'var(--heading-primary)', fontWeight: 500 }}>
          {m.location || '—'}
        </div>
        {m.company_type && m.company_type !== '—' && (
          <div style={{ fontSize: '11px', color: 'var(--ink-mute)', marginTop: '2px' }}>
            {m.company_type}
          </div>
        )}
      </div>
    );

    // 4. Status
    const statusCell = (() => {
      const val = m.customer_status || m.account_status || 'Prospect';
      if (val === 'Active' || val === 'Active Customer') return <Badge text={val} color="success" />;
      if (val === 'Paused') return <Badge text="Paused" color="warning" />;
      if (val === 'At Risk') return <Badge text="At Risk" color="danger" />;
      return <Badge text="Prospect" color="neutral" />;
    })();

    // 5. Won Pipeline
    const wonPipelineCell = (
      <div>
        <div style={{ fontSize: '13px', fontWeight: 700, color: 'var(--heading-primary)' }}>
          {formatCurrency(m.won_opps_val)}
        </div>
        <div style={{ fontSize: '11px', color: 'var(--ink-mute)' }}>
          {m.won_opps_count || 0} won deals
        </div>
      </div>
    );

    // 6. Total Revenue
    const revenueCell = (
      <div style={{ fontSize: '14px', fontWeight: 700, color: 'var(--success)' }}>
        {formatCurrency(m.revenue)}
      </div>
    );

    // 7. Orders & AOV
    const ordersCell = (
      <div>
        <div style={{ fontSize: '13px', fontWeight: 600, color: 'var(--heading-primary)' }}>
          {m.orders || 0} orders
        </div>
        <div style={{ fontSize: '11px', color: 'var(--ink-mute)' }}>
          Avg: {formatCurrency(m.aov)}
        </div>
      </div>
    );

    // 8. Tier
    const tierCell = m.tier && m.tier !== '—' ? (
      <Badge text={m.tier} color="info" />
    ) : (
      <span style={{ color: 'var(--ink-soft)' }}>—</span>
    );

    // 9. Churn Risk (ML)
    const churnCell = (() => {
      const val = m.churn_risk;
      if (val === 'Low') return <Badge text="Low" color="success" />;
      if (val === 'Medium') return <Badge text="Medium" color="warning" />;
      if (val === 'High') return <Badge text="High" color="danger" />;
      return <span style={{ color: 'var(--ink-soft)' }}>—</span>;
    })();

    return [
      companyCell,
      industryCell,
      locationCell,
      statusCell,
      wonPipelineCell,
      revenueCell,
      ordersCell,
      tierCell,
      churnCell
    ];
  });

  return (
    <div style={{ overflowX: 'auto', margin: '0 -20px', padding: '0 20px' }}>
      <DataTable headers={headers} rows={rows} rightCols={[4, 5, 6]} />
    </div>
  );
}
