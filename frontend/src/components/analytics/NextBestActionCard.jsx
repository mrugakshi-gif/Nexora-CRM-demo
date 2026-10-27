import React, { useState } from 'react';
import { Sparkles, History, TrendingDown, ShieldAlert, Calendar, Building2, TrendingUp, ShieldCheck, Shield } from 'lucide-react';
import { useNavigate } from 'react-router-dom';

export default function NextBestActionList({ actions, mode = 'next_best_action' }) {
  const navigate = useNavigate();
  const [expanded, setExpanded] = useState(false);
  
  if (!actions || actions.length === 0) return null;

  const isHistorical = mode === 'actions_taken';
  const displayActions = expanded ? actions : actions.slice(0, 3);

  return (
    <div style={{
      background: 'var(--white)',
      border: '1px solid var(--border)',
      borderRadius: '16px',
      padding: '28px',
      display: 'flex',
      flexDirection: 'column',
      gap: '28px',
      boxShadow: '0 4px 12px rgba(43,34,28,0.03)',
      width: '100%'
    }}>
      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', flexWrap: 'wrap', gap: '16px' }}>
        <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            {isHistorical ? (
              <History size={20} style={{ color: 'var(--accent-primary)' }} />
            ) : (
              <Sparkles size={20} style={{ color: 'var(--accent-primary)' }} />
            )}
            <span style={{ fontSize: '14px', fontWeight: 700, letterSpacing: '1px', color: 'var(--heading-primary)', textTransform: 'uppercase' }}>
              {isHistorical ? 'ACTIONS TAKEN' : 'NEXT BEST ACTION'}
            </span>
          </div>
          {!isHistorical && (
            <p style={{ fontSize: '13px', color: 'var(--ink-mute)', margin: 0, fontWeight: 500 }}>
              Top customer actions recommended for retention based on current risk signals.
            </p>
          )}
        </div>
        
        <div style={{ fontSize: '13px', color: 'var(--ink-mute)', fontWeight: 500, display: 'flex', alignItems: 'center', gap: '16px' }}>
          <span>Showing {displayActions.length} of {actions.length} recommendations</span>
          {actions.length > 3 && (
            <button 
              onClick={() => setExpanded(!expanded)}
              style={{
                background: 'var(--brown)',
                border: 'none',
                color: 'var(--white)',
                fontSize: '13px',
                fontWeight: 600,
                cursor: 'pointer',
                padding: '8px 16px',
                borderRadius: '6px',
                display: 'flex',
                alignItems: 'center',
                gap: '6px'
              }}
            >
              {expanded ? 'View Less ↑' : 'View More →'}
            </button>
          )}
        </div>
      </div>

      {/* List Items */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: '0' }}>
        {displayActions.map((action, idx) => {
          const churn = action.supporting_metrics?.churn_probability;
          const health = action.supporting_metrics?.account_health;
          const renewal = action.supporting_metrics?.renewal_days;
          
          return (
            <div key={idx} style={{ 
              display: 'flex', 
              justifyContent: 'space-between', 
              alignItems: 'center',
              padding: '24px 0',
              borderTop: idx !== 0 ? '1px solid rgba(0,0,0,0.06)' : 'none',
              gap: '24px',
              flexWrap: 'wrap'
            }}>
              
              {/* LEFT: Info */}
              <div style={{ display: 'flex', gap: '16px', flex: 1.2, minWidth: '320px' }}>
                {/* Number indicator */}
                <div style={{ 
                  minWidth: '32px', 
                  height: '32px', 
                  borderRadius: '50%', 
                  background: 'var(--white)', 
                  border: '1px solid rgba(0,0,0,0.1)',
                  display: 'flex', 
                  alignItems: 'center', 
                  justifyContent: 'center',
                  fontSize: '14px',
                  fontWeight: 600,
                  color: 'var(--brown)'
                }}>
                  {idx + 1}
                </div>
                
                <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '12px', flexWrap: 'wrap' }}>
                    <h3 style={{ fontSize: '15px', fontWeight: 700, color: 'var(--brown)', margin: 0 }}>
                      {isHistorical ? (action.activity_type || action.action) : action.action}
                    </h3>
                    
                    {!isHistorical && action.priority && (
                      <span style={{
                        padding: '3px 10px',
                        borderRadius: '16px',
                        fontSize: '11px',
                        fontWeight: 700,
                        background: action.priority === 'High' ? '#FEE2E2' : '#FEF3C7',
                        color: action.priority === 'High' ? '#B91C1C' : '#D97706',
                        border: `1px solid ${action.priority === 'High' ? 'rgba(220,38,38,0.3)' : 'rgba(217,119,6,0.3)'}`
                      }}>
                        {action.priority} Priority
                      </span>
                    )}
                  </div>
                  
                  <div style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                    <Building2 size={15} style={{ color: 'var(--ink-mute)' }} />
                    <span style={{ fontSize: '14px', color: 'var(--brown)', fontWeight: 600 }}>
                      {action.entity_name}
                    </span>
                  </div>
                  
                  {isHistorical && action.activity_date && (
                    <p style={{ fontSize: '13px', color: 'var(--ink-mute)', margin: 0, fontWeight: 500 }}>
                      {action.activity_date}
                    </p>
                  )}
                </div>
              </div>

              {/* MIDDLE: Risk Metric Blocks + Why */}
              <div style={{ display: 'flex', flexDirection: 'column', gap: '16px', flex: 2, minWidth: '400px' }}>
                {!isHistorical && (
                  <div style={{ display: 'flex', gap: '12px', flexWrap: 'wrap' }}>
                    {/* Churn Block */}
                    {churn !== undefined && churn !== null && churn >= 0.50 && (
                      <div style={{ 
                        display: 'flex', alignItems: 'center', gap: '12px',
                        padding: '12px 16px', background: '#FEF2F2', 
                        borderRadius: '8px',
                        minWidth: '140px'
                      }}>
                        <TrendingUp size={20} style={{ color: '#DC2626' }} />
                        <div style={{ display: 'flex', flexDirection: 'column' }}>
                          <span style={{ fontSize: '16px', fontWeight: 700, color: '#991B1B', lineHeight: 1 }}>
                            {(churn * 100).toFixed(1)}%
                          </span>
                          <span style={{ fontSize: '11px', fontWeight: 600, color: '#B91C1C', marginTop: '4px' }}>Churn Risk</span>
                        </div>
                      </div>
                    )}

                    {/* Health Block */}
                    {health !== undefined && health !== null && health < 70 && (
                      <div style={{ 
                        display: 'flex', alignItems: 'center', gap: '12px',
                        padding: '12px 16px', 
                        background: health < 40 ? '#FEF2F2' : '#FFFBEB', 
                        borderRadius: '8px',
                        minWidth: '140px'
                      }}>
                        <ShieldAlert size={20} style={{ color: health < 40 ? '#DC2626' : '#D97706' }} />
                        <div style={{ display: 'flex', flexDirection: 'column' }}>
                          <span style={{ fontSize: '16px', fontWeight: 700, color: health < 40 ? '#991B1B' : '#B45309', lineHeight: 1 }}>
                            {health < 40 ? 'Critical' : 'At Risk'}
                          </span>
                          <span style={{ fontSize: '11px', fontWeight: 600, color: health < 40 ? '#B91C1C' : '#D97706', marginTop: '4px' }}>Account Health</span>
                        </div>
                      </div>
                    )}

                    {/* Renewal Block */}
                    {renewal !== undefined && renewal !== null && renewal <= 90 && (
                      <div style={{ 
                        display: 'flex', alignItems: 'center', gap: '12px',
                        padding: '12px 16px', background: '#F0FDF4', 
                        borderRadius: '8px',
                        minWidth: '140px'
                      }}>
                        <Calendar size={20} style={{ color: '#15803D' }} />
                        <div style={{ display: 'flex', flexDirection: 'column' }}>
                          <span style={{ fontSize: '16px', fontWeight: 700, color: '#166534', lineHeight: 1 }}>
                            {renewal} days
                          </span>
                          <span style={{ fontSize: '11px', fontWeight: 600, color: '#15803D', marginTop: '4px' }}>Renewal</span>
                        </div>
                      </div>
                    )}
                  </div>
                )}

                {/* Reasons / Details Inline */}
                {(!isHistorical && action.reasons && action.reasons.length > 0) ? (
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flexWrap: 'wrap' }}>
                    <span style={{ fontSize: '13px', fontWeight: 700, color: 'var(--brown)' }}>Why:</span>
                    {action.reasons.map((reason, ridx) => {
                      let isImportant = reason.toLowerCase().includes('churn') || 
                                        reason.toLowerCase().includes('critical') || 
                                        reason.toLowerCase().includes('at risk') ||
                                        reason.toLowerCase().includes('renewal');
                      let dotColor = '#DC2626';
                      if (reason.toLowerCase().includes('renewal')) dotColor = '#15803D';
                      else if (reason.toLowerCase().includes('at risk')) dotColor = '#D97706';

                      return (
                        <div key={ridx} style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
                          <div style={{ width: '6px', height: '6px', borderRadius: '50%', background: dotColor }}></div>
                          <span style={{ fontSize: '13px', color: 'var(--ink-mute)', fontWeight: 500 }}>
                            {reason}
                          </span>
                        </div>
                      );
                    })}
                  </div>
                ) : isHistorical && action.subject ? (
                  <div>
                    <p style={{ fontSize: '13px', fontWeight: 600, color: 'var(--brown)', margin: '0 0 4px 0' }}>{action.subject}</p>
                    {action.description && (
                      <p style={{ fontSize: '13px', color: 'var(--ink-mute)', margin: 0 }}>
                        {action.description}
                      </p>
                    )}
                  </div>
                ) : null}
              </div>

              {/* RIGHT: action button */}
              <div style={{ minWidth: '150px', display: 'flex', justifyContent: 'flex-end' }}>
                <button 
                  onClick={() => navigate(`/customers/${action.customer_id}`)}
                  style={{
                    background: 'var(--white)',
                    color: 'var(--brown)',
                    border: '1px solid rgba(0,0,0,0.1)',
                    padding: '10px 16px',
                    borderRadius: '8px',
                    fontSize: '13px',
                    fontWeight: 600,
                    cursor: 'pointer',
                    transition: 'all 0.2s',
                    boxShadow: '0 1px 2px rgba(0,0,0,0.05)',
                    width: '100%',
                    textAlign: 'center',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    gap: '4px'
                  }}
                  onMouseOver={e => e.currentTarget.style.background = 'var(--ivory)'}
                  onMouseOut={e => e.currentTarget.style.background = 'var(--white)'}
                >
                  View Customer →
                </button>
              </div>
            </div>
          );
        })}
      </div>
      

    </div>
  );
}
