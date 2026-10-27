import React, { useState } from 'react';
import { Sparkles, ChevronDown, ChevronUp } from 'lucide-react';

export default function HealthCard({ title, data, loading, error }) {
  const [riskExpanded, setRiskExpanded] = useState(false);

  const cardStyle = {
    flex: 1,
    minWidth: '280px',
    background: 'var(--white)',
    padding: '24px',
    borderRadius: '16px',
    border: '1px solid var(--border)',
    boxShadow: '0 4px 12px rgba(43,34,28,0.03)',
    display: 'flex',
    flexDirection: 'column',
    transition: 'all 0.2s ease-in-out'
  };

  const titleStyle = {
    fontSize: '15px',
    fontWeight: 700,
    color: 'var(--heading-primary)',
    marginBottom: '20px',
    letterSpacing: '0.3px',
    textTransform: 'uppercase'
  };

  const scoreContainerStyle = {
    display: 'flex',
    alignItems: 'center',
    gap: '12px',
    marginBottom: '24px'
  };

  const scoreStyle = {
    fontSize: '42px',
    fontWeight: 800,
    color: 'var(--ink)',
    lineHeight: 1
  };

  const getBadgeStyle = (status) => {
    let bg = 'var(--ivory)';
    let color = 'var(--brown)';
    if (status === 'Critical') {
        bg = '#FEE2E2'; color = 'var(--danger)';
    } else if (status === 'At Risk') {
        bg = '#FEF3C7'; color = 'var(--warning)';
    } else if (status === 'Healthy' || status === 'Excellent') {
        bg = 'rgba(110,138,94,0.18)'; color = 'var(--success)';
    }
    return {
      padding: '6px 10px',
      borderRadius: '8px',
      fontSize: '13px',
      fontWeight: 700,
      background: bg,
      color: color,
      textTransform: 'uppercase',
      letterSpacing: '0.5px'
    };
  };

  const metricsRowStyle = {
    display: 'flex',
    alignItems: 'center',
    gap: '16px',
    marginBottom: '24px',
    paddingBottom: '24px',
    borderBottom: '1px solid var(--border-soft)'
  };

  const metricItemStyle = {
    display: 'flex',
    flexDirection: 'column',
    gap: '2px'
  };

  const metricValueStyle = {
    fontSize: '16px',
    fontWeight: 700,
    color: 'var(--brown)'
  };

  const metricLabelStyle = {
    fontSize: '10px',
    fontWeight: 600,
    color: 'var(--ink-mute)',
    textTransform: 'uppercase',
    letterSpacing: '0.5px'
  };

  const separatorStyle = {
    width: '1px',
    height: '24px',
    background: 'var(--border-soft)'
  };

  const insightStyle = {
    display: 'flex',
    gap: '12px',
    padding: '16px',
    background: 'var(--ivory)',
    borderRadius: '10px',
    borderLeft: '4px solid var(--brown)',
    marginTop: 'auto',
    alignItems: 'flex-start'
  };

  if (loading) {
    return (
      <div style={cardStyle}>
        <div style={titleStyle}>{title}</div>
        <div style={{ color: 'var(--ink-mute)', marginTop: '20px' }}>Loading...</div>
      </div>
    );
  }

  if (error || !data) {
    return (
      <div style={cardStyle}>
        <div style={titleStyle}>{title}</div>
        <div style={{ color: 'var(--danger)', marginTop: '20px' }}>Error loading health data.</div>
      </div>
    );
  }

  const { score, status, metrics, insights, risk_entities, insufficient_data } = data;

  if (insufficient_data) {
    return (
      <div style={cardStyle}>
        <div style={titleStyle}>{title}</div>
        <div style={{ color: 'var(--ink-mute)', marginTop: '20px' }}>Insufficient data to calculate health score.</div>
        <div style={insightStyle}>
          <Sparkles size={16} color="var(--brown)" style={{ flexShrink: 0, marginTop: '2px' }} />
          <div style={{ fontSize: '13px', color: 'var(--brown)', lineHeight: 1.5, fontWeight: 500 }}>
            {insights && insights.length > 0 ? insights[0].insight : "Needs more activity data."}
          </div>
        </div>
      </div>
    );
  }

  return (
    <div style={cardStyle}>
      <div style={titleStyle}>{title}</div>
      <div style={scoreContainerStyle}>
        <span style={scoreStyle}>{Math.round(score)}</span>
        <span style={getBadgeStyle(status)}>{status}</span>
      </div>

      <div style={metricsRowStyle}>
        <div style={metricItemStyle}>
          <span style={metricValueStyle}>{metrics.total_evaluated || 0}</span>
          <span style={metricLabelStyle}>Evaluated</span>
        </div>
        <div style={separatorStyle} />
        <div style={metricItemStyle}>
          <span style={metricValueStyle}>{metrics.healthy || 0}</span>
          <span style={metricLabelStyle}>Healthy</span>
        </div>
        <div style={separatorStyle} />
        <div style={metricItemStyle}>
          <span style={metricValueStyle}>{metrics.at_risk || 0}</span>
          <span style={metricLabelStyle}>At Risk</span>
        </div>
        <div style={separatorStyle} />
        <div style={metricItemStyle}>
          <span style={metricValueStyle}>{metrics.critical || 0}</span>
          <span style={metricLabelStyle}>Critical</span>
        </div>
      </div>

      {risk_entities && risk_entities.length > 0 && (
        <div style={{ marginBottom: '24px' }}>
          <div 
            onClick={() => setRiskExpanded(!riskExpanded)}
            style={{ 
              display: 'flex', 
              justifyContent: 'space-between', 
              alignItems: 'center', 
              cursor: 'pointer',
              padding: '8px 0',
              userSelect: 'none'
            }}
          >
            <div style={{ fontSize: '12px', fontWeight: 700, color: 'var(--brown)', textTransform: 'uppercase', letterSpacing: '0.5px' }}>
              At-Risk Records {riskExpanded ? '' : `· ${risk_entities.length}`}
            </div>
            {riskExpanded ? <ChevronUp size={18} color="var(--ink-mute)" /> : <ChevronDown size={18} color="var(--ink-mute)" />}
          </div>
          
          {riskExpanded && (
            <div style={{ marginTop: '12px', display: 'flex', flexDirection: 'column', gap: '8px' }}>
              {risk_entities.map(re => (
                <div key={re.id} style={{ display: 'flex', flexDirection: 'column', gap: '6px', padding: '12px', background: 'var(--white)', border: '1px solid var(--border-soft)', borderRadius: '8px' }}>
                   <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                      <span style={{ fontSize: '14px', fontWeight: 600, color: 'var(--brown)', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis', maxWidth: '160px' }}>{re.name}</span>
                      <span style={{ fontSize: '12px', fontWeight: 700, color: re.status === 'Critical' ? 'var(--danger)' : 'var(--warning)' }}>{re.score.toFixed(0)} • {re.status}</span>
                   </div>
                   <span style={{ fontSize: '12px', color: 'var(--ink-mute)', lineHeight: 1.4, fontWeight: 500 }}>{re.key_signal}</span>
                </div>
              ))}
            </div>
          )}
        </div>
      )}

      <div style={insightStyle}>
        <Sparkles size={18} color="var(--brown)" style={{ flexShrink: 0, marginTop: '2px' }} />
        <div style={{ fontSize: '13px', color: 'var(--brown)', lineHeight: 1.5, fontWeight: 500 }}>
          {insights && insights.length > 0 ? (
            insights.map((ins, idx) => <div key={idx}>{ins.insight}</div>)
          ) : "No insights available."}
        </div>
      </div>
    </div>
  );
}
