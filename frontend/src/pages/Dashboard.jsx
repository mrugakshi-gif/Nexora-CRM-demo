import React, { useState, useEffect, useMemo, useRef } from 'react';
import api from '../api';
import Icon from '../components/common/Icon';
import KpiCard from '../components/common/KpiCard';
import { Timeline, TimelineRow } from '../components/common/Timeline';
import AiInsightRow from '../components/common/AiInsightRow';
import CompanyComparisonPanel from '../components/company-comparison/CompanyComparisonPanel';
import RevenueOverviewPanel from '../components/analytics/RevenueOverviewPanel';
import { opportunityService, companyService, activityService, analyticsService } from '../services/crmService';
import { mlService } from '../services/mlService';
import { healthService } from '../services/healthService';
import { intelligenceService } from '../services/intelligenceService';
import { BarChart, Bar, AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip as RechartsTooltip, ResponsiveContainer } from 'recharts';

const CompactHealthCard = ({ title, data, loading, error, onClick }) => {
  if (loading) return <div style={{ flex: 1, minWidth: '280px', padding: '24px', background: 'var(--white)', borderRadius: '16px', border: '1px solid var(--border)' }}><div style={{ color: 'var(--ink-mute)', fontSize: '14px' }}>Loading...</div></div>;
  if (error || !data || data.insufficient_data) return (
    <div style={{ flex: 1, minWidth: '280px', padding: '24px', background: 'var(--white)', borderRadius: '16px', border: '1px solid var(--border)' }}>
      <div style={{ fontSize: '15px', fontWeight: 700, color: 'var(--heading-primary)', marginBottom: '16px', textTransform: 'uppercase' }}>{title}</div>
      <div style={{ color: 'var(--ink-mute)', fontSize: '14px' }}>No applicable data</div>
    </div>
  );

  const m = data.metrics || {};
  
  let bg = 'var(--ivory)';
  let color = 'var(--brown)';
  if (data.status === 'Critical') { bg = '#FEE2E2'; color = 'var(--danger)'; }
  else if (data.status === 'At Risk') { bg = '#FEF3C7'; color = 'var(--warning)'; }
  else if (data.status === 'Healthy' || data.status === 'Excellent') { bg = 'rgba(110,138,94,0.18)'; color = 'var(--success)'; }

  return (
    <div style={{ flex: 1, minWidth: '280px', padding: '24px', background: 'var(--white)', borderRadius: '16px', border: '1px solid var(--border)', display: 'flex', flexDirection: 'column' }}>
      <div style={{ fontSize: '15px', fontWeight: 700, color: 'var(--heading-primary)', marginBottom: '16px', textTransform: 'uppercase' }}>{title}</div>
      
      <div style={{ display: 'flex', alignItems: 'center', gap: '12px', marginBottom: '16px' }}>
        <div style={{ fontSize: '32px', fontWeight: 800, color: 'var(--ink)', lineHeight: 1 }}>{Math.round(data.score)}</div>
        <div style={{ padding: '4px 8px', borderRadius: '6px', fontSize: '12px', fontWeight: 700, background: bg, color: color, textTransform: 'uppercase' }}>{data.status}</div>
      </div>
      
      <div style={{ display: 'flex', gap: '16px', marginBottom: '20px', paddingBottom: '16px', borderBottom: '1px solid var(--border-soft)' }}>
        <div style={{ display: 'flex', flexDirection: 'column', gap: '2px' }}>
          <span style={{ fontSize: '14px', fontWeight: 700, color: 'var(--heading-primary)' }}>{m.healthy || 0}</span>
          <span style={{ fontSize: '10px', fontWeight: 600, color: 'var(--ink-mute)', textTransform: 'uppercase' }}>Healthy</span>
        </div>
        <div style={{ width: '1px', background: 'var(--border-soft)' }} />
        <div style={{ display: 'flex', flexDirection: 'column', gap: '2px' }}>
          <span style={{ fontSize: '14px', fontWeight: 700, color: 'var(--heading-primary)' }}>{m.at_risk || 0}</span>
          <span style={{ fontSize: '10px', fontWeight: 600, color: 'var(--ink-mute)', textTransform: 'uppercase' }}>At Risk</span>
        </div>
        <div style={{ width: '1px', background: 'var(--border-soft)' }} />
        <div style={{ display: 'flex', flexDirection: 'column', gap: '2px' }}>
          <span style={{ fontSize: '14px', fontWeight: 700, color: 'var(--heading-primary)' }}>{m.critical || 0}</span>
          <span style={{ fontSize: '10px', fontWeight: 600, color: 'var(--ink-mute)', textTransform: 'uppercase' }}>Critical</span>
        </div>
      </div>

      <button onClick={onClick} style={{ marginTop: 'auto', background: 'transparent', border: 'none', color: 'var(--accent-primary)', fontSize: '13px', fontWeight: 600, display: 'flex', alignItems: 'center', gap: '4px', cursor: 'pointer', padding: 0 }}>
        View Details <Icon name="arrow-right" size={14} />
      </button>
    </div>
  );
};

const CompactNBACard = ({ nba, onActionClick }) => {
  const priorityColor = nba.priority === 'High' ? 'var(--danger)' : nba.priority === 'Medium' ? 'var(--warning)' : 'var(--success)';
  const priorityBg = nba.priority === 'High' ? '#FEE2E2' : nba.priority === 'Medium' ? '#FEF3C7' : 'rgba(110,138,94,0.18)';

  const handleClick = () => {
    if (onActionClick) {
      onActionClick(nba);
    } else {
      if (nba.customer_id) {
        window.location.href = `/customers/${nba.customer_id}`;
      } else if (nba.company_id) {
        window.location.href = `/companies/${nba.company_id}`;
      } else if (nba.opportunity_id) {
        window.location.href = `/opportunities/${nba.opportunity_id}`;
      }
    }
  };

  return (
    <div 
      onClick={handleClick}
      style={{ padding: '16px', marginBottom: '12px', borderRadius: '12px', background: 'var(--white)', border: '1px solid var(--border)', display: 'flex', gap: '16px', alignItems: 'flex-start', cursor: 'pointer', transition: 'all 0.2s ease' }}
      onMouseEnter={(e) => { e.currentTarget.style.borderColor = 'var(--brown)'; e.currentTarget.style.background = 'var(--bg-light)'; }}
      onMouseLeave={(e) => { e.currentTarget.style.borderColor = 'var(--border)'; e.currentTarget.style.background = 'var(--white)'; }}
    >
      <div style={{ width: '40px', height: '40px', borderRadius: '8px', background: 'var(--ivory)', display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0 }}>
        <Icon name="zap" color="var(--brown)" size={18} stroke={2} />
      </div>
      <div style={{ flex: 1, display: 'flex', flexDirection: 'column', gap: '4px' }}>
        <div style={{ fontSize: '14px', fontWeight: 800, color: 'var(--ink)' }}>{nba.action_title || nba.action_type || nba.action || 'Recommended Action'}</div>
        <div style={{ fontSize: '13px', color: 'var(--ink-soft)' }}>
          <span style={{ fontWeight: 600, color: 'var(--heading-primary)' }}>{nba.entity_name}</span> - {nba.reasons ? nba.reasons.join(', ') : nba.reasoning}
        </div>
      </div>
      <div style={{ padding: '4px 8px', borderRadius: '6px', fontSize: '11px', fontWeight: 700, background: priorityBg, color: priorityColor, textTransform: 'uppercase', flexShrink: 0 }}>
        {nba.priority}
      </div>
    </div>
  );
};

const formatCurrency = (val) => new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR', maximumFractionDigits: 0 }).format(val);

const RecommendationCard = ({ icon, color, bgColor, borderColor, title, company, description, badgeLabel, badgeValue, buttonLabel, onClick, isLast }) => (
  <div style={{ padding: '16px 20px', marginBottom: isLast ? '0' : '12px', borderRadius: '12px', background: bgColor || 'var(--white)', border: `1px solid ${borderColor || 'var(--border)'}`, display: 'flex', gap: '16px', alignItems: 'center' }}>
    <div style={{ width: '48px', height: '48px', borderRadius: '12px', background: 'var(--white)', display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0, border: `1px solid ${borderColor || 'var(--border)'}` }}>
      <Icon name={icon} color={color} size={22} stroke={2} />
    </div>
    <div style={{ flex: 1, display: 'flex', flexDirection: 'column', gap: '4px' }}>
      <div style={{ fontSize: '15px', fontWeight: 800, color: 'var(--ink)' }}>{title}</div>
      <div style={{ fontSize: '13px', color: 'var(--ink-soft)', lineHeight: 1.4 }}>
        <span style={{ fontWeight: 600, color: 'var(--heading-primary)' }}>{company}</span> {description}
      </div>
      <div style={{ display: 'flex', gap: '12px', alignItems: 'center', marginTop: '4px' }}>
        <span style={{ fontSize: '11px', fontWeight: 700, padding: '2px 8px', background: 'var(--white)', color: color, borderRadius: '4px', border: `1px solid ${borderColor || 'var(--border)'}` }}>{badgeLabel}</span>
        <span style={{ fontSize: '12px', color: 'var(--ink-mute)', fontWeight: 600 }}>{badgeValue}</span>
      </div>
    </div>
    <button onClick={onClick} style={{ background: 'var(--accent-primary)', color: 'white', border: 'none', borderRadius: '8px', padding: '8px 16px', fontSize: '12px', fontWeight: 600, cursor: 'pointer', display: 'flex', alignItems: 'center', gap: '6px', whiteSpace: 'nowrap', flexShrink: 0 }}>
      {buttonLabel} <Icon name="arrow-right" size={14} stroke={2} />
    </button>
  </div>
);

const DashboardTimelineRow = ({ icon, title, companyName, ownerName, timeStr, dateStr, status, isLast }) => (
  <div style={{ display: 'flex', gap: '16px', position: 'relative', paddingBottom: '16px' }}>
    {!isLast && <div style={{ position: 'absolute', left: '19px', top: '40px', bottom: '-4px', width: '2px', background: 'var(--border-soft)' }} />}
    <div style={{ width: '40px', height: '40px', borderRadius: '50%', background: 'var(--accent-primary)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 1, flexShrink: 0, border: '3px solid var(--white)' }}>
      <Icon name={icon} size={18} color="var(--white)" stroke={2} />
    </div>
    <div style={{ flex: 1, display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', paddingTop: '2px' }}>
      <div style={{ paddingRight: '24px' }}>
        <div style={{ fontSize: '14px', fontWeight: 800, color: 'var(--ink)' }}>{title}</div>
        <div style={{ fontSize: '13px', fontWeight: 700, color: 'var(--heading-primary)', marginTop: '2px' }}>{companyName}</div>
        {ownerName && (
          <div style={{ display: 'flex', alignItems: 'center', gap: '6px', marginTop: '6px', color: 'var(--ink-mute)', fontSize: '12px', fontWeight: 500 }}>
            <Icon name="user" size={12} stroke={2} />
            {ownerName}
          </div>
        )}
      </div>
      <div style={{ display: 'flex', alignItems: 'flex-start', gap: '16px', textAlign: 'right', flexShrink: 0 }}>
        <div>
          <div style={{ fontSize: '12px', color: 'var(--ink-mute)', fontWeight: 500 }}>{dateStr}, {timeStr}</div>
          <div style={{ marginTop: '6px', display: 'flex', justifyContent: 'flex-end' }}>
            <span style={{ fontSize: '11px', fontWeight: 700, padding: '2px 8px', background: status === 'Completed' ? 'rgba(34, 197, 94, 0.1)' : 'rgba(245, 158, 11, 0.1)', color: status === 'Completed' ? '#15803d' : '#b45309', borderRadius: '12px' }}>
              {status}
            </span>
          </div>
        </div>
        <button style={{ background: 'transparent', border: 'none', cursor: 'pointer', color: 'var(--ink-mute)', padding: '2px', marginTop: '-2px' }}>
          <Icon name="more-vertical" size={14} stroke={2} />
        </button>
      </div>
    </div>
  </div>
);

const TaskActionModal = ({ action, onClose, onSubmit, submitting }) => {
  if (!action) return null;
  return (
    <div style={{ position: 'fixed', top: 0, left: 0, right: 0, bottom: 0, background: 'rgba(0,0,0,0.5)', zIndex: 1000, display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
      <div style={{ background: 'var(--white)', padding: '24px', borderRadius: '12px', width: '400px', maxWidth: '90%' }}>
        <h3 style={{ margin: '0 0 16px 0', fontSize: '18px', color: 'var(--ink)' }}>[AI Recommendation]</h3>
        <div style={{ marginBottom: '12px', fontSize: '14px', color: 'var(--ink)' }}>
          <strong>Customer/Company:</strong> {action.entityName}
        </div>
        <div style={{ marginBottom: '12px', fontSize: '14px', color: 'var(--ink)' }}>
          <strong>Reason:</strong> {action.reason}
        </div>
        <div style={{ marginBottom: '24px', fontSize: '14px', color: 'var(--ink)' }}>
          <strong>Recommended Action:</strong> Follow up with customer
        </div>
        <div style={{ display: 'flex', justifyContent: 'flex-end', gap: '12px' }}>
          <button onClick={onClose} disabled={submitting} style={{ padding: '8px 16px', background: 'var(--bg-light)', border: '1px solid var(--border)', borderRadius: '6px', cursor: 'pointer', fontSize: '14px', fontWeight: 600 }}>Cancel</button>
          <button onClick={() => onSubmit(action)} disabled={submitting} style={{ padding: '8px 16px', background: 'var(--brown)', color: 'white', border: 'none', borderRadius: '6px', cursor: 'pointer', fontSize: '14px', fontWeight: 600 }}>
            {submitting ? 'Creating...' : 'Create Task'}
          </button>
        </div>
      </div>
    </div>
  );
};

export default function Dashboard() {
  const [kpis, setKpis] = useState(null);
  const [pipelineStages, setPipelineStages] = useState([]);
  const [topCustomers, setTopCustomers] = useState([]);
  const [topProducts, setTopProducts] = useState([]);
  
  const [opportunities, setOpportunities] = useState([]);
  const [companies, setCompanies] = useState([]);
  const [totalCompanies, setTotalCompanies] = useState(0);
  const [activities, setActivities] = useState([]);
  
  const [loading, setLoading] = useState(true);
  const [forecast, setForecast] = useState(null);
  const [topLeads, setTopLeads] = useState([]);
  const [riskCustomers, setRiskCustomers] = useState([]);
  const [forecastLoading, setForecastLoading] = useState(true);
  const [error, setError] = useState(false);
  const [monthlyRevenue, setMonthlyRevenue] = useState([]);

  const [accountHealth, setAccountHealth] = useState({ data: null, loading: true, error: false });
  const [companyHealth, setCompanyHealth] = useState({ data: null, loading: true, error: false });
  const [productHealth, setProductHealth] = useState({ data: null, loading: true, error: false });
  const [intelligence, setIntelligence] = useState({ data: { actions: [] }, loading: true, error: false });

  // Date Filtering State
  const [dateRangeStr, setDateRangeStr] = useState('This Year');
  const [isDateDropdownOpen, setIsDateDropdownOpen] = useState(false);
  const dropdownRef = useRef(null);

  // Layout State
  const defaultLayout = { kpis: true, pipeline: true, comparison: true, activity: true, topLists: true };
  const [layout, setLayout] = useState(() => {
    try {
      const saved = localStorage.getItem('crm_dashboard_layout');
      if (saved) {
        const parsed = JSON.parse(saved);
        if (parsed && typeof parsed === 'object') {
          return { ...defaultLayout, ...parsed };
        }
      }
    } catch (e) {
      console.warn("Failed to parse crm_dashboard_layout from localStorage", e);
    }
    return defaultLayout;
  });
  const [isCustomizeOpen, setIsCustomizeOpen] = useState(false);
  const customizeRef = useRef(null);

  const [activeAction, setActiveAction] = useState(null);
  const [submittingAction, setSubmittingAction] = useState(false);

  const handleActionSubmit = async (action) => {
    setSubmittingAction(true);
    try {
      const payload = {
        action_type: action.type,
        reason: action.reason,
        customer_id: action.customer_id,
        opportunity_id: action.opportunity_id,
        company_id: action.company_id,
        support_case_id: action.support_case_id,
        lead_id: action.lead_id,
        trigger_email: false
      };
      
      const res = await api.post('/api/automation/create-task', payload);
      
      const responseData = res.data;
      setActiveAction(null);
      alert(responseData.message === 'Duplicate/already-created' ? 'Task already exists.' : 'Task created successfully!');
      window.location.reload();
    } catch (e) {
      console.error(e);
      alert(e.response?.data?.detail || e.response?.data?.message || e.message || 'Error creating task.');
    } finally {
      setSubmittingAction(false);
    }
  };

  const handleNBAClick = (nba) => {
    let actionType = nba.action_title || nba.action_type || nba.action;
    let type = 'Follow-up';
    if (actionType.includes('Churn') || actionType.toLowerCase().includes('retention')) type = 'High Churn Risk';
    else if (actionType.includes('Close') || actionType.includes('Opportunity')) type = 'Opportunity Closing Soon';
    else if (actionType.includes('Support')) type = 'High-Priority Support';
    else if (actionType.includes('Lead')) type = 'New High-Value Lead';
    
    setActiveAction({
      type: type,
      entityName: nba.entity_name,
      reason: nba.reasons ? nba.reasons.join(', ') : nba.reasoning,
      customer_id: nba.customer_id,
      opportunity_id: nba.opportunity_id,
      company_id: nba.company_id,
      support_case_id: nba.case_id,
      lead_id: nba.lead_id
    });
  };

  
  const resetLayout = () => {
    const defaultLayout = { kpis: true, pipeline: true, comparison: true, activity: true, topLists: true };
    setLayout(defaultLayout);
    localStorage.setItem('crm_dashboard_layout', JSON.stringify(defaultLayout));
  };

  const toggleLayout = (key) => {
    const newLayout = { ...layout, [key]: !layout[key] };
    setLayout(newLayout);
    localStorage.setItem('crm_dashboard_layout', JSON.stringify(newLayout));
  };

  const dateParams = useMemo(() => {
    const now = new Date();
    const year = now.getFullYear();
    const month = now.getMonth();
    let start_date = null;
    let end_date = null;
    
    const pad = (n) => String(n).padStart(2, '0');
    const toDateStr = (y, m, d) => `${y}-${pad(m + 1)}-${pad(d)}`;

    if (dateRangeStr === 'This Month') {
      const lastDay = new Date(year, month + 1, 0).getDate();
      start_date = toDateStr(year, month, 1);
      end_date = toDateStr(year, month, lastDay);
    } else if (dateRangeStr === 'Last Month') {
      const prevMonthDate = new Date(year, month - 1, 1);
      const pYear = prevMonthDate.getFullYear();
      const pMonth = prevMonthDate.getMonth();
      const lastDay = new Date(year, month, 0).getDate();
      start_date = toDateStr(pYear, pMonth, 1);
      end_date = toDateStr(pYear, pMonth, lastDay);
    } else if (dateRangeStr === 'This Quarter') {
      const q = Math.floor(month / 3);
      const startMonth = q * 3;
      const endMonth = q * 3 + 2;
      const lastDay = new Date(year, endMonth + 1, 0).getDate();
      start_date = toDateStr(year, startMonth, 1);
      end_date = toDateStr(year, endMonth, lastDay);
    } else if (dateRangeStr === 'This Year') {
      start_date = toDateStr(year, 0, 1);
      end_date = toDateStr(year, 11, 31);
    }
    return { start_date, end_date };
  }, [dateRangeStr]);

  useEffect(() => {
    function handleClickOutside(event) {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target)) {
        setIsDateDropdownOpen(false);
      }
      if (customizeRef.current && !customizeRef.current.contains(event.target)) {
        setIsCustomizeOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  useEffect(() => {
    let periodStr = 'all_time';
    if (dateRangeStr === 'This Month') periodStr = 'this_month';
    else if (dateRangeStr === 'Last Month') periodStr = 'last_month';
    else if (dateRangeStr === 'This Quarter') periodStr = 'this_quarter';
    else if (dateRangeStr === 'This Year') periodStr = 'this_year';

    setAccountHealth(prev => ({ ...prev, loading: true, error: false }));
    healthService.getAccountHealthSummary(periodStr)
      .then(res => setAccountHealth({ data: {
          score: res.average_score,
          status: res.status,
          insufficient_data: res.insufficient_data,
          risk_entities: res.risk_entities,
          metrics: {
            healthy: res.healthy_count,
            at_risk: res.at_risk_count,
            critical: res.critical_count
          }
      }, loading: false, error: false }))
      .catch(err => setAccountHealth({ data: null, loading: false, error: true }));

    setCompanyHealth(prev => ({ ...prev, loading: true, error: false }));
    healthService.getCompanyHealthSummary(periodStr)
      .then(res => setCompanyHealth({ data: {
          score: res.average_score,
          status: res.status,
          insufficient_data: res.insufficient_data,
          risk_entities: res.risk_entities,
          metrics: {
            healthy: res.healthy_count,
            at_risk: res.at_risk_count,
            critical: res.critical_count
          }
      }, loading: false, error: false }))
      .catch(err => setCompanyHealth({ data: null, loading: false, error: true }));

    setProductHealth(prev => ({ ...prev, loading: true, error: false }));
    healthService.getProductHealthSummary(periodStr)
      .then(res => setProductHealth({ data: {
          score: res.average_score,
          status: res.status,
          insufficient_data: res.insufficient_data,
          risk_entities: res.risk_entities,
          metrics: {
            healthy: res.healthy_count,
            at_risk: res.at_risk_count,
            critical: res.critical_count
          }
      }, loading: false, error: false }))
      .catch(err => setProductHealth({ data: null, loading: false, error: true }));

    setIntelligence(prev => ({ ...prev, loading: true, error: false }));
    intelligenceService.getRetentionNextBestActions(periodStr)
      .then(res => setIntelligence({ data: res.data || { actions: [] }, loading: false, error: false }))
      .catch(err => setIntelligence({ data: { actions: [] }, loading: false, error: true }));
  }, [dateRangeStr]);

  useEffect(() => {
    async function fetchData() {
      setLoading(true);
      try {
        const params = {};
        if (dateParams.start_date) params.start_date = dateParams.start_date;
        if (dateParams.end_date) params.end_date = dateParams.end_date;

        // Fetch data sequentially to avoid connection limits, proxy deadlocks, and SQLite locks
        // And catch errors individually so the dashboard gracefully degrades if one endpoint fails
        
        let kpiData = {};
        let pipeData = [];
        let custData = [];
        let prodData = [];
        let oppsData = [];
        let compData = [];
        let totalCompsCount = 0;
        let actData = [];
        let revData = [];
        let leads = [];
        let risks = [];

        try { const res = await analyticsService.getDashboardKpis(params); kpiData = res.data; } catch (e) { console.error("Kpis error", e); }
        try { const res = await analyticsService.getOpportunityPipeline(params); pipeData = res.data; } catch (e) { console.error("Pipeline error", e); }
        try { const res = await analyticsService.getTopCustomers(params); custData = res.data; } catch (e) { console.error("Top customers error", e); }
        try { const res = await analyticsService.getTopProducts(params); prodData = res.data; } catch (e) { console.error("Top products error", e); }
        try { const res = await opportunityService.getOpportunities({ limit: 500, page_size: 200 }); oppsData = res.data.items || res.data || []; } catch (e) { console.error("Opps error", e); }
        try { 
          const res = await companyService.getCompanies({ limit: 500, page_size: 200 }); 
          compData = res.data.items || res.data || []; 
          totalCompsCount = res.data.total || compData.length;
        } catch (e) { console.error("Companies error", e); }
        try { 
          const res = await activityService.getActivities({ limit: 500, page_size: 200, sort_by: 'activity_date', sort_order: 'desc' }); 
          actData = res.data.items || res.data || []; 
        } catch (e) { console.error("Activities error", e); }
        try { const res = await analyticsService.getRevenueByMonth({}); revData = res.data || []; } catch (e) { console.error("Revenue error", e); }
        try { const res = await mlService.getAggregateLeads(); leads = res.data?.top_leads || []; } catch (e) { console.error("Leads error", e); }
        try { const res = await mlService.getAggregateCustomerRisk(); risks = res.data?.top_at_risk_customers || []; } catch (e) { console.error("Risks error", e); }
        
        setKpis(kpiData);
        setPipelineStages(pipeData);
        setTopCustomers(custData);
        setTopProducts(prodData);
        
        if (params.start_date && params.end_date) {
          const startStr = params.start_date;
          const endStr = params.end_date;
          
          // 1. Filter Activities
          actData = actData.filter(a => {
            const dStr = (a.activity_date || a.due_date || a.created_at || '').substring(0, 10);
            return dStr >= startStr && dStr <= endStr;
          });
          
          // 2. Filter AI Recommendations (Leads, Risks) to only active companies
          const activeCompanies = new Set();
          
          // Add companies from filtered activities
          actData.forEach(a => {
            if (a.resolved_company_name) activeCompanies.add(a.resolved_company_name);
            else if (a.company_id) {
              const c = compData.find(c => c.company_id === a.company_id);
              if (c) activeCompanies.add(c.company_name);
            } else if (a.opportunity_id) {
              const o = oppsData.find(o => o.opportunity_id === a.opportunity_id);
              if (o && o.company_name) activeCompanies.add(o.company_name);
            }
          });
          
          // Add companies from opportunities active in period
          oppsData.forEach(o => {
            const dStr = (o.expected_close_date || o.actual_close_date || o.created_at || '').substring(0, 10);
            if (dStr >= startStr && dStr <= endStr && o.company_name) {
              activeCompanies.add(o.company_name);
            }
          });
          
          // Add companies created/updated in period
          compData.forEach(c => {
            const dStr = (c.updated_at || c.created_at || '').substring(0, 10);
            if (dStr >= startStr && dStr <= endStr) {
              activeCompanies.add(c.company_name);
            }
          });
          
          // Apply filter to ML records if there are active companies in this period
          if (activeCompanies.size > 0) {
            const filteredLeads = leads.filter(l => activeCompanies.has(l.company_name));
            const filteredRisks = risks.filter(r => activeCompanies.has(r.company_name));
            if (filteredLeads.length > 0) leads = filteredLeads;
            if (filteredRisks.length > 0) risks = filteredRisks;
          }
        }

        setOpportunities(oppsData);
        setCompanies(compData);
        setTotalCompanies(totalCompsCount);
        setActivities(actData.slice(0, 5));
        setMonthlyRevenue(revData);
        setTopLeads(leads);
        setRiskCustomers(risks);
        setError(false);
      } catch (err) {
        console.error("Dashboard error", err);
        setError(true);
      } finally {
        setLoading(false);
      }
    }
    fetchData();
  }, [dateParams]);

  useEffect(() => {
    async function fetchForecast() {
      try {
        const res = await mlService.getSalesForecast();
        setForecast(res.data);
      } catch (err) {
        console.error("Failed to load forecast:", err);
      } finally {
        setForecastLoading(false);
      }
    }
    fetchForecast();
  }, []);

  const handleDateSelect = (dr) => {
    setDateRangeStr(dr);
    setIsDateDropdownOpen(false);
  };

  return (
    <div className="page">
      <TaskActionModal 
        action={activeAction} 
        onClose={() => setActiveAction(null)} 
        onSubmit={handleActionSubmit} 
        submitting={submittingAction} 
      />
      <div className="page-header" style={{ paddingBottom: '16px' }}>
        <div>
          <h1 className="page-title">Sales Intelligence Dashboard</h1>
          <p className="page-desc" style={{ color: 'var(--ink-mute)' }}>Monitor your sales pipeline, customers and business performance.</p>
        </div>
        <div className="page-actions">
          <div className="chip" style={{ position: 'relative', cursor: 'pointer', background: 'var(--bg-light)', border: '1px solid var(--border)' }} ref={dropdownRef}>
            <div onClick={() => setIsDateDropdownOpen(!isDateDropdownOpen)} style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
              <Icon name="calendar" size={15} color="var(--ink-soft)" stroke={1.8} /> <span style={{ color: 'var(--ink)' }}>{dateRangeStr}</span>
              <Icon name="chevrondown" size={13} color="var(--ink-soft)" stroke={2} />
            </div>
            {isDateDropdownOpen && (
              <div style={{
                position: 'absolute', top: '100%', left: 0, marginTop: '8px',
                background: 'var(--white)', border: '1px solid var(--border)', borderRadius: '6px',
                boxShadow: '0 4px 12px rgba(0,0,0,0.5)', zIndex: 100, minWidth: '140px', overflow: 'hidden'
              }}>
                {['This Month', 'Last Month', 'This Quarter', 'This Year', 'All Time'].map(dr => (
                  <div key={dr} onClick={() => handleDateSelect(dr)} style={{
                    padding: '8px 12px', fontSize: '13px', color: dateRangeStr === dr ? 'var(--brown)' : 'var(--ink)',
                    cursor: 'pointer', background: dateRangeStr === dr ? 'var(--bg-light)' : 'transparent'
                  }}>
                    {dr}
                  </div>
                ))}
              </div>
            )}
          </div>
          <div style={{ position: 'relative' }} ref={customizeRef}>
            <button className="btn btn-secondary" onClick={() => setIsCustomizeOpen(!isCustomizeOpen)} style={{ background: 'var(--bg-light)', borderColor: 'var(--border)', color: 'var(--ink)' }}>
              <Icon name="sliders" size={15} color="var(--brown)" stroke={2} /> Customize
            </button>
            {isCustomizeOpen && (
              <div style={{
                position: 'absolute', top: '100%', right: 0, marginTop: '8px',
                background: 'var(--white)', border: '1px solid var(--border)', borderRadius: '6px',
                boxShadow: '0 4px 12px rgba(0,0,0,0.5)', zIndex: 100, width: '200px', padding: '12px'
              }}>
                <div style={{ fontSize: '12px', fontWeight: 600, color: 'var(--ink-mute)', marginBottom: '8px', textTransform: 'uppercase' }}>Visible Sections</div>
                {[
                  { key: 'kpis', label: 'KPI Cards' },
                  { key: 'pipeline', label: 'Sales Pipeline' },
                  { key: 'comparison', label: 'Company Comparison' },
                  { key: 'activity', label: 'Recent Activity' },
                  { key: 'topLists', label: 'Top Customers' },
                ].map(opt => (
                  <label key={opt.key} style={{ display: 'flex', alignItems: 'center', gap: '8px', padding: '6px 0', cursor: 'pointer', fontSize: '13px', color: 'var(--ink)' }}>
                    <input type="checkbox" checked={layout[opt.key]} onChange={() => toggleLayout(opt.key)} style={{ cursor: 'pointer' }} />
                    {opt.label}
                  </label>
                ))}

                <div style={{ marginTop: '12px', borderTop: '1px solid var(--border)', paddingTop: '12px', textAlign: 'center' }}>
                  <button onClick={resetLayout} style={{ background: 'none', border: 'none', color: 'var(--brown)', fontSize: '12px', cursor: 'pointer', fontWeight: 600 }}>Reset to Default</button>
                </div>
              </div>
            )}
          </div>
        </div>
      </div>

      {layout.kpis && (
        <div className="kpi-grid">
          <KpiCard label="Open Pipeline" value={kpis ? formatCurrency(kpis.pipeline_value_inr || 0) : '0'} icon="bar-chart" />
          <KpiCard label="Won Revenue" value={kpis ? formatCurrency(kpis.won_revenue_inr || 0) : '0'} icon="checkcircle" />
          <KpiCard 
            label="Total Companies" 
            value={totalCompanies ? totalCompanies.toLocaleString() : (kpis && kpis.total_companies !== undefined ? kpis.total_companies.toLocaleString() : (companies.length || '0'))} 
            icon="building-2" 
          />
          <KpiCard label="Total Deals" value={kpis ? kpis.total_opportunities : '0'} icon="target" />
          <KpiCard label="Conversion Rate" value={kpis ? (kpis.lead_conversion_rate_pct || 0) + '%' : '0%'} icon="zap" />
        </div>
      )}

      <div className="dashboard-content">
        
        {/* ROW 1 */}
        <div className="dashboard-card-pair">
          {layout.topLists ? (
            <div className="card" style={{ display: 'flex', flexDirection: 'column' }}>
              <div style={{ padding: '20px 24px 12px', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <h2 className="section-title">Top Companies</h2>
                <a href="/customers" style={{ color: 'var(--accent-primary)', fontSize: '13px', fontWeight: 600, textDecoration: 'none' }}>View All</a>
              </div>
              {loading ? (
                <div style={{ padding: '40px 0', textAlign: 'center', color: 'var(--ink-mute)' }}>Loading...</div>
              ) : topCustomers.length === 0 ? (
                <div style={{ padding: '40px 0', textAlign: 'center', color: 'var(--ink-mute)' }}>No customer revenue in this period.</div>
              ) : (
                <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', padding: '0 18px 12px', overflowY: 'auto' }}>
                  {topCustomers.map(c => (
                    <div 
                      key={c.customer_id} 
                      onClick={() => window.location.href = `/customers/${c.customer_id}`}
                      style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '12px', border: '1px solid var(--border-soft)', borderRadius: '8px', cursor: 'pointer', transition: 'all 0.2s ease', background: 'var(--bg-light)' }}
                      onMouseEnter={(e) => { e.currentTarget.style.borderColor = 'var(--brown)'; e.currentTarget.style.background = 'var(--beige)'; }}
                      onMouseLeave={(e) => { e.currentTarget.style.borderColor = 'var(--border-soft)'; e.currentTarget.style.background = 'var(--bg-light)'; }}
                    >
                      <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                        <div style={{ width: '36px', height: '36px', borderRadius: '50%', background: 'var(--accent-tint)', color: 'var(--accent-primary)', display: 'flex', alignItems: 'center', justifyContent: 'center', fontWeight: 600, fontSize: '14px' }}>
                          {(c.company_name || c.customer_id || 'CO').substring(0, 2).toUpperCase()}
                        </div>
                        <div>
                          <div style={{ fontSize: '14px', fontWeight: 700, color: 'var(--heading-primary)' }}>{c.company_name || c.customer_id || 'Unknown Company'}</div>
                          <div style={{ fontSize: '12px', color: 'var(--ink-mute)', marginTop: '2px' }}>{c.customer_id}</div>
                        </div>
                      </div>
                      <span style={{ fontSize: '14px', fontWeight: 700, color: 'var(--ink)' }}>{formatCurrency(c.revenue_inr)}</span>
                    </div>
                  ))}
                </div>
              )}
            </div>
          ) : <div />}

          {layout.pipeline ? (
            <div className="card" style={{ display: 'flex', flexDirection: 'column' }}>
              <h2 className="section-title" style={{ padding: '20px 24px 0' }}>Pipeline by Stage</h2>
              <div style={{ flex: 1, minHeight: '300px', padding: '10px 0 20px 0' }}>
                {loading ? (
                  <div style={{ height: '100%', display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'var(--ink-mute)' }}>Loading...</div>
                ) : pipelineStages.length === 0 ? (
                  <div style={{ height: '100%', display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'var(--ink-mute)' }}>No active pipeline data.</div>
                ) : (
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={pipelineStages} margin={{ top: 20, right: 30, left: 20, bottom: 20 }}>
                      <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="var(--border-soft)" />
                      <XAxis dataKey="stage" tick={{ fill: 'var(--ink-mute)', fontSize: 12 }} axisLine={false} tickLine={false} />
                      <YAxis tickFormatter={(val) => `₹${(val/100000).toFixed(1)}L`} tick={{ fill: 'var(--ink-mute)', fontSize: 12 }} axisLine={false} tickLine={false} />
                      <RechartsTooltip 
                        formatter={(value) => formatCurrency(value)}
                        contentStyle={{ borderRadius: '8px', backgroundColor: 'var(--beige)', borderColor: 'var(--border)', color: 'var(--ink)', boxShadow: '0 4px 12px rgba(0,0,0,0.1)' }}
                        itemStyle={{ color: 'var(--ink)' }}
                        cursor={{ fill: 'transparent' }}
                      />
                      <Bar dataKey="total_value_inr" fill="var(--brown)" radius={[4, 4, 0, 0]} />
                    </BarChart>
                  </ResponsiveContainer>
                )}
              </div>
            </div>
          ) : <div />}
        </div>

        {/* ROW 2 - Company Comparison */}
        {layout.comparison ? (
          <div style={{ width: '100%', marginBottom: '36px' }}>
            <CompanyComparisonPanel companies={companies} topCustomers={topCustomers} />
          </div>
        ) : null}

        {/* ROW 2.5 - Revenue Overview */}
        <div style={{ width: '100%', marginBottom: '36px' }}>
          <RevenueOverviewPanel data={monthlyRevenue} loading={loading} error={error} />
        </div>

        {/* ROW 2.75 - Business Health */}
        <div style={{ width: '100%', marginBottom: '36px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', marginBottom: '16px', padding: '0 4px' }}>
            <Icon name="activity" size={18} color="var(--accent-primary)" stroke={2} />
            <h2 className="section-title" style={{ fontSize: '18px', fontWeight: 800, color: 'var(--heading-primary)' }}>Business Health</h2>
          </div>
          <div style={{ display: 'flex', gap: '24px', flexWrap: 'wrap' }}>
            <CompactHealthCard 
              title="Customer Health" 
              data={accountHealth.data} 
              loading={accountHealth.loading} 
              error={accountHealth.error} 
              onClick={() => {
                const critical = accountHealth.data?.risk_entities?.[0];
                if (critical) window.location.href = `/customers/${critical.id}`;
                else window.location.href = '/analytics';
              }} 
            />
            <CompactHealthCard 
              title="Company Health" 
              data={companyHealth.data} 
              loading={companyHealth.loading} 
              error={companyHealth.error} 
              onClick={() => {
                const critical = companyHealth.data?.risk_entities?.[0];
                if (critical) window.location.href = `/companies/${critical.id}`;
                else window.location.href = '/analytics';
              }} 
            />
            <CompactHealthCard 
              title="Product Health" 
              data={productHealth.data} 
              loading={productHealth.loading} 
              error={productHealth.error} 
              onClick={() => {
                // Products list page
                window.location.href = '/products';
              }} 
            />
          </div>
        </div>

        {/* ROW 2.8 - Next Best Actions */}
        <div style={{ width: '100%', marginBottom: '36px' }}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: '16px', padding: '0 4px' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
              <Icon name="zap" size={18} color="var(--brown)" stroke={2} />
              <h2 className="section-title" style={{ fontSize: '18px', fontWeight: 800, color: 'var(--ink)' }}>Next Best Actions</h2>
            </div>
            <button style={{ background: 'var(--bg-light)', border: '1px solid var(--border)', borderRadius: '6px', padding: '6px 12px', fontSize: '12px', fontWeight: 600, color: 'var(--brown)', display: 'flex', alignItems: 'center', gap: '6px', cursor: 'pointer' }} onClick={() => window.location.href='/analytics'}>
              View All Next Best Actions <Icon name="arrow-right" size={12} stroke={2} />
            </button>
          </div>
          <div>
            {intelligence.loading ? (
               <div style={{ padding: '40px 0', textAlign: 'center', color: 'var(--ink-mute)', background: 'var(--white)', borderRadius: '12px', border: '1px solid var(--border)' }}>Loading actions...</div>
            ) : intelligence.error || !intelligence.data?.actions || intelligence.data.actions.length === 0 ? (
               <div style={{ padding: '40px 0', textAlign: 'center', color: 'var(--ink-mute)', background: 'var(--white)', borderRadius: '12px', border: '1px solid var(--border)' }}>No immediate actions</div>
            ) : (
              intelligence.data.actions.slice(0, 3).map((nba, idx) => (
                <CompactNBACard key={idx} nba={nba} onActionClick={handleNBAClick} />
              ))
            )}
          </div>
        </div>

        {/* ROW 3 */}
        <div className="dashboard-card-pair" style={{ alignItems: 'flex-start' }}>
          <div className="card" style={{ display: 'flex', flexDirection: 'column', background: 'var(--white)' }}>
            <div style={{ padding: '24px 24px 16px', display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', borderBottom: '1px solid var(--border-soft)' }}>
              <div style={{ display: 'flex', gap: '12px' }}>
                <Icon name="sparkles" size={24} color="var(--brown)" stroke={2} style={{ marginTop: '2px' }} />
                <div>
                  <h2 className="section-title" style={{ fontSize: '18px', fontWeight: 800, marginBottom: '4px', color: 'var(--ink)' }}>AI Recommended Actions</h2>
                  <div style={{ fontSize: '13px', color: 'var(--ink-mute)' }}>Personalized insights to help you close deals, retain customers, and grow revenue.</div>
                </div>
              </div>
            </div>
            {loading && forecastLoading ? (
               <div style={{ padding: '40px 0', textAlign: 'center', color: 'var(--ink-mute)' }}>Loading insights...</div>
            ) : (!forecast && topLeads.length === 0 && riskCustomers.length === 0) ? (
              <div style={{ padding: '40px 0', textAlign: 'center', color: 'var(--ink-mute)' }}>No active AI recommendations.</div>
            ) : (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '12px', padding: '24px' }}>
                {(() => {
                  const recs = [];
                  if (forecast) {
                    recs.push(
                      <RecommendationCard
                        key="forecast"
                        icon="trendingup"
                        color="#4f46e5"
                        bgColor="rgba(79, 70, 229, 0.03)"
                        borderColor="rgba(79, 70, 229, 0.15)"
                        title="Revenue Forecast"
                        company={forecast.period_description}
                        description={`has a predicted incoming revenue of ${formatCurrency(forecast.forecast_amount_inr)}.`}
                        badgeLabel="Forecast"
                        badgeValue={`Expected: ${formatCurrency(forecast.forecast_amount_inr)}`}
                        buttonLabel="View Pipeline"
                        onClick={() => window.location.href='/opportunities'}
                      />
                    );
                  }
                  riskCustomers.forEach((cust, idx) => {
                    const churnPct = cust.churn_probability != null ? (cust.churn_probability * 100).toFixed(1) : '0.0';
                    const entity = cust.company_name || 'Customer';
                    recs.push(
                      <RecommendationCard
                        key={`risk-${idx}`}
                        icon="alert-triangle"
                        color="#ef4444"
                        bgColor="rgba(239, 68, 68, 0.03)"
                        borderColor="rgba(239, 68, 68, 0.15)"
                        title="At Risk Customer"
                        company={entity}
                        description={`shows a ${churnPct}% churn risk based on recent activity models.`}
                        badgeLabel="Churn Risk"
                        badgeValue={`Score: ${churnPct}%`}
                        buttonLabel="Create Task"
                        onClick={() => {
                          setActiveAction({
                            type: 'High Churn Risk',
                            entityName: entity,
                            reason: `High Churn Risk (${churnPct}%)`,
                            customer_id: cust.customer_id
                          });
                        }}
                      />
                    );
                  });
                  topLeads.forEach((lead, idx) => {
                    const convPct = lead.conversion_probability != null ? (lead.conversion_probability * 100).toFixed(1) : '0.0';
                    const scorePct = lead.score_probability != null ? (lead.score_probability * 100).toFixed(1) : '0.0';
                    const entity = lead.company_name || 'Lead';
                    recs.push(
                      <RecommendationCard
                        key={`lead-${idx}`}
                        icon="trendingup"
                        color="#16a34a"
                        bgColor="rgba(22, 163, 74, 0.03)"
                        borderColor="rgba(22, 163, 74, 0.15)"
                        title="High Conversion Opportunity"
                        company={entity}
                        description={`has a ${convPct}% probability to convert based on lead attributes.`}
                        badgeLabel="High Priority"
                        badgeValue={`Score: ${scorePct}%`}
                        buttonLabel="Create Task"
                        onClick={() => {
                          setActiveAction({
                            type: 'New High-Value Lead',
                            entityName: entity,
                            reason: `High Value Lead (${scorePct}%)`,
                            lead_id: lead.lead_id
                          });
                        }}
                      />
                    );
                  });
                  
                  const top3 = recs.slice(0, 3);
                  return top3.map((el, idx) => React.cloneElement(el, { isLast: idx === top3.length - 1 }));
                })()}
              </div>
            )}
          </div>

          {layout.activity ? (
            <div className="card" style={{ display: 'flex', flexDirection: 'column', background: 'var(--white)' }}>
            <div style={{ padding: '24px 24px 16px', display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', borderBottom: '1px solid var(--border-soft)' }}>
              <div style={{ display: 'flex', gap: '12px' }}>
                <Icon name="clock" size={24} color="var(--brown)" stroke={2} style={{ marginTop: '2px' }} />
                <div>
                  <h2 className="section-title" style={{ fontSize: '18px', fontWeight: 800, marginBottom: '4px', color: 'var(--ink)' }}>Recent Activity</h2>
                  <div style={{ fontSize: '13px', color: 'var(--ink-mute)' }}>Latest interactions across your CRM</div>
                </div>
              </div>
              <button style={{ background: 'var(--bg-light)', border: '1px solid var(--border)', borderRadius: '6px', padding: '6px 12px', fontSize: '12px', fontWeight: 600, color: 'var(--brown)', display: 'flex', alignItems: 'center', gap: '6px', cursor: 'pointer' }} onClick={() => window.location.href='/activities'}>
                View All Activities <Icon name="arrow-right" size={12} stroke={2} />
              </button>
            </div>
              {loading ? (
                 <div style={{ padding: '40px 0', textAlign: 'center', color: 'var(--ink-mute)' }}>Loading activities...</div>
              ) : activities.length === 0 ? (
                <div style={{ padding: '40px 0', textAlign: 'center', color: 'var(--ink-mute)' }}>No recent activity.</div>
              ) : (
                <div style={{ padding: '24px 24px 0', flex: '0 1 auto', overflowY: 'auto' }}>
                  <div style={{ display: 'flex', flexDirection: 'column' }}>
                    {activities.map((act, index) => {
                      const dateObj = new Date(act.due_date || act.created_at);
                      const timeStr = dateObj.toLocaleTimeString([], {hour: '2-digit', minute:'2-digit'});
                      const dateStr = dateObj.toLocaleDateString('en-GB', { day: 'numeric', month: 'short', year: 'numeric' });
                      
                      let resolvedCompany = act.resolved_company_name;
                      if (!resolvedCompany) {
                        if (act.company_id) {
                          const cmp = companies.find(c => c && c.company_id === act.company_id);
                          if (cmp) resolvedCompany = cmp.company_name;
                        }
                      }
                      if (!resolvedCompany) {
                        if (act.opportunity_id) {
                          const opp = opportunities.find(o => o && o.opportunity_id === act.opportunity_id);
                          if (opp && opp.company_name) resolvedCompany = opp.company_name;
                        }
                      }
                      
                      return (
                        <DashboardTimelineRow 
                          key={act.activity_id}
                          icon={act.activity_type === 'Meeting' ? 'calendar' : (act.activity_type === 'Email' ? 'mail' : 'phone')}
                          title={act.subject || act.activity_type}
                          companyName={resolvedCompany || 'Unknown Company'}
                          ownerName={act.created_by}
                          timeStr={timeStr}
                          dateStr={dateStr}
                          status={act.status || 'Pending'}
                          isLast={index === activities.length - 1}
                        />
                      );
                    })}
                  </div>
                  <div style={{ borderTop: '1px solid var(--border-soft)', padding: '16px 0', textAlign: 'center' }}>
                    <button onClick={() => window.location.href='/activities'} style={{ background: 'var(--bg-light)', border: '1px solid var(--border)', borderRadius: '8px', padding: '12px', color: 'var(--brown)', fontSize: '13px', fontWeight: 600, cursor: 'pointer', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '6px', width: '100%' }}>
                      Load More Activities <Icon name="arrow-down" size={14} stroke={2} />
                    </button>
                  </div>
                </div>
              )}
            </div>
          ) : <div />}
        </div>
      </div>
    </div>
  );
}
