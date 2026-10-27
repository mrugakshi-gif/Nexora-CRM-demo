import React, { useState, useEffect } from 'react';
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
import { transactionService, lookupService } from '../services/crmService';

export default function Transactions() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const [transactions, setTransactions] = useState([]);
  const [totalRecords, setTotalRecords] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [summary, setSummary] = useState(null);

  const [search, setSearch] = useState('');
  const [typeFilter, setTypeFilter] = useState('All Transactions');
  const [page, setPage] = useState(1);
  const pageSize = 25;

  const [customerToCompanyMap, setCustomerToCompanyMap] = useState({});
  const [customers, setCustomers] = useState([]);

  const [isAddModalOpen, setIsAddModalOpen] = useState(false);
  const [isEditModalOpen, setIsEditModalOpen] = useState(false);
  const [isDeleteModalOpen, setIsDeleteModalOpen] = useState(false);
  const [selectedTx, setSelectedTx] = useState(null);

  const [formData, setFormData] = useState({
    customer_id: '', transaction_date: '', transaction_type: 'New Sale',
    amount_inr: '', payment_status: 'Paid', invoice_number: ''
  });
  const [formError, setFormError] = useState(null);
  const [submitting, setSubmitting] = useState(false);

  useEffect(() => { fetchTransactions(); }, [page, typeFilter, search]); // eslint-disable-line

  const fetchTransactions = async () => {
    setLoading(true);
    setError(null);
    try {
      const params = { page, page_size: pageSize };
      if (searchParams.get('company_id')) params.company_id = searchParams.get('company_id');
      if (searchParams.get('customer_id')) params.customer_id = searchParams.get('customer_id');

      if (typeFilter !== 'All Transactions') params.transaction_type = typeFilter;

      const [txRes, lookupsRes, summaryRes] = await Promise.all([
        transactionService.getTransactions(params),
        lookupService.getAllLookups(),
        transactionService.getTransactionSummary()
      ]);

      let txData = txRes.data?.items || [];
      const total = txRes.data?.total || 0;
      const customersData = lookupsRes.data?.customers || [];
      const companiesData = lookupsRes.data?.companies || [];
      setCustomers(customersData);
      setSummary(summaryRes.data);

      const companyIdToName = {};
      companiesData.forEach(c => { companyIdToName[c.id] = c.name; });

      const map = {};
      customersData.forEach(cust => {
        map[cust.id] = { name: cust.name || 'Unknown', id: null }; 
        // Wait, lookup_customers returns customer_id and customer_name (which is company name). 
        // We can just use cust.id as customer_id, cust.name as company_name. We don't have company_id in lookup_customers currently.
        // Actually, we don't strictly need company_id to navigate to company if we just navigate to customer. 
        // Let's modify map to use cust.name as company name, and we'll leave company id as null to disable the link.
        // Or if we need company_id, the old code used cust.company_id which is not in lookup_customers.
      });
      setCustomerToCompanyMap(map);

      if (search) {
        const q = search.toLowerCase();
        txData = txData.filter(t => {
          const cName = map[t.customer_id]?.name || '';
          return t.transaction_id?.toLowerCase().includes(q) || t.transaction_type?.toLowerCase().includes(q) || cName.toLowerCase().includes(q);
        });
      }

      setTransactions(txData);
      setTotalRecords(search ? txData.length : total);
    } catch (err) {
      setError('Failed to load transactions.');
    } finally {
      setLoading(false);
    }
  };

  const getStatusType = (status) => {
    if (status === 'Paid') return 'success';
    if (status === 'Pending') return 'warning';
    if (status === 'Overdue' || status === 'Failed') return 'error';
    return 'neutral';
  };

  const handleAddClick = () => {
    setFormData({ customer_id: '', transaction_date: new Date().toISOString().split('T')[0], transaction_type: 'New Sale', amount_inr: '', payment_status: 'Paid', invoice_number: '' });
    setFormError(null);
    setIsAddModalOpen(true);
  };

  const handleEditClick = (t) => {
    setSelectedTx(t);
    setFormData({ customer_id: t.customer_id || '', transaction_date: t.transaction_date ? t.transaction_date.split('T')[0] : '', transaction_type: t.transaction_type || 'New Sale', amount_inr: t.amount_inr !== null ? t.amount_inr : '', payment_status: t.payment_status || 'Paid', invoice_number: t.invoice_number || '' });
    setFormError(null);
    setIsEditModalOpen(true);
  };

  const handleDeleteClick = (t) => { setSelectedTx(t); setFormError(null); setIsDeleteModalOpen(true); };

  const validateForm = () => {
    if (!formData.customer_id) { setFormError('Customer is required'); return false; }
    if (!formData.transaction_date) { setFormError('Date is required'); return false; }
    if (!formData.amount_inr) { setFormError('Amount is required'); return false; }
    return true;
  };

  const handleAddSubmit = async () => {
    if (!validateForm()) return;
    setSubmitting(true);
    try { await transactionService.createTransaction({ ...formData, amount_inr: parseFloat(formData.amount_inr) }); setIsAddModalOpen(false); fetchTransactions(); }
    catch (err) { setFormError(err.response?.data?.detail || 'Failed to create'); }
    finally { setSubmitting(false); }
  };

  const handleEditSubmit = async () => {
    if (!validateForm()) return;
    setSubmitting(true);
    try { await transactionService.updateTransaction(selectedTx.transaction_id, { ...formData, amount_inr: parseFloat(formData.amount_inr) }); setIsEditModalOpen(false); fetchTransactions(); }
    catch (err) { setFormError(err.response?.data?.detail || 'Failed to update'); }
    finally { setSubmitting(false); }
  };

  const handleDeleteConfirm = async () => {
    setSubmitting(true);
    try { await transactionService.deleteTransaction(selectedTx.transaction_id); setIsDeleteModalOpen(false); fetchTransactions(); }
    catch (err) { setFormError(err.response?.data?.detail || 'Failed to delete'); }
    finally { setSubmitting(false); }
  };

  const headers = ['Transaction ID', 'Company / Customer', 'Date', 'Type', 'Amount (₹)', 'Status', ''];

  const rows = transactions.map(t => {
    const comp = customerToCompanyMap[t.customer_id] || { name: 'Unknown', id: null };
    return [
      <span style={{ fontWeight: 500, color: 'var(--brown)' }}>{t.transaction_id}</span>,
      <div>
        <div style={{ fontWeight: 500, color: comp.id ? 'var(--primary)' : 'var(--ink)', cursor: comp.id ? 'pointer' : 'default' }} onClick={() => comp.id && navigate(`/companies/${comp.id}`)}>{comp.name}</div>
        <div style={{ fontSize: '11px', color: 'var(--gray-500)', cursor: 'pointer' }} onClick={() => navigate(`/customers/${t.customer_id}`)}>{t.customer_id}</div>
      </div>,
      <span>{t.transaction_date ? new Date(t.transaction_date).toLocaleDateString() : '-'}</span>,
      <span>{t.transaction_type}</span>,
      <span style={{ fontWeight: 500 }}>{t.amount_inr != null ? t.amount_inr.toLocaleString() : '-'}</span>,
      <CRMStatusBadge status={t.payment_status || 'Unknown'} type={getStatusType(t.payment_status)} />,
      <div style={{ display: 'flex', gap: '8px', justifyContent: 'flex-end' }}>
        <Button variant="secondary" size="sm" onClick={() => handleEditClick(t)}>Edit</Button>
        <Button variant="danger" size="sm" onClick={() => handleDeleteClick(t)}>Delete</Button>
      </div>
    ];
  });

  const FormFields = () => (
    <>
      {formError && <div style={{ color: 'red', marginBottom: '14px' }}>{formError}</div>}
      <div style={{ marginBottom: '14px' }}>
        <label style={{ display: 'block', marginBottom: '6px', fontSize: '13px', fontWeight: 500 }}>Customer *</label>
        <select value={formData.customer_id} onChange={e => setFormData({...formData, customer_id: e.target.value})} style={{ width: '100%', padding: '8px 12px', border: '1px solid var(--border)', borderRadius: '6px' }}>
          <option value="">Select customer...</option>
          {customers.map(c => <option key={c.id} value={c.id}>{c.id} — {customerToCompanyMap[c.id]?.name}</option>)}
        </select>
      </div>
      <FormInput label="Transaction Date *" type="date" value={formData.transaction_date} onChange={e => setFormData({...formData, transaction_date: e.target.value})} />
      <FormInput label="Amount (₹) *" type="number" value={formData.amount_inr} onChange={e => setFormData({...formData, amount_inr: e.target.value})} />
      <div style={{ marginBottom: '14px' }}>
        <label style={{ display: 'block', marginBottom: '6px', fontSize: '13px', fontWeight: 500 }}>Transaction Type</label>
        <select value={formData.transaction_type} onChange={e => setFormData({...formData, transaction_type: e.target.value})} style={{ width: '100%', padding: '8px 12px', border: '1px solid var(--border)', borderRadius: '6px' }}>
          {['New Sale', 'Renewal', 'Upsell', 'Refund'].map(s => <option key={s} value={s}>{s}</option>)}
        </select>
      </div>
      <div style={{ marginBottom: '14px' }}>
        <label style={{ display: 'block', marginBottom: '6px', fontSize: '13px', fontWeight: 500 }}>Payment Status</label>
        <select value={formData.payment_status} onChange={e => setFormData({...formData, payment_status: e.target.value})} style={{ width: '100%', padding: '8px 12px', border: '1px solid var(--border)', borderRadius: '6px' }}>
          {['Paid', 'Pending', 'Overdue', 'Failed', 'Refunded'].map(s => <option key={s} value={s}>{s}</option>)}
        </select>
      </div>
      <FormInput label="Invoice Number" value={formData.invoice_number} onChange={e => setFormData({...formData, invoice_number: e.target.value})} />
    </>
  );

  const categories = summary ? [
    { name: 'All Transactions', count: summary.total_transactions },
    ...summary.category_counts.map(c => ({ name: c.category, count: c.count }))
  ] : [{ name: 'All Transactions', count: 0 }];

  return (
    <div className="page">
      <PageHeader title="Transactions" desc="View and manage all customer transactions."
        actions={<Button variant="primary" onClick={handleAddClick}>New Transaction</Button>}
      />
      <div style={{ padding: '0 28px 28px' }}>
        {summary && (
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '16px', marginBottom: '24px' }}>
            <KpiCard label="Total Transactions" value={summary.total_transactions} icon="layers" delta="0" ctx="Lifetime" dir="up" />
            <KpiCard label="Total Revenue" value={`₹${summary.total_revenue.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`} icon="dollar-sign" delta="0" ctx="Lifetime" dir="up" />
            <KpiCard label="Avg Transaction Value" value={`₹${summary.avg_transaction_value.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`} icon="trending-up" delta="0" ctx="Lifetime" dir="up" />
            <KpiCard label="Paid Transactions" value={summary.paid_transactions} icon="check-circle" delta="0" ctx="Lifetime" dir="up" />
          </div>
        )}

        <div style={{ marginBottom: '16px', display: 'flex', gap: '8px', overflowX: 'auto', alignItems: 'center', flexShrink: 0 }}>
          {categories.map(cat => {
            const isActive = typeFilter === cat.name;
            return (
              <button
                key={cat.name}
                onClick={() => { setTypeFilter(cat.name); setPage(1); }}
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

        <FilterBar searchPlaceholder="Search transactions..." searchValue={search} onSearchChange={(v) => { setSearch(v); setPage(1); }} />

        <CRMDataTable headers={headers} rows={rows} loading={loading} error={error} onRetry={fetchTransactions}
          emptyTitle="No transactions found" emptyDescription={search || typeFilter !== 'All Transactions' ? "No transactions match your filters." : "No transactions yet."} rightCols={[6]} />

        <TablePagination page={page} totalPages={Math.max(1, Math.ceil(totalRecords / pageSize))} totalRecords={totalRecords} onPrev={() => setPage(p => Math.max(1, p - 1))} onNext={() => setPage(p => p + 1)} />
      </div>

      <Modal isOpen={isAddModalOpen} onClose={() => setIsAddModalOpen(false)} title="New Transaction">
        <FormFields />
        <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '10px', marginTop: '24px' }}>
          <Button variant="secondary" onClick={() => setIsAddModalOpen(false)}>Cancel</Button>
          <Button variant="primary" onClick={handleAddSubmit} disabled={submitting}>{submitting ? 'Creating...' : 'Create'}</Button>
        </div>
      </Modal>

      <Modal isOpen={isEditModalOpen} onClose={() => setIsEditModalOpen(false)} title="Edit Transaction">
        <FormFields />
        <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '10px', marginTop: '24px' }}>
          <Button variant="secondary" onClick={() => setIsEditModalOpen(false)}>Cancel</Button>
          <Button variant="primary" onClick={handleEditSubmit} disabled={submitting}>{submitting ? 'Saving...' : 'Save Changes'}</Button>
        </div>
      </Modal>

      <Modal isOpen={isDeleteModalOpen} onClose={() => setIsDeleteModalOpen(false)} title="Delete Transaction">
        {formError && <div style={{ color: 'red', marginBottom: '12px' }}>{formError}</div>}
        <p>Delete transaction <strong>{selectedTx?.transaction_id}</strong>?</p>
        <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '10px', marginTop: '24px' }}>
          <Button variant="secondary" onClick={() => setIsDeleteModalOpen(false)}>Cancel</Button>
          <Button variant="danger" onClick={handleDeleteConfirm} disabled={submitting}>{submitting ? 'Deleting...' : 'Delete'}</Button>
        </div>
      </Modal>
    </div>
  );
}
