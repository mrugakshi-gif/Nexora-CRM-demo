import React, { useState, useEffect } from 'react';
import { useParams, useNavigate, Link } from 'react-router-dom';
import Icon from '../components/common/Icon';
import Badge from '../components/common/Badge';
import OpportunityEditModal from '../components/common/OpportunityEditModal';
import Avatar from '../components/common/Avatar';
import { Timeline, TimelineRow } from '../components/common/Timeline';
import { opportunityService, companyService, activityService } from '../services/crmService';

export default function OpportunityDetail() {
  const { id } = useParams();
  const navigate = useNavigate();
  
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [opportunity, setOpportunity] = useState(null);
  const [company, setCompany] = useState(null);
  const [history, setHistory] = useState([]);
  const [products, setProducts] = useState([]);
  const [activities, setActivities] = useState([]);
  const [dealHealth, setDealHealth] = useState(null);
  const [isEditModalOpen, setIsEditModalOpen] = useState(false);

  const loadData = async () => {
    setLoading(true);
    setError(null);
    try {
      const oppRes = await opportunityService.getOpportunity(id);
      setOpportunity(oppRes.data);
      
      const companyId = oppRes.data.company_id;

      const [histRes, prodRes, compRes, actRes, healthRes] = await Promise.all([
        opportunityService.getOpportunityHistory(id).catch(() => ({ data: [] })),
        opportunityService.getOpportunityProducts(id).catch(() => ({ data: [] })),
        companyId ? companyService.getCompany(companyId).catch(() => ({ data: null })) : Promise.resolve({ data: null }),
        activityService.getActivities({ opportunity_id: id }).catch(() => ({ data: [] })),
        opportunityService.getOpportunityHealth(id).catch(() => ({ data: null }))
      ]);
      
      setHistory(histRes.data?.items || histRes.data || []);
      setProducts(prodRes.data?.items || prodRes.data || []);
      setCompany(compRes.data);
      setActivities(actRes.data?.items || actRes.data || []);
      setDealHealth(healthRes.data || null);
    } catch (err) {
      console.error("Failed to load opportunity", err);
      setError("Failed to load opportunity details.");
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadData();
  }, [id]);

  if (loading) return <div style={{ padding: 28 }}>Loading opportunity details...</div>;
  if (error) return (
    <div style={{ padding: 28 }}>
      <div className="empty-state">
        <div className="empty-title">Error</div>
        <div className="empty-desc">{error}</div>
        <button onClick={() => navigate('/opportunities')} style={{ marginTop: 16 }}>Back to Opportunities</button>
      </div>
    </div>
  );
  if (!opportunity) return (
    <div style={{ padding: 28 }}>
      <div className="empty-state">
        <div className="empty-title">Not Found</div>
        <div className="empty-desc">Opportunity not found.</div>
        <button onClick={() => navigate('/opportunities')} style={{ marginTop: 16 }}>Back to Opportunities</button>
      </div>
    </div>
  );

  const formatINR = (val) => new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR', maximumFractionDigits: 0 }).format(val);
  const expectedCloseDate = opportunity.expected_close_date ? new Date(opportunity.expected_close_date) : null;
  const weightedValue = (opportunity.deal_value_inr || 0) * (opportunity.probability_pct || 0) / 100;
  
  // Calculate days left for expected close date
  let daysLeftText = '';
  if (expectedCloseDate) {
    const today = new Date();
    const diffTime = expectedCloseDate - today;
    const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24));
    if (diffDays > 0) {
      daysLeftText = `In ${diffDays} day${diffDays !== 1 ? 's' : ''}`;
    } else if (diffDays === 0) {
      daysLeftText = 'Today';
    } else {
      daysLeftText = `${Math.abs(diffDays)} day${Math.abs(diffDays) !== 1 ? 's' : ''} ago`;
    }
  }

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
    color: 'var(--brown)'
  };

  const rowStyle = {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    padding: '12px 20px',
    borderBottom: '1px solid var(--border-soft)',
    fontSize: '13px'
  };

  return (
    <div className="page" style={{ padding: '24px 28px', maxWidth: '1400px', margin: '0 auto', background: 'var(--beige)', minHeight: '100vh' }}>
      
      {/* ── Back link ── */}
      <div
        style={{ display: 'inline-flex', alignItems: 'center', gap: '6px', fontSize: '12px', fontWeight: 600, color: 'var(--ink-mute)', cursor: 'pointer', marginBottom: '18px' }}
        onClick={() => navigate('/opportunities')}
      >
        <Icon name="chevronleft" size={14} color="currentColor" stroke={2.2} />
        Back to Opportunities
      </div>

      {/* 1. OPPORTUNITY HEADER */}
      <div style={{ background: 'var(--white)', border: '1px solid var(--border)', borderRadius: '16px', padding: '24px 32px', display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '24px', boxShadow: '0 2px 12px rgba(0,0,0,0.03)' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '20px' }}>
          
          <Avatar 
            name={company?.company_name || opportunity.opportunity_name}
            size={64}
            style={{ borderRadius: '14px', boxShadow: 'var(--clay-shadow-sm)' }}
          />
          
          <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
             <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                <h1 style={{ fontSize: '24px', fontWeight: 700, color: 'var(--brown)', margin: 0, letterSpacing: '-0.3px' }}>{opportunity.opportunity_name}</h1>
             </div>
             <div style={{ display: 'flex', alignItems: 'center', gap: '12px', color: 'var(--ink-mute)', fontSize: '13px', fontWeight: 500 }}>
                <Badge text={opportunity.pipeline_stage || 'Unknown'} variant="neutral" />
                <Badge text={opportunity.close_outcome ? opportunity.close_outcome.toUpperCase() : 'OPEN'} variant={opportunity.close_outcome === 'won' ? 'success' : (opportunity.close_outcome === 'lost' ? 'error' : 'secondary')} />
                {dealHealth && (
                  <Badge 
                    text={`Risk: ${dealHealth.risk_level}`} 
                    variant={dealHealth.risk_level === 'Low' ? 'success' : (dealHealth.risk_level === 'Medium' ? 'warning' : 'error')} 
                  />
                )}
                {company && <span style={{display: 'flex', gap: 6, alignItems: 'center'}}>Company: <span style={{ textDecoration: 'underline', cursor: 'pointer' }} onClick={() => navigate(`/companies/${company.company_id}`)}>{company.company_name}</span></span>}
             </div>
          </div>
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: '32px' }}>
           <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-end', gap: '4px' }}>
              <span style={{ fontSize: '20px', fontWeight: 700, color: 'var(--brown)' }}>{formatINR(opportunity.deal_value_inr || 0)}</span>
              <span style={{ fontSize: '12px', color: 'var(--ink-mute)' }}>Deal Value</span>
           </div>
           <div style={{ width: '1px', height: '36px', background: 'var(--border)' }}></div>
           <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-end', gap: '4px' }}>
              <span style={{ fontSize: '20px', fontWeight: 700, color: 'var(--brown)' }}>{opportunity.probability_pct}%</span>
              <span style={{ fontSize: '12px', color: 'var(--ink-mute)' }}>Probability</span>
           </div>
           
           <button onClick={() => setIsEditModalOpen(true)} style={{ background: 'var(--brown)', border: 'none', borderRadius: '8px', padding: '10px 16px', display: 'flex', alignItems: 'center', gap: '8px', fontSize: '13px', fontWeight: 600, color: 'var(--ivory)', cursor: 'pointer' }}>
             <Icon name="edit-2" size={14} /> Edit Opportunity
           </button>
           <button style={{ background: 'var(--white)', border: '1px solid var(--border)', borderRadius: '8px', padding: '10px', display: 'flex', alignItems: 'center', justifyContent: 'center', cursor: 'pointer' }}>
             <Icon name="more-vertical" size={14} color="var(--ink)" />
           </button>
        </div>
      </div>

      <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
          
          {/* KPI CARDS GRID */}
          <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '16px' }}>
            
            <div style={{ background: 'var(--white)', border: '1px solid var(--border)', borderRadius: '12px', padding: '20px', boxShadow: '0 2px 8px rgba(0,0,0,0.02)', display: 'flex', alignItems: 'flex-start', gap: '16px' }}>
              <div style={{ width: '40px', height: '40px', borderRadius: '8px', background: 'var(--beige)', color: 'var(--brown)', display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0 }}>
                <Icon name="dollar-sign" size={20} />
              </div>
              <div style={{ display: 'flex', flexDirection: 'column' }}>
                <span style={{ fontSize: '12px', fontWeight: 600, color: 'var(--ink-mute)', marginBottom: '4px' }}>Deal Value</span>
                <span style={{ fontSize: '20px', fontWeight: 700, color: 'var(--brown)' }}>{formatINR(opportunity.deal_value_inr || 0)}</span>
              </div>
            </div>

            <div style={{ background: 'var(--white)', border: '1px solid var(--border)', borderRadius: '12px', padding: '20px', boxShadow: '0 2px 8px rgba(0,0,0,0.02)', display: 'flex', alignItems: 'flex-start', gap: '16px' }}>
              <div style={{ width: '40px', height: '40px', borderRadius: '8px', background: 'var(--beige)', color: 'var(--brown)', display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0 }}>
                <Icon name="percent" size={20} />
              </div>
              <div style={{ display: 'flex', flexDirection: 'column', width: '100%' }}>
                <span style={{ fontSize: '12px', fontWeight: 600, color: 'var(--ink-mute)', marginBottom: '4px' }}>Probability</span>
                <span style={{ fontSize: '20px', fontWeight: 700, color: 'var(--brown)', marginBottom: '8px' }}>{opportunity.probability_pct}%</span>
                <div style={{ width: '100%', height: '6px', background: 'var(--beige)', borderRadius: '3px', overflow: 'hidden' }}>
                  <div style={{ width: `${opportunity.probability_pct}%`, height: '100%', background: 'var(--brown)' }}></div>
                </div>
              </div>
            </div>

            <div style={{ background: 'var(--white)', border: '1px solid var(--border)', borderRadius: '12px', padding: '20px', boxShadow: '0 2px 8px rgba(0,0,0,0.02)', display: 'flex', alignItems: 'flex-start', gap: '16px' }}>
              <div style={{ width: '40px', height: '40px', borderRadius: '8px', background: 'var(--beige)', color: 'var(--brown)', display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0 }}>
                <Icon name="calendar" size={20} />
              </div>
              <div style={{ display: 'flex', flexDirection: 'column' }}>
                <span style={{ fontSize: '12px', fontWeight: 600, color: 'var(--ink-mute)', marginBottom: '4px' }}>Expected Close Date</span>
                <span style={{ fontSize: '20px', fontWeight: 700, color: 'var(--brown)', marginBottom: '4px' }}>
                  {expectedCloseDate ? expectedCloseDate.toLocaleDateString('en-GB', { day: 'numeric', month: 'short', year: 'numeric' }) : 'N/A'}
                </span>
                {daysLeftText && <span style={{ fontSize: '12px', color: 'var(--ink-mute)' }}><Icon name="clock" size={10} style={{marginRight: '4px'}}/>{daysLeftText}</span>}
              </div>
            </div>

            <div style={{ background: 'var(--white)', border: '1px solid var(--border)', borderRadius: '12px', padding: '20px', boxShadow: '0 2px 8px rgba(0,0,0,0.02)', display: 'flex', alignItems: 'flex-start', gap: '16px' }}>
              <div style={{ width: '40px', height: '40px', borderRadius: '8px', background: 'var(--beige)', color: 'var(--brown)', display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0 }}>
                <Icon name="bar-chart" size={20} />
              </div>
              <div style={{ display: 'flex', flexDirection: 'column' }}>
                <span style={{ fontSize: '12px', fontWeight: 600, color: 'var(--ink-mute)', marginBottom: '4px' }}>Weighted Pipeline Value</span>
                <span style={{ fontSize: '20px', fontWeight: 700, color: 'var(--brown)', marginBottom: '4px' }}>{formatINR(weightedValue)}</span>
                <span style={{ fontSize: '12px', color: 'var(--ink-mute)' }}>{formatINR(opportunity.deal_value_inr || 0)} × {opportunity.probability_pct}%</span>
              </div>
            </div>

          </div>

          {/* DEAL RISK & HEALTH ASSESSMENT PANEL */}
          {dealHealth && (
            <div style={{
              background: 'var(--white)',
              border: '1px solid var(--border)',
              borderRadius: '16px',
              padding: '22px 26px',
              boxShadow: '0 2px 10px rgba(0,0,0,0.02)',
              display: 'flex',
              flexDirection: 'column',
              gap: '16px'
            }}>
              <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '12px' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                  <div style={{ width: '40px', height: '40px', borderRadius: '10px', background: 'var(--beige)', color: 'var(--brown)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                    <Icon name="activity" size={20} />
                  </div>
                  <div>
                    <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                      <span style={{ fontSize: '16px', fontWeight: 700, color: 'var(--brown)' }}>Deal Risk & Health Assessment</span>
                      <span style={{ fontSize: '11px', background: 'var(--bg-subtle)', padding: '2px 8px', borderRadius: '6px', color: 'var(--ink-mute)', fontWeight: 600 }}>
                        Rule-Based Heuristic
                      </span>
                    </div>
                    <span style={{ fontSize: '12px', color: 'var(--ink-mute)' }}>
                      Evaluated across timeline adherence, stage velocity, product discounting, and engagement touchpoints
                    </span>
                  </div>
                </div>

                <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
                  <div style={{ textAlign: 'right' }}>
                    <span style={{ fontSize: '11px', color: 'var(--ink-mute)', display: 'block' }}>Health Score</span>
                    <span style={{ fontSize: '20px', fontWeight: 800, color: dealHealth.health_score >= 60 ? 'var(--success)' : (dealHealth.health_score >= 40 ? 'var(--warning)' : 'var(--danger)') }}>
                      {dealHealth.health_score}/100
                    </span>
                  </div>
                  <Badge 
                    text={`${dealHealth.risk_level.toUpperCase()} RISK (${dealHealth.risk_score}%)`}
                    variant={dealHealth.risk_level === 'Low' ? 'success' : (dealHealth.risk_level === 'Medium' ? 'warning' : 'error')}
                  />
                </div>
              </div>

              {/* Factors and Recommendations */}
              <div style={{ display: 'grid', gridTemplateColumns: '1.2fr 1fr', gap: '24px', paddingTop: '16px', borderTop: '1px solid var(--border-soft)' }}>
                <div>
                  <span style={{ fontSize: '12px', fontWeight: 700, color: 'var(--ink-soft)', textTransform: 'uppercase', letterSpacing: '0.4px', display: 'block', marginBottom: '10px' }}>
                    Contributing Signals ({dealHealth.contributing_factors.length})
                  </span>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                    {dealHealth.contributing_factors.length === 0 ? (
                      <span style={{ fontSize: '13px', color: 'var(--ink-mute)' }}>No adverse signals detected.</span>
                    ) : (
                      dealHealth.contributing_factors.map((f, idx) => (
                        <div key={idx} style={{ display: 'flex', alignItems: 'flex-start', gap: '8px', fontSize: '13px', color: 'var(--ink)' }}>
                          <span style={{ 
                            color: f.impact === 'positive' ? 'var(--success)' : (f.impact === 'negative' ? 'var(--danger)' : 'var(--ink-mute)'),
                            fontWeight: 700,
                            flexShrink: 0,
                            marginTop: '1px'
                          }}>
                            {f.impact === 'positive' ? '✓' : (f.impact === 'negative' ? '⚠' : '•')}
                          </span>
                          <div>
                            <strong style={{ color: 'var(--heading-primary)', marginRight: '4px' }}>{f.name}:</strong>
                            <span style={{ color: 'var(--ink-soft)' }}>{f.detail}</span>
                          </div>
                        </div>
                      ))
                    )}
                  </div>
                </div>

                <div>
                  <span style={{ fontSize: '12px', fontWeight: 700, color: 'var(--ink-soft)', textTransform: 'uppercase', letterSpacing: '0.4px', display: 'block', marginBottom: '10px' }}>
                    Actionable Recommendations
                  </span>
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                    {dealHealth.mitigation_recommendations.map((rec, idx) => (
                      <div key={idx} style={{ display: 'flex', alignItems: 'flex-start', gap: '8px', fontSize: '13px', color: 'var(--ink-soft)' }}>
                        <span style={{ color: 'var(--accent-primary)', fontWeight: 700, flexShrink: 0, marginTop: '1px' }}>→</span>
                        <span>{rec}</span>
                      </div>
                    ))}
                  </div>
                </div>
              </div>
            </div>
          )}

          {/* MAIN INFORMATION CARDS */}
          <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr 1fr', gap: '24px' }}>
            
            {/* Opportunity Details */}
            <div style={cardStyle}>
              <div style={cardHeaderStyle}>
                <div style={cardTitleStyle}><Icon name="file-text" size={16} /> Opportunity Details</div>
              </div>
              <div style={{ padding: '0', display: 'flex', flexDirection: 'column' }}>
                <div style={rowStyle}>
                  <span style={{ color: 'var(--ink-mute)', fontWeight: 500 }}>Opportunity ID</span>
                  <span style={{ color: 'var(--ink)', fontWeight: 600 }}>{opportunity.opportunity_id}</span>
                </div>
                <div style={rowStyle}>
                  <span style={{ color: 'var(--ink-mute)', fontWeight: 500 }}>Pipeline Stage</span>
                  <span style={{ color: 'var(--ink)', fontWeight: 600 }}>{opportunity.pipeline_stage}</span>
                </div>
                <div style={rowStyle}>
                  <span style={{ color: 'var(--ink-mute)', fontWeight: 500 }}>Status</span>
                  <Badge text={opportunity.close_outcome ? opportunity.close_outcome.toUpperCase() : 'OPEN'} variant={opportunity.close_outcome === 'won' ? 'success' : (opportunity.close_outcome === 'lost' ? 'error' : 'secondary')} />
                </div>
                <div style={rowStyle}>
                  <span style={{ color: 'var(--ink-mute)', fontWeight: 500 }}>Expected Close Date</span>
                  <span style={{ color: 'var(--ink)', fontWeight: 600 }}>{expectedCloseDate ? expectedCloseDate.toLocaleDateString('en-GB') : 'N/A'}</span>
                </div>
                <div style={rowStyle}>
                  <span style={{ color: 'var(--ink-mute)', fontWeight: 500 }}>Assigned Rep ID</span>
                  <span style={{ color: 'var(--ink)', fontWeight: 600 }}>{opportunity.owner_rep_id || 'Unassigned'}</span>
                </div>
                <div style={rowStyle}>
                  <span style={{ color: 'var(--ink-mute)', fontWeight: 500 }}>Created At</span>
                  <span style={{ color: 'var(--ink)', fontWeight: 600 }}>{new Date(opportunity.created_at).toLocaleString('en-GB')}</span>
                </div>
                <div style={rowStyle}>
                  <span style={{ color: 'var(--ink-mute)', fontWeight: 500 }}>Last Updated</span>
                  <span style={{ color: 'var(--ink)', fontWeight: 600 }}>{new Date(opportunity.updated_at).toLocaleString('en-GB')}</span>
                </div>
              </div>
            </div>

            {/* Company / Account */}
            <div style={cardStyle}>
              <div style={cardHeaderStyle}>
                <div style={cardTitleStyle}><Icon name="building" size={16} /> Company / Account</div>
              </div>
              <div style={{ padding: '16px 20px', display: 'flex', flexDirection: 'column', gap: '16px', flex: 1 }}>
                {company ? (
                  <>
                    <span 
                      style={{ fontSize: '15px', fontWeight: 600, color: 'var(--blue)', textDecoration: 'underline', cursor: 'pointer', display: 'flex', alignItems: 'center', gap: '4px' }}
                      onClick={() => navigate(`/companies/${company.company_id}`)}
                    >
                      {company.company_name} <Icon name="external-link" size={14} />
                    </span>
                    <div style={{ display: 'grid', gridTemplateColumns: '120px 1fr', gap: '12px', fontSize: '13px' }}>
                      <span style={{ color: 'var(--ink-mute)', fontWeight: 500 }}>Company ID</span>
                      <span style={{ color: 'var(--ink)', fontWeight: 600 }}>{company.company_id}</span>
                      
                      <span style={{ color: 'var(--ink-mute)', fontWeight: 500 }}>Industry</span>
                      <span style={{ color: 'var(--ink)', fontWeight: 600 }}>{company.industry_id || '-'}</span>
                      
                      <span style={{ color: 'var(--ink-mute)', fontWeight: 500 }}>Account Status</span>
                      <span><Badge text={company.account_status || 'Prospect'} variant={company.account_status === 'Active Customer' ? 'success' : 'neutral'} /></span>
                      
                      <span style={{ color: 'var(--ink-mute)', fontWeight: 500 }}>Phone</span>
                      <span style={{ color: 'var(--ink)', fontWeight: 600 }}>{company.phone || '-'}</span>
                      
                      <span style={{ color: 'var(--ink-mute)', fontWeight: 500 }}>Email</span>
                      <span style={{ color: 'var(--blue)', fontWeight: 600, textDecoration: 'underline' }}>{company.email || '-'}</span>
                      
                      <span style={{ color: 'var(--ink-mute)', fontWeight: 500 }}>Location</span>
                      <span style={{ color: 'var(--ink)', fontWeight: 600 }}>{[company.city, company.state].filter(Boolean).join(', ') || '-'}</span>
                    </div>
                  </>
                ) : (
                  <div style={{ fontSize: '13px', color: 'var(--ink-mute)' }}>No company details available.</div>
                )}
                
                <div style={{ marginTop: 'auto', paddingTop: '16px' }}>
                  <button 
                    onClick={() => company && navigate(`/companies/${company.company_id}`)}
                    style={{ width: '100%', padding: '10px', background: 'var(--beige)', border: 'none', borderRadius: '8px', fontSize: '13px', fontWeight: 600, color: 'var(--brown)', cursor: 'pointer', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '6px' }}
                    disabled={!company}
                  >
                    View Company Overview <Icon name="external-link" size={14} />
                  </button>
                </div>
              </div>
            </div>

            {/* Stage History */}
            <div style={cardStyle}>
              <div style={cardHeaderStyle}>
                <div style={cardTitleStyle}><Icon name="clock" size={16} /> Stage History</div>
              </div>
              <div style={{ padding: '16px 20px', flex: 1, overflowY: 'auto', maxHeight: '350px' }}>
                {history.length === 0 ? (
                  <div style={{ fontSize: '13px', color: 'var(--ink-mute)', textAlign: 'center', padding: '20px 0' }}>No stage transitions recorded.</div>
                ) : (
                  <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
                    {history.map((h, i) => (
                      <div key={h.history_id} style={{ display: 'flex', gap: '12px' }}>
                        <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
                          <div style={{ width: '12px', height: '12px', borderRadius: '50%', background: i === 0 ? 'var(--brown)' : 'var(--border)', marginTop: '4px' }}></div>
                          {i !== history.length - 1 && <div style={{ width: '2px', flex: 1, background: 'var(--border-soft)', marginTop: '4px', minHeight: '30px' }}></div>}
                        </div>
                        <div style={{ display: 'flex', flexDirection: 'column', gap: '4px', paddingBottom: '16px' }}>
                          <span style={{ fontSize: '13px', fontWeight: 600, color: 'var(--ink)' }}>{h.stage_to}</span>
                          <span style={{ fontSize: '12px', color: 'var(--ink-mute)' }}>{new Date(h.changed_at).toLocaleString('en-GB')}</span>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>
          </div>

          {/* LOWER CARDS */}
          <div style={{ display: 'grid', gridTemplateColumns: '1.5fr 1fr', gap: '24px' }}>
            
            {/* Products */}
            <div style={cardStyle}>
              <div style={cardHeaderStyle}>
                <div style={cardTitleStyle}><Icon name="package" size={16} /> Products ({products.length})</div>
              </div>
              <div style={{ padding: '0', overflowX: 'auto' }}>
                {products.length === 0 ? (
                  <div style={{ padding: '30px', textAlign: 'center', fontSize: '13px', color: 'var(--ink-mute)' }}>No products attached to this opportunity.</div>
                ) : (
                  <table style={{ width: '100%', borderCollapse: 'collapse', fontSize: '13px' }}>
                    <thead>
                      <tr style={{ borderBottom: '1px solid var(--border-soft)', textAlign: 'left' }}>
                        <th style={{ padding: '12px 20px', fontWeight: 600, color: 'var(--ink-soft)' }}>Product</th>
                        <th style={{ padding: '12px 20px', fontWeight: 600, color: 'var(--ink-soft)', textAlign: 'right' }}>Quantity</th>
                        <th style={{ padding: '12px 20px', fontWeight: 600, color: 'var(--ink-soft)', textAlign: 'right' }}>List Price (₹)</th>
                        <th style={{ padding: '12px 20px', fontWeight: 600, color: 'var(--ink-soft)', textAlign: 'right' }}>Discount</th>
                        <th style={{ padding: '12px 20px', fontWeight: 600, color: 'var(--ink-soft)', textAlign: 'right' }}>Line Total (₹)</th>
                      </tr>
                    </thead>
                    <tbody>
                      {products.map((p, i) => (
                        <tr key={i} style={{ borderBottom: '1px solid var(--border-light)' }}>
                          <td style={{ padding: '12px 20px', color: 'var(--blue)', fontWeight: 500, textDecoration: 'underline' }}>{p.product_id}</td>
                          <td style={{ padding: '12px 20px', textAlign: 'right', fontWeight: 500 }}>{p.quantity}</td>
                          <td style={{ padding: '12px 20px', textAlign: 'right' }}>{p.unit_price_inr?.toLocaleString('en-IN', { minimumFractionDigits: 2 })}</td>
                          <td style={{ padding: '12px 20px', textAlign: 'right' }}>{p.discount_pct}%</td>
                          <td style={{ padding: '12px 20px', textAlign: 'right', fontWeight: 600 }}>{p.line_total_inr?.toLocaleString('en-IN', { minimumFractionDigits: 2 })}</td>
                        </tr>
                      ))}
                      <tr style={{ background: 'var(--beige)' }}>
                        <td colSpan="4" style={{ padding: '12px 20px', textAlign: 'right', fontWeight: 700 }}>Total</td>
                        <td style={{ padding: '12px 20px', textAlign: 'right', fontWeight: 700, color: 'var(--brown)' }}>{formatINR(products.reduce((acc, p) => acc + (p.line_total_inr || 0), 0))}</td>
                      </tr>
                    </tbody>
                  </table>
                )}
              </div>
            </div>

            {/* Related Activities */}
            <div style={cardStyle}>
              <div style={cardHeaderStyle}>
                <div style={cardTitleStyle}><Icon name="check-square" size={16} /> Related Activities ({activities.length})</div>
                <span style={{ fontSize: '12px', fontWeight: 600, color: 'var(--brown)', cursor: 'pointer', textDecoration: 'underline' }}>View All</span>
              </div>
              <div style={{ padding: '0', display: 'flex', flexDirection: 'column' }}>
                {activities.length === 0 ? (
                  <div style={{ padding: '30px', textAlign: 'center', fontSize: '13px', color: 'var(--ink-mute)' }}>No related activities.</div>
                ) : (
                  activities.slice(0, 5).map((a, i) => (
                    <div key={a.activity_id} style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '16px 20px', borderBottom: '1px solid var(--border-soft)' }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                        <div style={{ width: '36px', height: '36px', borderRadius: '8px', background: 'var(--beige)', color: 'var(--blue)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
                          <Icon name={a.activity_type?.toLowerCase() === 'meeting' ? 'users' : a.activity_type?.toLowerCase() === 'call' ? 'phone' : 'mail'} size={18} />
                        </div>
                        <div style={{ display: 'flex', flexDirection: 'column', gap: '2px' }}>
                          <span style={{ fontSize: '13px', fontWeight: 600, color: 'var(--blue)' }}>{a.activity_type}</span>
                          <span style={{ fontSize: '12px', color: 'var(--ink-mute)' }}>{a.description?.substring(0, 40)}{a.description?.length > 40 ? '...' : ''}</span>
                        </div>
                      </div>
                      <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-end', gap: '4px' }}>
                        <span style={{ fontSize: '12px', color: 'var(--ink-mute)' }}>{a.scheduled_at ? new Date(a.scheduled_at).toLocaleString('en-GB', { day: 'numeric', month: 'numeric', year: 'numeric', hour: '2-digit', minute: '2-digit' }) : ''}</span>
                        <Icon name="more-vertical" size={14} color="var(--ink-mute)" style={{ cursor: 'pointer' }} />
                      </div>
                    </div>
                  ))
                )}
              </div>
            </div>

          </div>
      </div>
      
      {opportunity && (
        <OpportunityEditModal 
          isOpen={isEditModalOpen} 
          onClose={() => setIsEditModalOpen(false)} 
          onSave={() => {
            setIsEditModalOpen(false);
            loadData();
          }} 
          editingOpp={opportunity} 
        />
      )}
    </div>
  );
}
