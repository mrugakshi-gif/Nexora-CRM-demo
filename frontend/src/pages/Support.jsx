import React, { useState, useEffect, useRef } from 'react';
import {  useNavigate , useSearchParams } from "react-router-dom";
import PageHeader from '../components/common/PageHeader';
import CRMDataTable from '../components/common/table/CRMDataTable';
import TablePagination from '../components/common/table/TablePagination';
import FilterBar from '../components/common/table/FilterBar';
import CRMStatusBadge from '../components/common/table/CRMStatusBadge';
import Modal from '../components/common/Modal';
import FormInput from '../components/common/FormInput';
import Button from '../components/common/Button';
import KpiCard from '../components/common/KpiCard';
import { supportService, lookupService } from '../services/crmService';

export default function Support() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const [cases, setCases] = useState([]);
  const [totalRecords, setTotalRecords] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const abortControllerRef = useRef(null);

  const [inputSearch, setInputSearch] = useState('');
  const [search, setSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState('All');
  const [page, setPage] = useState(1);

  const pageSize = 25;

  // Debounce: only update the API search param 300ms after the user stops typing
  useEffect(() => {
    const timer = setTimeout(() => {
      setSearch(inputSearch);
      setPage(1);
    }, 300);
    return () => clearTimeout(timer);
  }, [inputSearch]);

  const [customerToCompanyMap, setCustomerToCompanyMap] = useState({});
  const [customers, setCustomers] = useState([]);

  const [summary, setSummary] = useState(null);

  const [isAddModalOpen, setIsAddModalOpen] = useState(false);
  const [isEditModalOpen, setIsEditModalOpen] = useState(false);
  const [isDeleteModalOpen, setIsDeleteModalOpen] = useState(false);
  const [selectedCase, setSelectedCase] = useState(null);

  const [formData, setFormData] = useState({ customer_id: '', case_type: 'General Query', priority: 'Low', status: 'Open', opened_at: '', satisfaction_score: '' });
  const [formError, setFormError] = useState(null);
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => { loadData(); }, [page, statusFilter, search]); // eslint-disable-line

  async function loadData() {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
    }
    abortControllerRef.current = new AbortController();
    const currentSignal = abortControllerRef.current.signal;

    setLoading(true);
    setError(null);
    try {
      const params = { page, page_size: pageSize };
      if (searchParams.get('company_id')) params.company_id = searchParams.get('company_id');
      if (searchParams.get('customer_id')) params.customer_id = searchParams.get('customer_id');

      if (statusFilter !== 'All') params.status = statusFilter;
      if (search) params.search = search;

      const [suppRes, lookupsRes, summaryRes] = await Promise.all([
        supportService.getSupportCases(params, { signal: currentSignal }),
        lookupService.getAllLookups(),
        supportService.getSupportSummary()
      ]);

      if (currentSignal.aborted) return;

      let items = suppRes.data?.items || suppRes.data || [];
      const total = suppRes.data?.total || items.length;

      const customersData = lookupsRes.data?.customers || [];
      const companiesData = lookupsRes.data?.companies || [];
      setCustomers(customersData);
      setSummary(summaryRes.data);

      const companyIdToName = {};
      companiesData.forEach(c => { companyIdToName[c.id] = c.name; });

      const map = {};
      customersData.forEach(cust => { map[cust.id] = { name: cust.name || 'Unknown', id: null }; });
      setCustomerToCompanyMap(map);

      setCases(items);
      setTotalRecords(total);
    } catch (err) {
      if (abortControllerRef.current?.signal.aborted || err.name === 'CanceledError' || err.code === 'ERR_CANCELED') {
        return;
      }
      setError('Failed to load support cases.');
    } finally {
      if (!abortControllerRef.current?.signal.aborted) {
        setLoading(false);
      }
    }
  }

  const getComp = (customerId) => customerToCompanyMap[customerId] || { name: 'Unknown', id: null };

  const getPriorityType = (val) => {
    const s = (val || '').toLowerCase();
    if (s.includes('high') || s.includes('critical')) return 'error';
    if (s.includes('medium')) return 'info';
    return 'neutral';
  };

  const getStatusType = (val) => {
    const s = (val || '').toLowerCase();
    if (s.includes('open') || s.includes('in progress')) return 'warning';
    if (s.includes('resolved') || s.includes('closed')) return 'success';
    if (s.includes('escalated')) return 'error';
    return 'neutral';
  };

  const handleAddClick = () => {
    setFormData({ customer_id: '', case_type: 'General Query', priority: 'Low', status: 'Open', opened_at: new Date().toISOString().split('T')[0], satisfaction_score: '' });
    setFormError(null);
    setIsAddModalOpen(true);
  };

  const handleEditClick = (c) => {
    setSelectedCase(c);
    setFormData({ customer_id: c.customer_id || '', case_type: c.case_type || 'General Query', priority: c.priority || 'Low', status: c.status || 'Open', opened_at: c.opened_at ? c.opened_at.split('T')[0] : '', satisfaction_score: c.satisfaction_score !== null ? c.satisfaction_score : '' });
    setFormError(null);
    setIsEditModalOpen(true);
  };

  const handleDeleteClick = (c) => { setSelectedCase(c); setFormError(null); setIsDeleteModalOpen(true); };

  const validateForm = () => {
    if (!formData.customer_id) { setFormError('Customer is required'); return false; }
    if (!formData.case_type) { setFormError('Case type is required'); return false; }
    if (!formData.opened_at) { setFormError('Opened date is required'); return false; }
    return true;
  };

  const makePayload = () => ({ ...formData, satisfaction_score: formData.satisfaction_score ? parseFloat(formData.satisfaction_score) : null });

  const handleAddSubmit = async () => {
    if (!validateForm()) return;
    setSubmitting(true);
    try { await supportService.createSupportCase(makePayload()); setIsAddModalOpen(false); loadData(); }
    catch (err) { setFormError(err.response?.data?.detail || 'Failed to create'); }
    finally { setSubmitting(false); }
  };

  const handleEditSubmit = async () => {
    if (!validateForm()) return;
    setSubmitting(true);
    try { await supportService.updateSupportCase(selectedCase.case_id, makePayload()); setIsEditModalOpen(false); loadData(); }
    catch (err) { setFormError(err.response?.data?.detail || 'Failed to update'); }
    finally { setSubmitting(false); }
  };

  const handleDeleteConfirm = async () => {
    setSubmitting(true);
    try { await supportService.deleteSupportCase(selectedCase.case_id); setIsDeleteModalOpen(false); loadData(); }
    catch (err) { setFormError(err.response?.data?.detail || 'Failed to delete'); }
    finally { setSubmitting(false); }
  };

  const headers = ['Case ID / Type', 'Customer', 'Opened', 'Priority', 'Status', 'CSAT', ''];

  const rows = cases.map(c => {
    const comp = getComp(c.customer_id);
    return [
      <div><div style={{ fontWeight: 500, color: 'var(--brown)' }}>{c.case_id}</div><div style={{ fontSize: '12px', color: 'var(--gray-500)' }}>{c.case_type}</div></div>,
      <div>
        <div style={{ fontWeight: 500, color: comp.id ? 'var(--primary)' : 'var(--ink)', cursor: comp.id ? 'pointer' : 'default' }} onClick={() => comp.id && navigate(`/companies/${comp.id}`)}>{comp.name}</div>
        <div style={{ fontSize: '11px', color: 'var(--gray-500)', cursor: 'pointer' }} onClick={() => navigate(`/customers/${c.customer_id}`)}>{c.customer_id}</div>
      </div>,
      <span>{c.opened_at ? new Date(c.opened_at).toLocaleDateString() : '-'}</span>,
      <CRMStatusBadge status={c.priority || 'Unknown'} type={getPriorityType(c.priority)} />,
      <CRMStatusBadge status={c.status || 'Unknown'} type={getStatusType(c.status)} />,
      <span style={{ fontWeight: 500 }}>{c.satisfaction_score !== null && c.satisfaction_score !== undefined ? c.satisfaction_score : '-'}</span>,
      <div style={{ display: 'flex', gap: '8px', justifyContent: 'flex-end' }}>
        <Button variant="secondary" size="sm" onClick={() => handleEditClick(c)}>Edit</Button>
        <Button variant="danger" size="sm" onClick={() => handleDeleteClick(c)}>Delete</Button>
      </div>
    ];
  });

  const FormFields = ({ error, data, setData }) => (
    <>
      {error && <div style={{ color: 'red', marginBottom: '14px' }}>{error}</div>}
      <div style={{ marginBottom: '14px' }}>
        <label style={{ display: 'block', marginBottom: '6px', fontSize: '13px', fontWeight: 500 }}>Customer *</label>
        <select value={data.customer_id} onChange={e => setData({...data, customer_id: e.target.value})} style={{ width: '100%', padding: '8px 12px', border: '1px solid var(--border)', borderRadius: '6px' }}>
          <option value="">Select customer...</option>
          {customers.map(c => <option key={c.id} value={c.id}>{c.id} — {c.name}</option>)}
        </select>
      </div>
      <div style={{ marginBottom: '14px' }}>
        <label style={{ display: 'block', marginBottom: '6px', fontSize: '13px', fontWeight: 500 }}>Case Type *</label>
        <select value={data.case_type} onChange={e => setData({...data, case_type: e.target.value})} style={{ width: '100%', padding: '8px 12px', border: '1px solid var(--border)', borderRadius: '6px' }}>
          {['General Query', 'Technical Issue', 'Billing', 'Feature Request'].map(t => <option key={t} value={t}>{t}</option>)}
        </select>
      </div>
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '14px' }}>
        <div>
          <label style={{ display: 'block', marginBottom: '6px', fontSize: '13px', fontWeight: 500 }}>Priority</label>
          <select value={data.priority} onChange={e => setData({...data, priority: e.target.value})} style={{ width: '100%', padding: '8px 12px', border: '1px solid var(--border)', borderRadius: '6px' }}>
            {['Low', 'Medium', 'High', 'Critical'].map(p => <option key={p} value={p}>{p}</option>)}
          </select>
        </div>
        <div>
          <label style={{ display: 'block', marginBottom: '6px', fontSize: '13px', fontWeight: 500 }}>Status</label>
          <select value={data.status} onChange={e => setData({...data, status: e.target.value})} style={{ width: '100%', padding: '8px 12px', border: '1px solid var(--border)', borderRadius: '6px' }}>
            {['Open', 'In Progress', 'Escalated', 'Resolved', 'Closed'].map(s => <option key={s} value={s}>{s}</option>)}
          </select>
        </div>
      </div>
      <FormInput label="Opened Date *" type="date" value={data.opened_at} onChange={e => setData({...data, opened_at: e.target.value})} />
      <FormInput label="CSAT Score (1-5)" type="number" min="1" max="5" step="0.1" value={data.satisfaction_score} onChange={e => setData({...data, satisfaction_score: e.target.value})} />
    </>
  );

  const categories = summary ? [
    { name: 'All Cases', count: summary.total_cases },
    ...summary.category_counts.map(c => ({ name: c.category, count: c.count }))
  ] : [{ name: 'All Cases', count: 0 }];

  return (
    <div className="page">
      <PageHeader title="Support" desc="Manage customer support cases and tickets."
        actions={<Button variant="primary" onClick={handleAddClick}>New Case</Button>}
      />

      <div style={{ padding: '0 28px' }}>
        {summary && (
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '16px', marginBottom: '24px' }}>
            <KpiCard label="Total Cases" value={summary.total_cases} icon="layers" delta="0" ctx="Lifetime" dir="up" />
            <KpiCard label="Open Cases" value={summary.open_cases} icon="folder-open" delta="0" ctx="Lifetime" dir="up" />
            <KpiCard label="Resolved Cases" value={summary.resolved_cases} icon="check-circle" delta="0" ctx="Lifetime" dir="up" />
            <KpiCard label="High Priority" value={summary.high_priority_cases} icon="alert-triangle" delta="0" ctx="Lifetime" dir="up" />
          </div>
        )}

        <div style={{ marginBottom: '16px', display: 'flex', gap: '8px', overflowX: 'auto', alignItems: 'center', flexShrink: 0 }}>
          {categories.map(cat => {
            const isActive = statusFilter === cat.name || (statusFilter === 'All' && cat.name === 'All Cases');
            return (
              <button
                key={cat.name}
                onClick={() => { setStatusFilter(cat.name === 'All Cases' ? 'All' : cat.name); setPage(1); }}
                style={{
                  padding: '6px 16px',
                  borderRadius: '20px',
                  border: isActive ? '1px solid black' : '1px solid transparent',
                  background: isActive ? 'black' : 'var(--white)',
                  color: isActive ? 'var(--white)' : 'var(--ink)',
                  fontWeight: 600,
                  fontSize: '13px',
                  cursor: 'pointer',
                  whiteSpace: 'nowrap',
                  transition: 'all 0.2s',
                  flexShrink: 0,
                  boxShadow: isActive ? '0 2px 4px rgba(0,0,0,0.15)' : 'none'
                }}
              >
                {cat.name} ({cat.count})
              </button>
            );
          })}
        </div>
      </div>

      <div style={{ padding: '0 28px 28px' }}>
        <FilterBar searchPlaceholder="Search tickets by ID, type, customer..." searchValue={inputSearch} onSearchChange={(v) => setInputSearch(v)} />

        <CRMDataTable headers={headers} rows={rows} loading={loading} error={error} onRetry={loadData}
          emptyTitle="No support cases found" emptyDescription={search || statusFilter !== 'All' ? "No cases match your filters." : "No support cases yet."} rightCols={[6]} />

        <TablePagination page={page} totalPages={Math.max(1, Math.ceil(totalRecords / pageSize))} totalRecords={totalRecords} onPrev={() => setPage(p => Math.max(1, p - 1))} onNext={() => setPage(p => p + 1)} />
      </div>

      <Modal isOpen={isAddModalOpen} onClose={() => setIsAddModalOpen(false)} title="New Support Case">
        <FormFields error={formError} data={formData} setData={setFormData} />
        <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '10px', marginTop: '24px' }}>
          <Button variant="secondary" onClick={() => setIsAddModalOpen(false)}>Cancel</Button>
          <Button variant="primary" onClick={handleAddSubmit} disabled={submitting}>{submitting ? 'Creating...' : 'Create Case'}</Button>
        </div>
      </Modal>

      <Modal isOpen={isEditModalOpen} onClose={() => setIsEditModalOpen(false)} title="Edit Support Case">
        <FormFields error={formError} data={formData} setData={setFormData} />
        <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '10px', marginTop: '24px' }}>
          <Button variant="secondary" onClick={() => setIsEditModalOpen(false)}>Cancel</Button>
          <Button variant="primary" onClick={handleEditSubmit} disabled={submitting}>{submitting ? 'Saving...' : 'Save Changes'}</Button>
        </div>
      </Modal>

      <Modal isOpen={isDeleteModalOpen} onClose={() => setIsDeleteModalOpen(false)} title="Delete Support Case">
        {formError && <div style={{ color: 'red', marginBottom: '12px' }}>{formError}</div>}
        <p>Delete case <strong>{selectedCase?.case_id}</strong>?</p>
        <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '10px', marginTop: '24px' }}>
          <Button variant="secondary" onClick={() => setIsDeleteModalOpen(false)}>Cancel</Button>
          <Button variant="danger" onClick={handleDeleteConfirm} disabled={submitting}>{submitting ? 'Deleting...' : 'Delete'}</Button>
        </div>
      </Modal>
    </div>
  );
}
