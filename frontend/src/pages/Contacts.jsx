import React, { useState, useEffect, useRef } from 'react';
import {  useNavigate , useSearchParams } from "react-router-dom";
import PageHeader from '../components/common/PageHeader';
import Button from '../components/common/Button';
import Modal from '../components/common/Modal';
import FormInput from '../components/common/FormInput';
import KpiCard from '../components/common/KpiCard';
import { CRMDataTable, TablePagination, FilterBar, CRMStatusBadge, TableLoadingSkeleton, TableEmptyState } from '../components/common/table';
import { contactService, companyService, customerService } from '../services/crmService';
import { User, Building2, Mail, Phone, Briefcase, Calendar, Crown, ExternalLink, Copy } from 'lucide-react';

export default function Contacts() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const [contacts, setContacts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  
  // Pagination & Search
  const [page, setPage] = useState(1);
  const [pageSize] = useState(25);
  const [totalItems, setTotalItems] = useState(0);
  const [totalPages, setTotalPages] = useState(1);
  const [search, setSearch] = useState('');
  const [debouncedSearch, setDebouncedSearch] = useState('');

  // Job Role Filter
  const [jobRoleFilter, setJobRoleFilter] = useState('All Contacts');
  const jobRoles = ['All Contacts', 'Leadership', 'Operations', 'Sales & Marketing', 'Procurement', 'Finance', 'IT', 'HR'];
  const [categoryCounts, setCategoryCounts] = useState({});

  const handleRoleFilter = (role) => {
    setJobRoleFilter(role);
    setPage(1);
    loadData(1, debouncedSearch, role);
  };


  // Debounce search
  useEffect(() => {
    const handler = setTimeout(() => {
      setDebouncedSearch(search);
    }, 500);
    return () => clearTimeout(handler);
  }, [search]);

  // Reset page to 1 when filters change
  useEffect(() => {
    setPage(1);
  }, [debouncedSearch]);

  const fetchCategoryCounts = async (searchQuery) => {
    try {
      const counts = {};
      const promises = jobRoles.map(async (role) => {
        const params = { skip: 0, limit: 1 };
      if (searchParams.get('company_id')) params.company_id = searchParams.get('company_id');
      if (searchParams.get('customer_id')) params.customer_id = searchParams.get('customer_id');

        if (role !== 'All Contacts') {
          params.job_role = role;
        }
        if (searchQuery) {
          params.search = searchQuery;
        }
        const res = await contactService.getContacts(params);
        counts[role] = res.data?.total || 0;
      });
      await Promise.all(promises);
      setCategoryCounts(counts);
    } catch (err) {
      console.error("Failed to fetch contact category counts", err);
    }
  };

  // Company Name Resolution
  const [companyCache, setCompanyCache] = useState({});

  // KPIs
  const [kpis, setKpis] = useState({
    total: 0,
    companiesRepresented: 0,
    withEmail: 0,
    withPhone: 0
  });

  // Modal State
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [isViewModalOpen, setIsViewModalOpen] = useState(false);
  const [viewingContact, setViewingContact] = useState(null);
  
  const openViewModal = (contact) => {
    setViewingContact(contact);
    setIsViewModalOpen(true);
  };
  const [editingContact, setEditingContact] = useState(null);
  const [formData, setFormData] = useState({
    company_id: '',
    full_name: '',
    job_title: '',
    seniority_level: '',
    department: '',
    email: '',
    phone: '',
    is_primary_contact: false,
    linkedin_handle: '',
    is_decision_maker: false
  });
  const [submitting, setSubmitting] = useState(false);
  const [formError, setFormError] = useState('');

  // Company Dropdown State
  const [companySearch, setCompanySearch] = useState('');
  const [companyResults, setCompanyResults] = useState([]);
  const [searchingCompanies, setSearchingCompanies] = useState(false);

  // Delete Confirmation State
  const [deleteConfirmOpen, setDeleteConfirmOpen] = useState(false);
  const [contactToDelete, setContactToDelete] = useState(null);
  const [deleteError, setDeleteError] = useState('');
  const [deleting, setDeleting] = useState(false);

  useEffect(() => {
    loadData(page, debouncedSearch, jobRoleFilter);
    // eslint-disable-next-line
  }, [page, debouncedSearch, jobRoleFilter]);

  async function loadData(currentPage = page, currentSearch = search, currentRole = jobRoleFilter) {
    setLoading(true);
    setError('');
    try {
      const skip = (currentPage - 1) * pageSize;
      const params = { skip, limit: pageSize };
      if (searchParams.get('company_id')) params.company_id = searchParams.get('company_id');
      if (searchParams.get('customer_id')) params.customer_id = searchParams.get('customer_id');

      if (currentSearch) params.search = currentSearch;
      if (currentRole && currentRole !== 'All Contacts') params.job_role = currentRole;
      
      const res = await contactService.getContacts(params);
      
      const items = res.data?.items || res.data || [];
      setContacts(items);
      setTotalItems(res.data?.total || 0);
      setTotalPages(res.data?.total_pages || 1);
      
      fetchCategoryCounts(currentSearch);

      // Resolve Company Names
      const uniqueCompanyIds = [...new Set(items.map(c => c.company_id).filter(Boolean))];
      const missingIds = uniqueCompanyIds.filter(id => !companyCache[id]);

      if (missingIds.length > 0) {
        const newCache = { ...companyCache };
        await Promise.all(
          missingIds.map(async (id) => {
            try {
              const [compRes, custRes] = await Promise.all([
                companyService.getCompany(id),
                customerService.getCustomers({ company_id: id }).catch(() => ({ data: { items: [] } }))
              ]);
              const companyData = compRes.data;
              let customerSince = null;
              if (custRes?.data?.items?.length > 0) {
                 customerSince = custRes.data.items[0].customer_since;
              }
              newCache[id] = {
                company_name: companyData.company_name,
                industry_id: companyData.industry_id,
                account_status: companyData.account_status,
                city: companyData.city,
                state: companyData.state,
                created_at: companyData.created_at,
                customer_since: customerSince
              };
            } catch (err) {
              newCache[id] = { company_name: 'Unknown Company' };
            }
          })
        );
        setCompanyCache(newCache);
      }

      // Update KPIs only on first load/search or we could approximate. The API doesn't give global KPIs,
      // but we can calculate from the current page to preserve UI, or mock the total.
      // Since it's a paginated list, "Total Contacts" can be totalItems.
      setKpis({
        total: res.data?.total || items.length,
        companiesRepresented: uniqueCompanyIds.length, // approximation for page
        withEmail: items.filter(c => c.email).length,
        withPhone: items.filter(c => c.phone).length
      });

    } catch (err) {
      console.error("Failed to load contacts:", err);
      setError('Failed to load contacts');
    } finally {
      setLoading(false);
    }
  }

  const handleSearchChange = (val) => {
    setSearch(val);
    setPage(1);
  };

  const getCompanyName = (id) => {
    return companyCache[id]?.company_name || 'Loading...';
  };

  const openAddModal = () => {
    setEditingContact(null);
    setFormData({
      company_id: '',
      full_name: '',
      job_title: '',
      seniority_level: '',
      department: '',
      email: '',
      phone: '',
      is_primary_contact: false,
      linkedin_handle: '',
      is_decision_maker: false
    });
    setFormError('');
    setCompanySearch('');
    setCompanyResults([]);
    setIsModalOpen(true);
  };

  const openEditModal = async (contact, e) => {
    e.stopPropagation();
    setEditingContact(contact);
    setFormData({
      company_id: contact.company_id || '',
      full_name: contact.full_name || '',
      job_title: contact.job_title || '',
      seniority_level: contact.seniority_level || '',
      department: contact.department || '',
      email: contact.email || '',
      phone: contact.phone || '',
      is_primary_contact: !!contact.is_primary_contact,
      linkedin_handle: contact.linkedin_handle || '',
      is_decision_maker: !!contact.is_decision_maker
    });
    setFormError('');
    
    // Pre-populate company search if possible
    if (contact.company_id) {
       setCompanySearch(companyCache[contact.company_id]?.company_name || contact.company_id);
       setCompanyResults([{ company_id: contact.company_id, company_name: companyCache[contact.company_id]?.company_name || 'Selected Company' }]);
    } else {
       setCompanySearch('');
       setCompanyResults([]);
    }
    
    setIsModalOpen(true);
  };

  const handleCompanySearch = async (val) => {
    setCompanySearch(val);
    if (!val) {
      setCompanyResults([]);
      return;
    }
    setSearchingCompanies(true);
    try {
      const res = await companyService.getCompanies({ search: val, limit: 10 });
      setCompanyResults(res.data?.items || []);
    } catch (err) {
      console.error("Failed to search companies", err);
    } finally {
      setSearchingCompanies(false);
    }
  };

  const openDeleteConfirm = (contact, e) => {
    e.stopPropagation();
    setContactToDelete(contact);
    setDeleteError('');
    setDeleteConfirmOpen(true);
  };

  const confirmDelete = async () => {
    if (!contactToDelete) return;
    setDeleting(true);
    setDeleteError('');
    try {
      await contactService.deleteContact(contactToDelete.contact_id);
      setDeleteConfirmOpen(false);
      setContactToDelete(null);
      loadData(page, search);
    } catch (err) {
      setDeleteError(err.response?.data?.detail || 'Failed to delete contact.');
    } finally {
      setDeleting(false);
    }
  };

  const handleFormSubmit = async () => {
    if (!formData.company_id || !formData.full_name) {
      setFormError('Company and Full Name are required');
      return;
    }
    setSubmitting(true);
    setFormError('');
    try {
      if (editingContact) {
        await contactService.updateContact(editingContact.contact_id, formData);
      } else {
        await contactService.createContact(formData);
      }
      setIsModalOpen(false);
      loadData(page, search);
    } catch (err) {
      setFormError(err.response?.data?.detail || 'An error occurred while saving the contact.');
    } finally {
      setSubmitting(false);
    }
  };

  const formatDate = (val) => {
    if (!val) return '-';
    return new Date(val).toLocaleDateString();
  };

  const headers = ['Contact', 'Company', 'Contact Info', 'Designation', 'Created Date', 'Actions'];
  const rows = contacts.map(c => {
    const initials = c.full_name ? c.full_name.substring(0, 2).toUpperCase() : '??';

    const entityCell = (
      <div key="contact" style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
        <div style={{
          width: '32px', height: '32px', borderRadius: '50%',
          background: 'var(--primary-light)', color: 'var(--primary)',
          display: 'flex', alignItems: 'center', justifyContent: 'center',
          fontWeight: 600, fontSize: '12px'
        }}>
          {initials}
        </div>
        <div style={{ display: 'flex', flexDirection: 'column' }}>
          <span style={{ fontWeight: 600, color: 'var(--brown)' }}>{c.full_name || '-'}</span>
          <span style={{ fontSize: '12px', color: 'var(--slate)' }}>{c.contact_id || '-'}</span>
        </div>
      </div>
    );
    
    const companyName = companyCache[c.company_id]?.company_name || c.company_id || '-';
    
    const contactInfo = (
      <div key="info" style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
        {c.email ? <a href={`mailto:${c.email}`} onClick={e => e.stopPropagation()} style={{ color: 'var(--primary)', textDecoration: 'none', fontSize: '13px' }}>{c.email}</a> : <span style={{ color: 'var(--slate)' }}>-</span>}
        {c.phone ? <a href={`tel:${c.phone}`} onClick={e => e.stopPropagation()} style={{ color: 'var(--ink-mute)', textDecoration: 'none', fontSize: '12px' }}>{c.phone}</a> : null}
      </div>
    );
    
    const designation = (
      <div key="job" style={{ display: 'flex', flexDirection: 'column' }}>
        <span style={{ color: 'var(--ink)' }}>{c.job_title || '-'}</span>
        <span style={{ fontSize: '12px', color: 'var(--slate)' }}>{c.department || c.seniority_level || ''}</span>
      </div>
    );

    return [
      entityCell,
      companyName,
      contactInfo,
      designation,
      formatDate(c.created_at),
      <div key="actions" className="row-actions" onClick={e => e.stopPropagation()} style={{ display: 'flex', gap: '6px', alignItems: 'center' }}>
        <Button variant="secondary" size="small" icon="eye" onClick={() => openViewModal(c)}>View Details</Button>
        <Button variant="ghost" size="small" icon="settings" onClick={(e) => openEditModal(c, e)}>Edit</Button>
        <Button variant="ghost" size="small" icon="x" onClick={(e) => openDeleteConfirm(c, e)} style={{ color: 'var(--danger)' }}>Delete</Button>
      </div>
    ];
  });

  return (
    <div className="page">
      <PageHeader 
        title="Contacts" 
        desc="Manage contact profiles and relationships."
        actions={
          <Button variant="primary" icon="plus" onClick={openAddModal}>Add Contact</Button>
        }
      />
      <div style={{ padding: '0 28px 28px', flex: 1, display: 'flex', flexDirection: 'column' }}>
        
        <div className="kpi-grid" style={{ marginBottom: '24px' }}>
          <KpiCard label="Total Contacts" value={kpis.total} icon="users" delta="0" ctx="All records" dir="up" />
          <KpiCard label="Companies Represented" value={kpis.companiesRepresented} icon="briefcase" delta="0" ctx="On current page" dir="up" />
          <KpiCard label="Contacts with Email" value={kpis.withEmail} icon="mail" delta="0" ctx="On current page" dir="up" />
          <KpiCard label="Contacts with Phone" value={kpis.withPhone} icon="phone" delta="0" ctx="On current page" dir="up" />
        </div>

        <div style={{ marginBottom: '16px', display: 'flex', gap: '8px', overflowX: 'auto', alignItems: 'center', flexShrink: 0 }}>
          {jobRoles.map(role => {
            const isActive = jobRoleFilter === role;
            return (
              <button
                key={role}
                onClick={() => handleRoleFilter(role)}
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
                {role} {categoryCounts[role] !== undefined ? `(${categoryCounts[role]})` : ''}
              </button>
            );
          })}
        </div>

        <FilterBar 
          searchPlaceholder="Search by name..." 
          searchValue={search} 
          onSearchChange={setSearch} 
        />
        <div style={{ display: 'flex', flexDirection: 'column', flex: 1, marginTop: '16px' }}>
          <CRMDataTable 
            headers={headers} 
            rows={rows} 
            loading={loading}
            error={error}
            onRowClick={() => {}}
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

      {/* View Modal */}
      <Modal 
        isOpen={isViewModalOpen} 
        onClose={() => setIsViewModalOpen(false)} 
        title=""
        maxWidth={600}
        footer={
          <Button variant="secondary" onClick={() => setIsViewModalOpen(false)}>Close</Button>
        }
      >
        {viewingContact && (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '24px', maxHeight: '70vh', overflowY: 'auto', paddingRight: '8px' }}>
            {/* Modal Header inside scroll area or outside depending on requirements. Wait, "Keep the modal header fixed". The Modal component renders `title` in a fixed header, so let's put it in `title`. Actually, we can just make the body scrollable. Modal.jsx has .modal-body which is by default scrollable if we set max-height, but let's do it on this div to be safe. */}
            
            <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
              <div style={{ fontSize: '20px', fontWeight: 700, color: 'var(--ink)', marginBottom: '-8px' }}>
                Overview
              </div>
              <div style={{ display: 'flex', gap: '16px', alignItems: 'center' }}>
                <div style={{
                  width: '64px', height: '64px', borderRadius: '50%',
                  background: 'var(--primary-light)', color: 'var(--primary)',
                  display: 'flex', alignItems: 'center', justifyContent: 'center',
                  fontWeight: 600, fontSize: '24px', flexShrink: 0
                }}>
                  {viewingContact.full_name ? viewingContact.full_name.substring(0, 2).toUpperCase() : '??'}
                </div>
                <div style={{ flex: 1, display: 'flex', flexDirection: 'column', gap: '4px' }}>
                  <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                    <h2 style={{ margin: 0, color: 'var(--ink)', fontSize: '20px', fontWeight: 600 }}>{viewingContact.full_name || 'N/A'}</h2>
                    {viewingContact.is_decision_maker && (
                      <div style={{ 
                        background: 'var(--primary-light)', color: 'var(--brown)', 
                        padding: '4px 12px', borderRadius: '16px', fontSize: '12px', fontWeight: 600,
                        display: 'flex', alignItems: 'center', gap: '6px'
                      }}>
                        <Crown size={14} /> Decision Maker
                      </div>
                    )}
                  </div>
                  <div style={{ color: 'var(--ink)', fontSize: '15px' }}>
                    {viewingContact.job_title || 'N/A'} • {companyCache[viewingContact.company_id]?.company_name || viewingContact.company_id || 'N/A'}
                  </div>
                </div>
              </div>
            </div>

            <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
              {/* Personal Information */}
              <div>
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px', color: 'var(--brown)', fontWeight: 600, marginBottom: '16px', fontSize: '16px', borderBottom: '2px solid var(--brown)', paddingBottom: '8px' }}>
                  <User size={18} /> PERSONAL INFORMATION
                </div>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px 24px', fontSize: '14px', background: 'var(--white)', padding: '16px', borderRadius: '8px', border: '1px solid var(--border-light)' }}>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
                    <span style={{ color: 'var(--slate)', fontSize: '12px', fontWeight: 600, textTransform: 'uppercase' }}>Full Name</span>
                    <span style={{ color: 'var(--ink)' }}>{viewingContact.full_name || 'N/A'}</span>
                  </div>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
                    <span style={{ color: 'var(--slate)', fontSize: '12px', fontWeight: 600, textTransform: 'uppercase' }}>Email</span>
                    {viewingContact.email ? (
                       <a href={`mailto:${viewingContact.email}`} style={{ color: 'var(--primary)', textDecoration: 'none' }}>{viewingContact.email}</a>
                    ) : <span style={{ color: 'var(--ink)' }}>N/A</span>}
                  </div>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
                    <span style={{ color: 'var(--slate)', fontSize: '12px', fontWeight: 600, textTransform: 'uppercase' }}>Contact ID</span>
                    <span style={{ color: 'var(--ink)' }}>{viewingContact.contact_id || 'N/A'}</span>
                  </div>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
                    <span style={{ color: 'var(--slate)', fontSize: '12px', fontWeight: 600, textTransform: 'uppercase' }}>Phone</span>
                    <span style={{ color: 'var(--ink)' }}>{viewingContact.phone || 'N/A'}</span>
                  </div>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
                    <span style={{ color: 'var(--slate)', fontSize: '12px', fontWeight: 600, textTransform: 'uppercase' }}>Job Title</span>
                    <span style={{ color: 'var(--ink)' }}>{viewingContact.job_title || 'N/A'}</span>
                  </div>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
                    <span style={{ color: 'var(--slate)', fontSize: '12px', fontWeight: 600, textTransform: 'uppercase' }}>LinkedIn</span>
                    {viewingContact.linkedin_handle ? (
                      <a href={viewingContact.linkedin_handle} target="_blank" rel="noopener noreferrer" style={{ color: 'var(--primary)', textDecoration: 'none' }}>{viewingContact.linkedin_handle}</a>
                    ) : <span style={{ color: 'var(--ink)' }}>N/A</span>}
                  </div>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
                    <span style={{ color: 'var(--slate)', fontSize: '12px', fontWeight: 600, textTransform: 'uppercase' }}>Department</span>
                    <span style={{ color: 'var(--ink)' }}>{viewingContact.department || 'N/A'}</span>
                  </div>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
                    <span style={{ color: 'var(--slate)', fontSize: '12px', fontWeight: 600, textTransform: 'uppercase' }}>Decision Maker</span>
                    <span style={{ color: 'var(--ink)' }}>{viewingContact.is_decision_maker ? 'Yes' : 'No'}</span>
                  </div>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
                    <span style={{ color: 'var(--slate)', fontSize: '12px', fontWeight: 600, textTransform: 'uppercase' }}>Seniority Level</span>
                    <span style={{ color: 'var(--ink)' }}>{viewingContact.seniority_level || 'N/A'}</span>
                  </div>
                </div>
              </div>

              {/* Company Information */}
              <div>
                <div style={{ display: 'flex', alignItems: 'center', gap: '8px', color: 'var(--brown)', fontWeight: 600, marginBottom: '16px', fontSize: '16px', borderBottom: '2px solid var(--brown)', paddingBottom: '8px' }}>
                  <Building2 size={18} /> COMPANY INFORMATION
                </div>
                <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px 24px', fontSize: '14px', background: 'var(--white)', padding: '16px', borderRadius: '8px', border: '1px solid var(--border-light)' }}>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
                    <span style={{ color: 'var(--slate)', fontSize: '12px', fontWeight: 600, textTransform: 'uppercase' }}>Company Name</span>
                    <span style={{ color: 'var(--ink)' }}>{companyCache[viewingContact.company_id]?.company_name || 'N/A'}</span>
                  </div>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
                    <span style={{ color: 'var(--slate)', fontSize: '12px', fontWeight: 600, textTransform: 'uppercase' }}>Company ID</span>
                    <span style={{ color: 'var(--ink)' }}>{viewingContact.company_id || 'N/A'}</span>
                  </div>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
                    <span style={{ color: 'var(--slate)', fontSize: '12px', fontWeight: 600, textTransform: 'uppercase' }}>Industry</span>
                    <span style={{ color: 'var(--ink)' }}>{companyCache[viewingContact.company_id]?.industry_id || 'N/A'}</span>
                  </div>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
                    <span style={{ color: 'var(--slate)', fontSize: '12px', fontWeight: 600, textTransform: 'uppercase' }}>Account Type</span>
                    <span style={{ color: 'var(--ink)' }}>{companyCache[viewingContact.company_id]?.account_status || 'Customer'}</span>
                  </div>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
                    <span style={{ color: 'var(--slate)', fontSize: '12px', fontWeight: 600, textTransform: 'uppercase' }}>Location</span>
                    <span style={{ color: 'var(--ink)' }}>
                      {companyCache[viewingContact.company_id]?.city ? `${companyCache[viewingContact.company_id].city}, ` : ''}
                      {companyCache[viewingContact.company_id]?.state || 'N/A'}
                    </span>
                  </div>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
                    <span style={{ color: 'var(--slate)', fontSize: '12px', fontWeight: 600, textTransform: 'uppercase' }}>Relationship Since</span>
                    <span style={{ color: 'var(--ink)' }}>
                      {companyCache[viewingContact.company_id]?.customer_since ? formatDate(companyCache[viewingContact.company_id].customer_since) : 
                       (companyCache[viewingContact.company_id]?.created_at ? formatDate(companyCache[viewingContact.company_id]?.created_at) : 'N/A')}
                    </span>
                  </div>
                </div>
              </div>

            </div>
          </div>
        )}
      </Modal>

      {/* Add / Edit Modal */}
      <Modal 
        isOpen={isModalOpen} 
        onClose={() => setIsModalOpen(false)} 
        title={editingContact ? 'Edit Contact' : 'Add Contact'}
        footer={
          <>
            <Button variant="secondary" onClick={() => setIsModalOpen(false)} disabled={submitting}>Cancel</Button>
            <Button variant="primary" onClick={handleFormSubmit} disabled={submitting}>
              {submitting ? 'Saving...' : 'Save Contact'}
            </Button>
          </>
        }
      >
        {formError && <div className="err" style={{ marginBottom: '16px', color: 'var(--red)', fontWeight: 500 }}>{formError}</div>}
        
        <div className="field">
          <label>Company *</label>
          <input 
            type="text" 
            placeholder="Search company..." 
            value={companySearch}
            onChange={(e) => handleCompanySearch(e.target.value)}
            disabled={!!editingContact}
            style={{ width: '100%', padding: '8px', borderRadius: '6px', border: '1px solid var(--gray-300)', marginBottom: '8px' }}
          />
          {searchingCompanies && <div style={{ fontSize: '12px', color: 'var(--gray-500)' }}>Searching...</div>}
          <select 
            value={formData.company_id} 
            onChange={e => setFormData({...formData, company_id: e.target.value})}
            disabled={!!editingContact || companyResults.length === 0}
            style={{ width: '100%', padding: '8px', borderRadius: '6px', border: '1px solid var(--gray-300)' }}
          >
            <option value="">Select a company...</option>
            {companyResults.map(c => (
              <option key={c.company_id} value={c.company_id}>{c.company_name}</option>
            ))}
          </select>
        </div>

        <FormInput label="Full Name *" required value={formData.full_name} onChange={e => setFormData({...formData, full_name: e.target.value})} />
        
        <div style={{ display: 'flex', gap: '16px' }}>
          <FormInput label="Email" type="email" value={formData.email} onChange={e => setFormData({...formData, email: e.target.value})} />
          <FormInput label="Phone" value={formData.phone} onChange={e => setFormData({...formData, phone: e.target.value})} />
        </div>

        <div style={{ display: 'flex', gap: '16px' }}>
          <FormInput label="Job Title" value={formData.job_title} onChange={e => setFormData({...formData, job_title: e.target.value})} />
          <FormInput label="Department" value={formData.department} onChange={e => setFormData({...formData, department: e.target.value})} />
        </div>
      </Modal>

      {/* Delete Confirmation Modal */}
      <Modal 
        isOpen={deleteConfirmOpen} 
        onClose={() => setDeleteConfirmOpen(false)} 
        title="Confirm Deletion"
        footer={
          <>
            <Button variant="secondary" onClick={() => setDeleteConfirmOpen(false)} disabled={deleting}>Cancel</Button>
            <Button variant="danger" onClick={confirmDelete} disabled={deleting}>
              {deleting ? 'Deleting...' : 'Delete'}
            </Button>
          </>
        }
      >
        {deleteError && <div className="err" style={{ marginBottom: '16px', color: 'var(--red)', fontWeight: 500 }}>{deleteError}</div>}
        <p>Are you sure you want to delete contact <strong>{contactToDelete?.full_name}</strong>?</p>
        <p style={{ fontSize: '14px', color: 'var(--gray-500)', marginTop: '8px' }}>This action will remove the contact from the system.</p>
      </Modal>
    </div>
  );
}
