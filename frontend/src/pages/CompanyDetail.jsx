import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import { LineChart, Line, AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from 'recharts';
import Icon from '../components/common/Icon';
import Badge from '../components/common/Badge';
import {
  companyService,
  customerService,
  activityService,
  transactionService,
  supportService
} from '../services/crmService';
import NoteModal from '../components/common/NoteModal';

export default function CompanyDetail() {
  const { id } = useParams();
  const navigate = useNavigate();

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const [company, setCompany] = useState(null);
  const [contacts, setContacts] = useState([]);
  const [customers, setCustomers] = useState([]);
  const [opportunities, setOpportunities] = useState([]);
  const [leads, setLeads] = useState([]);
  const [activities, setActivities] = useState([]);
  const [transactions, setTransactions] = useState([]);
  const [supportCases, setSupportCases] = useState([]);
  const [isNoteModalOpen, setIsNoteModalOpen] = useState(false);

  const fetchActivities = async () => {
    try {
      const actRes = await activityService.getActivities({ company_id: id });
      setActivities(actRes.data?.items || actRes.data || []);
    } catch (err) {
      console.error("Failed to fetch activities after note save", err);
    }
  };

  useEffect(() => {
    async function loadData() {
      setLoading(true);
      setError(null);
      try {
        const compRes = await companyService.getCompany(id);
        setCompany(compRes.data);

        // Dispatch event for Header breadcrumb
        if (compRes.data && compRes.data.company_name) {
          window.dispatchEvent(new CustomEvent('set-breadcrumb', { detail: compRes.data.company_name }));
        }

        const [contRes, oppRes, leadsRes, custRes, actRes] = await Promise.all([
          companyService.getCompanyContacts(id).catch(() => ({ data: [] })),
          companyService.getCompanyOpportunities(id).catch(() => ({ data: [] })),
          companyService.getCompanyLeads(id).catch(() => ({ data: [] })),
          customerService.getCustomers({ company_id: id }).catch(() => ({ data: {} })),
          activityService.getActivities({ company_id: id }).catch(() => ({ data: {} }))
        ]);

        setContacts(contRes.data?.items || contRes.data || []);
        setOpportunities(oppRes.data?.items || oppRes.data || []);
        setLeads(leadsRes.data?.items || leadsRes.data || []);

        const allCustomers = custRes.data?.items || custRes.data || [];
        setCustomers(allCustomers);

        setActivities(actRes.data?.items || actRes.data || []);

        const firstCustomer = allCustomers[0] || null;
        if (firstCustomer) {
          const custId = firstCustomer.customer_id;
          const [supRes, txnRes] = await Promise.all([
            supportService.getSupportCases({ customer_id: custId, page_size: 200 }).catch(() => ({ data: {} })),
            transactionService.getTransactions({ customer_id: custId, page_size: 200 }).catch(() => ({ data: {} }))
          ]);
          setSupportCases(supRes.data?.items || supRes.data || []);
          setTransactions(txnRes.data?.items || txnRes.data || []);
        } else {
          setSupportCases([]);
          setTransactions([]);
        }

      } catch (err) {
        console.error("Failed to load company details", err);
        setError("Failed to load company details.");
      } finally {
        setLoading(false);
      }
    }
    loadData();
  }, [id]);

  if (loading) return <div style={{ padding: 28 }}>Loading company profile...</div>;
  if (error) return (
    <div style={{ padding: 28 }}>
      <div className="empty-state">
        <div className="empty-title">Error</div>
        <div className="empty-desc">{error}</div>
      </div>
    </div>
  );
  if (!company) return (
    <div style={{ padding: 28 }}>
      <div className="empty-state">
        <div className="empty-title">Not Found</div>
        <div className="empty-desc">Company not found.</div>
      </div>
    </div>
  );

  // --- KPIs Calculations ---
  const totalRevenue = transactions.reduce((sum, t) => sum + (t.amount_inr || 0), 0);
  const totalTransactions = transactions.length;
  const avgTransactionValue = totalTransactions > 0 ? (totalRevenue / totalTransactions) : 0;

  const openOpps = opportunities.filter(o => !['Closed Won', 'Closed Lost', 'Closed'].includes(o.pipeline_stage));
  const openOppsCount = openOpps.length;
  const pipelineValue = openOpps.reduce((sum, o) => sum + (o.deal_value_inr || 0), 0);

  const totalContactsCount = contacts.length;

  // --- Revenue Trend Data (Monthly aggregation) ---
  const monthlyRevenueMap = {};
  transactions.forEach(t => {
    if (!t.transaction_date) return;
    const date = new Date(t.transaction_date);
    const monthKey = `${date.getFullYear()}-${String(date.getMonth() + 1).padStart(2, '0')}`;
    if (!monthlyRevenueMap[monthKey]) monthlyRevenueMap[monthKey] = 0;
    monthlyRevenueMap[monthKey] += (t.amount_inr || 0);
  });

  const revenueChartData = Object.keys(monthlyRevenueMap).sort().map(m => {
    const [year, month] = m.split('-');
    const dateObj = new Date(year, month - 1, 1);
    const monthName = dateObj.toLocaleString('default', { month: 'short' });
    return {
      month: `${monthName} ${year}`,
      revenue: monthlyRevenueMap[m]
    };
  });

  // --- AI Summary Fallback ---
  const firstCust = customers[0];
  const summaryText = `${company.company_name} is a ${company.account_status || 'prospect'} account operating in the ${company.industry_id || 'unspecified'} sector. Based in ${company.city || 'an unknown location'}, ${company.state || ''}, they currently have ${openOppsCount} open opportunit${openOppsCount === 1 ? 'y' : 'ies'} collectively valued at ₹${pipelineValue.toLocaleString()} and ${leads.length} active lead${leads.length === 1 ? '' : 's'}. ${firstCust ? `As a registered customer since ${new Date(firstCust.customer_since).getFullYear()}, they have generated ₹${totalRevenue.toLocaleString()} across ${totalTransactions} transactions.` : 'They have not completed any transactions yet.'}`;

  // Formatting helpers
  const formatINR = (val) => new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR', maximumFractionDigits: 0 }).format(val);
  const initials = company.company_name ? company.company_name.substring(0, 2).toUpperCase() : 'CO';
  const customerSince = firstCust && firstCust.customer_since ? new Date(firstCust.customer_since).toLocaleString('default', { month: 'short', year: 'numeric' }) : null;

  const cardStyle = {
    background: 'var(--white)',
    border: '1px solid var(--border)',
    borderRadius: '12px',
    boxShadow: '0 2px 8px rgba(0,0,0,0.02)',
    display: 'flex',
    flexDirection: 'column',
    overflow: 'hidden'
  };

  const cardHeaderStyle = {
    padding: '16px 20px',
    borderBottom: '1px solid var(--border-soft)',
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center'
  };

  const cardTitleStyle = {
    display: 'flex',
    alignItems: 'center',
    gap: '8px',
    fontSize: '14px',
    fontWeight: 700,
    color: 'var(--heading-primary)'
  };

  const cardBodyStyle = {
    padding: '0',
    display: 'flex',
    flexDirection: 'column',
    flex: 1
  };

  const rowStyle = {
    padding: '16px 20px',
    borderBottom: '1px solid var(--border-soft)',
    display: 'flex',
    flexDirection: 'column',
    gap: '6px'
  };

  const rowHeaderStyle = {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'flex-start'
  };

  const rowTitleStyle = {
    fontSize: '13px',
    fontWeight: 600,
    color: 'var(--heading-primary)'
  };

  const rowSubtextStyle = {
    fontSize: '12px',
    color: 'var(--ink-mute)'
  };

  const viewAllStyle = {
    padding: '12px 20px',
    fontSize: '13px',
    fontWeight: 600,
    color: 'var(--accent-primary)',
    cursor: 'pointer',
    background: 'var(--white)'
  };

  return (
    <div className="page" style={{ padding: '24px 28px', maxWidth: '1400px', margin: '0 auto', background: 'var(--beige)', minHeight: '100vh' }}>

      {/* ── Back link ── */}
      <div
        style={{ display: 'inline-flex', alignItems: 'center', gap: '6px', fontSize: '12px', fontWeight: 600, color: 'var(--ink-mute)', cursor: 'pointer', marginBottom: '18px' }}
        onClick={() => navigate('/companies')}
      >
        <Icon name="chevronleft" size={14} color="currentColor" stroke={2.2} />
        Back to Companies
      </div>

      {/* 1. COMPANY HEADER */}
      <div style={{ background: 'var(--white)', border: '1px solid var(--border)', borderRadius: '16px', padding: '24px 32px', display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '24px', boxShadow: '0 2px 12px rgba(0,0,0,0.03)' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '20px' }}>

          <div style={{ width: '64px', height: '64px', borderRadius: '14px', background: 'var(--brown)', color: 'var(--ivory)', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: '24px', fontWeight: 600, flexShrink: 0, boxShadow: 'var(--clay-shadow-sm)' }}>
             {initials}
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
             <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                <h1 style={{ fontSize: '24px', fontWeight: 700, color: 'var(--heading-primary)', margin: 0, letterSpacing: '-0.3px' }}>{company.company_name}</h1>
                <Badge text={company.account_status || 'Prospect'} variant={company.account_status === 'Active Customer' ? 'success' : 'neutral'} />
                {totalContactsCount > 10 && <Badge text="Enterprise" variant="neutral" />}
             </div>
             <div style={{ display: 'flex', alignItems: 'center', gap: '18px', color: 'var(--ink-mute)', fontSize: '13px', fontWeight: 500 }}>
                {company.industry_id && <span style={{display: 'flex', gap: 6, alignItems: 'center'}}><Icon name="building" size={14} /> {company.industry_id}</span>}
                {(company.city || company.state) && <span style={{display: 'flex', gap: 6, alignItems: 'center'}}><Icon name="map-pin" size={14} /> {company.city}, {company.state}</span>}
                {company.company_size && <span style={{ display: 'flex', gap: 6, alignItems: 'center' }}><Icon name="users" size={14} />{company.company_size} employees</span>}
                {customerSince && <span style={{ display: 'flex', gap: 6, alignItems: 'center' }}><Icon name="calendar" size={14} />Customer since {customerSince}</span>}
             </div>
          </div>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '32px' }}>
           {firstCust && (
             <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-end', gap: '6px' }}>
                <span style={{ fontSize: '12px', fontWeight: 600, color: 'var(--ink-mute)' }}>Customer Health</span>
                <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                   <div style={{ width: '64px', height: '4px', background: 'var(--border-soft)', borderRadius: '2px', overflow: 'hidden' }}>
                      <div style={{ width: '88%', height: '100%', background: 'var(--success)' }}></div>
                   </div>
                   <span style={{ fontSize: '16px', fontWeight: 700, color: 'var(--brown)' }}>88</span>
                </div>
             </div>
           )}
           <button
             style={{ background: 'var(--brown)', border: 'none', borderRadius: '8px', padding: '10px 16px', display: 'flex', alignItems: 'center', gap: '8px', fontSize: '13px', fontWeight: 600, color: 'var(--ivory)', cursor: 'pointer' }}
             onClick={() => setIsNoteModalOpen(true)}
           >
             <Icon name="file-text" size={14} /> New Note
           </button>
        </div>
      </div>

      <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>

          {/* KPI CARDS GRID */}
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(6, 1fr)', gap: '16px' }}>

            <div style={{ background: 'var(--white)', border: '1px solid var(--border)', borderRadius: '12px', padding: '20px', boxShadow: '0 2px 8px rgba(0,0,0,0.02)' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
                 <span style={{ fontSize: '12px', fontWeight: 700, color: 'var(--heading-primary)' }}>Total Revenue</span>
                 <Icon name="credit-card" size={14} color="var(--accent-primary)" />
              </div>
              <div style={{ fontSize: '24px', fontWeight: 700, color: 'var(--heading-primary)', marginBottom: '8px', letterSpacing: '-0.5px' }}>
                {formatINR(totalRevenue)}
              </div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                 <Badge text="↑ All time" variant="success" />
              </div>
            </div>

            <div style={{ background: 'var(--white)', border: '1px solid var(--border)', borderRadius: '12px', padding: '20px', boxShadow: '0 2px 8px rgba(0,0,0,0.02)' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
                 <span style={{ fontSize: '12px', fontWeight: 700, color: 'var(--heading-primary)' }}>Total Transactions</span>
                 <Icon name="package" size={14} color="var(--accent-primary)" />
              </div>
              <div style={{ fontSize: '24px', fontWeight: 700, color: 'var(--heading-primary)', marginBottom: '8px', letterSpacing: '-0.5px' }}>
                {totalTransactions}
              </div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                 <Badge text="↑ This year" variant="success" />
              </div>
            </div>

            <div style={{ background: 'var(--white)', border: '1px solid var(--border)', borderRadius: '12px', padding: '20px', boxShadow: '0 2px 8px rgba(0,0,0,0.02)' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
                 <span style={{ fontSize: '12px', fontWeight: 700, color: 'var(--heading-primary)' }}>Avg. Transaction Value</span>
                 <Icon name="bar-chart-2" size={14} color="var(--accent-primary)" />
              </div>
              <div style={{ fontSize: '24px', fontWeight: 700, color: 'var(--heading-primary)', marginBottom: '8px', letterSpacing: '-0.5px' }}>
                {formatINR(avgTransactionValue)}
              </div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                 <Badge text="↑ vs last year" variant="success" />
              </div>
            </div>

            <div style={{ background: 'var(--white)', border: '1px solid var(--border)', borderRadius: '12px', padding: '20px', boxShadow: '0 2px 8px rgba(0,0,0,0.02)' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
                 <span style={{ fontSize: '12px', fontWeight: 700, color: 'var(--heading-primary)' }}>Open Opportunities</span>
                 <Icon name="target" size={14} color="var(--accent-primary)" />
              </div>
              <div style={{ fontSize: '24px', fontWeight: 700, color: 'var(--heading-primary)', marginBottom: '8px', letterSpacing: '-0.5px' }}>
                {openOppsCount}
              </div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                 <Badge text="In pipeline" variant="warning" />
              </div>
            </div>

            <div style={{ background: 'var(--white)', border: '1px solid var(--border)', borderRadius: '12px', padding: '20px', boxShadow: '0 2px 8px rgba(0,0,0,0.02)' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
                 <span style={{ fontSize: '12px', fontWeight: 700, color: 'var(--heading-primary)' }}>Pipeline Value</span>
                 <Icon name="pie-chart" size={14} color="var(--accent-primary)" />
              </div>
              <div style={{ fontSize: '24px', fontWeight: 700, color: 'var(--heading-primary)', marginBottom: '8px', letterSpacing: '-0.5px' }}>
                {formatINR(pipelineValue)}
              </div>
              <div style={{ fontSize: '12px', color: 'var(--ink-mute)', fontWeight: 500 }}>
                 Across {openOppsCount} opportunities
              </div>
            </div>

            <div style={{ background: 'var(--white)', border: '1px solid var(--border)', borderRadius: '12px', padding: '20px', boxShadow: '0 2px 8px rgba(0,0,0,0.02)' }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '16px' }}>
                 <span style={{ fontSize: '12px', fontWeight: 700, color: 'var(--heading-primary)' }}>Total Contacts</span>
                 <Icon name="users" size={14} color="var(--accent-primary)" />
              </div>
              <div style={{ fontSize: '24px', fontWeight: 700, color: 'var(--heading-primary)', marginBottom: '8px', letterSpacing: '-0.5px' }}>
                {totalContactsCount}
              </div>
              <div style={{ fontSize: '12px', color: 'var(--ink-mute)', fontWeight: 500 }}>
                 Associated contacts
              </div>
            </div>

          </div>

          {/* AI SUMMARY & REVENUE TREND */}
          <div style={{ display: 'grid', gridTemplateColumns: revenueChartData.length >= 2 ? '1fr 1fr' : '1fr', gap: '24px' }}>
            <div style={{ background: 'var(--white)', border: '1px solid var(--border)', borderRadius: '12px', padding: '24px', display: 'flex', flexDirection: 'column', gap: '16px', boxShadow: '0 2px 8px rgba(0,0,0,0.02)' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '15px', fontWeight: 700, color: 'var(--brown)' }}>
                 <Icon name="sparkles" size={16} color="var(--brown)" /> AI Summary
              </div>
              <div style={{ fontSize: '14px', lineHeight: '1.6', color: 'var(--ink-soft)' }}>
                 {summaryText}
              </div>
              <div style={{ marginTop: 'auto', background: 'var(--brown)', padding: '16px', borderRadius: '8px', border: '1px solid var(--border)', display: 'flex', gap: '12px', alignItems: 'flex-start' }}>
                 <Icon name="check-square" size={18} color="var(--white)" style={{ marginTop: '2px' }} />
                 <div style={{ fontSize: '13px', lineHeight: '1.5', color: 'var(--white)', fontWeight: 500 }}>
                   This is a high-value account with strong transaction history and active pipeline. Consider prioritizing for expansion opportunities.
                 </div>
              </div>
            </div>

            {revenueChartData.length >= 2 && (
              <div style={{ background: 'var(--white)', border: '1px solid var(--border)', borderRadius: '12px', padding: '24px', display: 'flex', flexDirection: 'column', gap: '20px', boxShadow: '0 2px 8px rgba(0,0,0,0.02)' }}>
                <div>
                   <div style={{ display: 'flex', alignItems: 'center', gap: '8px', fontSize: '15px', fontWeight: 700, color: 'var(--brown)', marginBottom: '4px' }}>
                     <Icon name="bar-chart-2" size={16} color="var(--ink)" /> Revenue Trend
                   </div>
                   <div style={{ fontSize: '12px', color: 'var(--ink-mute)' }}>Monthly revenue over time</div>
                </div>

                <div style={{ height: '220px', width: '100%' }}>
                  <ResponsiveContainer>
                    <AreaChart data={revenueChartData} margin={{ top: 10, right: 10, left: -20, bottom: 0 }}>
                      <defs>
                        <linearGradient id="colorRev" x1="0" y1="0" x2="0" y2="1">
                          <stop offset="5%" stopColor="var(--brown)" stopOpacity={0.15}/>
                          <stop offset="95%" stopColor="var(--brown)" stopOpacity={0}/>
                        </linearGradient>
                      </defs>
                      <CartesianGrid strokeDasharray="3 3" vertical={false} stroke="var(--border)" />
                      <XAxis dataKey="month" tick={{ fontSize: 11, fill: 'var(--ink-mute)' }} axisLine={false} tickLine={false} dy={10} />
                      <YAxis tick={{ fontSize: 11, fill: 'var(--ink-mute)' }} axisLine={false} tickLine={false} tickFormatter={(val) => `₹${(val/1000)}k`} />
                      <Tooltip
                        contentStyle={{ borderRadius: '8px', border: '1px solid var(--border)', boxShadow: '0 4px 12px rgba(0,0,0,0.05)', backgroundColor: 'var(--white)' }}
                        formatter={(value) => [formatINR(value), 'Revenue']}
                      />
                      <Area type="monotone" dataKey="revenue" stroke="var(--brown)" strokeWidth={3} fillOpacity={1} fill="url(#colorRev)" activeDot={{ r: 6, fill: 'var(--brown)', stroke: 'var(--white)' }} />
                    </AreaChart>
                  </ResponsiveContainer>
                </div>
              </div>
            )}
          </div>

          {/* RELATED ENTITIES ROW 1: Contacts, Leads, Opps, Customer */}
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '16px' }}>

            {/* Contacts */}
            <div style={cardStyle}>
               <div style={cardHeaderStyle}>
                  <div style={cardTitleStyle}><Icon name="users" size={16} color="var(--brown)"/> Contacts</div>
                  <span style={{ fontSize: '12px', fontWeight: 700, color: 'var(--ink-mute)' }}>{contacts.length}</span>
               </div>
               <div style={cardBodyStyle}>
                  {contacts.length === 0 ? (
                    <div style={{ padding: '30px', textAlign: 'center', color: 'var(--ink-mute)', fontSize: '13px' }}>No contacts</div>
                  ) : (
                    contacts.slice(0, 3).map(c => (
                      <div key={c.contact_id} style={rowStyle} onClick={() => navigate(`/contacts/${c.contact_id}`)} className="hover-bg-beige" css={{ cursor: 'pointer' }}>
                        <div style={rowHeaderStyle}>
                           <div style={{ display: 'flex', gap: '12px', alignItems: 'center' }}>
                             <div style={{ width: '32px', height: '32px', borderRadius: '50%', background: 'var(--brown)', color: 'var(--white)', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: '12px', fontWeight: 700, border: '1px solid var(--border-soft)' }}>
                               {c.full_name ? c.full_name.substring(0,2).toUpperCase() : 'CO'}
                             </div>
                             <div style={{ display: 'flex', flexDirection: 'column' }}>
                                <span style={rowTitleStyle}>{c.full_name}</span>
                                <span style={rowSubtextStyle}>{c.job_title || 'No Title'}</span>
                             </div>
                           </div>
                        </div>
                      </div>
                    ))
                  )}
               </div>
               {contacts.length > 0 && (
                 <div style={viewAllStyle} onClick={() => navigate(`/contacts?company_id=${company.company_id}`)}>View all contacts →</div>
               )}
            </div>

            {/* Leads */}
            <div style={cardStyle}>
               <div style={cardHeaderStyle}>
                  <div style={cardTitleStyle}><Icon name="target" size={16} color="var(--brown)"/> Leads</div>
                  <span style={{ fontSize: '12px', fontWeight: 700, color: 'var(--ink-mute)' }}>{leads.length}</span>
               </div>
               <div style={cardBodyStyle}>
                  {leads.length === 0 ? (
                    <div style={{ padding: '30px', textAlign: 'center', color: 'var(--ink-mute)', fontSize: '13px' }}>No leads</div>
                  ) : (
                    leads.slice(0, 3).map(l => (
                      <div key={l.lead_id} style={rowStyle} onClick={() => navigate(`/leads/${l.lead_id}`)} className="hover-bg-beige" css={{ cursor: 'pointer' }}>
                        <div style={rowHeaderStyle}>
                           <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
                              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                                <Icon name="calendar" size={12} color="var(--ink-mute)"/>
                                <span style={rowTitleStyle}>{l.lead_status || 'New Lead'}</span>
                              </div>
                              <span style={rowSubtextStyle}>{l.created_at ? new Date(l.created_at).toLocaleDateString() : '-'}</span>
                           </div>
                           <Badge text={l.lead_status || 'New'} variant="neutral" />
                        </div>
                      </div>
                    ))
                  )}
               </div>
               {leads.length > 0 && (
                 <div style={viewAllStyle} onClick={() => navigate(`/leads?company_id=${company.company_id}`)}>View all leads →</div>
               )}
            </div>

            {/* Opportunities */}
            <div style={cardStyle}>
               <div style={cardHeaderStyle}>
                  <div style={cardTitleStyle}><Icon name="briefcase" size={16} color="var(--brown)"/> Opportunities</div>
                  <span style={{ fontSize: '12px', fontWeight: 700, color: 'var(--ink-mute)' }}>{opportunities.length}</span>
               </div>
               <div style={cardBodyStyle}>
                  {opportunities.length === 0 ? (
                    <div style={{ padding: '30px', textAlign: 'center', color: 'var(--ink-mute)', fontSize: '13px' }}>No opportunities</div>
                  ) : (
                    opportunities.slice(0, 3).map(o => (
                      <div key={o.opportunity_id} style={rowStyle} onClick={() => navigate(`/opportunities/${o.opportunity_id}`)} className="hover-bg-beige" css={{ cursor: 'pointer' }}>
                        <div style={rowHeaderStyle}>
                           <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
                              <span style={rowTitleStyle}>{o.opportunity_name}</span>
                              <span style={{ fontSize: '13px', fontWeight: 600, color: 'var(--ink-soft)' }}>
                                {o.deal_value_inr != null ? `₹${o.deal_value_inr.toLocaleString()}` : '-'}
                              </span>
                           </div>
                           <Badge text={o.pipeline_stage || 'Unknown'} variant={['Closed Won'].includes(o.pipeline_stage) ? 'success' : 'neutral'} />
                        </div>
                      </div>
                    ))
                  )}
               </div>
               {opportunities.length > 0 && (
                 <div style={viewAllStyle} onClick={() => navigate(`/opportunities?company_id=${company.company_id}`)}>View all opportunities →</div>
               )}
            </div>

            {/* Customer */}
            <div style={cardStyle}>
               <div style={cardHeaderStyle}>
                  <div style={cardTitleStyle}><Icon name="building" size={16} color="var(--brown)"/> Customer</div>
                  <span style={{ fontSize: '12px', fontWeight: 700, color: 'var(--ink-mute)' }}>{customers.length}</span>
               </div>
               <div style={cardBodyStyle}>
                  {customers.length === 0 ? (
                    <div style={{ padding: '30px', textAlign: 'center', color: 'var(--ink-mute)', fontSize: '13px' }}>No customer record</div>
                  ) : (
                    customers.slice(0, 1).map(c => (
                      <div key={c.customer_id} style={rowStyle} onClick={() => navigate(`/customers/${c.customer_id}`)} className="hover-bg-beige" css={{ cursor: 'pointer' }}>
                        <div style={rowHeaderStyle}>
                           <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                                <Icon name="file-text" size={14} color="var(--ink-mute)"/>
                                <span style={rowTitleStyle}>{company.company_name}</span>
                              </div>
                              <span style={rowSubtextStyle}>Customer ID: {c.customer_id}</span>
                              <span style={rowSubtextStyle}>Since: {c.customer_since ? new Date(c.customer_since).toLocaleDateString() : '-'}</span>
                           </div>
                           <Badge text={c.customer_status || 'Active'} variant="success" />
                        </div>
                      </div>
                    ))
                  )}
               </div>
               {customers.length > 0 && (
                 <div style={viewAllStyle} onClick={() => navigate(`/customers/${customers[0].customer_id}`)}>View customer details →</div>
               )}
            </div>

          </div>


          {/* RELATED ENTITIES ROW 2: Transactions, Activities, Support */}
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '16px' }}>

            {/* Transactions */}
            <div style={cardStyle}>
               <div style={cardHeaderStyle}>
                  <div style={cardTitleStyle}><Icon name="credit-card" size={16} color="var(--brown)"/> Transactions</div>
                  <span style={{ fontSize: '12px', fontWeight: 700, color: 'var(--ink-mute)' }}>{transactions.length}</span>
               </div>
               <div style={cardBodyStyle}>
                  {transactions.length === 0 ? (
                    <div style={{ padding: '30px', textAlign: 'center', color: 'var(--ink-mute)', fontSize: '13px' }}>No transactions</div>
                  ) : (
                    transactions.slice(0, 4).map(t => (
                      <div key={t.transaction_id} style={{...rowStyle, flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center'}} onClick={() => navigate(`/transactions/${t.transaction_id}`)} className="hover-bg-beige" css={{ cursor: 'pointer' }}>
                         <div style={{ display: 'flex', flexDirection: 'column', gap: '4px' }}>
                            <span style={rowTitleStyle}>{t.transaction_id}</span>
                            <span style={rowSubtextStyle}>{t.transaction_date ? new Date(t.transaction_date).toLocaleDateString() : '-'}</span>
                         </div>
                         <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                            <span style={{ fontSize: '13px', fontWeight: 600, color: 'var(--brown)' }}>{t.amount_inr != null ? `₹${t.amount_inr.toLocaleString()}` : '-'}</span>
                            <Badge text={t.payment_status || 'Completed'} variant={t.payment_status === 'Completed' ? 'success' : 'neutral'} />
                         </div>
                      </div>
                    ))
                  )}
               </div>
               {transactions.length > 0 && (
                 <div style={viewAllStyle} onClick={() => customers.length > 0 ? navigate(`/transactions?customer_id=${customers[0].customer_id}`) : null}>View all transactions →</div>
               )}
            </div>

            {/* Activities */}
            <div style={cardStyle}>
               <div style={cardHeaderStyle}>
                  <div style={cardTitleStyle}><Icon name="activity" size={16} color="var(--brown)"/> Activities</div>
                  <span style={{ fontSize: '12px', fontWeight: 700, color: 'var(--ink-mute)' }}>{activities.length}</span>
               </div>
               <div style={cardBodyStyle}>
                  {activities.length === 0 ? (
                    <div style={{ padding: '30px', textAlign: 'center', color: 'var(--ink-mute)', fontSize: '13px' }}>No activities</div>
                  ) : (
                    activities.slice(0, 4).map(a => (
                      <div key={a.activity_id} style={{...rowStyle, flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center'}} onClick={() => navigate(`/activities/${a.activity_id}`)} className="hover-bg-beige" css={{ cursor: 'pointer' }}>
                         <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                            <Icon name={a.activity_type?.toLowerCase().includes('call') ? 'phone' : a.activity_type?.toLowerCase().includes('email') ? 'mail' : 'calendar'} size={14} color="var(--ink-mute)" />
                            <div style={{ display: 'flex', flexDirection: 'column', gap: '2px' }}>
                               <span style={rowTitleStyle}>{a.subject}</span>
                               <span style={rowSubtextStyle}>{a.activity_type || 'Task'}</span>
                            </div>
                         </div>
                         <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-end', gap: '4px' }}>
                            <span style={rowSubtextStyle}>{a.due_date ? new Date(a.due_date).toLocaleDateString() : '-'}</span>
                         </div>
                      </div>
                    ))
                  )}
               </div>
               {activities.length > 0 && (
                 <div style={viewAllStyle} onClick={() => navigate(`/activities?company_id=${company.company_id}`)}>View all activities →</div>
               )}
            </div>

            {/* Support Cases */}
            <div style={cardStyle}>
               <div style={cardHeaderStyle}>
                  <div style={cardTitleStyle}><Icon name="headphones" size={16} color="var(--brown)"/> Support Cases</div>
                  <span style={{ fontSize: '12px', fontWeight: 700, color: 'var(--ink-mute)' }}>{supportCases.length}</span>
               </div>
               <div style={cardBodyStyle}>
                  {supportCases.length === 0 ? (
                    <div style={{ padding: '30px', textAlign: 'center', color: 'var(--ink-mute)', fontSize: '13px' }}>No support cases</div>
                  ) : (
                    supportCases.slice(0, 4).map(s => (
                      <div key={s.case_id} style={{...rowStyle, flexDirection: 'row', justifyContent: 'space-between', alignItems: 'center'}} onClick={() => navigate(`/support/${s.case_id}`)} className="hover-bg-beige" css={{ cursor: 'pointer' }}>
                         <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                            <Icon name={s.status === 'Resolved' ? 'check-circle' : 'alert-circle'} size={14} color={s.status === 'Resolved' ? 'var(--success)' : 'var(--ink-mute)'} />
                            <div style={{ display: 'flex', flexDirection: 'column', gap: '2px' }}>
                               <span style={rowTitleStyle}>{s.case_id}</span>
                               <span style={rowSubtextStyle}>{s.subject}</span>
                            </div>
                         </div>
                         <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                            <span style={rowSubtextStyle}>{s.created_at ? new Date(s.created_at).toLocaleDateString() : '-'}</span>
                            <Badge text={s.status || 'Open'} variant={s.status === 'Resolved' ? 'success' : 'warning'} />
                         </div>
                      </div>
                    ))
                  )}
               </div>
               {supportCases.length > 0 && (
                 <div style={viewAllStyle} onClick={() => customers.length > 0 ? navigate(`/support?customer_id=${customers[0].customer_id}`) : null}>View all support cases →</div>
               )}
            </div>

          </div>

      </div>

      {isNoteModalOpen && (
        <NoteModal
          isOpen={isNoteModalOpen}
          onClose={() => setIsNoteModalOpen(false)}
          companyId={id}
          salesRepId={company?.account_owner_rep_id}
          onSaved={fetchActivities}
        />
      )}
    </div>
  );
}
