import React, { useState, useEffect, useRef } from 'react';
import {  useNavigate , useSearchParams } from "react-router-dom";
import PageHeader from '../components/common/PageHeader';
import KpiCard from '../components/common/KpiCard';
import Badge from '../components/common/Badge';
import Icon from '../components/common/Icon';
import Button from '../components/common/Button';
import Modal from '../components/common/Modal';
import FormInput from '../components/common/FormInput';
import OpportunityEditModal from '../components/common/OpportunityEditModal';
import { CRMDataTable, TablePagination, FilterBar, CRMStatusBadge, TableLoadingSkeleton, TableEmptyState, CRMSubcategoryTabs } from '../components/common/table';
import { opportunityService, companyService, salesRepService } from '../services/crmService';
import { AuthContext } from '../AuthContext';

export default function Opportunities() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const { effectiveRole } = React.useContext(AuthContext);
  
  // Data State
  const [opportunities, setOpportunities] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  
  // Lookups
  const [companies, setCompanies] = useState({});
  const [reps, setReps] = useState({});

  // Pagination & Filter State
  const [page, setPage] = useState(1);
  const [pageSize] = useState(25);
  const [totalOppsCount, setTotalOppsCount] = useState(0);
  const [search, setSearch] = useState('');
  const [statusFilter, setStatusFilter] = useState('All');
  const [activeCategory, setActiveCategory] = useState('All Opportunities');
  const [categoryCounts, setCategoryCounts] = useState({});
  
  const OPPORTUNITY_CATEGORIES = [
    { id: 'All Opportunities', label: 'All Opportunities', statuses: 'All' },
    { id: 'Qualification', label: 'Qualification', statuses: 'Qualification' },
    { id: 'Active Pipeline', label: 'Active Pipeline', statuses: 'Needs Analysis,Value Proposition,Id. Decision Makers,Perception Analysis,Proposal/Price Quote,Negotiation/Review' },
    { id: 'Closed Won', label: 'Closed Won', statuses: 'Closed Won' },
    { id: 'Closed Lost', label: 'Closed Lost', statuses: 'Closed Lost' }
  ];
  
  const [viewMode, setViewMode] = useState('table'); // 'table' or 'kanban'

  // Modal State
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [editingOpp, setEditingOpp] = useState(null);
  
  const [submitting, setSubmitting] = useState(false);
  const [formError, setFormError] = useState('');
  
  // Drag and Drop State
  const [draggedOpp, setDraggedOpp] = useState(null);
  const [dragOverStage, setDragOverStage] = useState(null);
  
  // Stage Change Modal
  const [isStageModalOpen, setIsStageModalOpen] = useState(false);
  const [oppToChangeStage, setOppToChangeStage] = useState(null);
  const [stageData, setStageData] = useState({
    new_stage: '',
    close_outcome: 'None',
    loss_reason: ''
  });

  // Delete Modal State
  const [isDeleteModalOpen, setIsDeleteModalOpen] = useState(false);
  const [oppToDelete, setOppToDelete] = useState(null);



  const PIPELINE_STAGES = [
    'Qualification', 'Needs Analysis', 'Value Proposition', 'Id. Decision Makers',
    'Perception Analysis', 'Proposal/Price Quote', 'Negotiation/Review', 'Closed Won', 'Closed Lost'
  ];

  const debouncedSearch = search;
  const debouncedFilter = statusFilter;
  const debouncedCategory = activeCategory;
  const currentView = viewMode;

  useEffect(() => {
    loadData(page, debouncedSearch, debouncedFilter, debouncedCategory, currentView);
    // eslint-disable-next-line
  }, [page, debouncedSearch, debouncedFilter, debouncedCategory, currentView]);

  const fetchCategoryCounts = async (searchQuery) => {
    try {
      const counts = {};
      const promises = OPPORTUNITY_CATEGORIES.map(async (cat) => {
        const params = { page: 1, page_size: 1 };
      if (searchParams.get('company_id')) params.company_id = searchParams.get('company_id');
      if (searchParams.get('customer_id')) params.customer_id = searchParams.get('customer_id');

        if (cat.statuses !== 'All') {
          params.pipeline_stage = cat.statuses;
        }
        if (searchQuery) {
          params.search = searchQuery;
        }
        const res = await opportunityService.getOpportunities(params);
        counts[cat.id] = res.data?.total || 0;
      });
      await Promise.all(promises);
      setCategoryCounts(counts);
    } catch (err) {
      console.error("Failed to fetch category counts", err);
    }
  };

  async function loadData(pageIndex, searchQuery, stageFilter, currentCategory = activeCategory, currentViewMode = viewMode) {
    setLoading(true);
    setError('');
    try {
      const params = {
        page: pageIndex,
        page_size: currentViewMode === 'kanban' ? 200 : pageSize,
      };
      if (searchParams.get('company_id')) params.company_id = searchParams.get('company_id');
      if (searchParams.get('customer_id')) params.customer_id = searchParams.get('customer_id');

      if (searchQuery) params.search = searchQuery;
      
      let apiStage = '';
      if (stageFilter && stageFilter !== 'All') {
        apiStage = stageFilter;
      } else {
        const cat = OPPORTUNITY_CATEGORIES.find(c => c.id === currentCategory);
        if (cat && cat.statuses !== 'All') {
          apiStage = cat.statuses;
        }
      }

      if (apiStage) params.pipeline_stage = apiStage;

      const res = await opportunityService.getOpportunities(params);
      const data = res.data;
      
      let items = data?.items || data?.data || data || [];
      const total = data?.total || items.length || 0;
      const totalPagesRes = data?.total_pages || 1;
      
      if (currentViewMode === 'kanban' && totalPagesRes > 1) {
        const promises = [];
        for (let i = 2; i <= totalPagesRes; i++) {
          promises.push(opportunityService.getOpportunities({...params, page: i}));
        }
        const results = await Promise.all(promises);
        results.forEach(r => {
          items = items.concat(r.data?.items || []);
        });
      }
      
      setTotalOppsCount(total);
      
      // Also fetch counts for all categories
      fetchCategoryCounts(searchQuery);
      
      // Resolve Companies
      const newCompanyCache = { ...companies };
      const missingCompIds = [...new Set(items.map(o => o.company_id))].filter(id => id && !newCompanyCache[id]);
      if (missingCompIds.length > 0) {
        const compResults = await Promise.all(missingCompIds.map(id => companyService.getCompany(id).catch(() => null)));
        compResults.forEach((cRes, i) => {
          if (cRes && cRes.data) newCompanyCache[missingCompIds[i]] = cRes.data;
        });
        setCompanies(newCompanyCache);
      }

      // Resolve Reps
      const newRepCache = { ...reps };
      const missingRepIds = [...new Set(items.map(o => o.owner_rep_id))].filter(id => id && !newRepCache[id]);
      if (missingRepIds.length > 0) {
        const repResults = await Promise.all(missingRepIds.map(id => salesRepService.getSalesRep(id).catch(() => null)));
        repResults.forEach((rRes, i) => {
          if (rRes && rRes.data) newRepCache[missingRepIds[i]] = rRes.data;
        });
        setReps(newRepCache);
      }

      setOpportunities(items);
    } catch (err) {
      console.error("Failed to load opportunities:", err);
      setError('Failed to load opportunities from the API.');
    } finally {
      setLoading(false);
    }
  }

  // --- Handlers ---
  const handleRowClick = (opp) => {
    navigate(`/opportunities/${opp.opportunity_id}`);
  };

  // --- Modal Handlers ---
  const openAddModal = () => {
    setEditingOpp(null);
    setIsModalOpen(true);
  };

  const openEditModal = (opp) => {
    setEditingOpp(opp);
    setIsModalOpen(true);
  };

  const openStageModal = (opp) => {
    setOppToChangeStage(opp);
    setStageData({
      new_stage: opp.pipeline_stage || 'Qualification',
      close_outcome: opp.close_outcome || 'None',
      loss_reason: opp.loss_reason || ''
    });
    setIsStageModalOpen(true);
  };

  const initiateDelete = (opp) => {
    setOppToDelete(opp);
    setIsDeleteModalOpen(true);
  };

  const confirmDelete = () => {
    if (!oppToDelete) return;
    setSubmitting(true);
    opportunityService.deleteOpportunity(oppToDelete.opportunity_id)
      .then(() => {
        setIsDeleteModalOpen(false);
        setOppToDelete(null);
        loadData(page, search, statusFilter, activeCategory, viewMode);
      })
      .catch(err => {
        alert(err.response?.data?.detail || 'Failed to delete opportunity');
      })
      .finally(() => setSubmitting(false));
  };

  // Form submit handles within the extracted modal.

  const handleStageSubmit = async () => {
    if (!oppToChangeStage) return;
    setSubmitting(true);
    try {
      const payload = {
        new_stage: stageData.new_stage,
        close_outcome: stageData.close_outcome === 'None' ? null : stageData.close_outcome,
        loss_reason: stageData.loss_reason || null
      };
      await opportunityService.stageTransition(oppToChangeStage.opportunity_id, payload);
      setIsStageModalOpen(false);
      setOppToChangeStage(null);
      loadData(page, search, statusFilter, activeCategory, viewMode);
    } catch (err) {
      alert(err.response?.data?.detail || 'Failed to transition stage');
    } finally {
      setSubmitting(false);
    }
  };

  const handleDrop = async (oppId, newStage) => {
    if (submitting) return; // Prevent duplicate drops
    
    const oppIndex = opportunities.findIndex(o => String(o.opportunity_id) === String(oppId));
    if (oppIndex === -1) return;
    
    const opp = opportunities[oppIndex];
    if (opp.pipeline_stage === newStage) return; // Dropped on same stage, do nothing
    
    const oldStage = opp.pipeline_stage;
    
    // Optimistic UI update
    const updatedOpps = [...opportunities];
    updatedOpps[oppIndex] = { ...opp, pipeline_stage: newStage };
    setOpportunities(updatedOpps);
    
    setSubmitting(true);
    
    let close_outcome = null;
    if (newStage === 'Closed Won') close_outcome = 'Won';
    if (newStage === 'Closed Lost') close_outcome = 'Lost';

    try {
      await opportunityService.stageTransition(opp.opportunity_id, {
        new_stage: newStage,
        close_outcome: close_outcome,
        loss_reason: null
      });
      // Fetch latest from server to ensure full sync (e.g., removing from view if filter applied)
      loadData(page, search, statusFilter, activeCategory, viewMode);
    } catch (err) {
      // Revert on failure
      const revertedOpps = [...opportunities];
      revertedOpps[oppIndex] = { ...opp, pipeline_stage: oldStage };
      setOpportunities(revertedOpps);
      alert(err.response?.data?.detail || 'Failed to transition stage');
    } finally {
      setSubmitting(false);
      setDraggedOpp(null);
      setDragOverStage(null);
    }
  };

  // --- Formatting Helpers ---
  const formatINR = (val) => {
    if (val == null) return '-';
    return new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR', maximumFractionDigits: 0 }).format(val);
  };
  
  const formatPct = (val) => {
    if (val == null) return '-';
    return `${val}%`;
  };

  const formatDate = (val) => {
    if (!val) return '-';
    return new Date(val).toLocaleDateString();
  };

  // --- KPI / Kanban Helpers ---
  const isTerminalStage = (stage) => {
    if (!stage) return false;
    const s = stage.toLowerCase();
    return s.includes('closed won') || s.includes('closed lost');
  };

  const openOpps = opportunities.filter(o => !isTerminalStage(o.pipeline_stage));
  const openCount = openOpps.length;
  
  const pipelineValue = openOpps.reduce((sum, o) => sum + (o.deal_value_inr || 0), 0);
  const weightedPipeline = openOpps.reduce((sum, o) => {
    const val = o.deal_value_inr || 0;
    const prob = o.probability_pct || 0;
    return sum + (val * (prob / 100));
  }, 0);

  // --- Table Setup ---
  const ActionMenu = ({ opp }) => {
    const [open, setOpen] = useState(false);
    const dropdownRef = useRef(null);

    useEffect(() => {
      const handleClickOutside = (event) => {
        if (dropdownRef.current && !dropdownRef.current.contains(event.target)) {
          setOpen(false);
        }
      };
      if (open) {
        document.addEventListener('mousedown', handleClickOutside);
      } else {
        document.removeEventListener('mousedown', handleClickOutside);
      }
      return () => {
        document.removeEventListener('mousedown', handleClickOutside);
      };
    }, [open]);

    return (
      <div style={{ display: 'flex', gap: '6px', alignItems: 'center' }} onClick={e => e.stopPropagation()}>
        <Button variant="secondary" size="small" icon="eye" onClick={() => navigate(`/opportunities/${opp.opportunity_id}`)}>View 360</Button>
        <div className="dropdown" style={{ position: 'relative' }} ref={dropdownRef}>
          <Button variant="ghost" size="small" onClick={() => setOpen(!open)}>Actions ▾</Button>
          {open && (
            <div className="dropdown-menu" style={{ position: 'absolute', right: 0, top: '100%', zIndex: 10, background: 'var(--bg-surface)', border: '1px solid var(--border)', borderRadius: '10px', boxShadow: 'var(--clay-shadow-float)', padding: '6px 0', minWidth: '150px' }}>
              <button className="dropdown-item" style={{ width: '100%', textAlign: 'left', padding: '8px 16px', background: 'none', border: 'none', cursor: 'pointer', fontSize: '13px', color: 'var(--ink)' }} onClick={() => { setOpen(false); openEditModal(opp); }}>Edit Details</button>
              <button className="dropdown-item" style={{ width: '100%', textAlign: 'left', padding: '8px 16px', background: 'none', border: 'none', cursor: 'pointer', fontSize: '13px', color: 'var(--ink)' }} onClick={() => { setOpen(false); openStageModal(opp); }}>Change Stage</button>
              <button className="dropdown-item danger" style={{ width: '100%', textAlign: 'left', padding: '8px 16px', background: 'none', border: 'none', cursor: 'pointer', fontSize: '13px', color: 'var(--danger)' }} onClick={() => { setOpen(false); initiateDelete(opp); }}>Delete</button>
            </div>
          )}
        </div>
      </div>
    );
  };

  const headers = ['Opportunity', 'Pipeline Stage', 'Deal Value', 'Probability', 'Owner', 'Created', 'Actions'];
  const rows = opportunities.map(o => {
    const compName = companies[o.company_id]?.company_name || o.company_id || 'No Company';
    const repName = reps[o.owner_rep_id]?.full_name || o.owner_rep_id || 'Unassigned';
    
    return [
      <div style={{ display: 'flex', flexDirection: 'column' }}>
        <span 
          style={{ fontWeight: 600, color: 'var(--accent-primary)', cursor: 'pointer', transition: 'color 0.15s ease' }}
          onMouseEnter={(e) => e.target.style.color = 'var(--accent-hover)'}
          onMouseLeave={(e) => e.target.style.color = 'var(--accent-primary)'}
          onClick={() => navigate(`/opportunities/${o.opportunity_id}`)}
        >
          {o.opportunity_name || 'Unnamed Opportunity'}
        </span>
        <span style={{ fontSize: '13px', color: 'var(--slate)' }}>{compName}</span>
        <span style={{ fontSize: '11px', color: 'var(--ink-mute)', marginTop: '2px' }}>{o.opportunity_id}</span>
      </div>,
      <CRMStatusBadge status={o.pipeline_stage || 'Unknown'} />,
      <span style={{ fontWeight: 500 }}>{formatINR(o.deal_value_inr)}</span>,
      formatPct(o.probability_pct),
      <span style={{ fontSize: '14px' }}>{repName}</span>,
      formatDate(o.created_at),
      <ActionMenu opp={o} />
    ];
  });

  // --- Kanban Setup ---
  const renderKanban = () => {
    return (
      <div className="kanban-board" style={{ display: 'flex', gap: '20px', overflowX: 'auto', paddingBottom: '20px', alignItems: 'flex-start', minHeight: '500px' }}>
        {PIPELINE_STAGES.map(stage => {
          const columnOpps = opportunities.filter(o => o.pipeline_stage === stage);
          if (!draggedOpp && columnOpps.length === 0) return null;
          
          return (
            <div 
              key={stage} 
              className="kanban-column" 
              onDragOver={(e) => {
                e.preventDefault();
                e.dataTransfer.dropEffect = 'move';
                if (dragOverStage !== stage) setDragOverStage(stage);
              }}
              onDragLeave={() => {
                if (dragOverStage === stage) setDragOverStage(null);
              }}
              onDrop={(e) => {
                e.preventDefault();
                setDragOverStage(null);
                const oppId = e.dataTransfer.getData('text/plain') || draggedOpp?.opportunity_id;
                if (oppId) handleDrop(oppId, stage);
              }}
              style={{ 
                minWidth: '300px', 
                width: '300px', 
                backgroundColor: dragOverStage === stage ? '#eff6ff' : 'var(--beige)', 
                borderRadius: '12px', 
                padding: '16px', 
                display: 'flex', 
                flexDirection: 'column', 
                gap: '12px',
                border: dragOverStage === stage ? '2px dashed var(--primary)' : '2px solid transparent',
                transition: 'all 0.2s ease'
              }}
            >
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '8px' }}>
                <span style={{ fontWeight: 600, color: 'var(--brown)' }}>{stage}</span>
                <Badge text={columnOpps.length.toString()} variant="neutral" />
              </div>
              
              {columnOpps.length === 0 && draggedOpp && (
                <div style={{ padding: '24px', textAlign: 'center', color: 'var(--gray-500)', fontSize: '12px', border: '1px dashed var(--gray-300)', borderRadius: '8px' }}>
                  Drop here
                </div>
              )}

              {columnOpps.map(o => (
                <div 
                  key={o.opportunity_id} 
                  className="kanban-card" 
                  onClick={() => handleRowClick(o)}
                  draggable
                  onDragStart={(e) => {
                    e.dataTransfer.setData('text/plain', o.opportunity_id);
                    e.dataTransfer.effectAllowed = 'move';
                    setTimeout(() => setDraggedOpp(o), 0);
                  }}
                  onDragEnd={() => {
                    setDraggedOpp(null);
                    setDragOverStage(null);
                  }}
                  style={{ 
                    backgroundColor: 'var(--white)', 
                    padding: '16px', 
                    borderRadius: '8px', 
                    border: '1px solid var(--gray-200)', 
                    boxShadow: '0 1px 3px rgba(0,0,0,0.05)', 
                    display: 'flex', 
                    flexDirection: 'column', 
                    gap: '10px', 
                    cursor: 'grab',
                    opacity: draggedOpp?.opportunity_id === o.opportunity_id ? 0.5 : 1
                  }}
                >
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                    <span style={{ fontWeight: 600, fontSize: '14px', color: 'var(--heading-primary)' }}>{o.opportunity_name || o.opportunity_id}</span>
                  </div>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                    <span style={{ fontWeight: 700, color: 'var(--ink)' }}>{formatINR(o.deal_value_inr)}</span>
                    <Badge text={formatPct(o.probability_pct)} variant={o.probability_pct >= 70 ? 'success' : o.probability_pct >= 40 ? 'warning' : 'neutral'} />
                  </div>
                  <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', fontSize: '12px', color: 'var(--gray-500)', marginTop: '4px' }}>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '4px' }}>
                      <Icon name="user" size={12} /> {reps[o.owner_rep_id]?.full_name || 'Unassigned'}
                    </div>
                    <div>
                      {formatDate(o.created_at)}
                    </div>
                  </div>
                  <div style={{ display: 'flex', gap: '8px', marginTop: '8px' }} onClick={(e) => e.stopPropagation()} onDragStart={(e) => { e.preventDefault(); e.stopPropagation(); }}>
                    <Button variant="secondary" size="sm" onClick={() => openStageModal(o)}>Move Stage</Button>
                    <Button variant="ghost" size="sm" onClick={() => openEditModal(o)}>Edit</Button>
                  </div>
                </div>
              ))}
            </div>
          );
        })}
      </div>
    );
  };

  const chips = [
    { label: 'All', active: statusFilter === 'All', onClick: () => { setStatusFilter('All'); setPage(1); } },
    ...PIPELINE_STAGES.map(s => ({
      label: s,
      active: statusFilter === s,
      onClick: () => { 
        setStatusFilter(s); 
        setPage(1); 
        const matchingCat = OPPORTUNITY_CATEGORIES.find(c => c.statuses.split(',').includes(s));
        if (matchingCat) setActiveCategory(matchingCat.id);
      }
    }))
  ];

  const handleCategorySelect = (categoryId) => {
    setActiveCategory(categoryId);
    setStatusFilter('All');
    setPage(1);
  };

  const totalPages = Math.ceil(totalOppsCount / pageSize) || 1;

  return (
    <div className="page-container">
      <PageHeader 
        title="Opportunities" 
        desc="Manage your sales pipeline and track deal progression."
        actions={
          <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
            <div style={{ display: 'flex', backgroundColor: 'var(--gray-100)', borderRadius: '8px', padding: '4px' }}>
              <button 
                onClick={() => setViewMode('table')}
                style={{ padding: '6px 12px', borderRadius: '6px', border: 'none', background: viewMode === 'table' ? 'var(--white)' : 'transparent', color: viewMode === 'table' ? 'var(--ink)' : 'var(--gray-500)', fontWeight: viewMode === 'table' ? 600 : 500, cursor: 'pointer', boxShadow: viewMode === 'table' ? '0 1px 2px rgba(0,0,0,0.05)' : 'none', display: 'flex', alignItems: 'center', gap: '6px' }}
              >
                <Icon name="list" size={16} /> Table
              </button>
              <button 
                onClick={() => setViewMode('kanban')}
                style={{ padding: '6px 12px', borderRadius: '6px', border: 'none', background: viewMode === 'kanban' ? 'var(--white)' : 'transparent', color: viewMode === 'kanban' ? 'var(--ink)' : 'var(--gray-500)', fontWeight: viewMode === 'kanban' ? 600 : 500, cursor: 'pointer', boxShadow: viewMode === 'kanban' ? '0 1px 2px rgba(0,0,0,0.05)' : 'none', display: 'flex', alignItems: 'center', gap: '6px' }}
              >
                <Icon name="trello" size={16} /> Kanban
              </button>
            </div>
            <Button variant="primary" icon="plus" onClick={openAddModal}>New Opportunity</Button>
          </div>
        }
      />
      
      <div style={{ padding: '0 28px 28px', flex: 1, display: 'flex', flexDirection: 'column' }}>
        
        <div className="kpi-grid" style={{ marginBottom: '24px' }}>
          <KpiCard label="Total Opportunities" value={totalOppsCount} icon="briefcase" delta="0" ctx="All Time" dir="up" />
          <KpiCard label="Page Open Deals" value={openCount} icon="activity" delta="0" ctx="Excludes Terminal Stages" dir="up" />
          <KpiCard label="Page Pipeline Value" value={formatINR(pipelineValue)} icon="dollar-sign" delta="0" ctx="Open Opportunities" dir="up" />
          <KpiCard label="Page Weighted Pipeline" value={formatINR(weightedPipeline)} icon="trending-up" delta="0" ctx="Value × Probability" dir="up" />
        </div>

        <CRMSubcategoryTabs 
          categories={OPPORTUNITY_CATEGORIES.map(cat => ({
            ...cat,
            label: `${cat.label} ${categoryCounts[cat.id] !== undefined ? `(${categoryCounts[cat.id]})` : ''}`
          }))} 
          activeCategory={activeCategory} 
          onSelect={handleCategorySelect} 
        />

        <FilterBar 
          searchValue={search} 
          onSearchChange={(v) => { setSearch(v); setPage(1); }} 
          searchPlaceholder="Search by Opportunity name..." 
          chips={chips}
        />

        {error && (
          <div style={{ margin: '20px 0', padding: '16px', background: '#ffebee', color: '#c62828', borderRadius: '8px' }}>
            {error}
          </div>
        )}

        <div style={{ display: 'flex', flexDirection: 'column', flex: 1, marginTop: '16px' }}>
          {loading ? (
            <TableLoadingSkeleton rows={5} columns={headers.length} />
          ) : error ? (
            <TableEmptyState 
              icon="alert-circle" 
              title="Error Loading Opportunities" 
              desc={error} 
              action={<Button variant="secondary" onClick={() => loadData(page, search, statusFilter)}>Retry</Button>}
            />
          ) : opportunities.length === 0 ? (
            <TableEmptyState 
              icon="briefcase" 
              title="No Opportunities Found" 
              desc={search || statusFilter !== 'All' ? "No opportunities match your filter." : "Get started by adding a new opportunity."} 
              action={!search && statusFilter === 'All' ? <Button variant="primary" onClick={openAddModal}>Add Opportunity</Button> : null}
            />
          ) : (
            <>
              {viewMode === 'table' ? (
                <>
                  <CRMDataTable 
                    headers={headers} 
                    rows={rows} 
                    onRowClick={(row, idx) => handleRowClick(opportunities[idx])}
                  />
                  <div style={{ marginTop: 'auto', paddingTop: '16px', borderTop: '1px solid var(--border-light)' }}>
                    <TablePagination 
                      page={page} 
                      totalPages={totalPages} 
                      totalRecords={totalOppsCount} 
                      onPrev={() => setPage(p => Math.max(1, p - 1))}
                      onNext={() => setPage(p => Math.min(totalPages, p + 1))}
                    />
                  </div>
                </>
              ) : (
                renderKanban()
              )}
            </>
          )}
        </div>
      </div>

      <OpportunityEditModal
        isOpen={isModalOpen}
        onClose={() => setIsModalOpen(false)}
        onSave={() => {
          setIsModalOpen(false);
          loadData(page, search, statusFilter, activeCategory, viewMode);
        }}
        editingOpp={editingOpp}
      />

      {/* CHANGE STAGE MODAL */}
      <Modal 
        isOpen={isStageModalOpen} 
        onClose={() => !submitting && setIsStageModalOpen(false)} 
        title="Change Pipeline Stage"
        footer={
          <>
            <Button variant="secondary" onClick={() => setIsStageModalOpen(false)} disabled={submitting}>Cancel</Button>
            <Button variant="primary" onClick={handleStageSubmit} disabled={submitting}>
              {submitting ? 'Updating...' : 'Update Stage'}
            </Button>
          </>
        }
      >
        <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
          <div className="field">
            <label style={{ display: 'block', marginBottom: '8px', fontWeight: 500, fontSize: '13px', color: 'var(--brown)' }}>New Stage</label>
            <select 
              value={stageData.new_stage} 
              onChange={e => setStageData({...stageData, new_stage: e.target.value})}
              style={{ width: '100%', padding: '10px 12px', borderRadius: '6px', border: '1px solid var(--gray-300)' }}
            >
              {PIPELINE_STAGES.map(s => (
                <option key={s} value={s}>{s}</option>
              ))}
            </select>
          </div>
          
          <div className="field">
            <label style={{ display: 'block', marginBottom: '8px', fontWeight: 500, fontSize: '13px', color: 'var(--brown)' }}>Close Outcome</label>
            <select 
              value={stageData.close_outcome || 'None'} 
              onChange={e => setStageData({...stageData, close_outcome: e.target.value})}
              style={{ width: '100%', padding: '10px 12px', borderRadius: '6px', border: '1px solid var(--gray-300)' }}
            >
              <option value="None">None</option>
              <option value="Won">Won</option>
              <option value="Lost">Lost</option>
            </select>
          </div>
          
          {stageData.close_outcome === 'Lost' && (
            <div className="field">
              <FormInput label="Loss Reason" type="text" value={stageData.loss_reason} onChange={e => setStageData({...stageData, loss_reason: e.target.value})} />
            </div>
          )}
        </div>
      </Modal>

      {/* DELETE CONFIRMATION MODAL */}
      <Modal 
        isOpen={isDeleteModalOpen} 
        onClose={() => !submitting && setIsDeleteModalOpen(false)} 
        title="Confirm Deletion"
        footer={
          <>
            <Button variant="secondary" onClick={() => setIsDeleteModalOpen(false)} disabled={submitting}>Cancel</Button>
            <Button variant="danger" onClick={confirmDelete} disabled={submitting}>
              {submitting ? 'Deleting...' : 'Delete'}
            </Button>
          </>
        }
      >
        <p>Are you sure you want to delete opportunity <strong>{oppToDelete?.opportunity_id}</strong>?</p>
        <p style={{ color: 'var(--red)', fontSize: '13px', marginTop: '8px' }}>This action cannot be undone.</p>
      </Modal>
    </div>
  );
}
