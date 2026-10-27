import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import PageHeader from '../components/common/PageHeader';
import FilterBar from '../components/common/table/FilterBar';
import Modal from '../components/common/Modal';
import FormInput from '../components/common/FormInput';
import Button from '../components/common/Button';
import KpiCard from '../components/common/KpiCard';
import { CRMDataTable, TablePagination, CRMStatusBadge } from '../components/common/table';
import { companyService, referenceService } from '../services/crmService';

export default function Companies() {
  const navigate = useNavigate();
  const [companies, setCompanies] = useState([]);
  const [industries, setIndustries] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  
  // Pagination State
  const [page, setPage] = useState(1);
  const [pageSize] = useState(50);
  const [totalPages, setTotalPages] = useState(1);
  const [totalRecords, setTotalRecords] = useState(0);

  // Search & Filters
  const [search, setSearch] = useState('');
  const [debouncedSearch, setDebouncedSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState('All Status');
  const [stateFilter, setStateFilter] = useState('All');
  const [industryFilter, setIndustryFilter] = useState('All');

  const [isModalOpen, setIsModalOpen] = useState(false);
  const [editingCompany, setEditingCompany] = useState(null);
  const [formData, setFormData] = useState({
    company_name: '', industry_id: '', sub_industry: '',
    company_size_band: '', annual_revenue_band_inr: '',
    gstin: '', city: '', state: '', region: '', pincode: ''
  });
  const [submitting, setSubmitting] = useState(false);
  const [formError, setFormError] = useState('');

  const [isDeleteModalOpen, setIsDeleteModalOpen] = useState(false);
  const [companyToDelete, setCompanyToDelete] = useState(null);
  const [deleting, setDeleting] = useState(false);
  const [deleteError, setDeleteError] = useState('');

  // Debounce search
  useEffect(() => {
    const handler = setTimeout(() => {
      setDebouncedSearch(search);
    }, 500);
    return () => clearTimeout(handler);
  }, [search]);

  const [totalCompaniesGlobal, setTotalCompaniesGlobal] = useState(0);
  const [activeCustomersGlobal, setActiveCustomersGlobal] = useState(0);

  const [uniqueStatuses, setUniqueStatuses] = useState(['All Status']);
  const [categoryCounts, setCategoryCounts] = useState({});

  // Reset page to 1 when filters change
  useEffect(() => {
    setPage(1);
  }, [debouncedSearch, statusFilter]);

  const fetchCategoryCounts = async (searchQuery, statuses) => {
    if (!statuses || statuses.length === 0) return;
    try {
      const counts = {};
      const promises = statuses.map(async (status) => {
        const params = { page: 1, page_size: 1 };
        if (status !== 'All Status') {
          params.account_status = status;
        }
        if (searchQuery) {
          params.search = searchQuery;
        }
        const res = await companyService.getCompanies(params);
        counts[status] = res.data?.total || 0;
      });
      await Promise.all(promises);
      setCategoryCounts(counts);
    } catch (err) {
      console.error("Failed to fetch company category counts", err);
    }
  };

  useEffect(() => {
    fetchCategoryCounts(debouncedSearch, uniqueStatuses);
  }, [debouncedSearch, uniqueStatuses]);

  const loadKpis = async () => {
    try {
      const allRes = await companyService.getCompanies({ page_size: 200 });
      const allComps = allRes.data?.items || allRes.data || [];
      const statuses = [...new Set(allComps.map(c => c.account_status).filter(Boolean))];
      setUniqueStatuses(['All Status', ...statuses.sort()]);
      
      setTotalCompaniesGlobal(allRes.data?.total || 0);
      
      const activeRes = await companyService.getCompanies({ account_status: 'Active Customer', page_size: 1 });
      setActiveCustomersGlobal(activeRes.data?.total || 0);
    } catch (err) {
      console.error("Failed to load KPIs", err);
    }
  };

  const loadData = () => {
    setLoading(true);
    setError(null);
    const params = {
      page,
      page_size: pageSize,
      sort_by: 'account_status',
      ...(debouncedSearch ? { search: debouncedSearch } : {}),
      ...(statusFilter !== 'All Status' ? { account_status: statusFilter } : {})
    };

    companyService.getCompanies(params).then(res => {
      const data = res.data?.items || res.data || [];
      setCompanies(data);
      setTotalPages(res.data?.total_pages || 1);
      setTotalRecords(res.data?.total || data.length);
    }).catch(err => {
      console.error("Failed to load companies:", err);
      setError("Unable to load companies. Please try again.");
    }).finally(() => {
      setLoading(false);
    });
  };

  const loadReferenceData = async () => {
    try {
      const res = await referenceService.getIndustries();
      setIndustries(res.data || []);
    } catch (err) {
      console.error("Failed to load industries:", err);
    }
  };

  useEffect(() => {
    loadReferenceData();
    loadKpis();
  }, []);

  useEffect(() => {
    loadData();
  }, [page, debouncedSearch, statusFilter]);

  const openAddModal = () => {
    setEditingCompany(null);
    setFormData({
      company_name: '', industry_id: '', sub_industry: '',
      company_size_band: '', annual_revenue_band_inr: '',
      gstin: '', city: '', state: '', region: '', pincode: ''
    });
    setFormError('');
    setIsModalOpen(true);
  };

  const openEditModal = (comp, e) => {
    e.stopPropagation();
    setEditingCompany(comp);
    setFormData({
      company_name: comp.company_name || '',
      industry_id: comp.industry_id || '',
      sub_industry: comp.sub_industry || '',
      company_size_band: comp.company_size_band || '',
      annual_revenue_band_inr: comp.annual_revenue_band_inr || '',
      gstin: comp.gstin || '',
      city: comp.city || '',
      state: comp.state || '',
      region: comp.region || '',
      pincode: comp.pincode || ''
    });
    setFormError('');
    setIsModalOpen(true);
  };

  const handleDeleteClick = (comp, e) => {
    e.stopPropagation();
    setCompanyToDelete(comp);
    setDeleteError('');
    setIsDeleteModalOpen(true);
  };

  const confirmDelete = async () => {
    if (!companyToDelete) return;
    setDeleting(true);
    setDeleteError('');
    try {
      await companyService.deleteCompany(companyToDelete.company_id);
      setIsDeleteModalOpen(false);
      setCompanyToDelete(null);
      loadData();
    } catch (err) {
      setDeleteError(err.response?.data?.detail || 'Error deleting company');
    } finally {
      setDeleting(false);
    }
  };

  const handleFormSubmit = async () => {
    if (!formData.company_name) {
      setFormError('Company Name is required');
      return;
    }
    setSubmitting(true);
    setFormError('');
    
    // Clean up empty strings to null for backend optional fields, if needed.
    // The backend schemas allow Optional[str] = None. We can just send strings.
    const payload = { ...formData };

    try {
      if (editingCompany) {
        await companyService.updateCompany(editingCompany.company_id, payload);
      } else {
        await companyService.createCompany(payload);
      }
      setIsModalOpen(false);
      loadData();
    } catch (err) {
      setFormError(err.response?.data?.detail || 'An error occurred');
    } finally {
      setSubmitting(false);
    }
  };

  // KPI Calculations
  const industriesCount = industries.length;

  const headers = ['COMPANY', 'INDUSTRY', 'TERRITORY / LOCATION', 'STATUS', 'CREATED DATE', 'ACTIONS'];

  const getIndustryName = (id) => {
    const ind = industries.find(i => i.industry_id === id);
    return ind ? ind.industry_name : (id || '-');
  };

  const rows = companies.map(c => {
    // Format Date
    let createdStr = c.created_at || '-';
    if (createdStr !== '-') {
      try {
        const d = new Date(createdStr);
        createdStr = d.toLocaleDateString();
      } catch (e) {
        // ignore
      }
    }

    const territory = [c.city, c.state].filter(Boolean).join(', ') || '-';

    return [
      <div key="company" style={{ display: 'flex', flexDirection: 'column' }}>
        <span 
          style={{ fontWeight: 600, color: 'var(--accent-primary)', cursor: 'pointer', transition: 'color 0.15s ease' }}
          onMouseEnter={(e) => e.target.style.color = 'var(--accent-hover)'}
          onMouseLeave={(e) => e.target.style.color = 'var(--accent-primary)'}
          onClick={() => navigate(`/companies/${c.company_id}`)}
        >
          {c.company_name || '-'}
        </span>
        <span style={{ fontSize: '12px', color: 'var(--slate)' }}>{c.company_id || '-'}</span>
      </div>,
      getIndustryName(c.industry_id),
      territory,
      c.account_status ? <CRMStatusBadge status={c.account_status} /> : '-',
      createdStr,
      <div key="actions" className="row-actions" onClick={e => e.stopPropagation()} style={{ display: 'flex', gap: '6px', alignItems: 'center' }}>
        <Button variant="secondary" size="small" icon="eye" onClick={() => navigate(`/companies/${c.company_id}`)}>View 360</Button>
        <Button variant="ghost" size="small" icon="settings" onClick={(e) => openEditModal(c, e)}>Edit</Button>
        <Button variant="ghost" size="small" icon="x" onClick={(e) => handleDeleteClick(c, e)} style={{ color: 'var(--danger)' }}>Delete</Button>
      </div>
    ];
  });

  return (
    <div className="page" style={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
      <PageHeader 
        title="Companies" 
        desc="Manage all company records and view account statuses."
        actions={
          <div style={{ display: 'flex', gap: '12px', alignItems: 'center' }}>
            <Button variant="primary" icon="plus" onClick={openAddModal}>Add Company</Button>
          </div>
        }
      />
      
      <div className="row">
        <KpiCard label="TOTAL COMPANIES" value={totalCompaniesGlobal} ctx="All company records" />
        <KpiCard label="ACTIVE CUSTOMERS" value={activeCustomersGlobal} ctx="Active customer accounts" />
        <KpiCard label="INDUSTRIES" value={industriesCount} ctx="Distinct industries" />
      </div>

      {/* Status Subcategory */}
      <div style={{
        padding: '0 28px 20px',
        display: 'flex',
        gap: '10px',
        overflowX: 'auto',
        borderBottom: '1px solid var(--gray-200)',
        marginBottom: '20px',
        flexShrink: 0
      }}>
        {uniqueStatuses.map(status => (
          <button
            key={status}
            onClick={() => setStatusFilter(status)}
            style={{
              padding: '6px 16px',
              borderRadius: '20px',
              border: statusFilter === status ? '1px solid black' : '1px solid transparent',
              background: statusFilter === status ? 'black' : 'var(--white)',
              color: statusFilter === status ? 'var(--white)' : 'var(--ink)',
              fontSize: '13px',
              fontWeight: 600,
              cursor: 'pointer',
              whiteSpace: 'nowrap',
              transition: 'all 0.2s ease',
            }}
          >
            {status} {categoryCounts[status] !== undefined ? `(${categoryCounts[status]})` : ''}
          </button>
        ))}
      </div>

      <div style={{ padding: '0 28px 28px', flex: 1, display: 'flex', flexDirection: 'column' }}>
        <FilterBar 
          searchPlaceholder="Search by ID, Name, State, or Status..." 
          searchValue={search} 
          onSearchChange={setSearch} 
        />
        <div style={{ display: 'flex', flexDirection: 'column', flex: 1, marginTop: '16px' }}>
          <CRMDataTable 
            headers={headers}
            rows={rows}
            loading={loading}
            error={error}
            onRetry={loadData}
            emptyTitle="No Companies Found"
            emptyDescription={
              debouncedSearch || statusFilter !== 'All' || stateFilter !== 'All' || industryFilter !== 'All' 
                ? 'Try adjusting your search or filters.' 
                : 'No companies found in the CRM.'
            }
            onRowClick={(row, rIdx) => {
              const comp = companies[rIdx];
              if (comp && comp.company_id) {
                navigate(`/companies/${comp.company_id}`);
              }
            }}
          />
          {!loading && !error && companies.length > 0 && (
            <TablePagination
              page={page}
              totalPages={totalPages}
              totalRecords={totalRecords}
              onPrev={() => setPage(p => p - 1)}
              onNext={() => setPage(p => p + 1)}
            />
          )}
        </div>
      </div>

      {/* Add/Edit Modal */}
      <Modal 
        isOpen={isModalOpen} 
        onClose={() => setIsModalOpen(false)} 
        title={editingCompany ? 'Edit Company' : 'Add Company'}
        footer={
          <>
            <Button variant="secondary" onClick={() => setIsModalOpen(false)} disabled={submitting}>Cancel</Button>
            <Button variant="primary" onClick={handleFormSubmit} disabled={submitting}>
              {submitting ? 'Saving...' : 'Save Company'}
            </Button>
          </>
        }
      >
        {formError && <div className="err" style={{ marginBottom: '16px', color: 'var(--danger)' }}>{formError}</div>}
        <FormInput label="Company Name" required value={formData.company_name} onChange={e => setFormData({...formData, company_name: e.target.value})} />
        <FormInput label="Industry" value={formData.industry_id} onChange={e => setFormData({...formData, industry_id: e.target.value})} />
        <FormInput label="Sub Industry" value={formData.sub_industry} onChange={e => setFormData({...formData, sub_industry: e.target.value})} />
        <div style={{ display: 'flex', gap: '16px' }}>
          <FormInput label="City" value={formData.city} onChange={e => setFormData({...formData, city: e.target.value})} />
          <FormInput label="State" value={formData.state} onChange={e => setFormData({...formData, state: e.target.value})} />
        </div>
        <div style={{ display: 'flex', gap: '16px' }}>
          <FormInput label="Region" value={formData.region} onChange={e => setFormData({...formData, region: e.target.value})} />
          <FormInput label="Pincode" value={formData.pincode} onChange={e => setFormData({...formData, pincode: e.target.value})} />
        </div>
        <FormInput label="GSTIN" value={formData.gstin} onChange={e => setFormData({...formData, gstin: e.target.value})} />
      </Modal>

      {/* Delete Confirmation Modal */}
      <Modal 
        isOpen={isDeleteModalOpen} 
        onClose={() => setIsDeleteModalOpen(false)} 
        title="Delete Company"
        footer={
          <>
            <Button variant="secondary" onClick={() => setIsDeleteModalOpen(false)} disabled={deleting}>Cancel</Button>
            <Button variant="danger" onClick={confirmDelete} disabled={deleting}>
              {deleting ? 'Deleting...' : 'Delete'}
            </Button>
          </>
        }
      >
        {deleteError && <div className="err" style={{ marginBottom: '16px', color: 'var(--danger)' }}>{deleteError}</div>}
        <p>Are you sure you want to delete company <strong>{companyToDelete?.company_name}</strong>?</p>
        <p style={{ color: 'var(--ink-mute)', fontSize: '13px', marginTop: '8px' }}>This action cannot be undone.</p>
      </Modal>
    </div>
  );
}
