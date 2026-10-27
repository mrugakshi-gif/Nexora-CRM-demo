import React from 'react';
import DataTable from '../common/DataTable';
import Badge from '../common/Badge';

export default function LeadComparisonTable({ selectedLeads, metrics }) {
  if (selectedLeads.length < 2) {
    return (
      <div style={{ padding: '40px 20px', textAlign: 'center', background: 'var(--bg-light)', borderRadius: '8px', border: '1px dashed var(--border)' }}>
        <p style={{ color: 'var(--ink-mute)', fontSize: '14px' }}>Select at least 2 leads to compare.</p>
      </div>
    );
  }

  const formatCurrency = (val) => {
    if (!val) return '—';
    return new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR', maximumFractionDigits: 0 }).format(val);
  };

  const headers = [
    'LEAD',
    'STATUS',
    'COMPANY SIZE',
    'SOURCE',
    'CAMPAIGN',
    'INDUSTRY INTEREST',
    'ACTIVITY',
    'REP'
  ];

  const rows = selectedLeads.map(l => {
    const m = metrics[l.lead_id] || {};
    const title = m.lead_name || 'Unknown';

    const leadCell = (
      <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
        <div style={{
          width: '32px', height: '32px', borderRadius: '50%',
          background: 'var(--accent-primary)', color: '#ffffff',
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          fontWeight: 700, fontSize: '13px', flexShrink: 0
        }}>
          {title.substring(0, 1).toUpperCase()}
        </div>
        <div>
          <div style={{ fontSize: '14px', fontWeight: 700, color: 'var(--heading-primary)', lineHeight: '1.2' }}>
            {title}
          </div>
        </div>
      </div>
    );

    const statusCell = (() => {
      const val = m.lead_status;
      if (val === 'Converted' || val === 'Qualified (MQL)' || val === 'Sales Qualified (SQL)') return <Badge text={val} color="success" />;
      if (val === 'Dead' || val === 'Disqualified') return <Badge text={val} color="danger" />;
      return <Badge text={val || 'New'} color="info" />;
    })();


    const sizeCell = <div style={{ fontSize: '13px', color: 'var(--ink-dark)' }}>{m.company_size_at_lead_time || '—'}</div>;
    const sourceCell = <div style={{ fontSize: '13px', color: 'var(--ink-dark)' }}>{m.lead_source || '—'}</div>;
    const campaignCell = <div style={{ fontSize: '13px', color: 'var(--ink-dark)' }}>{m.campaign || '—'}</div>;
    const industryCell = <div style={{ fontSize: '13px', color: 'var(--ink-dark)' }}>{m.industry_interest || '—'}</div>;
    
    const activityCell = <div style={{ fontWeight: 600 }}>{m.activity_count || 0}</div>;
    const repCell = <div style={{ fontSize: '13px', color: 'var(--ink-dark)' }}>{m.assigned_rep || '—'}</div>;

    return [
      leadCell, statusCell, sizeCell, sourceCell, campaignCell, industryCell, activityCell, repCell
    ];
  });

  return (
    <div style={{ overflowX: 'auto', margin: '0 -20px', padding: '0 20px' }}>
      <DataTable headers={headers} rows={rows} rightCols={[6]} />
    </div>
  );
}
