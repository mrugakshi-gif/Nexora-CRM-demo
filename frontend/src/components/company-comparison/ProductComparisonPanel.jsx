import React, { useState, useEffect } from 'react';
import ProductSelector from './ProductSelector';
import ProductComparisonTable from './ProductComparisonTable';
import Icon from '../common/Icon';
import api from '../../api';

export default function ProductComparisonPanel({ products }) {
  const [selectedProducts, setSelectedProducts] = useState([]);
  const [metrics, setMetrics] = useState({});
  const [isLoading, setIsLoading] = useState(false);
  const [hasError, setHasError] = useState(false);
  const [initialized, setInitialized] = useState(false);

  useEffect(() => {
    let active = true;
    async function initDefaults() {
      if (initialized) return;
      try {
        const res = await api.get('/api/analytics/revenue/top-products?limit=3');
        const tops = res.data || [];
        if (active && tops.length > 0) {
          setSelectedProducts(tops.map(t => ({
            product_id: t.product_id,
            product_name: t.product_name,
            product_category: t.product_category || '—'
          })));
          setInitialized(true);
        }
      } catch (err) {
        console.warn("Failed to fetch top products", err);
      }
    }
    initDefaults();
    return () => { active = false; };
  }, [initialized]);

  const handleSelect = (product) => {
    if (selectedProducts.length < 3 && !selectedProducts.some(p => p.product_id === product.product_id)) {
      setSelectedProducts([...selectedProducts, product]);
    }
  };

  const handleRemove = (id) => {
    setSelectedProducts(selectedProducts.filter(p => p.product_id !== id));
  };

  useEffect(() => {
    let active = true;
    const fetchMetrics = async () => {
      if (selectedProducts.length === 0) {
        if (active) setMetrics({});
        return;
      }
      setIsLoading(true);
      setHasError(false);
      try {
        const ids = selectedProducts.map(p => p.product_id).join(',');
        const res = await api.get(`/api/compare/products?ids=${ids}`);
        if (active) {
          setMetrics(res.data);
        }
      } catch (e) {
        console.error("Error fetching product comparison metrics:", e);
        if (active) setHasError(true);
      } finally {
        if (active) setIsLoading(false);
      }
    };
    fetchMetrics();
    return () => { active = false; };
  }, [selectedProducts]);

  return (
    <div className="card" style={{ padding: '24px 32px' }}>
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '20px', flexWrap: 'wrap', gap: '12px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          <Icon name="package" size={28} color="var(--accent-primary)" stroke={2} />
          <div>
            <h2 className="section-title" style={{ fontSize: '22px', marginBottom: '4px', color: 'var(--heading-primary)' }}>Product Comparison</h2>
            <p style={{ color: 'var(--ink-mute)', fontSize: '14px', margin: 0 }}>Compare pricing, pipeline value, and volume</p>
          </div>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <div style={{ padding: '6px 12px', background: 'var(--accent-primary)', border: '1px solid var(--border-soft)', borderRadius: '8px', fontSize: '14px', fontWeight: 600, color: '#ffffff', display: 'flex', alignItems: 'center', gap: '8px' }}>
            <Icon name="layers" size={16} /> {selectedProducts.length} selected
          </div>
          <span style={{ fontSize: '13px', color: 'var(--ink-soft)' }}>(Max 3)</span>
        </div>
      </div>

      <div style={{ display: 'flex', flexWrap: 'wrap', gap: '12px', marginBottom: '16px' }}>
        {selectedProducts.map(product => (
          <div key={product.product_id} style={{
            display: 'flex', alignItems: 'center', gap: '8px',
            padding: '6px 12px', background: 'var(--bg-subtle)',
            border: '1px solid var(--border)', borderRadius: '6px',
            fontSize: '14px', fontWeight: 700, color: 'var(--heading-primary)',
            boxShadow: '0 1px 2px rgba(0,0,0,0.05)'
          }}>
            <strong>{product.product_name}</strong>
            <button
              onClick={() => handleRemove(product.product_id)}
              style={{ background: 'none', border: 'none', cursor: 'pointer', display: 'flex', alignItems: 'center', padding: '2px', color: 'var(--ink-soft)' }}
            >
              <Icon name="x" size={16} />
            </button>
          </div>
        ))}
      </div>

      <div style={{ marginBottom: '24px' }}>
        <ProductSelector selectedProducts={selectedProducts} onSelect={handleSelect} />
      </div>

      {hasError ? (
        <div style={{ padding: '40px 20px', textAlign: 'center', background: 'var(--bg-light)', borderRadius: '8px', border: '1px dashed var(--border)' }}>
          <p style={{ color: 'var(--danger)', fontSize: '14px', fontWeight: 500 }}>Unable to load product comparison data.</p>
        </div>
      ) : isLoading ? (
        <div style={{ padding: '40px 20px', textAlign: 'center', color: 'var(--ink-mute)', fontSize: '14px' }}>
          Loading metrics...
        </div>
      ) : (
        <div style={{ marginBottom: '24px' }}>
          <ProductComparisonTable selectedProducts={selectedProducts} metrics={metrics} />
        </div>
      )}
    </div>
  );
}
