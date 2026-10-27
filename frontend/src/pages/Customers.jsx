import React, { useState, useEffect, useRef } from 'react';
import { useNavigate } from 'react-router-dom';
import PageHeader from '../components/common/PageHeader';
import Button from '../components/common/Button';
import Modal from '../components/common/Modal';
import FormInput from '../components/common/FormInput';
import KpiCard from '../components/common/KpiCard';
import { CRMDataTable, TablePagination, FilterBar, CRMStatusBadge } from '../components/common/table';
import { companyService, customerService, opportunityService, salesRepService } from '../services/crmService';
import { AuthContext } from '../AuthContext';

export default function Customers() {
  const { effectiveRole } = React.useContext(AuthContext);
  const [customers, setCustomers] = useState([]);
  const [loading, setLoading] = useState(true);
  const [search, setSearch] = useState('');
  const [error, setError] = useState(null);
  const navigate = useNavigate();

  // KPI Stats from backend
  const [stats, setStats] = useState({ total: 0, active: 0, atRisk: 0, churned: 0 });

  // Status Filter State
  const [statuses, setStatuses] = useState([]);
  const [activeStatus, setActiveStatus] = useState('All Status');

  // Pagination State
  const [page, setPage] = useState(1);
  const [pageSize] = useState(5);
  const [totalItems, setTotalItems] = useState(0);
  const [totalPages, setTotalPages] = useState(1);

  // Caching
  const [salesReps, setSalesReps] = useState({});
  const [companyCache, setCompanyCache] = useState({});

  // Modal State
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [isDeleteModalOpen, setIsDeleteModalOpen] = useState(false);
  const [editingCustomer, setEditingCustomer] = useState(null);
  const [customerToDelete, setCustomerToDelete] = useState(null);

  const [formData, setFormData] = useState({
    company_id: '',
    originating_opportunity_id: '',
    customer_since: new Date().toISOString().split('T')[0],
    csm_rep_id: '',
    customer_tier: 'Standard',
    contract_type: 'Annual',
    renewal_date: '',
    customer_status: 'Active'
  });
  const [submitting, setSubmitting] = useState(false);
  const [formError, setFormError] = useState('');

  // Dropdown States
  const [companySearch, setCompanySearch] = useState('');
  const [companyResults, setCompanyResults] = useState([]);
  const [companySearching, setCompanySearching] = useState(false);

  const [oppSearch, setOppSearch] = useState('');
  const [oppResults, setOppResults] = useState([]);
  const [oppSearching, setOppSearching] = useState(false);

  const [repSearch, setRepSearch] = useState('');
  const [repResults, setRepResults] = useState([]);
  const [repSearching, setRepSearching] = useState(false);

  const searchTimeoutRef = useRef(null);
  const oppTimeoutRef = useRef(null);
  const repTimeoutRef = useRef(null);
  const companyCacheRef = useRef({});

  const loadData = (currentPage = page, searchQuery = search, statusFilter = activeStatus) => {
    setLoading(true);
    setError(null);
    const params = { page: currentPage, page_size: pageSize };
    if (searchQuery) params.search = searchQuery;
    if (statusFilter && statusFilter !== 'All Status') params.customer_status = statusFilter;

    customerService.getCustomers(params)
      .then(async (custRes) => {
        const custData = custRes.data?.data || custRes.data?.items || custRes.data || [];
        const total = custRes.data?.total || 0;
        setTotalItems(total);
        setTotalPages(Math.ceil(total / pageSize) || 1);

        // Resolve company names from cache
        const cache = companyCacheRef.current;
        const missingIds = [...new Set(custData.map(c => c.company_id))].filter(id => id && !cache[id]);

        if (missingIds.length > 0) {
          const results = await Promise.all(missingIds.map(id => companyService.getCompany(id).catch(() => null)));
          results.forEach((res, i) => {
            if (res?.data) cache[missingIds[i]] = res.data;
          });
          setCompanyCache({ ...cache });
        }

        const joined = custData.map(c => ({
          ...c,
          company_name: cache[c.company_id]?.company_name || c.company_id,
        }));
        setCustomers(joined);
      })
      .catch(err => {
        console.error('Failed to load customers:', err);
        setError('Failed to load customers');
      })
      .finally(() => setLoading(false));
  };

  useEffect(() => {
    loadData(page, search, activeStatus);
  }, [page, search, activeStatus]);

  // Load stats, statuses, and reps once on mount
  useEffect(() => {
    // Load global KPI stats
    customerService.getCustomerStats()
      .then(res => setStats(res.data))
      .catch(err => console.warn('Failed to load customer stats:', err));

    // Load status list for pills
    customerService.getCustomerStatuses()
      .then(res => setStatuses(res.data || []))
      .catch(() => setStatuses(['Active', 'At Risk', 'Paused']));

    // Load sales reps for name resolution
    salesRepService.getSalesReps({ page: 1, page_size: 500 })
      .then(res => {
        const reps = res.data?.items || res.data || [];
        const map = {};
        reps.forEach(r => { map[r.rep_id] = r.full_name; });
        setSalesReps(map);
      })
      .catch(err => console.error('Failed to load sales reps:', err));
  }, []);

  const handleSearch = (val) => {
    setSearch(val);
    setPage(1);
  };

  const handleStatusFilter = (status) => {
    setActiveStatus(status);
    setPage(1);
  };

  const openAddModal = () => {
    setEditingCustomer(null);
    setFormData({
      company_id: '', originating_opportunity_id: '',
      customer_since: new Date().toISOString().split('T')[0],
      csm_rep_id: '', customer_tier: 'Standard',
      contract_type: 'Annual', renewal_date: '', customer_status: 'Active'
    });
    setCompanySearch(''); setCompanyResults([]);
    setOppSearch(''); setOppResults([]);
    setRepSearch(''); setRepResults([]);
    setFormError('');
    setIsModalOpen(true);
  };

  const openEditModal = (c, e) => {
    e.stopPropagation();
    setEditingCustomer(c);
    setFormData({
      company_id: c.company_id || '',
      originating_opportunity_id: c.originating_opportunity_id || '',
      customer_since: c.customer_since || '',
      csm_rep_id: c.csm_rep_id || '',
      customer_tier: c.customer_tier || '',
      contract_type: c.contract_type || '',
      renewal_date: c.renewal_date || '',
      customer_status: c.customer_status || 'Active'
    });
    setCompanySearch(c.company_name || c.company_id || '');
    setCompanyResults([]);
    setOppSearch(c.originating_opportunity_id || '');
    setOppResults([]);
    setRepSearch(salesReps[c.csm_rep_id] || c.csm_rep_id || '');
    setRepResults([]);
    setFormError('');
    setIsModalOpen(true);
  };

  const initiateDelete = (c, e) => {
    e.stopPropagation();
    setCustomerToDelete(c);
    setIsDeleteModalOpen(true);
  };

  const confirmDelete = () => {
    if (!customerToDelete) return;
    customerService.deleteCustomer(customerToDelete.customer_id)
      .then(() => {
        setIsDeleteModalOpen(false);
        setCustomerToDelete(null);
        loadData(page, search, activeStatus);
        customerService.getCustomerStats().then(res => setStats(res.data)).catch(() => {});
      })
      .catch(err => alert(err.response?.data?.detail || 'Failed to delete customer'));
  };

  const handleFormSubmit = async () => {
    if (!formData.company_id) { setFormError('Company selection is required'); return; }
    if (!formData.originating_opportunity_id) { setFormError('Originating Opportunity is required'); return; }
    if (!formData.csm_rep_id) { setFormError('CSM Representative is required'); return; }
    setSubmitting(true);
    setFormError('');
    try {
      if (editingCustomer) {
        await customerService.updateCustomer(editingCustomer.customer_id, formData);
      } else {
        await customerService.createCustomer(formData);
      }
      setIsModalOpen(false);
      loadData(page, search, activeStatus);
      customerService.getCustomerStats().then(res => setStats(res.data)).catch(() => {});
    } catch (err) {
      setFormError(err.response?.data?.detail || 'An error occurred');
    } finally {
      setSubmitting(false);
    }
  };

  // Dropdown handlers
  const handleCompanySearch = (e) => {
    const val = e.target.value;
    setCompanySearch(val);
    if (searchTimeoutRef.current) clearTimeout(searchTimeoutRef.current);
    if (!val) { setCompanyResults([]); return; }
    setCompanySearching(true);
    searchTimeoutRef.current = setTimeout(() => {
      companyService.getCompanies({ search: val, page_size: 10 })
        .then(res => setCompanyResults(res.data?.items || res.data?.data || res.data || []))
        .finally(() => setCompanySearching(false));
    }, 400);
  };
  const selectCompany = (comp) => {
    setFormData({ ...formData, company_id: comp.company_id });
    setCompanySearch(comp.company_name);
    setCompanyResults([]);
  };

  const handleOppSearch = (e) => {
    const val = e.target.value;
    setOppSearch(val);
    if (oppTimeoutRef.current) clearTimeout(oppTimeoutRef.current);
    if (!val) { setOppResults([]); return; }
    setOppSearching(true);
    oppTimeoutRef.current = setTimeout(() => {
      opportunityService.getOpportunities({ search: val, page_size: 10 })
        .then(res => setOppResults(res.data?.items || res.data?.data || res.data || []))
        .finally(() => setOppSearching(false));
    }, 400);
  };
  const selectOpp = (opp) => {
    setFormData({ ...formData, originating_opportunity_id: opp.opportunity_id });
    setOppSearch(opp.opportunity_name || opp.opportunity_id);
    setOppResults([]);
  };

  const handleRepSearch = (e) => {
    const val = e.target.value;
    setRepSearch(val);
    if (repTimeoutRef.current) clearTimeout(repTimeoutRef.current);
    if (!val) { setRepResults([]); return; }
    setRepSearching(true);
    repTimeoutRef.current = setTimeout(() => {
      salesRepService.getSalesReps({ search: val, page_size: 10 })
        .then(res => setRepResults(res.data?.items || res.data?.data || res.data || []))
        .finally(() => setRepSearching(false));
    }, 400);
  };
  const selectRep = (rep) => {
    setFormData({ ...formData, csm_rep_id: rep.rep_id });
    setRepSearch(rep.full_name);
    setRepResults([]);
  };

  // Status count from stats
  const statusCount = (s) => {
    if (s === 'All Status') return stats.total;
    if (s === 'Active') return stats.active;
    if (s === 'At Risk') return stats.atRisk;
    if (s === 'Paused') return stats.churned;
    return null;
  };

  const headers = ['CUSTOMER ID', 'CUSTOMER NAME', 'STATUS', 'TIER', 'CONTRACT TYPE', 'RENEWAL DATE', 'CSM REP ID', 'ACTIONS'];

  const rows = customers.map(c => [
    <span key="id" style={{ fontFamily: 'monospace', fontSize: '12px', color: 'var(--ink-mute)' }}>{c.customer_id}</span>,
    <div key="name" style={{ display: 'flex', flexDirection: 'column' }}>
      <span 
        style={{ fontWeight: 600, color: 'var(--accent-primary)', cursor: 'pointer', transition: 'color 0.15s ease' }}
        onMouseEnter={(e) => e.target.style.color = 'var(--accent-hover)'}
        onMouseLeave={(e) => e.target.style.color = 'var(--accent-primary)'}
        onClick={() => navigate(`/customers/${c.customer_id}`)}
      >
        {c.company_name || '-'}
      </span>
    </div>,
    c.customer_status ? <CRMStatusBadge key="status" status={c.customer_status} /> : '-',
    c.customer_tier ? (
      <span key="tier" style={{ background: 'var(--ivory)', border: '1px solid var(--border)', borderRadius: '6px', padding: '3px 10px', fontSize: '12px', fontWeight: 500 }}>
        {c.customer_tier}
      </span>
    ) : '-',
    c.contract_type || '-',
    c.renewal_date ? new Date(c.renewal_date).toLocaleDateString('en-IN', { day: '2-digit', month: 'short', year: 'numeric' }) : '-',
    c.csm_rep_id || '-',
    <div key="actions" className="row-actions" onClick={e => e.stopPropagation()} style={{ display: 'flex', gap: '6px', alignItems: 'center' }}>
      <Button variant="secondary" size="small" icon="eye" onClick={() => navigate(`/customers/${c.customer_id}`)}>View Details</Button>
      <Button variant="ghost" size="small" icon="settings" onClick={(e) => openEditModal(c, e)}>Edit</Button>
      <Button variant="ghost" size="small" icon="x" onClick={(e) => initiateDelete(c, e)} style={{ color: 'var(--danger)' }}>Delete</Button>
    </div>
  ]);

  const dropdownStyle = {
    position: 'absolute', top: '100%', left: 0, right: 0,
    background: '#fff', border: '1px solid var(--border)', borderRadius: '8px',
    zIndex: 20, maxHeight: '180px', overflowY: 'auto',
    boxShadow: '0 8px 24px rgba(0,0,0,0.12)', marginTop: '2px'
  };
  const dropdownItemStyle = {
    padding: '9px 12px', cursor: 'pointer', borderBottom: '1px solid var(--border-light)', fontSize: '13px'
  };

  return (
    <div className="page" style={{ display: 'flex', flexDirection: 'column' }}>
      <PageHeader
        title="Customers"
        desc="Manage all customer accounts and view their status, value, and engagement."
        actions={
          <Button variant="primary" icon="plus" onClick={openAddModal}>Add Customer</Button>
        }
      />

      {/* KPI Cards */}
      <div className="kpi-grid" style={{ marginBottom: '8px' }}>
        <KpiCard label="TOTAL CUSTOMERS" value={stats.total} icon="users" delta="12%" dir="up" ctx="All customer accounts" />
        <KpiCard label="ACTIVE CUSTOMERS" value={stats.active} icon="check-circle" delta="8%" dir="up" ctx="Currently active" />
        <KpiCard label="AT RISK CUSTOMERS" value={stats.atRisk} icon="alert-triangle" delta="2%" dir="up" ctx="Need attention" />
        <KpiCard label="PAUSED CUSTOMERS" value={stats.churned} icon="pause-circle" delta="33%" dir="down" ctx="Temporarily paused" />
      </div>

      {/* Status Pills — matching Companies module exactly */}
      <div style={{ margin: '0 28px 16px 28px', display: 'flex', gap: '8px', overflowX: 'auto', alignItems: 'center', flexShrink: 0 }}>
        {['All Status', ...statuses].map(status => {
          const count = statusCount(status);
          const isActive = activeStatus === status;
          return (
            <button
              key={status}
              onClick={() => handleStatusFilter(status)}
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
              {status}{count != null ? ` (${count})` : ''}
            </button>
          );
        })}
      </div>

      {/* Search + Table */}
      <div style={{ padding: '0 28px 28px', flex: 1, display: 'flex', flexDirection: 'column' }}>
        <FilterBar
          searchPlaceholder="Search by customer ID, name, tier, contract type, or status..."
          searchValue={search}
          onSearchChange={handleSearch}
        />
        <div style={{ display: 'flex', flexDirection: 'column', flex: 1, marginTop: '16px' }}>
          <CRMDataTable
            headers={headers}
            rows={rows}
            loading={loading}
            error={error}
            onRowClick={(row, idx) => navigate(`/customers/${customers[idx].customer_id}`)}
          />
          {!loading && !error && (
            <div style={{ marginTop: 'auto', paddingTop: '16px', borderTop: '1px solid var(--border-light)' }}>
              <TablePagination
                page={page}
                totalPages={totalPages}
                totalRecords={totalItems}
                onPrev={() => setPage(p => Math.max(1, p - 1))}
                onNext={() => setPage(p => Math.min(totalPages, p + 1))}
              />
            </div>
          )}
        </div>
      </div>

      {/* Add/Edit Modal */}
      <Modal
        isOpen={isModalOpen}
        onClose={() => setIsModalOpen(false)}
        title={editingCustomer ? 'Edit Customer' : 'Add Customer'}
        footer={
          <>
            <Button variant="secondary" onClick={() => setIsModalOpen(false)} disabled={submitting}>Cancel</Button>
            <Button variant="primary" onClick={handleFormSubmit} disabled={submitting}>
              {submitting ? 'Saving...' : 'Save Customer'}
            </Button>
          </>
        }
      >
        {formError && <div className="err" style={{ marginBottom: '16px' }}>{formError}</div>}

        <div className="field" style={{ position: 'relative' }}>
          <label>Company *</label>
          <input type="text" className="input" placeholder="Search for a company..."
            value={companySearch} onChange={handleCompanySearch} disabled={!!editingCustomer} />
          {companySearching && <div style={{ fontSize: '11px', color: 'var(--ink-mute)', marginTop: '4px' }}>Searching...</div>}
          {companyResults.length > 0 && (
            <div style={dropdownStyle}>
              {companyResults.map(c => (
                <div key={c.company_id} onClick={() => selectCompany(c)} style={dropdownItemStyle}
                  onMouseEnter={e => e.currentTarget.style.background = 'var(--ivory)'}
                  onMouseLeave={e => e.currentTarget.style.background = 'transparent'}>
                  <div style={{ fontWeight: 500 }}>{c.company_name}</div>
                  <div style={{ fontSize: '11px', color: 'var(--ink-mute)' }}>{c.company_id}</div>
                </div>
              ))}
            </div>
          )}
        </div>

        <div className="field" style={{ position: 'relative', marginTop: '12px' }}>
          <label>Originating Opportunity *</label>
          <input type="text" className="input" placeholder="Search for an opportunity..."
            value={oppSearch} onChange={handleOppSearch} />
          {oppSearching && <div style={{ fontSize: '11px', color: 'var(--ink-mute)', marginTop: '4px' }}>Searching...</div>}
          {oppResults.length > 0 && (
            <div style={dropdownStyle}>
              {oppResults.map(o => (
                <div key={o.opportunity_id} onClick={() => selectOpp(o)} style={dropdownItemStyle}
                  onMouseEnter={e => e.currentTarget.style.background = 'var(--ivory)'}
                  onMouseLeave={e => e.currentTarget.style.background = 'transparent'}>
                  <div style={{ fontWeight: 500 }}>{o.opportunity_name || o.opportunity_id}</div>
                  <div style={{ fontSize: '11px', color: 'var(--ink-mute)' }}>₹{o.deal_value_inr?.toLocaleString() || 'N/A'}</div>
                </div>
              ))}
            </div>
          )}
        </div>

        <div className="field" style={{ position: 'relative', marginTop: '12px' }}>
          <label>CSM Representative *</label>
          <input type="text" className="input" placeholder="Search sales rep..."
            value={repSearch} onChange={handleRepSearch} 
            disabled={effectiveRole === 'Sales Rep'}
            style={{ backgroundColor: effectiveRole === 'Sales Rep' ? 'var(--bg-light)' : 'white' }}
          />
          {repSearching && <div style={{ fontSize: '11px', color: 'var(--ink-mute)', marginTop: '4px' }}>Searching...</div>}
          {repResults.length > 0 && (
            <div style={dropdownStyle}>
              {repResults.map(r => (
                <div key={r.rep_id} onClick={() => selectRep(r)} style={dropdownItemStyle}
                  onMouseEnter={e => e.currentTarget.style.background = 'var(--ivory)'}
                  onMouseLeave={e => e.currentTarget.style.background = 'transparent'}>
                  <div style={{ fontWeight: 500 }}>{r.full_name}</div>
                  <div style={{ fontSize: '11px', color: 'var(--ink-mute)' }}>{r.rep_id}</div>
                </div>
              ))}
            </div>
          )}
          {formData.csm_rep_id && !repResults.length && (
            <div style={{ fontSize: '11px', color: 'var(--success)', marginTop: '4px' }}>✓ Selected: {formData.csm_rep_id}</div>
          )}
        </div>

        <div style={{ display: 'flex', gap: '12px', marginTop: '12px' }}>
          <FormInput label="Customer Tier" value={formData.customer_tier}
            onChange={e => setFormData({ ...formData, customer_tier: e.target.value })} />
          <FormInput label="Contract Type" value={formData.contract_type}
            onChange={e => setFormData({ ...formData, contract_type: e.target.value })} />
        </div>

        <div style={{ display: 'flex', gap: '12px', marginTop: '12px' }}>
          <FormInput type="date" label="Customer Since" value={formData.customer_since}
            onChange={e => setFormData({ ...formData, customer_since: e.target.value })} />
          <FormInput type="date" label="Renewal Date" value={formData.renewal_date}
            onChange={e => setFormData({ ...formData, renewal_date: e.target.value })} />
        </div>

        <div className="field" style={{ marginTop: '12px' }}>
          <label>Customer Status</label>
          <select value={formData.customer_status}
            onChange={e => setFormData({ ...formData, customer_status: e.target.value })}
            style={{ width: '100%', padding: '9px 12px', borderRadius: '8px', border: '1px solid var(--border)', background: 'var(--white)', fontSize: '13px' }}>
            <option value="Active">Active</option>
            <option value="At Risk">At Risk</option>
            <option value="Paused">Paused</option>
          </select>
        </div>
      </Modal>

      {/* Delete Modal */}
      <Modal
        isOpen={isDeleteModalOpen}
        onClose={() => setIsDeleteModalOpen(false)}
        title="Archive Customer"
        footer={
          <>
            <Button variant="secondary" onClick={() => setIsDeleteModalOpen(false)}>Cancel</Button>
            <Button variant="danger" onClick={confirmDelete}>Archive Customer</Button>
          </>
        }
      >
        <p>Are you sure you want to archive the customer record for <strong>{customerToDelete?.company_name}</strong>?</p>
        <p style={{ fontSize: '13px', color: 'var(--ink-mute)', marginTop: '8px' }}>The record will be removed from this view but can be restored by an administrator.</p>
      </Modal>
    </div>
  );
}
