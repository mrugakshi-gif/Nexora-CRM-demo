import React, { useState, useEffect } from 'react';
import PageHeader from '../components/common/PageHeader';
import CRMDataTable from '../components/common/table/CRMDataTable';
import TablePagination from '../components/common/table/TablePagination';
import FilterBar from '../components/common/table/FilterBar';
import CRMStatusBadge from '../components/common/table/CRMStatusBadge';
import Modal from '../components/common/Modal';
import FormInput from '../components/common/FormInput';
import Button from '../components/common/Button';
import KpiCard from '../components/common/KpiCard';
import { productService } from '../services/crmService';

export default function Products() {
  const [products, setProducts] = useState([]);
  const [totalRecords, setTotalRecords] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const [search, setSearch] = useState('');
  const [selectedCategory, setSelectedCategory] = useState('All Products');
  const [page, setPage] = useState(1);
  const [globalMetrics, setGlobalMetrics] = useState({ totalProducts: 0, activeProducts: 0, categoriesCount: 0, avgPrice: 0, categories: [] });
  const pageSize = 25;

  const [isAddModalOpen, setIsAddModalOpen] = useState(false);
  const [isEditModalOpen, setIsEditModalOpen] = useState(false);
  const [isDeleteModalOpen, setIsDeleteModalOpen] = useState(false);
  const [selectedProduct, setSelectedProduct] = useState(null);

  const [formData, setFormData] = useState({ product_name: '', product_category: '', pricing_model: '', list_price_inr: '', is_active: true });
  const [formError, setFormError] = useState(null);
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => {
    const fetchGlobalData = async () => {
      try {
        const res = await productService.getProducts({ page: 1, page_size: 200 });
        const items = res.data?.items || [];
        const active = items.filter(i => i.is_active).length;
        const cats = Array.from(new Set(items.map(i => i.product_category).filter(Boolean))).sort();
        const priced = items.filter(i => i.list_price_inr != null);
        const avgPrice = priced.length > 0 ? priced.reduce((sum, i) => sum + i.list_price_inr, 0) / priced.length : 0;
        setGlobalMetrics({ totalProducts: items.length, activeProducts: active, categoriesCount: cats.length, avgPrice, categories: cats });
      } catch (err) {
        console.error("Failed to load global metrics", err);
      }
    };
    fetchGlobalData();
  }, []);

  const [categoryCounts, setCategoryCounts] = useState({});

  useEffect(() => { fetchProducts(); }, [page, search, selectedCategory]); // eslint-disable-line

  const fetchCategoryCounts = async (searchQuery, categories) => {
    if (!categories || categories.length === 0) return;
    try {
      const counts = {};
      const promises = ['All Products', ...categories].map(async (cat) => {
        const params = { page: 1, page_size: 1 };
        if (cat !== 'All Products') params.category = cat;
        if (searchQuery) params.search = searchQuery;
        const res = await productService.getProducts(params);
        counts[cat] = res.data?.total || 0;
      });
      await Promise.all(promises);
      setCategoryCounts(counts);
    } catch (err) {
      console.error("Failed to fetch product category counts", err);
    }
  };

  useEffect(() => {
    fetchCategoryCounts(search, globalMetrics.categories);
  }, [search, globalMetrics.categories]);
  const fetchProducts = async () => {
    setLoading(true);
    setError(null);
    try {
      const params = { page, page_size: pageSize };
      if (search) params.search = search;
      if (selectedCategory !== 'All Products') params.category = selectedCategory;
      const res = await productService.getProducts(params);
      setProducts(res.data?.items || []);
      setTotalRecords(res.data?.total || 0);
    } catch (err) {
      setError('Failed to load products. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  const handleAddClick = () => {
    setFormData({ product_name: '', product_category: '', pricing_model: '', list_price_inr: '', is_active: true });
    setFormError(null);
    setIsAddModalOpen(true);
  };

  const handleEditClick = (p) => {
    setSelectedProduct(p);
    setFormData({ product_name: p.product_name || '', product_category: p.product_category || '', pricing_model: p.pricing_model || '', list_price_inr: p.list_price_inr !== null ? p.list_price_inr : '', is_active: p.is_active ?? true });
    setFormError(null);
    setIsEditModalOpen(true);
  };

  const handleDeleteClick = (p) => { setSelectedProduct(p); setFormError(null); setIsDeleteModalOpen(true); };

  const validateForm = () => { if (!formData.product_name.trim()) { setFormError('Product name is required'); return false; } return true; };
  const makePayload = () => ({ ...formData, list_price_inr: formData.list_price_inr ? parseFloat(formData.list_price_inr) : null });

  const handleAddSubmit = async () => {
    if (!validateForm()) return;
    setSubmitting(true);
    try { await productService.createProduct(makePayload()); setIsAddModalOpen(false); fetchProducts(); }
    catch (err) { setFormError(err.response?.data?.detail || 'Failed to create product'); }
    finally { setSubmitting(false); }
  };

  const handleEditSubmit = async () => {
    if (!validateForm()) return;
    setSubmitting(true);
    try { await productService.updateProduct(selectedProduct.product_id, makePayload()); setIsEditModalOpen(false); fetchProducts(); }
    catch (err) { setFormError(err.response?.data?.detail || 'Failed to update product'); }
    finally { setSubmitting(false); }
  };

  const handleDeleteConfirm = async () => {
    setSubmitting(true);
    try { await productService.deleteProduct(selectedProduct.product_id); setIsDeleteModalOpen(false); fetchProducts(); }
    catch (err) { setFormError(err.response?.data?.detail || 'Failed to delete product.'); }
    finally { setSubmitting(false); }
  };

  const headers = ['Product Name', 'Category', 'Pricing Model', 'List Price (₹)', 'Status', ''];

  const rows = products.map(p => [
    <div><div style={{ fontWeight: 600, color: 'var(--heading-primary)' }}>{p.product_name}</div><div style={{ fontSize: '11px', color: 'var(--ink-mute)' }}>{p.product_id}</div></div>,
    <span>{p.product_category || '-'}</span>,
    <span>{p.pricing_model || '-'}</span>,
    <span>{p.list_price_inr != null ? `₹${p.list_price_inr.toLocaleString()}` : '-'}</span>,
    <CRMStatusBadge status={p.is_active ? 'Active' : 'Inactive'} type={p.is_active ? 'success' : 'neutral'} />,
    <div style={{ display: 'flex', gap: '6px', justifyContent: 'flex-end', alignItems: 'center' }}>
      <Button variant="ghost" size="small" icon="settings" onClick={() => handleEditClick(p)}>Edit</Button>
      <Button variant="ghost" size="small" icon="x" onClick={() => handleDeleteClick(p)} style={{ color: 'var(--danger)' }}>Delete</Button>
    </div>
  ]);

  const FormFields = ({ error, data, setData }) => (
    <>
      {error && <div style={{ color: 'red', marginBottom: '14px' }}>{error}</div>}
      <FormInput label="Product Name *" value={data.product_name} onChange={e => setData({...data, product_name: e.target.value})} />
      <FormInput label="Category" value={data.product_category} onChange={e => setData({...data, product_category: e.target.value})} />
      <FormInput label="Pricing Model" value={data.pricing_model} onChange={e => setData({...data, pricing_model: e.target.value})} />
      <FormInput label="List Price (₹)" type="number" value={data.list_price_inr} onChange={e => setData({...data, list_price_inr: e.target.value})} />
      <div style={{ display: 'flex', alignItems: 'center', gap: '10px', margin: '14px 0' }}>
        <input type="checkbox" id="is_active" checked={data.is_active} onChange={e => setData({...data, is_active: e.target.checked})} />
        <label htmlFor="is_active" style={{ fontSize: '13px', fontWeight: 500, color: 'var(--brown)', cursor: 'pointer' }}>Active Product</label>
      </div>
    </>
  );

  return (
    <div className="page">
      <PageHeader title="Products" desc="Manage your product catalog and offerings."
        actions={<Button variant="primary" onClick={handleAddClick}>Add Product</Button>}
      />
      <div style={{ padding: '0 28px 28px' }}>
        
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '20px', marginBottom: '28px' }}>
          <KpiCard label="Total Products" value={globalMetrics.totalProducts} icon="package" />
          <KpiCard label="Active Products" value={globalMetrics.activeProducts} icon="checksquare" />
          <KpiCard label="Product Categories" value={globalMetrics.categoriesCount} icon="grid" />
          <KpiCard label="Average List Price" value={`₹${Math.round(globalMetrics.avgPrice).toLocaleString()}`} icon="trendingup" />
        </div>

        <div style={{ display: 'flex', gap: '10px', overflowX: 'auto', paddingBottom: '12px', marginBottom: '16px', msOverflowStyle: 'none', scrollbarWidth: 'none' }}>
          {['All Products', ...globalMetrics.categories].map(cat => (
            <button
              key={cat}
              onClick={() => { setSelectedCategory(cat); setPage(1); }}
              style={{
                padding: '6px 16px',
                borderRadius: '20px',
                border: selectedCategory === cat ? '1px solid black' : '1px solid transparent',
                background: selectedCategory === cat ? 'black' : 'var(--white)',
                color: selectedCategory === cat ? 'var(--white)' : 'var(--ink)',
                fontSize: '13px',
                fontWeight: 600,
                cursor: 'pointer',
                whiteSpace: 'nowrap',
                transition: 'all 0.2s ease',
              }}
            >
              {cat} {categoryCounts[cat] !== undefined ? `(${categoryCounts[cat]})` : ''}
            </button>
          ))}
        </div>

        <FilterBar searchPlaceholder="Search products..." searchValue={search} onSearchChange={(v) => { setSearch(v); setPage(1); }} />

        <CRMDataTable headers={headers} rows={rows} loading={loading} error={error} onRetry={fetchProducts}
          emptyTitle="No products found" emptyDescription={search || selectedCategory !== 'All Products' ? "No products match your filters." : "You haven't added any products yet."} rightCols={[5]} />

        <TablePagination page={page} totalPages={Math.max(1, Math.ceil(totalRecords / pageSize))} totalRecords={totalRecords} onPrev={() => setPage(p => Math.max(1, p - 1))} onNext={() => setPage(p => p + 1)} />
      </div>

      <Modal isOpen={isAddModalOpen} onClose={() => setIsAddModalOpen(false)} title="Add Product">
        <FormFields error={formError} data={formData} setData={setFormData} />
        <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '10px', marginTop: '24px' }}>
          <Button variant="secondary" onClick={() => setIsAddModalOpen(false)}>Cancel</Button>
          <Button variant="primary" onClick={handleAddSubmit} disabled={submitting}>{submitting ? 'Creating...' : 'Create Product'}</Button>
        </div>
      </Modal>

      <Modal isOpen={isEditModalOpen} onClose={() => setIsEditModalOpen(false)} title="Edit Product">
        <FormFields error={formError} data={formData} setData={setFormData} />
        <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '10px', marginTop: '24px' }}>
          <Button variant="secondary" onClick={() => setIsEditModalOpen(false)}>Cancel</Button>
          <Button variant="primary" onClick={handleEditSubmit} disabled={submitting}>{submitting ? 'Saving...' : 'Save Changes'}</Button>
        </div>
      </Modal>

      <Modal isOpen={isDeleteModalOpen} onClose={() => setIsDeleteModalOpen(false)} title="Delete Product">
        {formError && <div style={{ color: 'red', marginBottom: '12px' }}>{formError}</div>}
        <p>Delete product <strong>{selectedProduct?.product_name}</strong>?</p>
        <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '10px', marginTop: '24px' }}>
          <Button variant="secondary" onClick={() => setIsDeleteModalOpen(false)}>Cancel</Button>
          <Button variant="danger" onClick={handleDeleteConfirm} disabled={submitting}>{submitting ? 'Deleting...' : 'Delete'}</Button>
        </div>
      </Modal>
    </div>
  );
}
