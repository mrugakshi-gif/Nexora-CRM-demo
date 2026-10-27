import React, { useState, useEffect, useRef } from 'react';
import {  useNavigate , useSearchParams } from "react-router-dom";
import PageHeader from '../components/common/PageHeader';
import KpiCard from '../components/common/KpiCard';
import Badge from '../components/common/Badge';
import Button from '../components/common/Button';
import Modal from '../components/common/Modal';
import { CRMDataTable, TablePagination, FilterBar, CRMStatusBadge, TableLoadingSkeleton, TableEmptyState, CRMSubcategoryTabs } from '../components/common/table';
import { 
  leadService, companyService, contactService, 
  campaignService, referenceService, analyticsService 
} from '../services/crmService';
import { mlService } from '../services/mlService';
import Icon from '../components/common/Icon';
import { AuthContext } from '../AuthContext';

export default function Leads() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const { effectiveRole } = React.useContext(AuthContext);
  const [leads, setLeads] = useState([]);
  
  // Lookup data caches
  const [companies, setCompanies] = useState({});
  const [contacts, setContacts] = useState({});
  const [campaigns, setCampaigns] = useState({});
  const [leadSources, setLeadSources] = useState([]);
  const [industries, setIndustries] = useState([]);
  
  const [loading, setLoading] = useState(true);
  const [errorMsg, setErrorMsg] = useState('');
  
  const [page, setPage] = useState(1);
  const [pageSize] = useState(25);
  const [totalLeads, setTotalLeads] = useState(0);
  const [search, setSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState('All');
  const [activeCategory, setActiveCategory] = useState('All Leads');
  const [categoryCounts, setCategoryCounts] = useState({});
  
  const [funnelCounts, setFunnelCounts] = useState({});

  const LEAD_CATEGORIES = [
    { id: 'All Leads', label: 'All Leads', statuses: 'All' },
    { id: 'New', label: 'New', statuses: 'New' },
    { id: 'Contacted', label: 'Contacted', statuses: 'Contacted' },
    { id: 'Qualification', label: 'Qualification', statuses: 'Qualifying,Qualified (MQL),Sales Qualified (SQL)' },
    { id: 'Nurture', label: 'Nurture', statuses: 'Nurture' },
    { id: 'Converted', label: 'Converted', statuses: 'Converted' },
    { id: 'Disqualified / Dead', label: 'Disqualified / Dead', statuses: 'Disqualified,Dead' }
  ];
  
  // Modals
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [isEdit, setIsEdit] = useState(false);
  
  const [isDeleteModalOpen, setIsDeleteModalOpen] = useState(false);
  const [leadToDelete, setLeadToDelete] = useState(null);

  const [isConvertModalOpen, setIsConvertModalOpen] = useState(false);
  const [leadToConvert, setLeadToConvert] = useState(null);
  const [conversionData, setConversionData] = useState({ create_opportunity: true, opportunity_name: '', deal_value_inr: 0 });

  const [isHistoryModalOpen, setIsHistoryModalOpen] = useState(false);
  const [leadHistory, setLeadHistory] = useState([]);
  const [historyLoading, setHistoryLoading] = useState(false);

  // Form State
  const initialLeadState = { 
    company_id: '', 
    contact_id: '', 
    lead_source_id: '',
    campaign_id: '',
    assigned_rep_id: '',
    lead_status: 'New', 
    industry_interest_id: '',
    estimated_budget_inr: '',
    company_size_at_lead_time: ''
  };
  const [currentLead, setCurrentLead] = useState(initialLeadState);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [modalError, setModalError] = useState('');
  
  // ML
  const [mlPredictions, setMlPredictions] = useState({});

  useEffect(() => {
    loadLookups();
    loadKpis();
  }, []);

  const debouncedSearch = search;
  const debouncedFilter = statusFilter;
  const debouncedCategory = activeCategory;

  useEffect(() => {
    loadData(page, debouncedSearch, debouncedFilter, debouncedCategory);
    // eslint-disable-next-line
  }, [page, debouncedSearch, debouncedFilter, debouncedCategory]);

  const fetchCategoryCounts = async (searchQuery) => {
    try {
      const counts = {};
      const promises = LEAD_CATEGORIES.map(async (cat) => {
        const params = { page: 1, page_size: 1 };
      if (searchParams.get('company_id')) params.company_id = searchParams.get('company_id');
      if (searchParams.get('customer_id')) params.customer_id = searchParams.get('customer_id');

        if (cat.statuses !== 'All') {
          params.lead_status = cat.statuses;
        }
        if (searchQuery) {
          params.search = searchQuery;
        }
        const res = await leadService.getLeads(params);
        counts[cat.id] = res.data?.total || 0;
      });
      await Promise.all(promises);
      setCategoryCounts(counts);
    } catch (err) {
      console.error("Failed to fetch lead category counts", err);
    }
  };

  async function loadLookups() {
    try {
      const [srcRes, indRes] = await Promise.all([
        referenceService.getLeadSources(),
        referenceService.getIndustries()
      ]);
      setLeadSources(srcRes.data || []);
      setIndustries(indRes.data || []);
    } catch (err) {
      console.error("Failed to load reference data", err);
    }
  }

  async function loadKpis() {
    try {
      const res = await analyticsService.getLeadFunnel();
      const counts = res.data || [];
      const countMap = {};
      counts.forEach(item => {
        countMap[item.status] = item.count;
      });
      setFunnelCounts(countMap);
    } catch (err) {
      console.error("Failed to load KPI funnel counts", err);
    }
  }

  async function loadData(currentPage = page, searchQuery = search, currentFilter = statusFilter, currentCategory = activeCategory) {
    setLoading(true);
    setErrorMsg(null);
    try {
      const params = {
        page: currentPage,
        page_size: pageSize
      };
      if (searchParams.get('company_id')) params.company_id = searchParams.get('company_id');
      if (searchParams.get('customer_id')) params.customer_id = searchParams.get('customer_id');

      if (searchQuery) params.search = searchQuery;

      let apiStatus = '';
      if (currentFilter !== 'All') {
        apiStatus = currentFilter;
      } else {
        const cat = LEAD_CATEGORIES.find(c => c.id === currentCategory);
        if (cat && cat.statuses !== 'All') {
          apiStatus = cat.statuses;
        }
      }
      
      if (apiStatus) params.lead_status = apiStatus;
      
      const res = await leadService.getLeads(params);
      
      const items = res.data?.items || res.data?.data || res.data || [];
      const total = res.data?.total || items.length || 0;
      setTotalLeads(total);
      fetchCategoryCounts(searchQuery);

      // Resolve Company Names
      const newCompanyCache = { ...companies };
      const missingCompIds = [...new Set(items.map(l => l.company_id))].filter(id => id && !newCompanyCache[id]);
      if (missingCompIds.length > 0) {
        const compResults = await Promise.all(missingCompIds.map(id => companyService.getCompany(id).catch(() => null)));
        compResults.forEach((cRes, i) => {
          if (cRes && cRes.data) newCompanyCache[missingCompIds[i]] = cRes.data;
        });
        setCompanies(newCompanyCache);
      }

      // Resolve Contact Names
      const newContactCache = { ...contacts };
      const missingContactIds = [...new Set(items.map(l => l.contact_id))].filter(id => id && !newContactCache[id]);
      if (missingContactIds.length > 0) {
        const contResults = await Promise.all(missingContactIds.map(id => contactService.getContact(id).catch(() => null)));
        contResults.forEach((cRes, i) => {
          if (cRes && cRes.data) newContactCache[missingContactIds[i]] = cRes.data;
        });
        setContacts(newContactCache);
      }

      // Resolve Campaign Names
      const newCampaignCache = { ...campaigns };
      const missingCampaignIds = [...new Set(items.map(l => l.campaign_id))].filter(id => id && !newCampaignCache[id]);
      if (missingCampaignIds.length > 0) {
        const campResults = await Promise.all(missingCampaignIds.map(id => campaignService.getCampaign(id).catch(() => null)));
        campResults.forEach((cRes, i) => {
          if (cRes && cRes.data) newCampaignCache[missingCampaignIds[i]] = cRes.data;
        });
        setCampaigns(newCampaignCache);
      }

      setLeads(items);
    } catch (err) {
      console.error("Failed to load leads:", err);
      setErrorMsg("Failed to load leads. Please check your connection.");
    } finally {
      setLoading(false);
    }
  }

  // Derived vocabularies for UI
  const uniqueStatuses = ["New", "Contacted", "Qualifying", "Qualified (MQL)", "Sales Qualified (SQL)", "Nurture", "Converted", "Disqualified", "Dead"];

  const getCompanyName = (id) => {
    return companies[id]?.company_name || id || 'No company';
  };
  
  const getContactName = (id) => {
    return contacts[id]?.full_name || id || 'No contact linked';
  };

  const getSourceName = (id) => {
    const src = leadSources.find(s => s.lead_source_id === id);
    return src ? src.source_name : id || 'Unknown Source';
  };

  const getCampaignName = (id) => {
    return campaigns[id]?.campaign_name || id || 'No campaign linked';
  };

  const handleAnalyzeLead = async (leadId, e) => {
    e.stopPropagation();
    setMlPredictions(prev => ({ ...prev, [leadId]: { loading: true, data: null, error: false } }));
    try {
      const [convRes, scoreRes] = await Promise.all([
        mlService.getLeadConversion(leadId),
        mlService.getLeadScore(leadId)
      ]);
      setMlPredictions(prev => ({
        ...prev,
        [leadId]: {
          loading: false,
          data: { conversion: convRes.data, score: scoreRes.data },
          error: false
        }
      }));
    } catch (err) {
      console.warn("ML analysis failed for lead", leadId, err);
      setMlPredictions(prev => ({ ...prev, [leadId]: { loading: false, data: null, error: true } }));
    }
  };

  const openCreateModal = () => {
    setIsEdit(false);
    setCurrentLead(initialLeadState);
    setModalError('');
    setIsModalOpen(true);
  };

  const openEditModal = (lead) => {
    setIsEdit(true);
    setCurrentLead({
      lead_id: lead.lead_id,
      company_id: lead.company_id || '',
      contact_id: lead.contact_id || '',
      lead_source_id: lead.lead_source_id || '',
      campaign_id: lead.campaign_id || '',
      assigned_rep_id: lead.assigned_rep_id || '',
      lead_status: lead.lead_status || 'New',
      industry_interest_id: lead.industry_interest_id || '',
      estimated_budget_inr: lead.estimated_budget_inr || '',
      company_size_at_lead_time: lead.company_size_at_lead_time || '',
      _original_status: lead.lead_status // Keep track for patch
    });
    setModalError('');
    setIsModalOpen(true);
  };

  const openHistoryModal = async (leadId) => {
    setIsHistoryModalOpen(true);
    setHistoryLoading(true);
    try {
      const res = await leadService.getLeadHistory(leadId);
      setLeadHistory(res.data || []);
    } catch (err) {
      console.error("Failed to load history", err);
      setLeadHistory([]);
    } finally {
      setHistoryLoading(false);
    }
  };

  const openConvertModal = (lead) => {
    setLeadToConvert(lead);
    setConversionData({
      create_opportunity: true,
      opportunity_name: `Opp - ${getCompanyName(lead.company_id)}`,
      deal_value_inr: lead.estimated_budget_inr || 0
    });
    setIsConvertModalOpen(true);
  };

  const handleDeleteClick = (lead) => {
    setLeadToDelete(lead);
    setIsDeleteModalOpen(true);
  };

  const confirmDelete = async () => {
    if (!leadToDelete) return;
    setIsSubmitting(true);
    try {
      await leadService.deleteLead(leadToDelete.lead_id);
      setIsDeleteModalOpen(false);
      setLeadToDelete(null);
      loadData(page, search, statusFilter);
      loadKpis();
    } catch (err) {
      console.error(err);
      alert("Failed to delete lead. You may not have permission.");
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleConvertLead = async () => {
    setIsSubmitting(true);
    try {
      await leadService.convertLead(leadToConvert.lead_id, conversionData);
      setIsConvertModalOpen(false);
      setLeadToConvert(null);
      loadData(page, search, statusFilter);
      loadKpis();
    } catch (err) {
      console.error(err);
      alert("Failed to convert lead.");
    } finally {
      setIsSubmitting(false);
    }
  };

  const handleSaveLead = async () => {
    if (!currentLead.company_id || !currentLead.lead_source_id) {
      setModalError("Company and Lead Source are required.");
      return;
    }
    
    const payload = { ...currentLead };
    Object.keys(payload).forEach(key => {
      if (payload[key] === '') payload[key] = null;
    });

    setIsSubmitting(true);
    setModalError('');
    try {
      if (isEdit) {
        const { lead_id, _original_status, lead_status, ...updatePayload } = payload;
        
        await leadService.updateLead(lead_id, { ...updatePayload, lead_status: _original_status });
        
        if (currentLead.lead_status !== currentLead._original_status) {
          await leadService.updateLeadStatus(lead_id, currentLead.lead_status);
        }
      } else {
        await leadService.createLead(payload);
      }
      setIsModalOpen(false);
      loadData(page, search, statusFilter);
      loadKpis();
    } catch (err) {
      console.error(err);
      setModalError("Failed to save lead. Please check validation requirements.");
    } finally {
      setIsSubmitting(false);
    }
  };

  const ActionMenu = ({ lead }) => {
    const [open, setOpen] = useState(false);
    return (
      <div className="dropdown" style={{ position: 'relative' }} onClick={e => e.stopPropagation()}>
        <Button variant="ghost" size="small" onClick={() => setOpen(!open)}>Actions ▾</Button>
        {open && (
          <div className="dropdown-menu" style={{ position: 'absolute', right: 0, top: '100%', zIndex: 10, background: 'var(--bg-surface)', border: '1px solid var(--border)', borderRadius: '10px', boxShadow: 'var(--clay-shadow-float)', padding: '6px 0', minWidth: '150px' }}>
            <button className="dropdown-item" style={{ width: '100%', textAlign: 'left', padding: '8px 16px', background: 'none', border: 'none', cursor: 'pointer', fontSize: '13px', color: 'var(--ink)' }} onClick={() => { setOpen(false); openEditModal(lead); }}>Edit</button>
            <button className="dropdown-item" style={{ width: '100%', textAlign: 'left', padding: '8px 16px', background: 'none', border: 'none', cursor: 'pointer', fontSize: '13px', color: 'var(--ink)' }} onClick={() => { setOpen(false); openHistoryModal(lead.lead_id); }}>View History</button>
            {lead.lead_status !== 'Converted' && (
              <button className="dropdown-item" style={{ width: '100%', textAlign: 'left', padding: '8px 16px', background: 'none', border: 'none', cursor: 'pointer', fontSize: '13px', color: 'var(--ink)' }} onClick={() => { setOpen(false); openConvertModal(lead); }}>Convert Lead</button>
            )}
            <button className="dropdown-item danger" style={{ width: '100%', textAlign: 'left', padding: '8px 16px', background: 'none', border: 'none', cursor: 'pointer', fontSize: '13px', color: 'var(--danger)' }} onClick={() => { setOpen(false); handleDeleteClick(lead); }}>Delete</button>
          </div>
        )}
      </div>
    );
  };

  const headers = ['Lead', 'Source & Campaign', 'Status', 'Assigned Rep', 'Created Date', 'ML Score', 'Actions'];
  const rows = leads.map(l => {
    const mlState = mlPredictions[l.lead_id];
    let mlCell = (
      <Button variant="secondary" size="small" icon="sparkles" onClick={(e) => handleAnalyzeLead(l.lead_id, e)}>Analyze</Button>
    );
    if (mlState?.loading) {
      mlCell = <span style={{ color: 'var(--slate)', fontSize: '12px' }}>Loading...</span>;
    } else if (mlState?.error) {
      mlCell = <span style={{ color: 'var(--error)', fontSize: '12px' }}>Unavailable</span>;
    } else if (mlState?.data) {
      const prob = (mlState.data.conversion.conversion_probability * 100).toFixed(0);
      const rawScore = mlState.data.score.score_probability ?? mlState.data.score.lead_score ?? 0;
      const score = (rawScore * 100).toFixed(0);
      const driversTooltip = mlState.data.score.key_factors?.length
        ? "Key Drivers:\n" + mlState.data.score.key_factors.map(f => `• ${f.description}`).join("\n")
        : `Model: ${mlState.data.score.model_identifier || "LogisticRegression"}`;
      mlCell = (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
          <span 
            title={driversTooltip}
            style={{ fontSize: '12px', fontWeight: 600, color: 'var(--brown)', cursor: 'help' }}
          >
            Score: {score}
          </span>
          <Badge text={`${prob}% Conv`} variant={prob > 50 ? 'success' : 'warning'} />
        </div>
      );
    }

    const entityCell = (
      <div style={{ display: 'flex', flexDirection: 'column' }}>
        <span 
          style={{ fontWeight: 600, color: 'var(--accent-primary)', cursor: 'pointer', transition: 'color 0.15s ease' }}
          onMouseEnter={(e) => e.target.style.color = 'var(--accent-hover)'}
          onMouseLeave={(e) => e.target.style.color = 'var(--accent-primary)'}
          onClick={() => {
            if (l.company_id) navigate(`/companies/${l.company_id}`);
          }}
        >
          {getCompanyName(l.company_id)}
        </span>
        <span style={{ fontSize: '13px', color: 'var(--heading-primary)', fontWeight: 500 }}>{getContactName(l.contact_id)}</span>
        <span style={{ fontSize: '11px', color: 'var(--ink-mute)', marginTop: '2px' }}>{l.lead_id}</span>
      </div>
    );

    const sourceCell = (
      <div style={{ display: 'flex', flexDirection: 'column' }}>
        <span style={{ fontSize: '14px', color: 'var(--ink)' }}>{getSourceName(l.lead_source_id)}</span>
        <span style={{ fontSize: '12px', color: 'var(--slate)' }}>{getCampaignName(l.campaign_id)}</span>
      </div>
    );

    return [
      entityCell,
      sourceCell,
      <CRMStatusBadge status={l.lead_status || 'Unknown'} />,
      l.assigned_rep_id || 'Unassigned',
      l.created_at ? new Date(l.created_at).toLocaleDateString() : '-',
      mlCell,
      <ActionMenu lead={l} />
    ];
  });

  const chips = [
    { label: 'All', active: statusFilter === 'All', onClick: () => { setStatusFilter('All'); setPage(1); } },
    ...uniqueStatuses.map(s => ({
      label: s,
      active: statusFilter === s,
      onClick: () => { 
        setStatusFilter(s); 
        setPage(1); 
        const matchingCat = LEAD_CATEGORIES.find(c => c.statuses.split(',').includes(s));
        if (matchingCat) setActiveCategory(matchingCat.id);
      }
    }))
  ];

  const handleCategorySelect = (categoryId) => {
    setActiveCategory(categoryId);
    setStatusFilter('All'); // Clear detailed filter to let category take over
    setPage(1);
  };

  const totalPages = Math.ceil(totalLeads / pageSize) || 1;

  return (
    <div className="page-container">
      <PageHeader 
        title="Leads" 
        desc="Manage inbound prospects and lead conversions."
        actions={<Button variant="primary" icon="plus" onClick={openCreateModal}>Add Lead</Button>}
      />
      <div style={{ padding: '0 28px 28px', flex: 1, display: 'flex', flexDirection: 'column' }}>
        
        <div className="kpi-grid" style={{ marginBottom: '24px', gridTemplateColumns: 'repeat(7, 1fr)' }}>
          {LEAD_CATEGORIES.map(cat => {
            let count = 0;
            if (cat.id === 'All Leads') {
              count = Object.values(funnelCounts).reduce((a, b) => a + b, 0);
            } else {
              const statuses = cat.statuses.split(',');
              statuses.forEach(s => {
                count += funnelCounts[s] || 0;
              });
            }
            const isActive = activeCategory === cat.id;

            const iconMap = {
              'All Leads': 'users',
              'New': 'sparkles',
              'Contacted': 'phone',
              'Qualification': 'target',
              'Nurture': 'mail',
              'Converted': 'check',
              'Disqualified / Dead': 'x'
            };
            const iconName = iconMap[cat.id] || 'users';
            
            return (
              <div 
                key={cat.id} 
                onClick={() => handleCategorySelect(cat.id)}
                className="kpi-card"
                style={{ 
                  cursor: 'pointer',
                  border: isActive ? '2px solid var(--primary)' : '1px solid var(--border-light)',
                  boxShadow: isActive ? '0 0 0 4px var(--primary-light)' : 'none',
                  transition: 'all 0.2s ease',
                  transform: isActive ? 'translateY(-2px)' : 'none'
                }}
              >
                <div className="kpi-top">
                  <span className="kpi-label">{cat.label}</span>
                  <div className="kpi-icon">
                    <Icon name={iconName} size={15} color="var(--white)" stroke={1.9} />
                  </div>
                </div>
                <div className="kpi-value">{count.toLocaleString()}</div>
                <div className="kpi-delta-row">
                  <span className="kpi-ctx" style={{ color: isActive ? 'var(--primary)' : 'var(--slate)' }}>Real-time</span>
                </div>
              </div>
            );
          })}
        </div>

        <CRMSubcategoryTabs 
          categories={LEAD_CATEGORIES.map(cat => ({
            ...cat,
            label: `${cat.label} ${categoryCounts[cat.id] !== undefined ? `(${categoryCounts[cat.id]})` : ''}`
          }))} 
          activeCategory={activeCategory} 
          onSelect={handleCategorySelect} 
        />

        <FilterBar 
          searchValue={search} 
          onSearchChange={(v) => { setSearch(v); setPage(1); }} 
          searchPlaceholder="Search leads..." 
          chips={chips}
        />

        {errorMsg && (
          <div style={{ margin: '20px 0', padding: '16px', background: '#ffebee', color: '#c62828', borderRadius: '8px' }}>
            {errorMsg}
          </div>
        )}

        <div style={{ display: 'flex', flexDirection: 'column', flex: 1, marginTop: '16px' }}>
          {loading ? (
            <TableLoadingSkeleton rows={5} columns={headers.length} />
          ) : errorMsg ? (
            <TableEmptyState 
              icon="alert-circle" 
              title="Error Loading Leads" 
              desc={errorMsg} 
              action={<Button variant="secondary" onClick={() => loadData()}>Retry</Button>}
            />
          ) : leads.length === 0 ? (
            <TableEmptyState 
              icon="users" 
              title="No Leads Found" 
              desc={search || statusFilter !== 'All' ? "No leads match your filter." : "Get started by adding a new lead."} 
              action={!search && statusFilter === 'All' ? <Button variant="primary" onClick={openCreateModal}>Add Lead</Button> : null}
            />
          ) : (
            <>
              <CRMDataTable 
                headers={headers} 
                rows={rows} 
                onRowClick={(l, idx) => {}}
              />
              <div style={{ marginTop: 'auto', paddingTop: '16px', borderTop: '1px solid var(--border-light)' }}>
                <TablePagination 
                  page={page} 
                  totalPages={totalPages} 
                  totalRecords={totalLeads} 
                  onPrev={() => setPage(p => Math.max(1, p - 1))}
                  onNext={() => setPage(p => Math.min(totalPages, p + 1))}
                />
              </div>
            </>
          )}
        </div>
      </div>

      {/* CREATE / EDIT MODAL */}
      <Modal 
        isOpen={isModalOpen} 
        onClose={() => !isSubmitting && setIsModalOpen(false)} 
        title={isEdit ? "Edit Lead" : "Add New Lead"}
        footer={
          <>
            <Button variant="secondary" onClick={() => setIsModalOpen(false)} disabled={isSubmitting}>Cancel</Button>
            <Button variant="primary" onClick={handleSaveLead} disabled={isSubmitting}>
              {isSubmitting ? 'Saving...' : 'Save Lead'}
            </Button>
          </>
        }
      >
        <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
          {modalError && <div style={{ color: 'var(--red)', fontSize: '13px' }}>{modalError}</div>}
          
          <div>
            <label style={{ display: 'block', fontSize: '12px', fontWeight: 600, color: 'var(--brown)', marginBottom: '6px' }}>Company * (e.g. COMP-1)</label>
            <input 
              type="text"
              style={{ width: '100%', padding: '8px 12px', borderRadius: '6px', border: '1px solid var(--gray-200)' }}
              value={currentLead.company_id || ''} 
              onChange={e => setCurrentLead({...currentLead, company_id: e.target.value})}
            />
          </div>

          <div>
            <label style={{ display: 'block', fontSize: '12px', fontWeight: 600, color: 'var(--brown)', marginBottom: '6px' }}>Contact ID (Optional, e.g. CONT-1)</label>
            <input 
              type="text"
              style={{ width: '100%', padding: '8px 12px', borderRadius: '6px', border: '1px solid var(--gray-200)' }}
              value={currentLead.contact_id || ''} 
              onChange={e => setCurrentLead({...currentLead, contact_id: e.target.value})}
            />
          </div>

          <div>
            <label style={{ display: 'block', fontSize: '12px', fontWeight: 600, color: 'var(--brown)', marginBottom: '6px' }}>Lead Source *</label>
            <select 
              style={{ width: '100%', padding: '8px 12px', borderRadius: '6px', border: '1px solid var(--gray-200)' }}
              value={currentLead.lead_source_id || ''} 
              onChange={e => setCurrentLead({...currentLead, lead_source_id: e.target.value})}
            >
              <option value="">Select Source</option>
              {leadSources.map(s => <option key={s.lead_source_id} value={s.lead_source_id}>{s.source_name}</option>)}
            </select>
          </div>

          <div>
            <label style={{ display: 'block', fontSize: '12px', fontWeight: 600, color: 'var(--brown)', marginBottom: '6px' }}>Campaign</label>
            <input 
              type="text"
              placeholder="e.g. CAMP-1"
              style={{ width: '100%', padding: '8px 12px', borderRadius: '6px', border: '1px solid var(--gray-200)' }}
              value={currentLead.campaign_id || ''} 
              onChange={e => setCurrentLead({...currentLead, campaign_id: e.target.value})}
            />
          </div>

          <div>
            <label style={{ display: 'block', fontSize: '12px', fontWeight: 600, color: 'var(--brown)', marginBottom: '6px' }}>Assigned Rep ID</label>
            <input 
              type="text"
              placeholder="e.g. REP-1"
              style={{ width: '100%', padding: '8px 12px', borderRadius: '6px', border: '1px solid var(--gray-200)' }}
              value={currentLead.assigned_rep_id || ''} 
              onChange={e => setCurrentLead({...currentLead, assigned_rep_id: e.target.value})}
              disabled={effectiveRole === 'Sales Rep'}
            />
          </div>

          <div>
            <label style={{ display: 'block', fontSize: '12px', fontWeight: 600, color: 'var(--brown)', marginBottom: '6px' }}>Lead Status</label>
            <select 
              style={{ width: '100%', padding: '8px 12px', borderRadius: '6px', border: '1px solid var(--gray-200)' }}
              value={currentLead.lead_status || 'New'} 
              onChange={e => setCurrentLead({...currentLead, lead_status: e.target.value})}
            >
              {uniqueStatuses.map(s => <option key={s} value={s}>{s}</option>)}
            </select>
            {isEdit && currentLead.lead_status !== currentLead._original_status && (
               <span style={{fontSize: '11px', color: 'var(--orange)'}}>Note: Status changes will generate a new history record.</span>
            )}
          </div>
          
          <div style={{ display: 'flex', gap: '16px' }}>
            <div style={{ flex: 1 }}>
              <label style={{ display: 'block', fontSize: '12px', fontWeight: 600, color: 'var(--brown)', marginBottom: '6px' }}>Est. Budget (INR)</label>
              <input 
                type="number"
                placeholder="Optional"
                style={{ width: '100%', padding: '8px 12px', borderRadius: '6px', border: '1px solid var(--gray-200)' }}
                value={currentLead.estimated_budget_inr || ''} 
                onChange={e => setCurrentLead({...currentLead, estimated_budget_inr: e.target.value ? parseFloat(e.target.value) : ''})}
              />
            </div>
            <div style={{ flex: 1 }}>
              <label style={{ display: 'block', fontSize: '12px', fontWeight: 600, color: 'var(--brown)', marginBottom: '6px' }}>Company Size</label>
              <select 
                style={{ width: '100%', padding: '8px 12px', borderRadius: '6px', border: '1px solid var(--gray-200)' }}
                value={currentLead.company_size_at_lead_time || ''} 
                onChange={e => setCurrentLead({...currentLead, company_size_at_lead_time: e.target.value})}
              >
                <option value="">Unknown</option>
                <option value="1-50">1-50</option>
                <option value="51-200">51-200</option>
                <option value="201-1000">201-1000</option>
                <option value="1001+">1001+</option>
              </select>
            </div>
          </div>
        </div>
      </Modal>

      {/* HISTORY MODAL */}
      <Modal 
        isOpen={isHistoryModalOpen} 
        onClose={() => setIsHistoryModalOpen(false)} 
        title="Lead Status History"
        footer={<Button variant="primary" onClick={() => setIsHistoryModalOpen(false)}>Close</Button>}
      >
        {historyLoading ? <p>Loading history...</p> : leadHistory.length === 0 ? <p>No history records found.</p> : (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
            {leadHistory.map(h => (
              <div key={h.history_id} style={{ padding: '12px', border: '1px solid var(--border-light)', borderRadius: '8px' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '8px' }}>
                  <span style={{ fontSize: '12px', color: 'var(--slate)' }}>{new Date(h.changed_at).toLocaleString()}</span>
                  <span style={{ fontSize: '12px', fontWeight: 500 }}>Rep: {h.changed_by_rep_id || 'System'}</span>
                </div>
                <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                  <CRMStatusBadge status={h.status_from || 'None'} />
                  <span style={{ color: 'var(--slate)' }}>→</span>
                  <CRMStatusBadge status={h.status_to} />
                </div>
              </div>
            ))}
          </div>
        )}
      </Modal>

      {/* CONVERT MODAL */}
      <Modal 
        isOpen={isConvertModalOpen} 
        onClose={() => !isSubmitting && setIsConvertModalOpen(false)} 
        title="Convert Lead"
        footer={
          <>
            <Button variant="secondary" onClick={() => setIsConvertModalOpen(false)} disabled={isSubmitting}>Cancel</Button>
            <Button variant="primary" onClick={handleConvertLead} disabled={isSubmitting}>
              {isSubmitting ? 'Processing...' : 'Confirm Conversion'}
            </Button>
          </>
        }
      >
        <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
          <p style={{ fontSize: '14px', color: 'var(--ink)' }}>
            Converting Lead <strong>{leadToConvert?.lead_id}</strong> will mark the lead as Converted and optionally create an Opportunity.
          </p>
          <label style={{ display: 'flex', alignItems: 'center', gap: '8px', cursor: 'pointer' }}>
            <input 
              type="checkbox" 
              checked={conversionData.create_opportunity} 
              onChange={e => setConversionData({...conversionData, create_opportunity: e.target.checked})}
            />
            <span style={{ fontSize: '14px', color: 'var(--ink)' }}>Create Opportunity</span>
          </label>

          {conversionData.create_opportunity && (
            <>
              <div>
                <label style={{ display: 'block', fontSize: '12px', fontWeight: 600, color: 'var(--brown)', marginBottom: '6px' }}>Opportunity Name</label>
                <input 
                  type="text"
                  style={{ width: '100%', padding: '8px 12px', borderRadius: '6px', border: '1px solid var(--gray-200)' }}
                  value={conversionData.opportunity_name} 
                  onChange={e => setConversionData({...conversionData, opportunity_name: e.target.value})}
                />
              </div>
              <div>
                <label style={{ display: 'block', fontSize: '12px', fontWeight: 600, color: 'var(--brown)', marginBottom: '6px' }}>Deal Value (INR)</label>
                <input 
                  type="number"
                  style={{ width: '100%', padding: '8px 12px', borderRadius: '6px', border: '1px solid var(--gray-200)' }}
                  value={conversionData.deal_value_inr} 
                  onChange={e => setConversionData({...conversionData, deal_value_inr: parseFloat(e.target.value) || 0})}
                />
              </div>
            </>
          )}
        </div>
      </Modal>

      {/* DELETE MODAL */}
      <Modal 
        isOpen={isDeleteModalOpen} 
        onClose={() => !isSubmitting && setIsDeleteModalOpen(false)} 
        title="Delete Lead"
        footer={
          <>
            <Button variant="secondary" onClick={() => setIsDeleteModalOpen(false)} disabled={isSubmitting}>Cancel</Button>
            <Button variant="primary" style={{ background: 'var(--error)', color: 'white', borderColor: 'var(--error)' }} onClick={confirmDelete} disabled={isSubmitting}>
              {isSubmitting ? 'Deleting...' : 'Delete Lead'}
            </Button>
          </>
        }
      >
        <p>Are you sure you want to delete lead <strong>{leadToDelete?.lead_id}</strong>? This will soft-delete the record.</p>
      </Modal>
    </div>
  );
}
