import React, { useState, useEffect } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import Icon from '../common/Icon';
import { notificationService } from '../../services/crmService';

const NAV_LABELS = {
  '/': 'Dashboard',
  '/dashboard': 'Dashboard',
  '/companies': 'Companies',
  '/customers': 'Customers',
  '/contacts': 'Contacts',
  '/leads': 'Leads',
  '/opportunities': 'Opportunities',
  '/products': 'Products',
  '/transactions': 'Transactions',
  '/activities': 'Tasks & Activities',
  '/campaigns': 'Campaigns',
  '/support': 'Support',
  '/ai-workspace': 'AI Workspace',
  '/ml-insights': 'ML Insights',
  '/reports': 'Reports',
  '/analytics': 'Analytics',
  '/company-comparison': 'Comparison',
  '/profile': 'Profile',
  '/settings': 'Settings'
};

export default function Header({ onMenuClick }) {
  const location = useLocation();
  const navigate = useNavigate();

  const [notifications, setNotifications] = useState([]);
  const [showNotifDropdown, setShowNotifDropdown] = useState(false);
  const notifRef = React.useRef(null);

  const [detailName, setDetailName] = useState('');
  const [theme, setTheme] = useState(() => {
    try {
      const p = JSON.parse(localStorage.getItem('nexora_crm_prefs') || '{}');
      return p.theme || 'light';
    } catch (e) {
      return 'light';
    }
  });

  useEffect(() => {
    const handler = (e) => setDetailName(e.detail);
    window.addEventListener('set-breadcrumb', handler);
    return () => window.removeEventListener('set-breadcrumb', handler);
  }, []);

  useEffect(() => {
    const themeHandler = (e) => setTheme(e.detail || 'light');
    window.addEventListener('nexora-theme-change', themeHandler);
    return () => window.removeEventListener('nexora-theme-change', themeHandler);
  }, []);

  const toggleTheme = () => {
    const nextTheme = theme === 'dark' ? 'light' : 'dark';
    setTheme(nextTheme);
    try {
      const p = JSON.parse(localStorage.getItem('nexora_crm_prefs') || '{}');
      p.theme = nextTheme;
      localStorage.setItem('nexora_crm_prefs', JSON.stringify(p));
    } catch (e) {}
    document.documentElement.setAttribute('data-theme', nextTheme);
    window.dispatchEvent(new CustomEvent('nexora-theme-change', { detail: nextTheme }));
  };

  useEffect(() => {
    const fetchNotifications = async () => {
      try {
        const res = await notificationService.getNotifications();
        setNotifications(res.data.notifications || []);
      } catch (err) {
        console.error("Failed to load notifications", err);
      }
    };
    fetchNotifications();
  }, []);

  let prefs = {};
  try {
    prefs = JSON.parse(localStorage.getItem('nexora_crm_prefs') || '{}');
  } catch (e) {}
  
  const taskReminders = prefs.taskReminders ?? true;
  const supportNotifs = prefs.supportNotifications ?? true;
  const aiAlerts = prefs.aiRecommendationAlerts ?? true;

  const filteredNotifications = notifications.filter(n => {
    if (n.type === 'support') return supportNotifs;
    if (n.type === 'churn') return aiAlerts;
    if (['lead', 'opportunity', 'renewal'].includes(n.type)) return taskReminders;
    return true;
  });


  useEffect(() => {
    function handleClickOutside(event) {
      if (notifRef.current && !notifRef.current.contains(event.target)) {
        setShowNotifDropdown(false);
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  const getBreadcrumbLabel = () => {
    // Basic mapping, could be expanded for detail pages like /customers/123
    const path = '/' + location.pathname.split('/')[1];
    return NAV_LABELS[path] || 'Home';
  };

  return (
    <header id="header">
      <div style={{ display: 'flex', alignItems: 'center', gap: '14px', minWidth: 0 }}>
        <button id="menu-btn" className="icon-btn" style={{ display: 'none' }} aria-label="Toggle menu" onClick={onMenuClick}>
          <Icon name="menu" size={16} />
        </button>
        <div id="breadcrumb" style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <span onClick={() => navigate('/dashboard')} style={{ cursor: 'pointer' }} className="hover-text-ink">Home</span>
          <span><Icon name="chevronright" size={11} color="var(--ink-mute)" stroke={2} /></span>
          
          {location.pathname.startsWith('/companies/') && location.pathname.length > 11 ? (
             <>
                <span onClick={() => navigate('/companies')} style={{ cursor: 'pointer' }} className="hover-text-ink">Companies</span>
                <span><Icon name="chevronright" size={11} color="var(--ink-mute)" stroke={2} /></span>
                <span className="current">{detailName || 'Loading...'}</span>
             </>
          ) : (
             <span className="current">{getBreadcrumbLabel()}</span>
          )}
        </div>
      </div>
      <div id="header-right">
        <style>{`
          #notif-btn {
            position: relative;
            cursor: pointer;
            display: flex;
            align-items: center;
            justify-content: center;
            padding: 6px;
            border-radius: 8px;
            color: var(--brown);
            transition: all 0.2s ease;
            outline: none;
          }
          #notif-btn:hover, #notif-btn:focus-visible {
            background-color: var(--accent-tint);
          }
          #notif-btn:focus-visible {
            box-shadow: 0 0 0 2px var(--accent-primary);
          }
          #notif-btn.has-unread svg {
            fill: var(--accent-tint) !important;
          }
        `}</style>
        <div 
          className={`icon-btn ${filteredNotifications.length > 0 ? 'has-unread' : ''}`} 
          id="notif-btn" 
          aria-label="Notifications" 
          role="button"
          tabIndex={0}
          ref={notifRef} 
          onClick={() => setShowNotifDropdown(!showNotifDropdown)} 
          onKeyDown={(e) => {
            if (e.key === 'Enter' || e.key === ' ') {
              e.preventDefault();
              setShowNotifDropdown(!showNotifDropdown);
            }
          }}
        >
          <Icon name="bell" size={20} stroke={2.2} color="var(--brown)" />
          {filteredNotifications.length > 0 && (
            <div style={{
              position: 'absolute', top: '0', right: '0', background: 'var(--danger)', 
              color: 'white', fontSize: '10px', fontWeight: 600, padding: '2px 5px', 
              borderRadius: '10px', lineHeight: 1, border: '2px solid white', transform: 'translate(25%, -25%)'
            }}>
              {filteredNotifications.length}
            </div>
          )}
          
          {showNotifDropdown && (
            <div style={{
              position: 'absolute', top: 'calc(100% + 8px)', right: 0, width: 'min(360px, calc(100vw - 32px))',
              background: 'var(--bg-surface)', border: '1px solid var(--border)', borderRadius: '14px',
              boxShadow: 'var(--clay-shadow-float)', zIndex: 100,
              cursor: 'default', textAlign: 'left', overflow: 'hidden'
            }} onClick={(e) => e.stopPropagation()}>
              <div style={{ padding: '14px 18px', borderBottom: '1px solid var(--border-soft)', display: 'flex', alignItems: 'center', justifyContent: 'space-between', background: 'var(--bg-subtle)' }}>
                <div style={{ fontSize: '15px', fontWeight: 800, color: 'var(--heading-primary)' }}>Notifications</div>
                <div style={{ background: 'var(--accent-primary)', color: '#ffffff', fontSize: '11px', fontWeight: 700, padding: '2px 8px', borderRadius: '12px' }}>
                  {filteredNotifications.length}
                </div>
              </div>
              <div style={{ maxHeight: '250px', overflowY: 'auto' }}>
                {filteredNotifications.length > 0 ? (
                  filteredNotifications.map((n) => {
                    const style = (() => {
                      switch (n.type) {
                        case 'support': return { icon: 'lifebuoy', bg: 'var(--accent-tint)', color: 'var(--accent-primary)' };
                        case 'lead': return { icon: 'user', bg: 'var(--accent-tint)', color: 'var(--accent-primary)' };
                        case 'opportunity': return { icon: 'clock', bg: 'rgba(234, 179, 8, 0.15)', color: 'var(--warning)' };
                        case 'churn': return { icon: 'shield', bg: 'rgba(239, 68, 68, 0.15)', color: 'var(--danger)' };
                        case 'renewal': return { icon: 'calendar', bg: 'rgba(16, 185, 129, 0.15)', color: 'var(--success)' };
                        default: return { icon: 'bell', bg: 'var(--bg-subtle)', color: 'var(--ink-mute)' };
                      }
                    })();
                    return (
                    <div key={n.id} style={{
                      padding: '12px 16px', borderBottom: '1px solid var(--border-soft)', display: 'flex', gap: '12px', alignItems: 'flex-start', cursor: 'pointer', transition: 'background 0.18s ease'
                    }} onClick={() => { setShowNotifDropdown(false); navigate(n.link); }}
                       onMouseEnter={(e) => e.currentTarget.style.backgroundColor = 'var(--bg-subtle)'}
                       onMouseLeave={(e) => e.currentTarget.style.backgroundColor = 'transparent'}
                    >
                      <div style={{
                        width: '34px', height: '34px', borderRadius: '10px', background: style.bg,
                        display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0
                      }}>
                        <Icon name={style.icon} size={17} color={style.color} stroke={2.2} />
                      </div>
                      <div style={{ flex: 1, minWidth: 0 }}>
                        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '2px' }}>
                          <div style={{ fontSize: '13.5px', fontWeight: 700, color: 'var(--heading-primary)', whiteSpace: 'nowrap', overflow: 'hidden', textOverflow: 'ellipsis', paddingRight: '8px' }}>
                            {n.title}
                          </div>
                          <div style={{ display: 'flex', alignItems: 'center', gap: '8px', flexShrink: 0, height: '20px' }}>
                            {n.read !== true && <div style={{ width: '7px', height: '7px', borderRadius: '50%', background: 'var(--danger)' }} />}
                            <Icon name="chevronright" size={14} color="var(--ink-mute)" stroke={2} />
                          </div>
                        </div>
                        <div style={{ 
                          fontSize: '12.5px', color: 'var(--ink-soft)', marginBottom: '4px', lineHeight: 1.35,
                          display: '-webkit-box', WebkitLineClamp: 2, WebkitBoxOrient: 'vertical', overflow: 'hidden', whiteSpace: 'normal'
                        }}>
                          {n.message}
                        </div>
                        <div style={{ fontSize: '11px', color: 'var(--ink-mute)', display: 'flex', alignItems: 'center', gap: '5px', fontWeight: 500 }}>
                          <Icon name="calendar" size={11} color="currentColor" stroke={2} />
                          {new Date(n.timestamp).toLocaleDateString('en-GB')}
                        </div>
                      </div>
                    </div>
                  )})
                ) : (
                  <div style={{ padding: '32px 16px', textAlign: 'center' }}>
                    <div style={{ fontSize: '14px', fontWeight: 700, color: 'var(--heading-primary)', marginBottom: '4px' }}>No new notifications</div>
                    <div style={{ fontSize: '12.5px', color: 'var(--ink-mute)' }}>You're all caught up.</div>
                  </div>
                )}
              </div>
            </div>
          )}
        </div>
        <button
          className="icon-btn theme-toggle-btn"
          id="theme-toggle"
          aria-label={theme === 'dark' ? 'Switch to Day Mode (Sky Blue Clay)' : 'Switch to Night Mode (Warm Neutral Clay)'}
          title={theme === 'dark' ? 'Switch to Day Mode' : 'Switch to Night Mode'}
          onClick={toggleTheme}
          style={{
            background: 'transparent',
            border: 'none',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            cursor: 'pointer',
            padding: '6px',
            borderRadius: '9px',
            color: 'var(--brown)',
            transition: 'all 0.2s ease'
          }}
        >
          <Icon name={theme === 'dark' ? 'sun' : 'moon'} size={19} color="var(--brown)" stroke={2.1} />
        </button>
      </div>
    </header>
  );
}
