import React, { useState, useEffect, useMemo, useRef } from 'react';
import HealthCard from '../components/analytics/HealthCard';
import NextBestActionCard from '../components/analytics/NextBestActionCard';
import { healthService } from '../services/healthService';
import { intelligenceService } from '../services/intelligenceService';
import PageHeader from '../components/common/PageHeader';
import Card from '../components/common/Card';
import { analyticsService } from '../services/crmService';
import Icon from '../components/common/Icon';
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip as RechartsTooltip, ResponsiveContainer,
  FunnelChart, Funnel, LabelList
} from 'recharts';

const formatCurrency = (val) => {
  if (val >= 100000) return `₹${(val / 100000).toFixed(1)} L`;
  return `₹${val.toLocaleString()}`;
};

export default function Analytics() {
  const [activeTab, setActiveTab] = useState('Overview');
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(false);
  
  const [kpis, setKpis] = useState(null);
  const [leadFunnel, setLeadFunnel] = useState([]);
  const [oppPipeline, setOppPipeline] = useState([]);
  const [monthlyRevenue, setMonthlyRevenue] = useState([]);
  const [companiesByState, setCompaniesByState] = useState([]);

  // Date Filtering State
    const [accountHealth, setAccountHealth] = useState({ data: null, loading: true, error: false });
  const [companyHealth, setCompanyHealth] = useState({ data: null, loading: true, error: false });
  const [productHealth, setProductHealth] = useState({ data: null, loading: true, error: false });
  const [intelligence, setIntelligence] = useState({ data: { mode: 'next_best_action', actions: [] }, loading: true, error: false });

const [dateRangeStr, setDateRangeStr] = useState('This Year');
  const [isDateDropdownOpen, setIsDateDropdownOpen] = useState(false);
  const dropdownRef = useRef(null);

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
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  useEffect(() => {
    const loadAll = async () => {
      setLoading(true);
      try {
        const params = {};
        if (dateParams.start_date) params.start_date = dateParams.start_date;
        if (dateParams.end_date) params.end_date = dateParams.end_date;

        const [kpiRes, lfRes, pipeRes, revRes, stateRes] = await Promise.all([
          analyticsService.getDashboardKpis(params),
          analyticsService.getLeadFunnel(params),
          analyticsService.getOpportunityPipeline(params),
          analyticsService.getRevenueByMonth(params),
          analyticsService.getCompaniesByState(params)
        ]);
        
        setKpis(kpiRes.data);
        setLeadFunnel(lfRes.data);
        setOppPipeline(pipeRes.data);
        setMonthlyRevenue(revRes.data);
        setCompaniesByState(stateRes.data);
        setError(false);
      } catch (err) {
        console.error("Failed to load analytics data", err);
        setError(true);
      } finally {
        setLoading(false);
      }
    };
    loadAll();
  }, [dateParams]);

  
  useEffect(() => {
    let periodStr = 'all_time';
    if (dateRangeStr === 'This Month') periodStr = 'this_month';
    else if (dateRangeStr === 'Last Month') periodStr = 'last_month';
    else if (dateRangeStr === 'This Quarter') periodStr = 'this_quarter';
    else if (dateRangeStr === 'This Year') periodStr = 'this_year';

    healthService.getAccountHealthSummary(periodStr)
      .then(res => setAccountHealth({ data: {
          score: res.average_score,
          status: res.status,
          insufficient_data: res.insufficient_data,
          insights: res.insights,
          risk_entities: res.risk_entities,
          metrics: {
            total_evaluated: res.total_evaluated,
            healthy: res.healthy_count,
            at_risk: res.at_risk_count,
            critical: res.critical_count
          }
      }, loading: false, error: false }))
      .catch(err => setAccountHealth({ data: null, loading: false, error: true }));
      
    healthService.getCompanyHealthSummary(periodStr)
      .then(res => setCompanyHealth({ data: {
          score: res.average_score,
          status: res.status,
          insufficient_data: res.insufficient_data,
          insights: res.insights,
          risk_entities: res.risk_entities,
          metrics: {
            total_evaluated: res.total_evaluated,
            healthy: res.healthy_count,
            at_risk: res.at_risk_count,
            critical: res.critical_count
          }
      }, loading: false, error: false }))
      .catch(err => setCompanyHealth({ data: null, loading: false, error: true }));
      
    healthService.getProductHealthSummary(periodStr)
      .then(res => setProductHealth({ data: {
          score: res.average_score,
          status: res.status,
          insufficient_data: res.insufficient_data,
          insights: res.insights,
          risk_entities: res.risk_entities,
          metrics: {
            total_evaluated: res.total_evaluated,
            healthy: res.healthy_count,
            at_risk: res.at_risk_count,
            critical: res.critical_count
          }
      }, loading: false, error: false }))
      .catch(err => {
        console.error("Failed to load product health", err);
        setProductHealth(prev => ({ ...prev, loading: false, error: true }));
      });
      
    // Load NBA with periodStr
    setIntelligence(prev => ({ ...prev, loading: true, error: false }));
    intelligenceService.getRetentionNextBestActions(periodStr)
      .then(res => setIntelligence({ data: { mode: res.data.mode, actions: res.data.actions }, loading: false, error: false }))
      .catch(err => {
        console.error("Failed to load NBAs", err);
        setIntelligence(prev => ({ ...prev, loading: false, error: true }));
      });
  }, [dateRangeStr]);

  const handleDateSelect = (dr) => {
    setDateRangeStr(dr);
    setIsDateDropdownOpen(false);
  };

  // Compute metrics from fetched data
  const totalCompanies = kpis ? kpis.total_companies : 0;
  const totalLeads = kpis ? kpis.total_leads : 0;
  const totalOpps = kpis ? kpis.total_opportunities : 0;
  const openPipelineValue = kpis ? kpis.pipeline_value_inr : 0;
  const totalTransactions = kpis ? kpis.total_transactions : 0;
  const wonOpps = kpis ? kpis.won_opportunities : 0;
  const closedOpps = kpis ? (kpis.total_opportunities - kpis.open_opportunities) : 0;
  
  const winRate = closedOpps > 0 ? ((wonOpps / closedOpps) * 100).toFixed(1) + '%' : 'N/A';

  const leadChartData = leadFunnel.map(item => ({
    name: item.status,
    value: item.count
  }));

  const funnelStages = [
    'Qualification', 'Needs Analysis', 'Value Proposition', 'Id. Decision Makers',
    'Perception Analysis', 'Proposal/Price Quote', 'Negotiation/Review', 'Closed Won', 'Closed Lost'
  ];
  const funnelData = funnelStages.map((s, i) => {
    const stageData = oppPipeline.find(o => o.stage === s);
    const count = stageData ? stageData.count : 0;
    const colors = ['#8b7355', '#9a856a', '#a9967f', '#b8a894', '#c7b9a9', '#d6cabe'];
    return { name: s, value: count, fill: colors[i % colors.length] };
  }).filter(d => d.value > 0);

  const dealValueByStage = funnelStages.map(s => {
    const stageData = oppPipeline.find(o => o.stage === s);
    const val = stageData ? stageData.total_value_inr : 0;
    return { name: s, value: val };
  });

  const companyChartData = companiesByState.map(item => ({
    name: item.state,
    value: item.count
  }));

  const revenueChartData = monthlyRevenue.map(item => ({
    name: item.month, // YYYY-MM
    value: item.revenue_inr
  }));

  const renderTab = () => {
    if (loading) {
      return <div style={{ padding: '40px', textAlign: 'center', color: 'var(--ink-mute)' }}>Loading analytics...</div>;
    }
    
    if (error) {
      return <div style={{ padding: '40px', textAlign: 'center', color: 'var(--danger)' }}>Failed to load analytics. Please try again.</div>;
    }

    const healthCardsSection = (
      <div style={{ display: 'flex', gap: '20px', padding: '0 28px', marginTop: '20px', marginBottom: '20px' }}>
        <HealthCard title="Account Health" data={accountHealth.data} loading={accountHealth.loading} error={accountHealth.error} />
        <HealthCard title="Company Health" data={companyHealth.data} loading={companyHealth.loading} error={companyHealth.error} />
        <HealthCard title="Product Health" data={productHealth.data} loading={productHealth.loading} error={productHealth.error} />
      </div>
    );

    const nextBestActionSection = (
      <div style={{ padding: '0 28px', marginBottom: '20px' }}>
        {intelligence.loading ? (
          <div style={{ padding: '20px', textAlign: 'center', color: 'var(--ink-mute)' }}>Loading next best actions...</div>
        ) : intelligence.error ? (
          <div style={{ padding: '20px', textAlign: 'center', color: 'var(--danger)' }}>Failed to load next best actions.</div>
        ) : intelligence.data.actions.length > 0 ? (
          <NextBestActionCard actions={intelligence.data.actions} mode={intelligence.data.mode} />
        ) : (
          <div style={{ padding: '20px', textAlign: 'center', color: 'var(--ink-mute)' }}>
            {intelligence.data.mode === 'actions_taken' ? 'No recorded action in this period.' : 'No retention actions identified for this period.'}
          </div>
        )}
      </div>
    );


    if (activeTab === 'Overview') {
      return (
        <>
          <div className="kpi-grid">
            <div className="kpi-card">
              <div className="kpi-top">
                <span className="kpi-label">Total Companies</span>
                <div className="kpi-icon"><Icon name="briefcase" size={15} color="var(--white)" stroke={1.8} /></div>
              </div>
              <div className="kpi-value">{totalCompanies}</div>
              <div className="kpi-delta-row"><span className="kpi-ctx">In period</span></div>
            </div>
            <div className="kpi-card">
              <div className="kpi-top">
                <span className="kpi-label">Total Leads</span>
                <div className="kpi-icon"><Icon name="target" size={15} color="var(--white)" stroke={1.8} /></div>
              </div>
              <div className="kpi-value">{totalLeads}</div>
              <div className="kpi-delta-row"><span className="kpi-ctx">In period</span></div>
            </div>
            <div className="kpi-card">
              <div className="kpi-top">
                <span className="kpi-label">Open Pipeline</span>
                <div className="kpi-icon"><Icon name="activity" size={15} color="var(--white)" stroke={1.8} /></div>
              </div>
              <div className="kpi-value">{formatCurrency(openPipelineValue)}</div>
              <div className="kpi-delta-row"><span className="kpi-ctx">Expected revenue</span></div>
            </div>
            <div className="kpi-card">
              <div className="kpi-top">
                <span className="kpi-label">Total Transactions</span>
                <div className="kpi-icon"><Icon name="creditcard" size={15} color="var(--white)" stroke={1.8} /></div>
              </div>
              <div className="kpi-value">{totalTransactions}</div>
              <div className="kpi-delta-row"><span className="kpi-ctx">Completed payments</span></div>
            </div>
          </div>
          {healthCardsSection}
          {nextBestActionSection}
          <div className="row" style={{ padding: '0 28px' }}>
            <Card style={{ padding: '18px 22px', flex: 1, minWidth: '300px' }}>
              <div className="section-title">Global Lead Status Distribution</div>
              <div className="section-sub" style={{ marginBottom: '10px' }}>Count by status</div>
              <div style={{ height: '220px', marginTop: '16px' }}>
                {leadChartData.length > 0 ? (
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={leadChartData} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                      <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="var(--border)" />
                      <XAxis dataKey="name" axisLine={false} tickLine={false} tick={{ fontSize: 12, fill: 'var(--ink-mute)' }} />
                      <YAxis axisLine={false} tickLine={false} tick={{ fontSize: 12, fill: 'var(--ink-mute)' }} />
                      <RechartsTooltip cursor={false} contentStyle={{ borderRadius: '8px', border: '1px solid var(--border)', boxShadow: '0 4px 12px rgba(0,0,0,0.05)' }} />
                      <Bar dataKey="value" fill="var(--brown)" radius={[4, 4, 0, 0]} maxBarSize={50} />
                    </BarChart>
                  </ResponsiveContainer>
                ) : <div style={{ textAlign: 'center', marginTop: '80px', color: 'var(--ink-mute)' }}>No lead data</div>}
              </div>
            </Card>
          </div>
        </>
      );
    } else if (activeTab === 'Pipeline') {
      return (
        <>
          <div className="kpi-grid">
            <div className="kpi-card">
              <div className="kpi-top">
                <span className="kpi-label">Total Opportunities</span>
                <div className="kpi-icon"><Icon name="briefcase" size={15} color="var(--white)" stroke={1.8} /></div>
              </div>
              <div className="kpi-value">{totalOpps}</div>
              <div className="kpi-delta-row"><span className="kpi-ctx">In period</span></div>
            </div>
            <div className="kpi-card">
              <div className="kpi-top">
                <span className="kpi-label">Win Rate</span>
                <div className="kpi-icon"><Icon name="checksquare" size={15} color="var(--white)" stroke={1.8} /></div>
              </div>
              <div className="kpi-value">{winRate}</div>
              <div className="kpi-delta-row"><span className="kpi-ctx">Closed Won / All Closed</span></div>
            </div>
          </div>
          <div className="row" style={{ padding: '0 28px' }}>
            <Card style={{ padding: '18px 22px', flex: 1, minWidth: '300px' }}>
              <div className="section-title">Conversion Funnel</div>
              <div className="section-sub" style={{ marginBottom: '12px' }}>Deal count by stage</div>
              <div style={{ height: '260px' }}>
                {funnelData.length > 0 ? (
                  <ResponsiveContainer width="100%" height="100%">
                    <FunnelChart>
                      <RechartsTooltip cursor={false} />
                      <Funnel dataKey="value" data={funnelData} isAnimationActive>
                        <LabelList position="right" fill="var(--ink)" stroke="none" dataKey="name" />
                      </Funnel>
                    </FunnelChart>
                  </ResponsiveContainer>
                ) : <div style={{ textAlign: 'center', marginTop: '100px', color: 'var(--ink-mute)' }}>No funnel data</div>}
              </div>
            </Card>
            <Card style={{ padding: '18px 22px', flex: 1, minWidth: '300px' }}>
              <div className="section-title">Pipeline Value by Stage</div>
              <div className="section-sub" style={{ marginBottom: '10px' }}>Sum of deal values (₹)</div>
              <div style={{ height: '220px', marginTop: '16px' }}>
                {dealValueByStage.length > 0 ? (
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={dealValueByStage} margin={{ top: 10, right: 10, left: -10, bottom: 0 }}>
                      <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="var(--border)" />
                      <XAxis dataKey="name" axisLine={false} tickLine={false} tick={{ fontSize: 12, fill: 'var(--ink-mute)' }} />
                      <YAxis axisLine={false} tickLine={false} tick={{ fontSize: 12, fill: 'var(--ink-mute)' }} tickFormatter={(val) => `₹${val/1000}k`} />
                      <RechartsTooltip formatter={(val) => formatCurrency(val)} cursor={false} contentStyle={{ borderRadius: '8px', border: '1px solid var(--border)' }} />
                      <Bar dataKey="value" fill="var(--brown)" radius={[4, 4, 0, 0]} maxBarSize={50} />
                    </BarChart>
                  </ResponsiveContainer>
                ) : <div style={{ textAlign: 'center', marginTop: '80px', color: 'var(--ink-mute)' }}>No deal value data</div>}
              </div>
            </Card>
          </div>
        </>
      );
    } else if (activeTab === 'Customers') {
      return (
        <>
          <div className="kpi-grid">
            <div className="kpi-card">
              <div className="kpi-top">
                <span className="kpi-label">Total Companies</span>
                <div className="kpi-icon"><Icon name="briefcase" size={15} color="var(--white)" stroke={1.8} /></div>
              </div>
              <div className="kpi-value">{totalCompanies}</div>
              <div className="kpi-delta-row"><span className="kpi-ctx">In period</span></div>
            </div>
            <div className="kpi-card">
              <div className="kpi-top">
                <span className="kpi-label">Active Customers</span>
                <div className="kpi-icon"><Icon name="users" size={15} color="var(--white)" stroke={1.8} /></div>
              </div>
              <div className="kpi-value">{kpis ? kpis.active_customers : 0}</div>
              <div className="kpi-delta-row"><span className="kpi-ctx">Customers</span></div>
            </div>
          </div>
          <div className="row" style={{ padding: '0 28px' }}>
            <Card style={{ padding: '18px 22px', flex: 1, minWidth: '300px' }}>
              <div className="section-title">Companies by State</div>
              <div className="section-sub" style={{ marginBottom: '10px' }}>Company count by location</div>
              <div style={{ height: '220px', marginTop: '16px' }}>
                {companyChartData.length > 0 ? (
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={companyChartData} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                      <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="var(--border)" />
                      <XAxis dataKey="name" axisLine={false} tickLine={false} tick={{ fontSize: 12, fill: 'var(--ink-mute)' }} />
                      <YAxis axisLine={false} tickLine={false} tick={{ fontSize: 12, fill: 'var(--ink-mute)' }} />
                      <RechartsTooltip cursor={false} contentStyle={{ borderRadius: '8px', border: '1px solid var(--border)' }} />
                      <Bar dataKey="value" fill="var(--brown)" radius={[4, 4, 0, 0]} maxBarSize={50} />
                    </BarChart>
                  </ResponsiveContainer>
                ) : <div style={{ textAlign: 'center', marginTop: '80px', color: 'var(--ink-mute)' }}>No state data</div>}
              </div>
            </Card>
          </div>
        </>
      );
    } else if (activeTab === 'Revenue & Products') {
      return (
        <>
          <div className="kpi-grid">
            <div className="kpi-card">
              <div className="kpi-top">
                <span className="kpi-label">Total Revenue</span>
                <div className="kpi-icon"><Icon name="briefcase" size={15} color="var(--white)" stroke={1.8} /></div>
              </div>
              <div className="kpi-value">{formatCurrency(kpis ? kpis.total_revenue_inr : 0)}</div>
              <div className="kpi-delta-row"><span className="kpi-ctx">Paid transactions</span></div>
            </div>
            <div className="kpi-card">
              <div className="kpi-top">
                <span className="kpi-label">Won Revenue</span>
                <div className="kpi-icon"><Icon name="creditcard" size={15} color="var(--white)" stroke={1.8} /></div>
              </div>
              <div className="kpi-value">{formatCurrency(kpis ? kpis.won_revenue_inr : 0)}</div>
              <div className="kpi-delta-row"><span className="kpi-ctx">Closed won opportunities</span></div>
            </div>
          </div>
          <div className="row" style={{ padding: '0 28px' }}>
            <Card style={{ padding: '18px 22px', flex: 1, minWidth: '300px' }}>
              <div className="section-title">Monthly Revenue</div>
              <div className="section-sub" style={{ marginBottom: '10px' }}>Paid transactions over time</div>
              <div style={{ height: '220px', marginTop: '16px' }}>
                {revenueChartData.length > 0 ? (
                  <ResponsiveContainer width="100%" height="100%">
                    <BarChart data={revenueChartData} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                      <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="var(--border)" />
                      <XAxis dataKey="name" axisLine={false} tickLine={false} tick={{ fontSize: 12, fill: 'var(--ink-mute)' }} />
                      <YAxis axisLine={false} tickLine={false} tick={{ fontSize: 12, fill: 'var(--ink-mute)' }} tickFormatter={(val) => `₹${val/1000}k`} />
                      <RechartsTooltip formatter={(val) => formatCurrency(val)} cursor={false} contentStyle={{ borderRadius: '8px', border: '1px solid var(--border)' }} />
                      <Bar dataKey="value" fill="var(--brown)" radius={[4, 4, 0, 0]} maxBarSize={50} />
                    </BarChart>
                  </ResponsiveContainer>
                ) : <div style={{ textAlign: 'center', marginTop: '80px', color: 'var(--ink-mute)' }}>No revenue data</div>}
              </div>
            </Card>
          </div>
        </>
      );
    }
    return null;
  };

  const tabs = ['Overview', 'Pipeline', 'Customers', 'Revenue & Products'];

  return (
    <div className="page" style={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
      <div className="page-header" style={{ paddingBottom: 0 }}>
        <div>
          <h1 className="page-title">Analytics</h1>
          <p className="page-desc">Deep performance analysis across pipeline, customers, and operations.</p>
        </div>
        <div className="page-actions">
          <div className="chip" style={{ position: 'relative', cursor: 'pointer' }} ref={dropdownRef}>
            <div onClick={() => setIsDateDropdownOpen(!isDateDropdownOpen)} style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
              <Icon name="calendar" size={15} color="var(--ink-soft)" stroke={1.8} /> {dateRangeStr} 
              <Icon name="chevrondown" size={13} color="var(--ink-soft)" stroke={2} />
            </div>
            {isDateDropdownOpen && (
              <div style={{
                position: 'absolute', top: '100%', right: 0, marginTop: '8px',
                background: 'white', border: '1px solid var(--border)', borderRadius: '6px',
                boxShadow: '0 4px 12px rgba(0,0,0,0.1)', zIndex: 100, minWidth: '140px', overflow: 'hidden'
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
        </div>
      </div>

      <div className="tabbar" style={{ margin: '16px 0 16px', padding: '0 28px' }}>
        {tabs.map(t => (
          <div 
            key={t}
            className={`tab ${activeTab === t ? 'active' : ''}`}
            onClick={() => setActiveTab(t)}
          >
            {t}
          </div>
        ))}
      </div>
      <div style={{ flex: 1 }}>
        {renderTab()}
      </div>
    </div>
  );
}
