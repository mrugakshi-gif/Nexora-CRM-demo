import React from 'react';
import DataTable from '../common/DataTable';
import Badge from '../common/Badge';

export default function ProductComparisonTable({ selectedProducts, metrics }) {
  if (selectedProducts.length < 2) {
    return (
      <div style={{ padding: '40px 20px', textAlign: 'center', background: 'var(--bg-light)', borderRadius: '8px', border: '1px dashed var(--border)' }}>
        <p style={{ color: 'var(--ink-mute)', fontSize: '14px' }}>Select at least 2 products to compare.</p>
      </div>
    );
  }

  const formatCurrency = (val) => {
    if (!val) return '₹0';
    return new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR', maximumFractionDigits: 0 }).format(val);
  };
  const formatPercent = (val) => {
    if (!val) return '0%';
    return `${val.toFixed(1)}%`;
  };

  const headers = [
    'PRODUCT',
    'CATEGORY',
    'PRICING MODEL',
    'LIST PRICE',
    'STATUS',
    'PIPELINE VALUE',
    'QUANTITY',
    'AVG DISCOUNT',
    'OPPORTUNITIES'
  ];

  const rows = selectedProducts.map(p => {
    const m = metrics[p.product_id] || {};

    const productCell = (
      <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
        <div style={{
          width: '32px', height: '32px', borderRadius: '50%',
          background: 'var(--accent-primary)', color: '#ffffff',
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          fontWeight: 700, fontSize: '13px', flexShrink: 0
        }}>
          {(m.product_name || 'P').substring(0, 1).toUpperCase()}
        </div>
        <div>
          <div style={{ fontSize: '14px', fontWeight: 700, color: 'var(--heading-primary)', lineHeight: '1.2' }}>
            {m.product_name || 'Unknown'}
          </div>
        </div>
      </div>
    );

    const categoryCell = <div style={{ fontSize: '13px', color: 'var(--ink-dark)' }}>{m.product_category || '—'}</div>;
    const pricingCell = <div style={{ fontSize: '13px', color: 'var(--ink-dark)' }}>{m.pricing_model || '—'}</div>;

    const listPriceCell = (
      <div style={{ fontSize: '14px', fontWeight: 600, color: 'var(--ink-dark)' }}>
        {formatCurrency(m.list_price_inr)}
      </div>
    );

    const statusCell = (() => {
      const val = m.is_active;
      if (val) return <Badge text="Active" color="success" />;
      return <Badge text="Inactive" color="neutral" />;
    })();

    const pipelineCell = (
      <div style={{ fontSize: '14px', fontWeight: 700, color: 'var(--success)' }}>
        {formatCurrency(m.pipeline_value)}
      </div>
    );
    
    const unitsCell = <div style={{ fontWeight: 600 }}>{m.units_sold || 0}</div>;
    const discountCell = <div style={{ fontWeight: 600 }}>{formatPercent(m.avg_discount)}</div>;
    const oppsCell = <div style={{ fontWeight: 600 }}>{m.opportunity_count || 0}</div>;

    return [
      productCell, categoryCell, pricingCell, listPriceCell, statusCell, pipelineCell, unitsCell, discountCell, oppsCell
    ];
  });

  return (
    <div style={{ overflowX: 'auto', margin: '0 -20px', padding: '0 20px' }}>
      <DataTable headers={headers} rows={rows} rightCols={[3, 5, 6, 7, 8]} />
    </div>
  );
}
