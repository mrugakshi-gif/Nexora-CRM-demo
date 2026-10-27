import React, { useState, useEffect } from 'react';
import { useSearchParams } from 'react-router-dom';
import PageHeader from '../components/common/PageHeader';
import CRMDataTable from '../components/common/table/CRMDataTable';
import TablePagination from '../components/common/table/TablePagination';
import FilterBar from '../components/common/table/FilterBar';
import CRMStatusBadge from '../components/common/table/CRMStatusBadge';
import { Timeline, TimelineRow, TimelineDateSeparator } from '../components/common/Timeline';
import Modal from '../components/common/Modal';
import FormInput from '../components/common/FormInput';
import Button from '../components/common/Button';
import KpiCard from '../components/common/KpiCard';
import { activityService, lookupService } from '../services/crmService';

export default function Activities() {
  const [searchParams] = useSearchParams();
  const [tableActivities, setTableActivities] = useState([]);
  const [tableTotal, setTableTotal] = useState(0);
  const [tablePage, setTablePage] = useState(1);
  
  const [timelineActivities, setTimelineActivities] = useState([]);
  const [timelineTotal, setTimelineTotal] = useState(0);
  const [timelinePage, setTimelinePage] = useState(1);
  const [yearFilter, setYearFilter] = useState('All Years');
  const [companies, setCompanies] = useState([]);
  const [contacts, setContacts] = useState([]);
  const [leads, setLeads] = useState([]);
  const [opportunities, setOpportunities] = useState([]);
  const [customers, setCustomers] = useState([]);
  const [salesReps, setSalesReps] = useState([]);

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState('');
  const [summary, setSummary] = useState(null);
  const pageSize = 25;
  const [search, setSearch] = useState('');
  const [typeFilter, setTypeFilter] = useState('All Activities');
  const [timelineTypeFilter, setTimelineTypeFilter] = useState('All Activities');
  const [viewMode, setViewMode] = useState('table');

  const [isModalOpen, setIsModalOpen] = useState(false);
  const [isDeleteModalOpen, setIsDeleteModalOpen] = useState(false);
  const [editingActivity, setEditingActivity] = useState(null);
  const [activityToDelete, setActivityToDelete] = useState(null);
  const [formError, setFormError] = useState('');
  const [isSubmitting, setIsSubmitting] = useState(false);

  const [formData, setFormData] = useState({
    activity_type: 'Email', subject: '', description: '', activity_date: '',
    due_date: '', status: 'Pending', priority: 'Medium',
    company_id: '', contact_id: '', lead_id: '', opportunity_id: '', customer_id: '', sales_rep_id: ''
  });

  useEffect(() => { loadLookups(); }, []);
  useEffect(() => { 
    if (viewMode === 'table') {
      loadData('table');
    } else {
      loadData('timeline');
    }
  }, [tablePage, timelinePage, search, typeFilter, timelineTypeFilter, yearFilter, viewMode]); // eslint-disable-line

  async function loadLookups() {
    try {
      const lookupsRes = await lookupService.getAllLookups();
      const l = lookupsRes.data || {};
      setCompanies(l.companies || []);
      setContacts(l.contacts || []);
      setLeads(l.leads || []);
      setOpportunities(l.opportunities || []);
      setSalesReps(l.sales_reps || []);
      setCustomers(l.customers || []);
    } catch (err) { console.error('Lookup load failed:', err); }
  }

  async function loadData(mode = viewMode) {
    setLoading(true);
    setError('');
    try {
      const isTable = mode === 'table';
      const params = { 
        page: isTable ? tablePage : timelinePage, 
        page_size: pageSize, 
        sort_by: 'activity_date', 
        sort_order: 'desc' 
      };
      if (searchParams.get('company_id')) params.company_id = searchParams.get('company_id');
      if (searchParams.get('customer_id')) params.customer_id = searchParams.get('customer_id');

      
      if (search) params.search = search;
      
      if (isTable && typeFilter !== 'All Activities') {
        params.activity_type = typeFilter;
      }
      
      if (!isTable && timelineTypeFilter !== 'All Activities') {
        params.activity_type = timelineTypeFilter;
      }
      
      if (!isTable && yearFilter !== 'All Years') {
        params.year = yearFilter;
      }
      
      const [res, summaryRes] = await Promise.all([
        activityService.getActivities(params),
        activityService.getActivitySummary()
      ]);
      
      let items = res.data?.items || [];
      const total = res.data?.total || items.length;
      
      if (isTable) {
        setTableActivities(items);
        setTableTotal(total);
      } else {
        setTimelineActivities(items);
        setTimelineTotal(total);
      }
      setSummary(summaryRes.data);
    } catch (err) {
      setError('Failed to fetch activities.');
    } finally {
      setLoading(false);
    }
  }

  const getCompanyName = (id) => companies.find(c => c.id === id)?.name || id || 'N/A';
  const getContactName = (id) => contacts.find(c => c.id === id)?.name || id || 'N/A';
  const getRepName = (id) => { const r = salesReps.find(r => r.id === id); return r ? r.name : id || 'System'; };

  const getBadgeType = (status) => {
    if (!status) return 'neutral';
    const s = status.toLowerCase();
    if (s.includes('completed')) return 'success';
    if (s.includes('cancelled')) return 'error';
    if (s.includes('progress') || s.includes('planned')) return 'info';
    return 'warning';
  };

  const getPriorityType = (priority) => {
    const p = (priority || '').toLowerCase();
    if (p === 'urgent' || p === 'high') return 'error';
    if (p === 'low') return 'neutral';
    return 'info';
  };

  const formatDate = (val) => val ? new Date(val).toLocaleDateString() : '-';

  const handleOpenModal = (activity = null) => {
    setFormError('');
    if (activity?.activity_id) {
      setEditingActivity(activity);
      setFormData({
        activity_type: activity.activity_type || 'Email', subject: activity.subject || '',
        description: activity.description || '', activity_date: activity.activity_date ? activity.activity_date.substring(0,10) : '',
        due_date: activity.due_date ? activity.due_date.substring(0,10) : '', status: activity.status || 'Pending',
        priority: activity.priority || 'Medium', company_id: activity.company_id || '',
        contact_id: activity.contact_id || '', lead_id: activity.lead_id || '',
        opportunity_id: activity.opportunity_id || '', customer_id: activity.customer_id || '', sales_rep_id: activity.sales_rep_id || ''
      });
    } else {
      setEditingActivity(null);
      setFormData({ activity_type: 'Email', subject: '', description: '', activity_date: new Date().toISOString().substring(0,10), due_date: new Date().toISOString().substring(0,10), status: 'Pending', priority: 'Medium', company_id: '', contact_id: '', lead_id: '', opportunity_id: '', customer_id: '', sales_rep_id: '' });
    }
    setIsModalOpen(true);
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setIsSubmitting(true);
    setFormError('');
    const payload = { ...formData };
    Object.keys(payload).forEach(k => { if (payload[k] === '') payload[k] = null; });
    try {
      if (editingActivity) await activityService.updateActivity(editingActivity.activity_id, payload);
      else await activityService.createActivity(payload);
      setIsModalOpen(false);
      loadData();
    } catch (err) {
      setFormError('Failed to save activity.');
    } finally { setIsSubmitting(false); }
  };

  const handleCompleteActivity = async (id) => {
    try { await activityService.completeActivity(id); loadData(); }
    catch (err) { alert('Failed to complete activity.'); }
  };

  const confirmDelete = async () => {
    if (!activityToDelete) return;
    setIsSubmitting(true);
    try {
      if (activityService.deleteActivity) await activityService.deleteActivity(activityToDelete.activity_id);
      setIsDeleteModalOpen(false);
      loadData();
    } catch (err) { alert('Error deleting activity.'); }
    finally { setIsSubmitting(false); }
  };

  const headers = ['Subject / Type', 'Related To', 'Assigned To', 'Date', 'Priority', 'Status', ''];

  const rows = tableActivities.map(a => {
    let related = '-';
    if (a.company_id) related = `Company: ${getCompanyName(a.company_id)}`;
    else if (a.contact_id) related = `Contact: ${getContactName(a.contact_id)}`;
    else if (a.lead_id) related = `Lead: ${a.lead_id}`;
    else if (a.opportunity_id) related = `Opp: ${a.opportunity_id}`;
    else if (a.customer_id) related = `Customer: ${a.customer_id}`;

    return [
      <div><div style={{ fontWeight: 600, color: 'var(--heading-primary)' }}>{a.subject || 'No Subject'}</div><div style={{ fontSize: '11px', color: 'var(--ink-mute)' }}>{a.activity_type}</div></div>,
      <span style={{ fontSize: '13px' }}>{related}</span>,
      <span>{getRepName(a.sales_rep_id)}</span>,
      <span>{formatDate(a.activity_date)}</span>,
      <CRMStatusBadge status={a.priority || 'Medium'} type={getPriorityType(a.priority)} />,
      <CRMStatusBadge status={a.status || 'Unknown'} type={getBadgeType(a.status)} />,
      <div style={{ display: 'flex', gap: '6px', justifyContent: 'flex-end', alignItems: 'center' }}>
        <Button variant="ghost" size="small" icon="settings" onClick={() => handleOpenModal(a)}>Edit</Button>
        {a.status !== 'Completed' && (
          <Button variant="success" size="small" onClick={() => handleCompleteActivity(a.activity_id)}>Done</Button>
        )}
      </div>
    ];
  });

  const categories = summary ? [
    { name: 'All Activities', count: summary.total_activities },
    ...summary.category_counts.map(c => ({ name: c.category, count: c.count }))
  ] : [{ name: 'All Activities', count: 0 }];

  // Group activities by date for the timeline while preserving descending chronological order
  const groupedActivitiesMap = new Map();
  timelineActivities.forEach(a => {
    const d = a.activity_date ? new Date(a.activity_date).toLocaleDateString('en-US', { weekday: 'long', year: 'numeric', month: 'long', day: 'numeric' }) : 'Unknown Date';
    if (!groupedActivitiesMap.has(d)) {
      groupedActivitiesMap.set(d, []);
    }
    groupedActivitiesMap.get(d).push(a);
  });
  const groupedActivities = Array.from(groupedActivitiesMap.entries());

  return (
    <div className="page">
      <PageHeader title="Tasks & Activities" desc="Track emails, calls, meetings, and tasks."
        actions={
          <div style={{ display: 'flex', gap: '12px' }}>
            <div style={{ display: 'flex', backgroundColor: 'var(--bg-subtle)', padding: '4px', borderRadius: '10px', border: '1px solid var(--border-soft)' }}>
              {['table', 'timeline'].map(mode => (
                <button
                  key={mode}
                  onClick={() => setViewMode(mode)}
                  style={{
                    padding: '6px 14px',
                    border: 'none',
                    borderRadius: '8px',
                    backgroundColor: viewMode === mode ? 'var(--bg-surface)' : 'transparent',
                    color: viewMode === mode ? 'var(--heading-primary)' : 'var(--ink-mute)',
                    fontWeight: viewMode === mode ? 600 : 500,
                    cursor: 'pointer',
                    boxShadow: viewMode === mode ? 'var(--clay-shadow-sm)' : 'none',
                    transition: 'all 0.2s',
                    textTransform: 'capitalize'
                  }}
                >
                  {mode}
                </button>
              ))}
            </div>
            <Button variant="primary" onClick={() => handleOpenModal()}>Log Activity</Button>
          </div>
        }
      />
      <div style={{ padding: '0 28px 28px' }}>
        {summary && (
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))', gap: '16px', marginBottom: '24px' }}>
            <KpiCard label="Total Activities" value={summary.total_activities} icon="layers" delta="0" ctx="Lifetime" dir="up" />
            <KpiCard label="Completed Activities" value={summary.completed_activities} icon="check-circle" delta="0" ctx="Lifetime" dir="up" />
            <KpiCard label="Pending Activities" value={summary.pending_activities} icon="clock" delta="0" ctx="Lifetime" dir="up" />
            <KpiCard label="Overdue Activities" value={summary.overdue_activities} icon="alert-circle" delta="0" ctx="Lifetime" dir="up" />
          </div>
        )}

        {viewMode === 'table' && (
          <div style={{ marginBottom: '16px', display: 'flex', gap: '8px', overflowX: 'auto', alignItems: 'center', flexShrink: 0 }}>
            {categories.map(cat => {
              const isActive = typeFilter === cat.name;
              return (
                <button
                  key={cat.name}
                  onClick={() => { setTypeFilter(cat.name); setTablePage(1); }}
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
        )}

        <FilterBar searchPlaceholder="Search activities..." searchValue={search} onSearchChange={(v) => { setSearch(v); setTablePage(1); setTimelinePage(1); }} />

        {viewMode === 'table' ? (
          <>
            <CRMDataTable headers={headers} rows={rows} loading={loading && viewMode === 'table'} error={error} onRetry={() => loadData('table')}
              emptyTitle="No activities found" emptyDescription={search || typeFilter !== 'All Activities' ? "No activities match your filters." : "No activities yet."} rightCols={[6]} />
            <TablePagination page={tablePage} totalPages={Math.max(1, Math.ceil(tableTotal / pageSize))} totalRecords={tableTotal} onPrev={() => setTablePage(p => Math.max(1, p - 1))} onNext={() => setTablePage(p => p + 1)} />
          </>
        ) : (
          <div className="card" style={{ padding: '24px 28px' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '24px', flexWrap: 'wrap', gap: '12px' }}>
              <h3 style={{ margin: 0, fontSize: '17px', fontWeight: 700, color: 'var(--heading-primary)' }}>Timeline</h3>
              <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                <span style={{ fontSize: '13px', color: 'var(--ink-mute)', fontWeight: 500 }}>Filter by</span>
                <select
                  value={timelineTypeFilter}
                  onChange={(e) => { setTimelineTypeFilter(e.target.value); setTimelinePage(1); }}
                  style={{
                    padding: '6px 12px',
                    borderRadius: '8px',
                    border: '1px solid var(--border)',
                    backgroundColor: 'var(--bg-surface)',
                    color: 'var(--ink)',
                    outline: 'none',
                    fontSize: '13px',
                    fontWeight: 500,
                    cursor: 'pointer',
                    boxShadow: 'var(--clay-shadow-sm)'
                  }}
                >
                  <option value="All Activities" style={{ backgroundColor: 'var(--bg-surface)', color: 'var(--ink)' }}>All Activities</option>
                  {(summary?.category_counts || []).map(c => (
                    <option key={c.category} value={c.category} style={{ backgroundColor: 'var(--bg-surface)', color: 'var(--ink)' }}>{c.category}</option>
                  ))}
                </select>
                <select 
                  value={yearFilter} 
                  onChange={(e) => { setYearFilter(e.target.value); setTimelinePage(1); }}
                  style={{
                    padding: '6px 12px',
                    borderRadius: '8px',
                    border: '1px solid var(--border)',
                    backgroundColor: 'var(--bg-surface)',
                    color: 'var(--ink)',
                    outline: 'none',
                    fontSize: '13px',
                    fontWeight: 500,
                    cursor: 'pointer',
                    boxShadow: 'var(--clay-shadow-sm)'
                  }}
                >
                  <option value="All Years" style={{ backgroundColor: 'var(--bg-surface)', color: 'var(--ink)' }}>All Years</option>
                  {(summary?.years || []).map(y => (
                    <option key={y} value={y} style={{ backgroundColor: 'var(--bg-surface)', color: 'var(--ink)' }}>{y}</option>
                  ))}
                </select>
              </div>
            </div>

            {loading && viewMode === 'timeline' ? <p style={{ padding: '24px 0', color: 'var(--ink-mute)' }}>Loading...</p> : error ? <p style={{ color: 'var(--danger)', padding: '24px 0' }}>{error}</p> : timelineActivities.length === 0 ? <p style={{ color: 'var(--ink-mute)', padding: '24px 0' }}>No activities to show.</p> : (
              <Timeline>
                {groupedActivities.map(([dateLabel, dateActivities]) => (
                  <React.Fragment key={dateLabel}>
                    <TimelineDateSeparator date={dateLabel} />
                    {dateActivities.map(a => {
                      let related = '';
                      if (a.company_id) related = `Company: ${getCompanyName(a.company_id)}`;
                      else if (a.contact_id) related = `Contact: ${getContactName(a.contact_id)}`;
                      else if (a.customer_id) related = `Customer: ${a.customer_id}`;
                      else if (a.opportunity_id) related = `Opp: ${a.opportunity_id}`;
                      
                      return (
                        <TimelineRow
                          key={a.activity_id}
                          icon={a.activity_type === 'Email' ? 'mail' : a.activity_type === 'Call' ? 'phone' : a.activity_type === 'Meeting' ? 'users' : 'check-square'}
                          title={a.subject || 'No Subject'}
                          type={a.activity_type}
                          time={a.activity_date ? new Date(a.activity_date).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' }) : ''}
                          owner={getRepName(a.sales_rep_id)}
                          status={<CRMStatusBadge status={a.status || 'Unknown'} type={getBadgeType(a.status)} />}
                          relatedTo={related}
                        >
                          {a.description}
                        </TimelineRow>
                      );
                    })}
                  </React.Fragment>
                ))}
              </Timeline>
            )}
            <TablePagination page={timelinePage} totalPages={Math.max(1, Math.ceil(timelineTotal / pageSize))} totalRecords={timelineTotal} onPrev={() => setTimelinePage(p => Math.max(1, p - 1))} onNext={() => setTimelinePage(p => p + 1)} />
          </div>
        )}
      </div>

      <Modal isOpen={isModalOpen} onClose={() => setIsModalOpen(false)} title={editingActivity ? 'Edit Activity' : 'Log Activity'}>
        <form onSubmit={handleSubmit}>
          {formError && <div style={{ color: 'red', marginBottom: '14px' }}>{formError}</div>}
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '14px' }}>
            <div>
              <label style={{ display: 'block', marginBottom: '6px', fontSize: '13px', fontWeight: 500 }}>Type *</label>
              <select value={formData.activity_type} onChange={e => setFormData({...formData, activity_type: e.target.value})} required style={{ width: '100%', padding: '8px 12px', border: '1px solid var(--border)', borderRadius: '6px' }}>
                {['Email', 'Call', 'Meeting', 'Task', 'Demo'].map(t => <option key={t} value={t}>{t}</option>)}
              </select>
            </div>
            <FormInput label="Subject *" value={formData.subject} onChange={e => setFormData({...formData, subject: e.target.value})} required />
          </div>
          <div style={{ margin: '14px 0' }}>
            <label style={{ display: 'block', marginBottom: '6px', fontSize: '13px', fontWeight: 500 }}>Description</label>
            <textarea value={formData.description} onChange={e => setFormData({...formData, description: e.target.value})} rows="3" style={{ width: '100%', padding: '8px 12px', border: '1px solid var(--border)', borderRadius: '6px', fontFamily: 'inherit', resize: 'vertical' }} />
          </div>
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '14px' }}>
            <FormInput label="Activity Date *" type="date" value={formData.activity_date} onChange={e => setFormData({...formData, activity_date: e.target.value})} required />
            <FormInput label="Due Date" type="date" value={formData.due_date} onChange={e => setFormData({...formData, due_date: e.target.value})} />
            <div>
              <label style={{ display: 'block', marginBottom: '6px', fontSize: '13px', fontWeight: 500 }}>Status</label>
              <select value={formData.status} onChange={e => setFormData({...formData, status: e.target.value})} style={{ width: '100%', padding: '8px 12px', border: '1px solid var(--border)', borderRadius: '6px' }}>
                {['Pending', 'In Progress', 'Completed', 'Cancelled'].map(s => <option key={s} value={s}>{s}</option>)}
              </select>
            </div>
            <div>
              <label style={{ display: 'block', marginBottom: '6px', fontSize: '13px', fontWeight: 500 }}>Priority</label>
              <select value={formData.priority} onChange={e => setFormData({...formData, priority: e.target.value})} style={{ width: '100%', padding: '8px 12px', border: '1px solid var(--border)', borderRadius: '6px' }}>
                {['High', 'Medium', 'Low'].map(p => <option key={p} value={p}>{p}</option>)}
              </select>
            </div>
          </div>
          <div style={{ padding: '14px', backgroundColor: 'var(--bg-light)', borderRadius: '8px', margin: '14px 0' }}>
            <h4 style={{ fontSize: '13px', margin: '0 0 10px', color: 'var(--ink)' }}>Related To</h4>
            <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '10px' }}>
              {[['company_id', companies, 'Company'], ['contact_id', contacts, 'Contact']].map(([field, list, label]) => (
                <select key={field} value={formData[field]} onChange={e => setFormData({...formData, [field]: e.target.value})} style={{ width: '100%', padding: '8px', border: '1px solid var(--border)', borderRadius: '6px', fontSize: '13px' }}>
                  <option value="">-- {label} --</option>
                  {list.map(item => <option key={item.id} value={item.id}>{item.name}</option>)}
                </select>
              ))}
              <select value={formData.opportunity_id} onChange={e => setFormData({...formData, opportunity_id: e.target.value})} style={{ width: '100%', padding: '8px', border: '1px solid var(--border)', borderRadius: '6px', fontSize: '13px' }}>
                <option value="">-- Opportunity --</option>
                {opportunities.map(o => <option key={o.id} value={o.id}>{o.name}</option>)}
              </select>
              <select value={formData.lead_id} onChange={e => setFormData({...formData, lead_id: e.target.value})} style={{ width: '100%', padding: '8px', border: '1px solid var(--border)', borderRadius: '6px', fontSize: '13px' }}>
                <option value="">-- Lead --</option>
                {leads.map(l => <option key={l.id} value={l.id}>{l.name}</option>)}
              </select>
            </div>
          </div>
          <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '10px', marginTop: '20px' }}>
            <Button variant="secondary" onClick={() => setIsModalOpen(false)} type="button">Cancel</Button>
            <Button variant="primary" type="submit" disabled={isSubmitting}>{isSubmitting ? 'Saving...' : 'Save Activity'}</Button>
          </div>
        </form>
      </Modal>

      <Modal isOpen={isDeleteModalOpen} onClose={() => setIsDeleteModalOpen(false)} title="Delete Activity">
        <p>Are you sure you want to delete this activity?</p>
        <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '10px', marginTop: '24px' }}>
          <Button variant="secondary" onClick={() => setIsDeleteModalOpen(false)}>Cancel</Button>
          <Button variant="danger" onClick={confirmDelete} disabled={isSubmitting}>{isSubmitting ? 'Deleting...' : 'Delete'}</Button>
        </div>
      </Modal>
    </div>
  );
}
