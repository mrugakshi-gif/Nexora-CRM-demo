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
import { campaignService, referenceService } from '../services/crmService';

export default function Campaigns() {
  const [campaigns, setCampaigns] = useState([]);
  const [totalRecords, setTotalRecords] = useState(0);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [summary, setSummary] = useState(null);

  const [industries, setIndustries] = useState([]);
  const [departments, setDepartments] = useState([]);

  const [search, setSearch] = useState('');
  const [channelFilter, setChannelFilter] = useState('All');
  const [page, setPage] = useState(1);
  const pageSize = 25;

  const [isModalOpen, setIsModalOpen] = useState(false);
  const [editingCampaign, setEditingCampaign] = useState(null);
  const [formData, setFormData] = useState({
    campaign_name: '', campaign_type: '', start_date: '',
    end_date: '', budget_inr: '', target_industry_id: '', owner_department_id: ''
  });
  const [submitting, setSubmitting] = useState(false);
  const [formError, setFormError] = useState('');
  const [isDeleteModalOpen, setIsDeleteModalOpen] = useState(false);
  const [campaignToDelete, setCampaignToDelete] = useState(null);
  const [deleting, setDeleting] = useState(false);
  const [deleteError, setDeleteError] = useState('');

  const campaignTypes = ["Social Media", "Paid Search", "Email", "Partner Event", "Webinar", "Content/SEO", "Trade Show"];

  useEffect(() => { loadReferenceData(); }, []);
  useEffect(() => { loadData(); }, [page, search, channelFilter]); // eslint-disable-line

  const loadReferenceData = async () => {
    try {
      const [indRes, depRes] = await Promise.all([
        referenceService.getIndustries(),
        referenceService.getDepartments()
      ]);
      setIndustries(indRes.data || []);
      setDepartments(depRes.data || []);
    } catch (err) { console.error('Failed to load reference data', err); }
  };

  const loadData = async () => {
    setLoading(true);
    setError(null);
    try {
      const params = { page, page_size: pageSize };
      if (search) params.search = search;
      if (channelFilter !== 'All') params.campaign_type = channelFilter;
      
      const [res, summaryRes] = await Promise.all([
        campaignService.getCampaigns(params),
        campaignService.getCampaignSummary()
      ]);
      setCampaigns(res.data?.items || []);
      setTotalRecords(res.data?.total || 0);
      setSummary(summaryRes.data);
    } catch (err) {
      setError('Unable to load campaigns. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  const getDeptName = (id) => {
    const dep = departments.find(d => d.department_id === id);
    return dep ? dep.department_name : id || '-';
  };

  const getCampaignStatus = (camp) => {
    if (!camp.start_date) return 'Draft';
    const start = new Date(camp.start_date);
    const end = camp.end_date ? new Date(camp.end_date) : null;
    const now = new Date();
    if (start > now) return 'Planned';
    if (end && end < now) return 'Completed';
    return 'Active';
  };

  const openAddModal = () => {
    setEditingCampaign(null);
    setFormData({ campaign_name: '', campaign_type: '', start_date: '', end_date: '', budget_inr: '', target_industry_id: '', owner_department_id: '' });
    setFormError('');
    setIsModalOpen(true);
  };

  const openEditModal = (camp, e) => {
    e.stopPropagation();
    setEditingCampaign(camp);
    setFormData({
      campaign_name: camp.campaign_name || '', campaign_type: camp.campaign_type || '',
      start_date: camp.start_date || '', end_date: camp.end_date || '',
      budget_inr: camp.budget_inr !== null ? camp.budget_inr : '',
      target_industry_id: camp.target_industry_id || '', owner_department_id: camp.owner_department_id || ''
    });
    setFormError('');
    setIsModalOpen(true);
  };

  const handleDeleteClick = (camp, e) => {
    e.stopPropagation();
    setCampaignToDelete(camp);
    setDeleteError('');
    setIsDeleteModalOpen(true);
  };

  const confirmDelete = async () => {
    setDeleting(true);
    try {
      await campaignService.deleteCampaign(campaignToDelete.campaign_id);
      setIsDeleteModalOpen(false);
      loadData();
    } catch (err) {
      setDeleteError(err.response?.data?.detail || 'Error deleting campaign');
    } finally { setDeleting(false); }
  };

  const handleFormSubmit = async () => {
    if (!formData.campaign_name || !formData.campaign_type || !formData.start_date || !formData.owner_department_id) {
      setFormError('Please fill in all required fields.');
      return;
    }
    setSubmitting(true);
    setFormError('');
    const payload = { ...formData, budget_inr: formData.budget_inr === '' ? null : Number(formData.budget_inr), target_industry_id: formData.target_industry_id || null, end_date: formData.end_date || null };
    try {
      if (editingCampaign) await campaignService.updateCampaign(editingCampaign.campaign_id, payload);
      else await campaignService.createCampaign(payload);
      setIsModalOpen(false);
      loadData();
    } catch (err) {
      setFormError(err.response?.data?.detail || 'Error saving campaign.');
    } finally { setSubmitting(false); }
  };

  const headers = ['Campaign', 'Channel', 'Department', 'Start Date', 'Budget', 'Status', ''];

  const rows = campaigns.map(c => {
    const status = getCampaignStatus(c);
    const type = status === 'Active' ? 'success' : status === 'Planned' ? 'info' : status === 'Completed' ? 'primary' : 'neutral';
    return [
      <div><div style={{ fontWeight: 500, color: 'var(--brown)' }}>{c.campaign_name}</div><div style={{ fontSize: '11px', color: 'var(--gray-500)' }}>{c.campaign_id}</div></div>,
      <span>{c.campaign_type}</span>,
      <span>{getDeptName(c.owner_department_id)}</span>,
      <span>{c.start_date || '-'}</span>,
      <span>{c.budget_inr != null ? `₹${c.budget_inr.toLocaleString()}` : '-'}</span>,
      <CRMStatusBadge status={status} type={type} />,
      <div style={{ display: 'flex', gap: '8px', justifyContent: 'flex-end' }}>
        <Button variant="secondary" size="sm" onClick={(e) => openEditModal(c, e)}>Edit</Button>
        <Button variant="danger" size="sm" onClick={(e) => handleDeleteClick(c, e)}>Delete</Button>
      </div>
    ];
  });

  const categories = summary ? [
    { name: 'All', count: summary.total_campaigns },
    ...summary.category_counts.map(c => ({ name: c.category, count: c.count }))
  ] : [{ name: 'All', count: 0 }];

  return (
    <div className="page">
      <PageHeader title="Campaigns" desc="Plan and track marketing campaigns."
        actions={<Button variant="primary" onClick={openAddModal}>Create Campaign</Button>}
      />
      <div style={{ padding: '0 28px 28px' }}>
        {summary && (
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '16px', marginBottom: '24px' }}>
            <KpiCard label="Total Campaigns" value={summary.total_campaigns} icon="flag" delta="0" ctx="Lifetime" dir="up" />
            <KpiCard label="Total Budget" value={`₹${summary.total_budget.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`} icon="dollar-sign" delta="0" ctx="Lifetime" dir="up" />
            <KpiCard label="Total Engagements" value={summary.total_engagements} icon="users" delta="0" ctx="Lifetime" dir="up" />
            <KpiCard label="Demo Requests" value={summary.demo_requests} icon="airplay" delta="0" ctx="Lifetime" dir="up" />
          </div>
        )}

        <div style={{ marginBottom: '16px', display: 'flex', gap: '8px', overflowX: 'auto', alignItems: 'center', flexShrink: 0 }}>
          {categories.map(cat => {
            const isActive = channelFilter === cat.name;
            return (
              <button
                key={cat.name}
                onClick={() => { setChannelFilter(cat.name); setPage(1); }}
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

        <FilterBar searchPlaceholder="Search campaigns..." searchValue={search} onSearchChange={(v) => { setSearch(v); setPage(1); }}>
        </FilterBar>

        <CRMDataTable
          headers={headers}
          rows={rows}
          loading={loading}
          error={error}
          onRetry={loadData}
          emptyTitle="No campaigns found"
          emptyDescription={search || channelFilter !== 'All' ? "No campaigns match your current filters." : "You haven't created any campaigns yet."}
          rightCols={[6]}
        />

        <TablePagination
          page={page}
          totalPages={Math.max(1, Math.ceil(totalRecords / pageSize))}
          totalRecords={totalRecords}
          onPrev={() => setPage(p => Math.max(1, p - 1))}
          onNext={() => setPage(p => p + 1)}
        />
      </div>

      <Modal isOpen={isModalOpen} onClose={() => setIsModalOpen(false)} title={editingCampaign ? 'Edit Campaign' : 'Create Campaign'}>
        {formError && <div style={{ padding: '10px', backgroundColor: '#fee2e2', color: '#b91c1c', borderRadius: '6px', marginBottom: '16px', fontSize: '14px' }}>{formError}</div>}
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '16px' }}>
          <FormInput label="Campaign Name *" value={formData.campaign_name} onChange={e => setFormData({...formData, campaign_name: e.target.value})} />
          <div>
            <label style={{ display: 'block', marginBottom: '6px', fontSize: '13px', fontWeight: 500, color: 'var(--brown)' }}>Channel/Type *</label>
            <select value={formData.campaign_type} onChange={e => setFormData({...formData, campaign_type: e.target.value})} style={{ width: '100%', padding: '8px 12px', border: '1px solid var(--border)', borderRadius: '6px' }}>
              <option value="">Select...</option>
              {campaignTypes.map(t => <option key={t} value={t}>{t}</option>)}
            </select>
          </div>
          <FormInput label="Start Date *" type="date" value={formData.start_date} onChange={e => setFormData({...formData, start_date: e.target.value})} />
          <FormInput label="End Date" type="date" value={formData.end_date} onChange={e => setFormData({...formData, end_date: e.target.value})} />
          <FormInput label="Budget (₹)" type="number" value={formData.budget_inr} onChange={e => setFormData({...formData, budget_inr: e.target.value})} />
          <div>
            <label style={{ display: 'block', marginBottom: '6px', fontSize: '13px', fontWeight: 500, color: 'var(--brown)' }}>Owner Department *</label>
            <select value={formData.owner_department_id} onChange={e => setFormData({...formData, owner_department_id: e.target.value})} style={{ width: '100%', padding: '8px 12px', border: '1px solid var(--border)', borderRadius: '6px' }}>
              <option value="">Select...</option>
              {departments.map(d => <option key={d.department_id} value={d.department_id}>{d.department_name}</option>)}
            </select>
          </div>
        </div>
        <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '10px', marginTop: '24px' }}>
          <Button variant="secondary" onClick={() => setIsModalOpen(false)}>Cancel</Button>
          <Button variant="primary" onClick={handleFormSubmit} disabled={submitting}>{submitting ? 'Saving...' : 'Save Campaign'}</Button>
        </div>
      </Modal>

      <Modal isOpen={isDeleteModalOpen} onClose={() => setIsDeleteModalOpen(false)} title="Delete Campaign">
        {deleteError && <div style={{ color: 'red', marginBottom: '12px' }}>{deleteError}</div>}
        <p>Are you sure you want to delete <strong>{campaignToDelete?.campaign_name}</strong>?</p>
        <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '10px', marginTop: '24px' }}>
          <Button variant="secondary" onClick={() => setIsDeleteModalOpen(false)}>Cancel</Button>
          <Button variant="danger" onClick={confirmDelete} disabled={deleting}>{deleting ? 'Deleting...' : 'Delete'}</Button>
        </div>
      </Modal>
    </div>
  );
}
