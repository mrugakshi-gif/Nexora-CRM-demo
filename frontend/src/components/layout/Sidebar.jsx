import React, { useState, useRef, useEffect } from 'react';
import { Link, useLocation, useNavigate } from 'react-router-dom';
import Icon from '../common/Icon';
import { auth } from '../../services/firebase';
import { signOut } from 'firebase/auth';
import { AuthContext } from '../../AuthContext';
import Modal from '../common/Modal';

const NAV = {
  main: [
    { key: 'dashboard', label: 'Dashboard', icon: 'dashboard', path: '/dashboard' },
    { key: 'companies', label: 'Companies', icon: 'database', path: '/companies' },
    { key: 'customers', label: 'Customers', icon: 'users', path: '/customers' },
    { key: 'contacts', label: 'Contacts', icon: 'user', path: '/contacts' },
    { key: 'leads', label: 'Leads', icon: 'target', path: '/leads' },
    { key: 'opportunities', label: 'Opportunities', icon: 'briefcase', path: '/opportunities' },
    { key: 'products', label: 'Products', icon: 'package', path: '/products' },
    { key: 'transactions', label: 'Transactions', icon: 'creditcard', path: '/transactions' },
    { key: 'activities', label: 'Tasks & Activities', icon: 'checksquare', path: '/activities' }
  ],
  operations: [
    { key: 'campaigns', label: 'Campaigns', icon: 'megaphone', path: '/campaigns' },
    { key: 'support', label: 'Support', icon: 'lifebuoy', path: '/support' }
  ],
  intelligent: [
    { key: 'ai-workspace', label: 'AI Workspace', icon: 'sparkles', path: '/ai-workspace' },
    { key: 'ml-insights', label: 'ML Insights', icon: 'brain', path: '/ml-insights', allowedRoles: ['Admin', 'Manager'] },
    { key: 'reports', label: 'Reports', icon: 'filetext', path: '/reports', allowedRoles: ['Admin', 'Manager'] },
    { key: 'analytics', label: 'Analytics', icon: 'barchart', path: '/analytics', allowedRoles: ['Admin', 'Manager'] },
    { key: 'company-comparison', label: 'Comparison', icon: 'grid', path: '/company-comparison' }
  ],
  footer: [
    { key: 'settings', label: 'Settings', icon: 'settings', path: '/settings', allowedRoles: ['Admin'] }
  ]
};

export default function Sidebar({ isOpen, onClose }) {
  const location = useLocation();
  const navigate = useNavigate();
  const { crmProfile: userProfile, effectiveRole, previewRole, setPreviewRole } = React.useContext(AuthContext);

  const [accountMenuOpen, setAccountMenuOpen] = useState(false);
  const [showRbacModal, setShowRbacModal] = useState(false);
  const accountMenuRef = useRef(null);

  // Close dropdown on click outside
  useEffect(() => {
    function handleClickOutside(event) {
      if (accountMenuRef.current && !accountMenuRef.current.contains(event.target)) {
        setAccountMenuOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  // Close dropdown on route change
  useEffect(() => {
    setAccountMenuOpen(false);
  }, [location.pathname]);

  const handleLogout = async () => {
    setAccountMenuOpen(false);
    if (onClose) onClose();
    try {
      await signOut(auth);
      navigate('/login');
    } catch (err) {
      console.error("Logout failed", err);
    }
  };

  const fbUser = auth.currentUser;
  const rawEmail = userProfile?.email || fbUser?.email || 'user@example.com';
  const emailPrefix = rawEmail.split('@')[0];
  const formattedPrefix = emailPrefix.charAt(0).toUpperCase() + emailPrefix.slice(1);
  const displayName = userProfile?.full_name || fbUser?.displayName || formattedPrefix;
  const roleName = previewRole ? `${effectiveRole} (Preview)` : (effectiveRole || userProfile?.role || 'User');

  const nameParts = displayName.split(' ');
  const initials = nameParts.length > 1 
    ? (nameParts[0].charAt(0) + nameParts[nameParts.length - 1].charAt(0)).toUpperCase()
    : displayName.substring(0, 2).toUpperCase();

  const renderNavItems = (items) => items
    .filter(item => !item.allowedRoles || (effectiveRole && item.allowedRoles.includes(effectiveRole)))
    .map(item => {
    const isActive = location.pathname === item.path || (item.path === '/dashboard' && location.pathname === '/') || (item.path !== '/' && item.path !== '/dashboard' && location.pathname.startsWith(item.path));
    return (
      <Link
        key={item.key}
        to={item.path}
        className={`nav-item ${isActive ? 'active' : ''}`}
        onClick={onClose}
      >
        <span className="nav-icon">
          <Icon name={item.icon} size={17} color={isActive ? 'var(--ivory)' : 'var(--ink-soft)'} stroke={isActive ? 2 : 1.8} />
        </span>
        <span>{item.label}</span>
      </Link>
    );
  });

  return (
    <>
      <div id="sidebar-scrim" className={isOpen ? 'show' : ''} onClick={onClose} hidden={!isOpen}></div>
      <nav id="sidebar" className={isOpen ? 'open' : ''} aria-label="Primary" style={{ position: 'relative' }}>
        <Link to="/dashboard" className="brand" onClick={onClose}>
          <div className="brand-mark">
            <Icon name="sparkles" size={17} color="var(--ivory)" stroke={2} />
          </div>
          <div>
            <div className="brand-name">Nexora CRM</div>
            <div className="brand-tag">Smart. Predict. Grow.</div>
          </div>
        </Link>
        <div className="nav-section-label">Main</div>
        {renderNavItems(NAV.main)}
        
        <div className="nav-section-label">Operations</div>
        {renderNavItems(NAV.operations)}
        
        <div className="nav-section-label">Intelligent</div>
        {renderNavItems(NAV.intelligent)}
        
        <div id="sidebar-spacer"></div>
        
        <div id="sidebar-footer">
          {renderNavItems(NAV.footer)}

          {/* Account Profile Trigger & Dropdown */}
          <div ref={accountMenuRef} style={{ position: 'relative', marginTop: '8px' }}>
            {accountMenuOpen && (
              <div 
                style={{
                  position: 'absolute',
                  bottom: 'calc(100% + 6px)',
                  left: 0,
                  right: 0,
                  background: 'var(--bg-surface)',
                  border: '1px solid var(--border)',
                  borderRadius: '12px',
                  boxShadow: 'var(--clay-shadow-float)',
                  padding: '6px',
                  zIndex: 100,
                  display: 'flex',
                  flexDirection: 'column',
                  gap: '2px'
                }}
              >
                <button
                  type="button"
                  onClick={() => {
                    setAccountMenuOpen(false);
                    if (onClose) onClose();
                    navigate('/profile');
                  }}
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: '10px',
                    padding: '8px 12px',
                    borderRadius: '8px',
                    fontSize: '13px',
                    fontWeight: 500,
                    color: 'var(--ink)',
                    background: 'transparent',
                    border: 'none',
                    cursor: 'pointer',
                    width: '100%',
                    textAlign: 'left',
                    transition: 'background 0.15s ease'
                  }}
                  onMouseEnter={(e) => e.currentTarget.style.background = 'var(--bg-subtle)'}
                  onMouseLeave={(e) => e.currentTarget.style.background = 'transparent'}
                >
                  <Icon name="user" size={15} color="var(--accent-primary)" stroke={2} />
                  <span>Profile</span>
                </button>

                <button
                  type="button"
                  onClick={() => {
                    setAccountMenuOpen(false);
                    setShowRbacModal(true);
                  }}
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: '10px',
                    padding: '8px 12px',
                    borderRadius: '8px',
                    fontSize: '13px',
                    fontWeight: 500,
                    color: 'var(--ink)',
                    background: 'transparent',
                    border: 'none',
                    cursor: 'pointer',
                    width: '100%',
                    textAlign: 'left',
                    transition: 'background 0.15s ease'
                  }}
                  onMouseEnter={(e) => e.currentTarget.style.background = 'var(--bg-subtle)'}
                  onMouseLeave={(e) => e.currentTarget.style.background = 'transparent'}
                >
                  <Icon name="shield" size={15} color="var(--accent-primary)" stroke={2} />
                  <span>RBAC</span>
                </button>

                <div style={{ height: '1px', background: 'var(--border-soft)', margin: '4px 2px' }} />

                <button
                  type="button"
                  onClick={handleLogout}
                  style={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: '10px',
                    padding: '8px 12px',
                    borderRadius: '8px',
                    fontSize: '13px',
                    fontWeight: 500,
                    color: 'var(--danger)',
                    background: 'transparent',
                    border: 'none',
                    cursor: 'pointer',
                    width: '100%',
                    textAlign: 'left',
                    transition: 'background 0.15s ease'
                  }}
                  onMouseEnter={(e) => e.currentTarget.style.background = 'var(--danger-bg)'}
                  onMouseLeave={(e) => e.currentTarget.style.background = 'transparent'}
                >
                  <Icon name="logout" size={15} color="var(--danger)" stroke={2} />
                  <span>Logout</span>
                </button>
              </div>
            )}

            <button
              type="button"
              aria-label="User Account Menu"
              aria-expanded={accountMenuOpen}
              onClick={() => setAccountMenuOpen(!accountMenuOpen)}
              onKeyDown={(e) => {
                if (e.key === 'Enter' || e.key === ' ') {
                  e.preventDefault();
                  setAccountMenuOpen(!accountMenuOpen);
                } else if (e.key === 'Escape') {
                  setAccountMenuOpen(false);
                }
              }}
              style={{
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between',
                width: '100%',
                padding: '8px 10px',
                borderRadius: 'var(--radius-control)',
                background: accountMenuOpen ? 'var(--bg-subtle)' : 'transparent',
                border: '1px solid',
                borderColor: accountMenuOpen ? 'var(--border)' : 'transparent',
                cursor: 'pointer',
                transition: 'all 0.16s ease',
                textAlign: 'left',
                outline: 'none'
              }}
              onMouseEnter={(e) => {
                if (!accountMenuOpen) e.currentTarget.style.background = 'var(--accent-tint)';
              }}
              onMouseLeave={(e) => {
                if (!accountMenuOpen) e.currentTarget.style.background = 'transparent';
              }}
            >
              <div style={{ display: 'flex', alignItems: 'center', gap: '10px', minWidth: 0, flex: 1 }}>
                <div 
                  className="avatar" 
                  style={{ 
                    width: '32px', 
                    height: '32px', 
                    fontSize: '12px', 
                    background: 'var(--accent-primary)',
                    color: '#ffffff',
                    flexShrink: 0
                  }}
                >
                  {initials}
                </div>
                <div style={{ minWidth: 0, flex: 1 }}>
                  <div 
                    style={{ 
                      fontSize: '12.5px', 
                      fontWeight: 600, 
                      color: 'var(--heading-primary)', 
                      lineHeight: 1.25, 
                      whiteSpace: 'nowrap', 
                      overflow: 'hidden', 
                      textOverflow: 'ellipsis' 
                    }}
                  >
                    {displayName}
                  </div>
                  <div 
                    style={{ 
                      fontSize: '10.5px', 
                      color: 'var(--ink-mute)', 
                      lineHeight: 1.25, 
                      whiteSpace: 'nowrap', 
                      overflow: 'hidden', 
                      textOverflow: 'ellipsis' 
                    }}
                  >
                    {roleName}
                  </div>
                </div>
              </div>
              <div style={{ color: 'var(--ink-mute)', display: 'flex', alignItems: 'center', paddingLeft: '4px' }}>
                <Icon name={accountMenuOpen ? "chevrondown" : "chevronright"} size={14} stroke={2} />
              </div>
            </button>
          </div>
        </div>
      </nav>

      {/* RBAC Modal */}
      <Modal isOpen={showRbacModal} onClose={() => setShowRbacModal(false)} title="RBAC Preview Mode">
        <div style={{ padding: '4px 0' }}>
          <p style={{ fontSize: '13px', color: 'var(--ink-mute)', marginBottom: '16px' }}>
            Preview the frontend experience as a different role. This only affects the UI; backend API calls still use your real Admin credentials.
          </p>
          <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
            {['Admin', 'Manager', 'Sales Rep'].map(role => (
              <div
                key={role}
                onClick={() => {
                  setPreviewRole(role === userProfile?.effective_role ? null : role);
                  setShowRbacModal(false);
                }}
                style={{
                  padding: '12px',
                  borderRadius: '6px',
                  border: `1px solid ${previewRole === role || (!previewRole && role === userProfile?.effective_role) ? 'var(--primary)' : 'var(--border)'}`,
                  background: previewRole === role || (!previewRole && role === userProfile?.effective_role) ? 'var(--primary-light)' : 'var(--bg)',
                  cursor: 'pointer',
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'center'
                }}
              >
                <span style={{ fontSize: '14px', fontWeight: 500, color: 'var(--ink)' }}>{role}</span>
                {(previewRole === role || (!previewRole && role === userProfile?.effective_role)) && (
                  <Icon name="check" size={16} color="var(--primary)" />
                )}
              </div>
            ))}
          </div>
          {previewRole && (
            <div style={{ marginTop: '16px', textAlign: 'center' }}>
              <button 
                className="btn btn-secondary" 
                onClick={() => { setPreviewRole(null); setShowRbacModal(false); }}
                style={{ width: '100%', justifyContent: 'center' }}
              >
                Exit Preview Mode
              </button>
            </div>
          )}
        </div>
      </Modal>
    </>
  );
}
