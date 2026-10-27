import React from 'react';
import Icon from './Icon';

export function Timeline({ children }) {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', padding: '16px 0' }}>
      {children}
    </div>
  );
}

export function TimelineDateSeparator({ date }) {
  return (
    <div style={{ display: 'flex', alignItems: 'center', margin: '24px 0 16px', position: 'relative' }}>
      <div style={{ flex: 1, height: '1px', backgroundColor: 'var(--border-soft)' }}></div>
      <div style={{ padding: '0 16px', fontSize: '13px', fontWeight: 600, color: 'var(--ink-mute)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
        {date}
      </div>
      <div style={{ flex: 1, height: '1px', backgroundColor: 'var(--border-soft)' }}></div>
    </div>
  );
}

export function TimelineRow({ icon, title, type, status, time, owner, relatedTo, children }) {
  return (
    <div className="timeline-row" style={{ display: 'flex', gap: '16px', position: 'relative', paddingBottom: '24px' }}>
      <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', width: '32px' }}>
        <div style={{ width: '32px', height: '32px', borderRadius: '50%', backgroundColor: 'var(--bg-subtle)', border: '1px solid var(--border)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 2, boxShadow: 'var(--clay-shadow-sm)' }}>
          <Icon name={icon} size={15} color="var(--accent-primary)" stroke={1.8} />
        </div>
        <div style={{ width: '1px', flex: 1, backgroundColor: 'var(--border)', marginTop: '8px' }}></div>
      </div>
      <div style={{ flex: 1, display: 'flex', flexDirection: 'column', gap: '8px', paddingTop: '4px' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
          <div>
            <div style={{ fontSize: '14px', fontWeight: 600, color: 'var(--heading-primary)' }}>{title}</div>
            <div style={{ fontSize: '12px', color: 'var(--ink-mute)', marginTop: '2px', display: 'flex', alignItems: 'center', gap: '8px' }}>
              <span style={{ fontWeight: 500 }}>{type}</span>
              {relatedTo && (
                <>
                  <span style={{ color: 'var(--border)' }}>•</span>
                  <span>{relatedTo}</span>
                </>
              )}
            </div>
          </div>
          <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-end', gap: '4px' }}>
            <span style={{ fontSize: '12px', fontWeight: 500, color: 'var(--ink-soft)' }}>{time}</span>
            {status}
          </div>
        </div>
        {children && (
          <div style={{ fontSize: '13px', color: 'var(--ink)', backgroundColor: 'var(--bg-subtle)', padding: '12px 14px', borderRadius: '10px', border: '1px solid var(--border-soft)', lineHeight: '1.5', boxShadow: 'var(--clay-inset)' }}>
            {children}
          </div>
        )}
        {owner && (
          <div style={{ fontSize: '11px', color: 'var(--ink-mute)', display: 'flex', alignItems: 'center', gap: '4px', marginTop: '4px' }}>
            <Icon name="user" size={11} stroke={2} /> Assigned to {owner}
          </div>
        )}
      </div>
    </div>
  );
}
