import React, { useState, useEffect } from 'react';
import { Sparkles, TrendingUp } from 'lucide-react';
import PageHeader from '../components/common/PageHeader';
import { mlService } from '../services/mlService';
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, Legend, ResponsiveContainer, PieChart, Pie, Cell, ScatterChart, Scatter, ZAxis } from 'recharts';

export default function MlInsights() {
  const [forecast, setForecast] = useState(null);
  const [forecastLoading, setForecastLoading] = useState(true);
  const [forecastError, setForecastError] = useState(false);

  const [aggLeads, setAggLeads] = useState(null);
  const [aggLeadsLoading, setAggLeadsLoading] = useState(true);
  const [aggLeadsError, setAggLeadsError] = useState(false);

  const [aggRisk, setAggRisk] = useState(null);
  const [aggRiskLoading, setAggRiskLoading] = useState(true);
  const [aggRiskError, setAggRiskError] = useState(false);

  const [aggSegments, setAggSegments] = useState(null);
  const [aggSegmentsLoading, setAggSegmentsLoading] = useState(true);
  const [aggSegmentsError, setAggSegmentsError] = useState(false);

  const formatCurrency = (val) => {
    return new Intl.NumberFormat('en-IN', { style: 'currency', currency: 'INR', maximumFractionDigits: 0 }).format(val);
  };
  
  const formatPct = (val) => {
    if (val >= 0.99) return (val * 100).toFixed(2) + '%';
    return (val * 100).toFixed(1) + '%';
  };

  useEffect(() => {
    mlService.getSalesForecast()
      .then(res => { setForecast(res.data); setForecastLoading(false); })
      .catch(err => { console.error(err); setForecastError(true); setForecastLoading(false); });

    mlService.getAggregateLeads()
      .then(res => { setAggLeads(res.data); setAggLeadsLoading(false); })
      .catch(err => { console.error(err); setAggLeadsError(true); setAggLeadsLoading(false); });

    mlService.getAggregateCustomerRisk()
      .then(res => { setAggRisk(res.data); setAggRiskLoading(false); })
      .catch(err => { console.error(err); setAggRiskError(true); setAggRiskLoading(false); });

    mlService.getAggregateCustomerSegments()
      .then(res => { setAggSegments(res.data); setAggSegmentsLoading(false); })
      .catch(err => { console.error(err); setAggSegmentsError(true); setAggSegmentsLoading(false); });
  }, []);

  const sectionStyle = {
    marginBottom: '24px',
    background: 'var(--white)',
    padding: '24px',
    borderRadius: '14px',
    border: '1px solid var(--border)',
    boxShadow: '0 4px 12px rgba(43,34,28,0.02)',
    display: 'flex',
    flexDirection: 'column'
  };

  const sectionTitleStyle = {
    fontSize: '16px',
    fontWeight: 700,
    color: 'var(--heading-primary)',
    marginBottom: '16px',
    letterSpacing: '0.2px'
  };
  
  const insightStyle = {
    display: 'flex',
    gap: '12px',
    padding: '14px 16px',
    background: 'var(--bg-subtle)',
    borderRadius: '10px',
    borderLeft: '3px solid var(--accent-primary)',
    border: '1px solid var(--border-soft)',
    borderLeftWidth: '3px',
    borderLeftColor: 'var(--accent-primary)',
    marginBottom: '20px',
    alignItems: 'flex-start',
    boxShadow: 'var(--clay-shadow-sm)'
  };
  
  const insightIconStyle = {
    color: 'var(--accent-primary)',
    flexShrink: 0,
    marginTop: '2px'
  };

  const insightTextStyle = {
    fontSize: '13.5px',
    color: 'var(--ink-soft)',
    lineHeight: '1.5',
    fontWeight: 500
  };
  
  const insightLabelStyle = {
    fontSize: '11px',
    fontWeight: 800,
    textTransform: 'uppercase',
    color: 'var(--heading-primary)',
    letterSpacing: '0.6px',
    marginBottom: '4px',
    display: 'block'
  };
  
  const rowStyle = {
    display: 'flex', 
    justifyContent: 'space-between', 
    padding: '14px 16px',
    borderBottom: '1px solid var(--border)',
    alignItems: 'center'
  };

  const generateHistogramData = (data, key) => {
    if (!data) return [];
    const bins = Array(10).fill(0).map((_, i) => ({ name: `${i*10}-${(i+1)*10}`, count: 0 }));
    data.forEach(item => {
      const val = item[key];
      const binIdx = Math.min(9, Math.floor(val * 10));
      bins[binIdx].count += 1;
    });
    return bins;
  };

  const COLORS = ['#3B82F6', '#0D9488', '#10B981', '#F59E0B', '#6366F1']; 
  const RISK_COLORS = ['#EF4444', '#F97316', '#F59E0B', '#10B981', '#3B82F6'];
  
  const DIST_COLORS = [
    '#3B82F6', '#2563EB', '#1D4ED8', '#0D9488', '#059669', 
    '#10B981', '#F59E0B', '#F97316', '#EF4444', '#6366F1'
  ];

  const segmentData = aggSegments && aggSegments.distribution ? Object.entries(aggSegments.distribution).map(([k, v]) => ({ name: `Cluster ${k}`, value: v })) : [];
  const totalSegments = segmentData.reduce((acc, curr) => acc + curr.value, 0);

  const leadScoreData = generateHistogramData(aggLeads?.top_leads, 'score_probability');
  const convScoreData = generateHistogramData(aggLeads?.top_leads, 'conversion_probability');
  const churnData = generateHistogramData(aggRisk?.top_at_risk_customers, 'churn_probability');

  const scatterData = aggLeads?.top_leads?.map(l => ({
    x: l.score_probability * 100,
    y: l.conversion_probability * 100,
    name: l.company_name
  })) || [];

  const commonChartProps = {
    margin: { top: 10, right: 10, left: -20, bottom: 20 }
  };
  const axisProps = {
    tick: { fontSize: 11.5, fill: 'var(--ink-soft)', fontWeight: 500 },
    axisLine: { stroke: 'var(--border)' },
    tickLine: { stroke: 'var(--border)' }
  };
  const gridProps = {
    strokeDasharray: "4 4",
    vertical: false,
    stroke: 'var(--border-soft)'
  };
  const tooltipStyle = {
    contentStyle: { backgroundColor: 'var(--ivory)', border: '1px solid var(--border)', borderRadius: '8px', fontSize: '13px', color: 'var(--ink)', boxShadow: '0 4px 12px rgba(43,34,28,0.1)' },
    itemStyle: { color: 'var(--brown)', fontWeight: 600 }
  };

  const CustomPieTooltip = ({ active, payload }) => {
    if (active && payload && payload.length) {
      const data = payload[0].payload;
      const pct = totalSegments > 0 ? ((data.value / totalSegments) * 100).toFixed(1) : 0;
      return (
        <div style={{ backgroundColor: 'var(--ivory)', border: '1px solid var(--border)', padding: '12px', borderRadius: '8px', boxShadow: '0 4px 12px rgba(43,34,28,0.1)' }}>
          <div style={{ fontSize: '13px', fontWeight: 700, color: 'var(--brown)', marginBottom: '4px' }}>{data.name}</div>
          <div style={{ fontSize: '12.5px', color: 'var(--ink-soft)' }}>
            Customers: <span style={{ fontWeight: 600, color: 'var(--brown)' }}>{data.value}</span>
          </div>
          <div style={{ fontSize: '12.5px', color: 'var(--ink-soft)' }}>
            Total: <span style={{ fontWeight: 600, color: 'var(--brown)' }}>{pct}%</span>
          </div>
        </div>
      );
    }
    return null;
  };

  return (
    <div className="page" style={{ display: 'flex', flexDirection: 'column', height: '100%', overflowY: 'auto', backgroundColor: 'var(--ivory)' }}>
      <PageHeader 
        title="ML Aggregate Intelligence" 
        desc="Batch predictive analytics across authorized accounts."
      />

      <div style={{ padding: '0 28px 28px', flex: 1, display: 'flex', flexDirection: 'column', gap: '24px' }}>
        
        {/* ROW 1: Forecast and Segmentation */}
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '24px' }}>
          
          <div style={sectionStyle}>
            <h3 style={sectionTitleStyle}>Sales Forecasting</h3>
            <div style={insightStyle}>
              <TrendingUp size={18} style={insightIconStyle} />
              <div>
                <span style={insightLabelStyle}>Forecast Methodology</span>
                <div style={insightTextStyle}>Forecast based on the average realized net cash collections across the three most recent completed calendar months.</div>
              </div>
            </div>
            {forecastLoading ? (
              <div style={{ color: 'var(--ink-mute)' }}>Loading ML forecasts...</div>
            ) : forecastError || !forecast ? (
              <div className="empty-state">
                <div className="empty-desc">Insufficient data to generate a sales forecast.</div>
              </div>
            ) : (
              <div style={{ display: 'flex', flexDirection: 'column', flex: 1, justifyContent: 'center', alignItems: 'center' }}>
                <div style={{ padding: '24px', background: 'linear-gradient(180deg, var(--beige) 0%, var(--ivory) 100%)', border: '1px solid var(--border)', borderRadius: '12px', textAlign: 'center', width: '100%', maxWidth: '300px' }}>
                  <div style={{ fontSize: '12px', fontWeight: 600, color: 'var(--ink-mute)', textTransform: 'uppercase', letterSpacing: '0.5px', marginBottom: '8px' }}>
                    Forecast: {forecast.period_description}
                  </div>
                  <div style={{ fontSize: '32px', fontWeight: 800, color: 'var(--ink)', display: 'flex', alignItems: 'center', justifyContent: 'center', gap: '8px' }}>
                    <TrendingUp size={28} color="var(--sage)" />
                    {formatCurrency(forecast.forecast_amount_inr)}
                  </div>
                  <div style={{ marginTop: '12px', display: 'inline-flex', alignItems: 'center', gap: '6px', background: 'var(--white)', padding: '4px 8px', borderRadius: '4px', fontSize: '11px', fontWeight: 600, color: 'var(--brown)', border: '1px solid var(--border)' }}>
                    {forecast.is_ml_model ? <Sparkles size={12} /> : <TrendingUp size={12} />} {
                      forecast.is_ml_model ? 'ML PREDICTION' :
                      forecast.model_identifier === 'trailing_3mo_baseline' ? '3-MONTH BASELINE' :
                      forecast.model_identifier === 'closed_won_opps_monthly_baseline' ? 'OPPORTUNITY BASELINE' :
                      forecast.model_identifier === 'historical_window_baseline' ? 'HISTORICAL BASELINE' :
                      forecast.model_identifier === 'sparse_trailing_baseline' ? 'SPARSE BASELINE' :
                      forecast.model_identifier === 'insufficient_data' ? 'INSUFFICIENT DATA' : 'STATISTICAL BASELINE'
                    }
                  </div>
                  {forecast.baseline_note && (
                    <div style={{ marginTop: '8px', fontSize: '11px', color: 'var(--ink-mute)', lineHeight: '1.4', maxWidth: '260px' }}>
                      {forecast.baseline_note}
                    </div>
                  )}
                  {forecast.data_quality_warning && (
                    <div style={{ marginTop: '6px', fontSize: '10.5px', color: '#D98341', lineHeight: '1.35', maxWidth: '260px' }}>
                      ⚠️ {forecast.data_quality_warning}
                    </div>
                  )}
                </div>
              </div>
            )}
          </div>

          <div style={sectionStyle}>
            <h3 style={sectionTitleStyle}>Customer Segments</h3>
            <div style={insightStyle}>
              <Sparkles size={18} style={insightIconStyle} />
              <div>
                <span style={insightLabelStyle}>AI Insight</span>
                <div style={insightTextStyle}>Distribution of customers across ML-generated behavioral clusters. {segmentData.length > 0 && `Cluster ${segmentData.sort((a,b)=>b.value-a.value)[0].name.replace('Cluster ','')} contains the highest concentration.`}</div>
              </div>
            </div>
            {aggSegmentsLoading ? (
              <div style={{ color: 'var(--ink-mute)' }}>Loading segments...</div>
            ) : aggSegmentsError || !aggSegments ? (
              <div className="empty-state">
                <div className="empty-desc">Unable to calculate segments.</div>
              </div>
            ) : segmentData.length === 0 ? (
              <div className="empty-state">
                <div className="empty-desc">No active customers to segment.</div>
              </div>
            ) : (
              <div style={{ height: '220px', flex: 1 }}>
                <ResponsiveContainer width="100%" height="100%">
                  <PieChart>
                    <Pie data={segmentData} cx="50%" cy="50%" innerRadius={60} outerRadius={90} paddingAngle={2} dataKey="value" nameKey="name">
                      {segmentData.map((entry, index) => (
                        <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                      ))}
                    </Pie>
                    <Tooltip content={<CustomPieTooltip />} cursor={false} />
                    <Legend wrapperStyle={{ fontSize: '12.5px', color: 'var(--ink-soft)', fontWeight: 500, paddingTop: '10px' }} />
                  </PieChart>
                </ResponsiveContainer>
              </div>
            )}
          </div>
        </div>

        {/* ROW 2: Lead Intelligence & Risk Lists */}
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '24px' }}>
          
          <div style={sectionStyle}>
            <h3 style={sectionTitleStyle}>Top 5 Active Leads</h3>
            <div style={insightStyle}>
              <Sparkles size={18} style={insightIconStyle} />
              <div>
                <span style={insightLabelStyle}>AI Insight</span>
                <div style={insightTextStyle}>Leads with the absolute highest model confidence for qualification (Score Prob), paired with their likelihood of closing (Conv Prob).</div>
              </div>
            </div>
            {aggLeadsLoading ? (
              <div style={{ color: 'var(--ink-mute)' }}>Loading leads...</div>
            ) : aggLeadsError || !aggLeads ? (
              <div className="empty-state">
                <div className="empty-desc">Leads Unavailable</div>
              </div>
            ) : aggLeads.top_leads.length === 0 ? (
              <div className="empty-state">
                <div className="empty-desc">No active leads found in pipeline.</div>
              </div>
            ) : (
              <div style={{ border: '1px solid var(--border)', borderRadius: '8px', overflow: 'hidden', flex: 1, backgroundColor: 'var(--white)' }}>
                <div style={{ ...rowStyle, background: 'var(--beige)', fontWeight: 700, fontSize: '11.5px', color: 'var(--ink-soft)', textTransform: 'uppercase', letterSpacing: '0.5px' }}>
                  <div style={{ flex: 1 }}>Company & Lead ID</div>
                  <div style={{ width: '90px', textAlign: 'right' }}>Score Prob</div>
                  <div style={{ width: '90px', textAlign: 'right' }}>Conv Prob</div>
                </div>
                {aggLeads.top_leads.slice(0, 5).map((l, idx) => (
                  <div key={l.lead_id} style={{...rowStyle, borderBottom: idx === 4 ? 'none' : '1px solid var(--border-soft)'}}>
                    <div style={{ flex: 1, whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis', paddingRight: '12px' }}>
                      <div style={{ fontWeight: 700, color: 'var(--heading-primary)', fontSize: '13.5px' }}>{l.company_name}</div>
                      <div style={{ fontSize: '12px', color: 'var(--ink-mute)', marginTop: '2px' }}>{l.lead_id}</div>
                    </div>
                    <div style={{ width: '90px', textAlign: 'right', fontWeight: 700, color: 'var(--brown)', fontSize: '13.5px' }}>{formatPct(l.score_probability)}</div>
                    <div style={{ width: '90px', textAlign: 'right', fontWeight: 700, color: 'var(--sage)', fontSize: '13.5px' }}>{formatPct(l.conversion_probability)}</div>
                  </div>
                ))}
              </div>
            )}
          </div>

          <div style={sectionStyle}>
            <h3 style={sectionTitleStyle}>Top 5 At-Risk Customers</h3>
            <div style={insightStyle}>
              <Sparkles size={18} style={insightIconStyle} />
              <div>
                <span style={insightLabelStyle}>AI Insight</span>
                <div style={insightTextStyle}>High-risk accounts based on decaying transaction patterns and recent support case volume. Immediate outreach recommended.</div>
              </div>
            </div>
            {aggRiskLoading ? (
              <div style={{ color: 'var(--ink-mute)' }}>Loading risk data...</div>
            ) : aggRiskError || !aggRisk ? (
              <div className="empty-state">
                <div className="empty-desc">Risk Data Unavailable</div>
              </div>
            ) : aggRisk.top_at_risk_customers.length === 0 ? (
              <div className="empty-state">
                <div className="empty-desc">No active customers found.</div>
              </div>
            ) : (
              <div style={{ height: '230px', flex: 1 }}>
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={aggRisk.top_at_risk_customers.slice(0, 5)} layout="vertical" margin={{ top: 5, right: 30, left: 10, bottom: 20 }}>
                    <CartesianGrid strokeDasharray="4 4" horizontal={false} stroke="var(--border-soft)" />
                    <XAxis type="number" domain={[0, 1]} tickFormatter={val => `${(val*100).toFixed(0)}%`} {...axisProps} label={{ value: 'Churn Probability', position: 'insideBottom', offset: -10, fontSize: 12, fill: 'var(--ink-soft)' }} />
                    <YAxis dataKey="company_name" type="category" width={110} {...axisProps} label={{ value: 'Customer', angle: -90, position: 'insideLeft', offset: -5, fontSize: 12, fill: 'var(--ink-soft)' }} />
                    <Tooltip {...tooltipStyle} cursor={false} formatter={(val) => [(val*100).toFixed(1)+'%', 'Churn Probability']} />
                    <Bar dataKey="churn_probability" radius={[0, 4, 4, 0]} barSize={26}>
                      {aggRisk.top_at_risk_customers.slice(0, 5).map((entry, index) => (
                        <Cell key={`cell-${index}`} fill={RISK_COLORS[index % RISK_COLORS.length]} />
                      ))}
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
              </div>
            )}
          </div>
        </div>

        {/* ROW 3: Distributions */}
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '24px' }}>
          
          <div style={sectionStyle}>
            <h3 style={sectionTitleStyle}>Lead Score Distribution</h3>
            <div style={insightStyle}>
              <Sparkles size={18} style={insightIconStyle} />
              <div>
                <span style={insightLabelStyle}>AI Insight</span>
                <div style={insightTextStyle}>Shows pipeline density by qualification probability. Notice the extreme right-skew concentration (values approaching 100%).</div>
              </div>
            </div>
            {aggLeadsLoading ? (
              <div style={{ color: 'var(--ink-mute)' }}>Loading...</div>
            ) : aggLeadsError || !aggLeads ? (
              <div className="empty-state">
                <div className="empty-desc">Data unavailable</div>
              </div>
            ) : (
              <div style={{ height: '260px', flex: 1 }}>
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={leadScoreData} {...commonChartProps}>
                    <CartesianGrid {...gridProps} />
                    <XAxis dataKey="name" {...axisProps} label={{ value: 'Lead Score Probability Range', position: 'insideBottom', offset: -10, fontSize: 12, fill: 'var(--ink-soft)' }} />
                    <YAxis allowDecimals={false} {...axisProps} label={{ value: 'Lead Count', angle: -90, position: 'insideLeft', offset: 10, fontSize: 12, fill: 'var(--ink-soft)' }} />
                    <Tooltip {...tooltipStyle} cursor={false} formatter={(val) => [val, 'Leads']} labelFormatter={(label) => `Score Range: ${label}%`} />
                    <Bar dataKey="count" radius={[4, 4, 0, 0]}>
                      {leadScoreData.map((entry, index) => (
                        <Cell key={`cell-${index}`} fill={DIST_COLORS[index % DIST_COLORS.length]} />
                      ))}
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
              </div>
            )}
          </div>

          <div style={sectionStyle}>
            <h3 style={sectionTitleStyle}>Conversion Prob Distribution</h3>
            <div style={insightStyle}>
              <Sparkles size={18} style={insightIconStyle} />
              <div>
                <span style={insightLabelStyle}>AI Insight</span>
                <div style={insightTextStyle}>Overall pipeline likelihood of closing. This distribution typically shows a wider spread than basic lead qualification scores.</div>
              </div>
            </div>
            {aggLeadsLoading ? (
              <div style={{ color: 'var(--ink-mute)' }}>Loading...</div>
            ) : aggLeadsError || !aggLeads ? (
              <div className="empty-state">
                <div className="empty-desc">Data unavailable</div>
              </div>
            ) : (
              <div style={{ height: '260px', flex: 1 }}>
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={convScoreData} {...commonChartProps}>
                    <CartesianGrid {...gridProps} />
                    <XAxis dataKey="name" {...axisProps} label={{ value: 'Conversion Probability Range', position: 'insideBottom', offset: -10, fontSize: 12, fill: 'var(--ink-soft)' }} />
                    <YAxis allowDecimals={false} {...axisProps} label={{ value: 'Lead Count', angle: -90, position: 'insideLeft', offset: 10, fontSize: 12, fill: 'var(--ink-soft)' }} />
                    <Tooltip {...tooltipStyle} cursor={false} formatter={(val) => [val, 'Leads']} labelFormatter={(label) => `Conv Range: ${label}%`} />
                    <Bar dataKey="count" radius={[4, 4, 0, 0]}>
                      {convScoreData.map((entry, index) => (
                        <Cell key={`cell-${index}`} fill={DIST_COLORS[index % DIST_COLORS.length]} />
                      ))}
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
              </div>
            )}
          </div>

        </div>

        {/* ROW 4: Scatter & Churn Risk */}
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '24px' }}>
          <div style={sectionStyle}>
            <h3 style={sectionTitleStyle}>Score vs Conversion</h3>
            <div style={insightStyle}>
              <Sparkles size={18} style={insightIconStyle} />
              <div>
                <span style={insightLabelStyle}>AI Insight</span>
                <div style={insightTextStyle}>Maps qualification strength against closing likelihood. High-score, low-conversion leads (bottom-right) may require different sales strategies.</div>
              </div>
            </div>
            {aggLeadsLoading ? (
              <div style={{ color: 'var(--ink-mute)' }}>Loading...</div>
            ) : aggLeadsError || !aggLeads ? (
              <div className="empty-state">
                <div className="empty-desc">Data unavailable</div>
              </div>
            ) : (
              <div style={{ height: '280px', flex: 1 }}>
                <ResponsiveContainer width="100%" height="100%">
                  <ScatterChart margin={{ top: 10, right: 20, bottom: 20, left: 0 }}>
                    <CartesianGrid {...gridProps} />
                    <XAxis type="number" dataKey="x" name="Lead Score" unit="%" domain={[0, 100]} {...axisProps} label={{ value: 'Lead Score Probability', position: 'insideBottom', offset: -10, fontSize: 12, fill: 'var(--ink-soft)' }} />
                    <YAxis type="number" dataKey="y" name="Conversion" unit="%" domain={[0, 100]} {...axisProps} />
                    <ZAxis type="category" dataKey="name" name="Company" />
                    <Tooltip {...tooltipStyle} cursor={false} />
                    <Scatter name="Leads" data={scatterData}>
                      {scatterData.map((entry, index) => (
                        <Cell key={`cell-${index}`} fill={DIST_COLORS[index % DIST_COLORS.length]} />
                      ))}
                    </Scatter>
                  </ScatterChart>
                </ResponsiveContainer>
              </div>
            )}
          </div>

          <div style={sectionStyle}>
            <h3 style={sectionTitleStyle}>Churn Probability Distribution</h3>
            <div style={insightStyle}>
              <Sparkles size={18} style={insightIconStyle} />
              <div>
                <span style={insightLabelStyle}>AI Insight</span>
                <div style={insightTextStyle}>Shows predicted churn probabilities across the customer base. A heavy concentration on the left (0-20%) represents accounts with low model-predicted risk.</div>
              </div>
            </div>
            {aggRiskLoading ? (
              <div style={{ color: 'var(--ink-mute)' }}>Loading...</div>
            ) : aggRiskError || !aggRisk ? (
              <div className="empty-state">
                <div className="empty-desc">Data unavailable</div>
              </div>
            ) : (
              <div style={{ height: '280px', flex: 1 }}>
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={churnData} {...commonChartProps}>
                    <CartesianGrid {...gridProps} />
                    <XAxis dataKey="name" {...axisProps} label={{ value: 'Churn Probability Range', position: 'insideBottom', offset: -10, fontSize: 12, fill: 'var(--ink-soft)' }} />
                    <YAxis allowDecimals={false} {...axisProps} label={{ value: 'Customer Count', angle: -90, position: 'insideLeft', offset: 10, fontSize: 12, fill: 'var(--ink-soft)' }} />
                    <Tooltip {...tooltipStyle} cursor={false} formatter={(val) => [val, 'Customers']} labelFormatter={(label) => `Churn Range: ${label}%`} />
                    <Bar dataKey="count" radius={[4, 4, 0, 0]}>
                      {churnData.map((entry, index) => (
                        <Cell key={`cell-${index}`} fill={DIST_COLORS[index % DIST_COLORS.length]} />
                      ))}
                    </Bar>
                  </BarChart>
                </ResponsiveContainer>
              </div>
            )}
          </div>
        </div>

      </div>
    </div>
  );
}
