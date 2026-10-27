import React, { useState } from 'react';
import PageHeader from '../components/common/PageHeader';
import Card from '../components/common/Card';
import { companyService, leadService, opportunityService, contactService, activityService, customerService } from '../services/crmService';
import Icon from '../components/common/Icon';
import Modal from '../components/common/Modal';
import FormInput from '../components/common/FormInput';
import Button from '../components/common/Button';

const REPORT_LIBRARY = [
  { id: 'companies', name: 'Company Demographics Report', cat: 'Companies' },
  { id: 'leads', name: 'Lead Status Report', cat: 'Leads' },
  { id: 'opportunities', name: 'Opportunity Pipeline Snapshot', cat: 'Opportunities' },
  { id: 'contacts', name: 'Contact Directory Report', cat: 'Contacts' },
  { id: 'activities', name: 'Activity Log Report', cat: 'Activities' },
];

export default function Reports() {
  const [exportingId, setExportingId] = useState(null);
  const [showCustomReportModal, setShowCustomReportModal] = useState(false);
  const [customExporting, setCustomExporting] = useState(false);
  const [customError, setCustomError] = useState('');
  
  // Card filters
  const [cardFilters, setCardFilters] = useState({
    companies: { account_status: '' },
    leads: { lead_status: '' },
    opportunities: { pipeline_stage: '' },
    contacts: { is_decision_maker: '' },
    activities: { activity_type: '' }
  });

  // Custom Report State
  const [customSource, setCustomSource] = useState('');
  const [customFilters, setCustomFilters] = useState({});
  const [customFields, setCustomFields] = useState([]);

  const CUSTOM_CONFIGS = {
    companies: {
      label: 'Companies',
      service: companyService.getCompanies,
      filterOptions: [
        { key: 'account_status', label: 'Status', options: ['Active', 'Inactive', 'Pending'] }
      ],
      fieldOptions: [
        { key: 'company_id', label: 'ID' },
        { key: 'company_name', label: 'Company Name' },
        { key: 'account_status', label: 'Status' },
        { key: 'industry_id', label: 'Industry ID' },
        { key: 'annual_revenue_band_inr', label: 'Annual Revenue' },
        { key: 'created_at', label: 'Date Created' }
      ]
    },
    leads: {
      label: 'Leads',
      service: leadService.getLeads,
      filterOptions: [
        { key: 'lead_status', label: 'Status', options: ['New', 'Contacted', 'Qualified', 'Lost'] }
      ],
      fieldOptions: [
        { key: 'lead_id', label: 'ID' },
        { key: 'company_id', label: 'Company ID' },
        { key: 'lead_status', label: 'Status' },
        { key: 'created_at', label: 'Date Created' }
      ]
    },
    opportunities: {
      label: 'Opportunities',
      service: opportunityService.getOpportunities,
      filterOptions: [
        { key: 'pipeline_stage', label: 'Stage', options: ['Prospecting', 'Qualification', 'Proposal', 'Negotiation', 'Closed Won', 'Closed Lost'] }
      ],
      fieldOptions: [
        { key: 'opportunity_id', label: 'ID' },
        { key: 'opportunity_name', label: 'Opportunity Name' },
        { key: 'pipeline_stage', label: 'Stage' },
        { key: 'deal_value_inr', label: 'Amount' },
        { key: 'expected_close_date', label: 'Close Date' },
        { key: 'created_at', label: 'Date Created' }
      ]
    },
    customers: {
      label: 'Customers',
      service: customerService.getCustomers,
      filterOptions: [
        { key: 'customer_status', label: 'Status', options: ['Active', 'Churned', 'At Risk', 'Onboarding'] }
      ],
      fieldOptions: [
        { key: 'customer_id', label: 'ID' },
        { key: 'company_id', label: 'Company ID' },
        { key: 'customer_status', label: 'Status' },
        { key: 'customer_since', label: 'Customer Since' },
        { key: 'renewal_date', label: 'Renewal Date' }
      ]
    }
  };

  const updateCardFilter = (reportId, field, value) => {
    setCardFilters(prev => ({
      ...prev,
      [reportId]: {
        ...prev[reportId],
        [field]: value
      }
    }));
  };

  const fetchAll = async (serviceMethod, filters = {}) => {
    let all = [];
    let skip = 0;
    const limit = 100;
    
    // Clean filters (remove empty strings)
    const cleanFilters = {};
    for (const [k, v] of Object.entries(filters)) {
      if (v !== '' && v !== null && v !== undefined) {
        cleanFilters[k] = v;
      }
    }

    while (true) {
      const res = await serviceMethod({ skip, limit, ...cleanFilters });
      const items = res.data?.items || res.data || [];
      if (items.length === 0) break;
      all = all.concat(items);
      if (items.length < limit) break;
      skip += limit;
    }
    return all;
  };

  const downloadCSV = (data, filename, allowedFields = null) => {
    if (data.length === 0) {
      alert("No data available to export.");
      return;
    }

    let keys = Object.keys(data[0]).filter(k => typeof data[0][k] !== 'object');
    
    if (allowedFields && allowedFields.length > 0) {
      keys = allowedFields.filter(f => keys.includes(f));
    }

    const csv = [
      keys.join(','),
      ...data.map(row => keys.map(k => `"${String(row[k] || '').replace(/"/g, '""')}"`).join(','))
    ].join('\n');

    const blob = new Blob([csv], { type: 'text/csv' });
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    window.URL.revokeObjectURL(url);
    document.body.removeChild(a);
  };

  const handleExport = async (reportId) => {
    setExportingId(reportId);
    try {
      let data = [];
      const filters = cardFilters[reportId] || {};

      if (reportId === 'companies') {
        data = await fetchAll(companyService.getCompanies, filters);
      } else if (reportId === 'leads') {
        data = await fetchAll(leadService.getLeads, filters);
      } else if (reportId === 'opportunities') {
        data = await fetchAll(opportunityService.getOpportunities, filters);
      } else if (reportId === 'contacts') {
        // Handle is_decision_maker boolean conversion
        const cFilters = {};
        if (filters.is_decision_maker === 'true') cFilters.is_decision_maker = true;
        else if (filters.is_decision_maker === 'false') cFilters.is_decision_maker = false;
        data = await fetchAll(contactService.getContacts, cFilters);
      } else if (reportId === 'activities') {
        data = await fetchAll(activityService.getActivities, filters);
      }

      downloadCSV(data, `${reportId}_export.csv`);
    } catch (err) {
      console.error(err);
      alert("Failed to export report.");
    } finally {
      setExportingId(null);
    }
  };

  const handleCustomExport = async () => {
    if (!customSource || !CUSTOM_CONFIGS[customSource]) {
      setCustomError('Please select a data source.');
      return;
    }
    if (customFields.length === 0) {
      setCustomError('Please select at least one field to export.');
      return;
    }

    setCustomExporting(true);
    setCustomError('');

    try {
      const config = CUSTOM_CONFIGS[customSource];
      const data = await fetchAll(config.service, customFilters);
      downloadCSV(data, `custom_${customSource}_export.csv`, customFields);
      alert("Custom report exported successfully!");
      setShowCustomReportModal(false);
      // Reset state for next time
      setCustomSource('');
      setCustomFilters({});
      setCustomFields([]);
    } catch (err) {
      console.error(err);
      setCustomError("Failed to generate custom export.");
    } finally {
      setCustomExporting(false);
    }
  };

  const toggleCustomField = (key) => {
    setCustomFields(prev => 
      prev.includes(key) ? prev.filter(f => f !== key) : [...prev, key]
    );
  };

  return (
    <div className="page" style={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
      <PageHeader 
        title="Reports" 
        desc="A library of ready-made and custom reports across every module."
        actions={
          <div className="page-actions">
            <button className="btn btn-primary" onClick={() => setShowCustomReportModal(true)}>
              Create Custom Report
            </button>
          </div>
        }
      />
      <div style={{ padding: '0 28px 28px', flex: 1, overflowY: 'auto' }}>
        <h3 style={{ fontSize: '15px', fontWeight: '600', marginBottom: '16px', color: 'var(--brown)' }}>Available Reports</h3>
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))', gap: '16px', marginBottom: '32px' }}>
          
          {/* Companies Report */}
          <Card style={{ padding: '16px 18px', display: 'flex', flexDirection: 'column' }}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '10px' }}>
              <span className="badge neutral">Companies</span>
              <Icon name="file" size={16} color="var(--brown)" stroke={1.8} />
            </div>
            <div style={{ fontSize: '13.5px', fontWeight: '700', color: 'var(--ink)', marginTop: '12px', marginBottom: '8px' }}>Company Demographics Report</div>
            <select 
              value={cardFilters.companies.account_status} 
              onChange={e => updateCardFilter('companies', 'account_status', e.target.value)}
              style={{ width: '100%', padding: '6px', fontSize: '12px', borderRadius: '4px', border: '1px solid var(--border-soft)' }}
            >
              <option value="">All Statuses</option>
              <option value="Active">Active</option>
              <option value="Inactive">Inactive</option>
              <option value="Pending">Pending</option>
            </select>
            <div style={{ marginTop: 'auto', paddingTop: '16px', display: 'flex' }}>
              <button className="btn btn-ghost" style={{ flex: 1, justifyContent: 'center' }} onClick={() => handleExport('companies')} disabled={exportingId === 'companies'}>
                <Icon name="download" size={14} stroke={1.8} />
                {exportingId === 'companies' ? 'Exporting...' : 'Export CSV'}
              </button>
            </div>
          </Card>

          {/* Leads Report */}
          <Card style={{ padding: '16px 18px', display: 'flex', flexDirection: 'column' }}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '10px' }}>
              <span className="badge neutral">Leads</span>
              <Icon name="file" size={16} color="var(--brown)" stroke={1.8} />
            </div>
            <div style={{ fontSize: '13.5px', fontWeight: '700', color: 'var(--ink)', marginTop: '12px', marginBottom: '8px' }}>Lead Status Report</div>
            <select 
              value={cardFilters.leads.lead_status} 
              onChange={e => updateCardFilter('leads', 'lead_status', e.target.value)}
              style={{ width: '100%', padding: '6px', fontSize: '12px', borderRadius: '4px', border: '1px solid var(--border-soft)' }}
            >
              <option value="">All Statuses</option>
              <option value="New">New</option>
              <option value="Contacted">Contacted</option>
              <option value="Qualified">Qualified</option>
              <option value="Lost">Lost</option>
            </select>
            <div style={{ marginTop: 'auto', paddingTop: '16px', display: 'flex' }}>
              <button className="btn btn-ghost" style={{ flex: 1, justifyContent: 'center' }} onClick={() => handleExport('leads')} disabled={exportingId === 'leads'}>
                <Icon name="download" size={14} stroke={1.8} />
                {exportingId === 'leads' ? 'Exporting...' : 'Export CSV'}
              </button>
            </div>
          </Card>

          {/* Opportunities Report */}
          <Card style={{ padding: '16px 18px', display: 'flex', flexDirection: 'column' }}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '10px' }}>
              <span className="badge neutral">Opportunities</span>
              <Icon name="file" size={16} color="var(--brown)" stroke={1.8} />
            </div>
            <div style={{ fontSize: '13.5px', fontWeight: '700', color: 'var(--ink)', marginTop: '12px', marginBottom: '8px' }}>Opportunity Pipeline Snapshot</div>
            <select 
              value={cardFilters.opportunities.pipeline_stage} 
              onChange={e => updateCardFilter('opportunities', 'pipeline_stage', e.target.value)}
              style={{ width: '100%', padding: '6px', fontSize: '12px', borderRadius: '4px', border: '1px solid var(--border-soft)' }}
            >
              <option value="">All Stages</option>
              <option value="Prospecting">Prospecting</option>
              <option value="Qualification">Qualification</option>
              <option value="Proposal">Proposal</option>
              <option value="Negotiation">Negotiation</option>
              <option value="Closed Won">Closed Won</option>
              <option value="Closed Lost">Closed Lost</option>
            </select>
            <div style={{ marginTop: 'auto', paddingTop: '16px', display: 'flex' }}>
              <button className="btn btn-ghost" style={{ flex: 1, justifyContent: 'center' }} onClick={() => handleExport('opportunities')} disabled={exportingId === 'opportunities'}>
                <Icon name="download" size={14} stroke={1.8} />
                {exportingId === 'opportunities' ? 'Exporting...' : 'Export CSV'}
              </button>
            </div>
          </Card>

          {/* Contacts Report */}
          <Card style={{ padding: '16px 18px', display: 'flex', flexDirection: 'column' }}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '10px' }}>
              <span className="badge neutral">Contacts</span>
              <Icon name="file" size={16} color="var(--brown)" stroke={1.8} />
            </div>
            <div style={{ fontSize: '13.5px', fontWeight: '700', color: 'var(--ink)', marginTop: '12px', marginBottom: '8px' }}>Contact Directory Report</div>
            <select 
              value={cardFilters.contacts.is_decision_maker} 
              onChange={e => updateCardFilter('contacts', 'is_decision_maker', e.target.value)}
              style={{ width: '100%', padding: '6px', fontSize: '12px', borderRadius: '4px', border: '1px solid var(--border-soft)' }}
            >
              <option value="">All Contacts</option>
              <option value="true">Decision Makers Only</option>
              <option value="false">Non-Decision Makers</option>
            </select>
            <div style={{ marginTop: 'auto', paddingTop: '16px', display: 'flex' }}>
              <button className="btn btn-ghost" style={{ flex: 1, justifyContent: 'center' }} onClick={() => handleExport('contacts')} disabled={exportingId === 'contacts'}>
                <Icon name="download" size={14} stroke={1.8} />
                {exportingId === 'contacts' ? 'Exporting...' : 'Export CSV'}
              </button>
            </div>
          </Card>

          {/* Activities Report */}
          <Card style={{ padding: '16px 18px', display: 'flex', flexDirection: 'column' }}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: '10px' }}>
              <span className="badge neutral">Activities</span>
              <Icon name="file" size={16} color="var(--brown)" stroke={1.8} />
            </div>
            <div style={{ fontSize: '13.5px', fontWeight: '700', color: 'var(--ink)', marginTop: '12px', marginBottom: '8px' }}>Activity Log Report</div>
            <select 
              value={cardFilters.activities.activity_type} 
              onChange={e => updateCardFilter('activities', 'activity_type', e.target.value)}
              style={{ width: '100%', padding: '6px', fontSize: '12px', borderRadius: '4px', border: '1px solid var(--border-soft)' }}
            >
              <option value="">All Types</option>
              <option value="Email">Email</option>
              <option value="Call">Call</option>
              <option value="Meeting">Meeting</option>
              <option value="Task">Task</option>
              <option value="Demo">Demo</option>
            </select>
            <div style={{ marginTop: 'auto', paddingTop: '16px', display: 'flex' }}>
              <button className="btn btn-ghost" style={{ flex: 1, justifyContent: 'center' }} onClick={() => handleExport('activities')} disabled={exportingId === 'activities'}>
                <Icon name="download" size={14} stroke={1.8} />
                {exportingId === 'activities' ? 'Exporting...' : 'Export CSV'}
              </button>
            </div>
          </Card>

        </div>
      </div>

      <Modal
        isOpen={showCustomReportModal}
        onClose={() => setShowCustomReportModal(false)}
        title="Create Custom Export"
        maxWidth={500}
        footer={
          <>
            <button className="btn btn-ghost" onClick={() => setShowCustomReportModal(false)} disabled={customExporting}>Cancel</button>
            <button className="btn btn-primary" onClick={handleCustomExport} disabled={customExporting}>
              {customExporting ? 'Generating CSV...' : 'Download CSV'}
            </button>
          </>
        }
      >
        <div style={{ display: 'flex', flexDirection: 'column', gap: '24px', alignItems: 'flex-start', textAlign: 'left', width: '100%' }}>
          {customError && <div style={{ color: 'red', fontSize: '13px' }}>{customError}</div>}
          
          <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', width: '100%' }}>
            <label style={{ fontWeight: 600, fontSize: '13.5px', color: 'var(--ink)' }}>Data Source</label>
            <select 
              className="form-input" 
              style={{ width: '260px' }}
              value={customSource}
              onChange={e => {
                setCustomSource(e.target.value);
                setCustomFilters({});
                setCustomFields([]); // reset fields when source changes
              }}
            >
              <option value="">Select a module...</option>
              <option value="companies">Companies</option>
              <option value="leads">Leads</option>
              <option value="opportunities">Opportunities</option>
              <option value="customers">Customers</option>
            </select>
          </div>

          {customSource && CUSTOM_CONFIGS[customSource] && (
            <>
              <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', width: '100%' }}>
                <label style={{ fontWeight: 600, fontSize: '13.5px', color: 'var(--ink)' }}>Filters</label>
                {CUSTOM_CONFIGS[customSource].filterOptions.map(fOpt => (
                  <div key={fOpt.key} style={{ display: 'flex', flexDirection: 'column', gap: '6px', marginTop: '4px' }}>
                    <label style={{ fontSize: '12.5px', color: 'var(--ink-mute)' }}>{fOpt.label}</label>
                    <select
                      className="form-input"
                      style={{ padding: '6px', fontSize: '13px', width: '260px' }}
                      value={customFilters[fOpt.key] || ''}
                      onChange={e => setCustomFilters({...customFilters, [fOpt.key]: e.target.value})}
                    >
                      <option value="">Any {fOpt.label}</option>
                      {fOpt.options.map(o => (
                        <option key={o} value={o}>{o}</option>
                      ))}
                    </select>
                  </div>
                ))}
              </div>

              <div style={{ display: 'flex', flexDirection: 'column', gap: '10px', width: '100%' }}>
                <label style={{ fontWeight: 600, fontSize: '13.5px', color: 'var(--ink)' }}>Include Fields</label>
                <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
                  {CUSTOM_CONFIGS[customSource].fieldOptions.map(field => (
                    <button
                      key={field.key}
                      onClick={() => toggleCustomField(field.key)}
                      style={{
                        padding: '5px 12px',
                        borderRadius: '16px',
                        border: '1px solid',
                        borderColor: customFields.includes(field.key) ? 'var(--brown)' : 'var(--border-soft)',
                        background: customFields.includes(field.key) ? 'var(--beige)' : 'var(--white)',
                        color: customFields.includes(field.key) ? 'var(--brown)' : 'var(--ink-mute)',
                        fontSize: '12px',
                        cursor: 'pointer',
                        transition: 'all 0.2s',
                        fontWeight: customFields.includes(field.key) ? 600 : 400
                      }}
                      type="button"
                    >
                      {field.label}
                    </button>
                  ))}
                </div>
              </div>
            </>
          )}
        </div>
      </Modal>
    </div>
  );
}
