import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import { auth } from '../services/firebase';
import { signInWithEmailAndPassword } from 'firebase/auth';
import Icon from '../components/common/Icon';
import { Eye, EyeOff } from 'lucide-react';

export default function Login() {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [showPassword, setShowPassword] = useState(false);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);
  const navigate = useNavigate();

  const [theme, setTheme] = useState(() => {
    try {
      const p = JSON.parse(localStorage.getItem('nexora_crm_prefs') || '{}');
      return p.theme || document.documentElement.getAttribute('data-theme') || 'light';
    } catch (e) {
      return document.documentElement.getAttribute('data-theme') || 'light';
    }
  });

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
    document.body.setAttribute('data-theme', nextTheme);
    window.dispatchEvent(new CustomEvent('nexora-theme-change', { detail: nextTheme }));
  };

  const handleLogin = async (e) => {
    e.preventDefault();
    if (loading) return;
    setError('');
    setLoading(true);
    try {
      await signInWithEmailAndPassword(auth, email, password);
      try {
        const prefs = JSON.parse(localStorage.getItem('nexora_crm_prefs') || '{}');
        const target = (prefs.defaultPage === '/' ? '/dashboard' : prefs.defaultPage) || '/dashboard';
        navigate(target);
      } catch (e) {
        navigate('/dashboard');
      }
    } catch (err) {
      console.error("Login failed", err);
      setError('Invalid credentials or Firebase configuration error. Please try again.');
    } finally {
      setLoading(false);
    }
  };

  const isDark = theme === 'dark';

  return (
    <div 
      data-theme={theme}
      style={{ 
        minHeight: '100vh', 
        backgroundColor: 'var(--bg-canvas)', 
        border: isDark ? '12px solid #2B2821' : '12px solid #1C2B44', 
        boxSizing: 'border-box',
        position: 'relative',
        overflow: 'hidden',
        display: 'flex',
        flexDirection: 'column',
        fontFamily: 'var(--font, Inter, system-ui, -apple-system, sans-serif)',
        transition: 'background-color 0.25s ease, border-color 0.25s ease'
      }}
    >
      {/* HEADER */}
      <header style={{ 
        position: 'absolute', 
        top: 0, 
        left: 0, 
        right: 0, 
        padding: '28px 40px', 
        display: 'flex', 
        justifyContent: 'space-between', 
        alignItems: 'center',
        zIndex: 30,
        pointerEvents: 'none'
      }}>
        {/* Brand */}
        <div style={{ display: 'flex', alignItems: 'center', gap: '9px', pointerEvents: 'auto' }}>
          <div style={{ 
            display: 'flex', 
            alignItems: 'center', 
            justifyContent: 'center',
            width: '38px',
            height: '38px',
            borderRadius: '11px',
            background: 'var(--accent-primary)',
            boxShadow: 'var(--clay-shadow-sm)'
          }}>
            <Icon name="sparkles" size={20} color="#FFFFFF" stroke={2.2} />
          </div>
          <div style={{ display: 'flex', alignItems: 'baseline', gap: '5px' }}>
            <span style={{ fontSize: '23px', fontWeight: 800, color: 'var(--heading-primary)', letterSpacing: '-0.5px' }}>Nexora</span>
            <span style={{ fontSize: '19px', fontWeight: 600, color: 'var(--accent-primary)' }}>CRM</span>
          </div>
        </div>

        {/* Theme Toggle Button */}
        <button
          type="button"
          id="theme-toggle"
          aria-label={isDark ? 'Switch to day mode' : 'Switch to night mode'}
          title={isDark ? 'Switch to day mode' : 'Switch to night mode'}
          onClick={toggleTheme}
          style={{
            background: 'var(--bg-surface)',
            border: '1px solid var(--border)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            cursor: 'pointer',
            padding: '9px',
            borderRadius: 'var(--radius-control)',
            color: 'var(--accent-primary)',
            boxShadow: 'var(--clay-shadow-sm)',
            transition: 'all 0.2s cubic-bezier(0.16, 1, 0.3, 1)',
            outline: 'none',
            pointerEvents: 'auto'
          }}
          onMouseEnter={(e) => {
            e.currentTarget.style.background = 'var(--bg-subtle)';
            e.currentTarget.style.transform = 'translateY(-1px)';
          }}
          onMouseLeave={(e) => {
            e.currentTarget.style.background = 'var(--bg-surface)';
            e.currentTarget.style.transform = 'translateY(0)';
          }}
          onFocus={(e) => {
            e.currentTarget.style.boxShadow = '0 0 0 3px var(--accent-tint), var(--clay-shadow-sm)';
          }}
          onBlur={(e) => {
            e.currentTarget.style.boxShadow = 'var(--clay-shadow-sm)';
          }}
        >
          <Icon name={isDark ? 'sun' : 'moon'} size={19} color="var(--accent-primary)" stroke={2.2} />
        </button>
      </header>

      {/* BACKGROUND DECORATIONS */}
      <div 
        style={{ 
          position: 'absolute', 
          inset: 0, 
          zIndex: 0, 
          pointerEvents: 'none',
          opacity: isDark ? 0.35 : 0.85,
          transition: 'opacity 0.25s ease'
        }} 
        className="hidden lg:block"
      >
        {/* Left Side */}
        <svg style={{ position: 'absolute', left: '10%', top: '40%', width: '200px', height: '350px', overflow: 'visible' }}>
          <path d="M 0,50 Q 20,-20 40,30 T 80,10 T 120,40" fill="none" stroke={isDark ? "#8E8272" : "#1C2B44"} strokeWidth="1" />
          <circle cx="160" cy="80" r="4" fill="none" stroke={isDark ? "#8E8272" : "#1C2B44"} strokeWidth="1" />
          
          <g transform="translate(30, 80)">
            <rect x="0" y="0" width="80" height="60" fill={isDark ? "#24221D" : "#F8FAFF"} stroke={isDark ? "#8E8272" : "#1C2B44"} strokeWidth="1" />
            <polygon points="20,60 20,75 35,60" fill={isDark ? "#24221D" : "#F8FAFF"} stroke={isDark ? "#8E8272" : "#1C2B44"} strokeWidth="1" />
            <line x1="20" y1="20" x2="60" y2="20" stroke={isDark ? "#8E8272" : "#1C2B44"} strokeWidth="1" />
            <line x1="20" y1="40" x2="40" y2="40" stroke={isDark ? "#8E8272" : "#1C2B44"} strokeWidth="1" />
          </g>

          <g transform="translate(-20, 190)">
            <rect x="0" y="0" width="60" height="120" fill={isDark ? "#3A4D39" : "#B3C8EA"} stroke={isDark ? "#8E8272" : "#1C2B44"} strokeWidth="1" />
            <circle cx="15" cy="20" r="2" fill={isDark ? "#F5F0E8" : "#1C2B44"} />
            <circle cx="45" cy="40" r="2" fill={isDark ? "#F5F0E8" : "#1C2B44"} />
            <circle cx="20" cy="70" r="2" fill={isDark ? "#F5F0E8" : "#1C2B44"} />
            <circle cx="35" cy="90" r="2" fill={isDark ? "#F5F0E8" : "#1C2B44"} />
            <circle cx="50" cy="110" r="2" fill={isDark ? "#F5F0E8" : "#1C2B44"} />
            <circle cx="10" cy="100" r="2" fill={isDark ? "#F5F0E8" : "#1C2B44"} />
            <circle cx="40" cy="15" r="2" fill={isDark ? "#F5F0E8" : "#1C2B44"} />
          </g>
          
          <g transform="translate(60, 240)">
            <rect x="0" y="0" width="80" height="70" fill={isDark ? "#24221D" : "#F8FAFF"} stroke={isDark ? "#8E8272" : "#1C2B44"} strokeWidth="1" />
            <path d="M 20,50 Q 40,50 60,20" fill="none" stroke={isDark ? "#D6AE76" : "#3B82F6"} strokeWidth="1.5" />
            <polygon points="60,20 50,22 58,28" fill={isDark ? "#D6AE76" : "#3B82F6"} />
          </g>
        </svg>

        {/* Right Side */}
        <svg style={{ position: 'absolute', right: '15%', top: '35%', width: '250px', height: '350px', overflow: 'visible' }}>
          <g transform="translate(20, 20)">
            <rect x="0" y="0" width="60" height="40" fill={isDark ? "#24221D" : "#F8FAFF"} stroke={isDark ? "#8E8272" : "#1C2B44"} strokeWidth="1" />
            <polygon points="40,40 40,50 50,40" fill={isDark ? "#24221D" : "#F8FAFF"} stroke={isDark ? "#8E8272" : "#1C2B44"} strokeWidth="1" />
            <line x1="15" y1="15" x2="45" y2="15" stroke={isDark ? "#8E8272" : "#1C2B44"} strokeWidth="1" />
            <line x1="15" y1="25" x2="35" y2="25" stroke={isDark ? "#8E8272" : "#1C2B44"} strokeWidth="1" />
          </g>
          <circle cx="0" cy="150" r="3" fill="none" stroke={isDark ? "#8E8272" : "#1C2B44"} strokeWidth="1" />
          
          <path d="M 180,30 Q 200,-10 220,10 T 250,5" fill="none" stroke={isDark ? "#8E8272" : "#1C2B44"} strokeWidth="1" />
          <circle cx="250" cy="-10" r="3" fill="none" stroke={isDark ? "#8E8272" : "#1C2B44"} strokeWidth="1" />

          {/* Dotted block */}
          <g transform="translate(160, 200)">
            <rect x="0" y="0" width="50" height="120" fill={isDark ? "#453D33" : "#D4E2F9"} stroke={isDark ? "#8E8272" : "#1C2B44"} strokeWidth="1" />
            <circle cx="15" cy="20" r="2" fill={isDark ? "#F5F0E8" : "#1C2B44"} />
            <circle cx="35" cy="40" r="2" fill={isDark ? "#F5F0E8" : "#1C2B44"} />
            <circle cx="20" cy="70" r="2" fill={isDark ? "#F5F0E8" : "#1C2B44"} />
            <circle cx="40" cy="90" r="2" fill={isDark ? "#F5F0E8" : "#1C2B44"} />
            <circle cx="25" cy="110" r="2" fill={isDark ? "#F5F0E8" : "#1C2B44"} />
            <circle cx="10" cy="55" r="2" fill={isDark ? "#F5F0E8" : "#1C2B44"} />
            <circle cx="45" cy="15" r="2" fill={isDark ? "#F5F0E8" : "#1C2B44"} />
          </g>

          <g transform="translate(80, 180)">
             <rect x="0" y="0" width="80" height="140" fill={isDark ? "#24221D" : "#F8FAFF"} stroke={isDark ? "#8E8272" : "#1C2B44"} strokeWidth="1" />
          </g>

          {/* Person Illustration */}
          <g transform="translate(40, 70)">
            <path d="M 50,45 Q 60,35 70,45" fill="none" stroke={isDark ? "#8E8272" : "#1C2B44"} strokeWidth="1" />
            <circle cx="60" cy="30" r="12" fill={isDark ? "#24221D" : "#F8FAFF"} stroke={isDark ? "#8E8272" : "#1C2B44"} strokeWidth="1" />
            <path d="M 60,18 C 65,15 75,18 75,25 C 75,32 80,35 85,35 L 95,35 C 95,40 90,45 80,45 L 70,45" fill={isDark ? "#D6AE76" : "#1C2B44"} />
            <circle cx="75" cy="15" r="4" fill={isDark ? "#D6AE76" : "#1C2B44"} />
            <path d="M 40,110 L 60,110 L 90,170 L 70,170 Z" fill={isDark ? "#24221D" : "#F8FAFF"} stroke={isDark ? "#8E8272" : "#1C2B44"} strokeWidth="1" />
            <path d="M 60,110 L 80,110 L 100,160 L 85,160 Z" fill={isDark ? "#24221D" : "#F8FAFF"} stroke={isDark ? "#8E8272" : "#1C2B44"} strokeWidth="1" />
            <path d="M 60,45 Q 40,65 50,85 C 55,95 70,110 80,110 C 90,110 95,95 95,85 L 90,50 Z" fill={isDark ? "#302A22" : "#E1EBFC"} stroke={isDark ? "#8E8272" : "#1C2B44"} strokeWidth="1" />
            <line x1="60" y1="55" x2="65" y2="60" stroke={isDark ? "#8E8272" : "#FFFFFF"} strokeWidth="1" />
            <line x1="80" y1="65" x2="85" y2="70" stroke={isDark ? "#8E8272" : "#FFFFFF"} strokeWidth="1" />
            <line x1="70" y1="80" x2="75" y2="85" stroke={isDark ? "#8E8272" : "#FFFFFF"} strokeWidth="1" />
            <line x1="55" y1="70" x2="60" y2="75" stroke={isDark ? "#8E8272" : "#FFFFFF"} strokeWidth="1" />
            
            <path d="M 50,60 Q 20,60 10,80" fill="none" stroke={isDark ? "#8E8272" : "#1C2B44"} strokeWidth="1" />
            <path d="M 10,80 L 15,85" stroke={isDark ? "#8E8272" : "#1C2B44"} strokeWidth="1" />

            <path d="M 70,70 Q 100,85 85,110" fill="none" stroke={isDark ? "#8E8272" : "#1C2B44"} strokeWidth="1" />
            
            {/* Laptop */}
            <polygon points="10,80 -10,105 10,110 25,85" fill={isDark ? "#4B5F80" : "#BFDBFE"} stroke={isDark ? "#8E8272" : "#1C2B44"} strokeWidth="1" />
            <line x1="-10" y1="105" x2="15" y2="105" stroke={isDark ? "#8E8272" : "#1C2B44"} strokeWidth="1" />

            {/* Feet */}
            <path d="M 70,170 L 60,175 L 50,170 L 60,165 Z" fill={isDark ? "#D6AE76" : "#1C2B44"} />
            <path d="M 85,160 L 95,165 L 85,175 L 75,170 Z" fill={isDark ? "#D6AE76" : "#1C2B44"} />
          </g>
        </svg>

        {/* Floor Line */}
        <line x1="5%" y1="75%" x2="95%" y2="75%" stroke={isDark ? "#5C5245" : "rgba(186, 206, 235, 0.85)"} strokeWidth="1" style={{ position: 'absolute', top: '75%', width: '100%' }} />
      </div>

      {/* LOGIN CARD */}
      <main style={{ flex: 1, display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 10, padding: '24px' }}>
        <div style={{ 
          width: '100%', 
          maxWidth: '440px', 
          background: 'var(--bg-surface)', 
          borderRadius: 'var(--radius-card, 18px)', 
          padding: '44px 38px', 
          boxShadow: 'var(--clay-shadow-float), var(--clay-inset)',
          border: '1px solid var(--border)',
          boxSizing: 'border-box',
          transition: 'background-color 0.25s ease, border-color 0.25s ease, box-shadow 0.25s ease'
        }}>
          <div style={{ textAlign: 'center', marginBottom: '28px' }}>
            <h1 style={{ 
              fontSize: '28px', 
              fontWeight: 800, 
              color: 'var(--heading-primary)', 
              marginBottom: '8px', 
              letterSpacing: '-0.025em',
              lineHeight: 1.2
            }}>
              Welcome Back
            </h1>
            <p style={{ 
              fontSize: '14.5px', 
              color: 'var(--ink-mute)', 
              fontWeight: 450,
              lineHeight: 1.4,
              margin: 0
            }}>
              Sign in to your Nexora CRM account
            </p>
          </div>

          <form onSubmit={handleLogin} style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
            {error && (
              <div 
                role="alert"
                style={{ 
                  padding: '12px 14px', 
                  background: 'var(--danger-bg)', 
                  color: 'var(--danger)', 
                  borderRadius: '10px', 
                  fontSize: '13px', 
                  fontWeight: 500, 
                  textAlign: 'center',
                  border: '1px solid var(--danger-bg)',
                  lineHeight: 1.4
                }}
              >
                {error}
              </div>
            )}
            
            <div style={{ display: 'flex', flexDirection: 'column', gap: '7px' }}>
              <label 
                htmlFor="login-email"
                style={{ 
                  fontSize: '13px', 
                  fontWeight: 650, 
                  color: 'var(--ink)',
                  letterSpacing: '-0.01em'
                }}
              >
                Email
              </label>
              <div style={{ position: 'relative' }}>
                <div 
                  style={{ 
                    position: 'absolute', 
                    left: '14px', 
                    top: '50%', 
                    transform: 'translateY(-50%)', 
                    color: 'var(--ink-mute)',
                    display: 'flex',
                    alignItems: 'center',
                    pointerEvents: 'none'
                  }}
                >
                  <Icon name="mail" size={17} stroke={2} />
                </div>
                <input
                  id="login-email"
                  type="email"
                  required
                  placeholder="name@company.com"
                  value={email}
                  onChange={(e) => setEmail(e.target.value)}
                  style={{
                    width: '100%',
                    padding: '12px 16px 12px 42px',
                    borderRadius: 'var(--radius-control, 11px)',
                    border: '1px solid var(--border)',
                    fontSize: '14px',
                    outline: 'none',
                    color: 'var(--ink)',
                    background: 'var(--bg-canvas)',
                    boxShadow: 'var(--clay-recessed)',
                    transition: 'all 0.18s ease',
                    boxSizing: 'border-box'
                  }}
                  onFocus={(e) => {
                    e.target.style.borderColor = 'var(--accent-primary)';
                    e.target.style.boxShadow = '0 0 0 3px var(--accent-tint), var(--clay-recessed)';
                  }}
                  onBlur={(e) => {
                    e.target.style.borderColor = 'var(--border)';
                    e.target.style.boxShadow = 'var(--clay-recessed)';
                  }}
                />
              </div>
            </div>

            <div style={{ display: 'flex', flexDirection: 'column', gap: '7px' }}>
              <label 
                htmlFor="login-password"
                style={{ 
                  fontSize: '13px', 
                  fontWeight: 650, 
                  color: 'var(--ink)',
                  letterSpacing: '-0.01em'
                }}
              >
                Password
              </label>
              <div style={{ position: 'relative' }}>
                <div 
                  style={{ 
                    position: 'absolute', 
                    left: '14px', 
                    top: '50%', 
                    transform: 'translateY(-50%)', 
                    color: 'var(--ink-mute)',
                    display: 'flex',
                    alignItems: 'center',
                    pointerEvents: 'none'
                  }}
                >
                  <Icon name="lock" size={17} stroke={2} />
                </div>
                <input
                  id="login-password"
                  type={showPassword ? 'text' : 'password'}
                  required
                  placeholder="Enter your password"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  style={{
                    width: '100%',
                    padding: '12px 42px 12px 42px',
                    borderRadius: 'var(--radius-control, 11px)',
                    border: '1px solid var(--border)',
                    fontSize: '14px',
                    outline: 'none',
                    color: 'var(--ink)',
                    background: 'var(--bg-canvas)',
                    boxShadow: 'var(--clay-recessed)',
                    transition: 'all 0.18s ease',
                    boxSizing: 'border-box'
                  }}
                  onFocus={(e) => {
                    e.target.style.borderColor = 'var(--accent-primary)';
                    e.target.style.boxShadow = '0 0 0 3px var(--accent-tint), var(--clay-recessed)';
                  }}
                  onBlur={(e) => {
                    e.target.style.borderColor = 'var(--border)';
                    e.target.style.boxShadow = 'var(--clay-recessed)';
                  }}
                />
                <button
                  type="button"
                  onClick={() => setShowPassword(!showPassword)}
                  style={{
                    position: 'absolute',
                    right: '10px',
                    top: '50%',
                    transform: 'translateY(-50%)',
                    background: 'transparent',
                    border: 'none',
                    color: 'var(--ink-mute)',
                    cursor: 'pointer',
                    padding: '6px',
                    borderRadius: '8px',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    transition: 'all 0.15s ease'
                  }}
                  onMouseEnter={(e) => {
                    e.currentTarget.style.color = 'var(--ink)';
                    e.currentTarget.style.background = 'var(--accent-tint)';
                  }}
                  onMouseLeave={(e) => {
                    e.currentTarget.style.color = 'var(--ink-mute)';
                    e.currentTarget.style.background = 'transparent';
                  }}
                  aria-label={showPassword ? 'Hide password' : 'Show password'}
                  title={showPassword ? 'Hide password' : 'Show password'}
                >
                  {showPassword ? <Eye size={17} strokeWidth={2} /> : <EyeOff size={17} strokeWidth={2} />}
                </button>
              </div>
            </div>

            <button
              type="submit"
              disabled={loading}
              style={{
                width: '100%',
                padding: '13px 18px',
                background: 'var(--accent-primary)',
                color: isDark ? '#1C1C1C' : '#FFFFFF',
                border: '1px solid rgba(255, 255, 255, 0.25)',
                borderRadius: 'var(--radius-control, 11px)',
                fontSize: '14.5px',
                fontWeight: 650,
                cursor: loading ? 'not-allowed' : 'pointer',
                opacity: loading ? 0.75 : 1,
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                gap: '8px',
                marginTop: '6px',
                boxShadow: 'var(--clay-shadow-sm), var(--clay-inset)',
                transition: 'all 0.18s cubic-bezier(0.16, 1, 0.3, 1)',
                outline: 'none'
              }}
              onMouseEnter={(e) => {
                if (!loading) {
                  e.currentTarget.style.backgroundColor = 'var(--accent-hover)';
                  e.currentTarget.style.transform = 'translateY(-1px)';
                  e.currentTarget.style.boxShadow = 'var(--clay-shadow-hover), var(--clay-inset)';
                }
              }}
              onMouseLeave={(e) => {
                if (!loading) {
                  e.currentTarget.style.backgroundColor = 'var(--accent-primary)';
                  e.currentTarget.style.transform = 'translateY(0)';
                  e.currentTarget.style.boxShadow = 'var(--clay-shadow-sm), var(--clay-inset)';
                }
              }}
              onFocus={(e) => {
                e.currentTarget.style.boxShadow = '0 0 0 3px var(--accent-tint), var(--clay-shadow-sm)';
              }}
              onBlur={(e) => {
                e.currentTarget.style.boxShadow = 'var(--clay-shadow-sm), var(--clay-inset)';
              }}
            >
              {loading ? (
                <>
                  <span 
                    style={{
                      width: '14px',
                      height: '14px',
                      border: '2px solid rgba(255, 255, 255, 0.4)',
                      borderTopColor: isDark ? '#1C1C1C' : '#FFFFFF',
                      borderRadius: '50%',
                      animation: 'spin 0.75s linear infinite',
                      display: 'inline-block'
                    }} 
                  />
                  <span>Signing In...</span>
                  <style>{`
                    @keyframes spin {
                      to { transform: rotate(360deg); }
                    }
                  `}</style>
                </>
              ) : (
                'Sign In'
              )}
            </button>
          </form>
        </div>
      </main>
    </div>
  );
}
