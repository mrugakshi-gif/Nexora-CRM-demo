import React, { useState, useEffect, useContext } from 'react';
import PageHeader from '../components/common/PageHeader';
import Icon from '../components/common/Icon';
import Card from '../components/common/Card';
import { AuthContext } from '../AuthContext';
import api from '../api';

export default function Settings() {
  const { effectiveRole, user } = useContext(AuthContext);
  const [prefs, setPrefs] = useState({
    density: 'standard',
    defaultPage: '/dashboard',
    taskReminders: true,
    supportNotifications: true,
    aiRecommendationAlerts: true,
    emailNotifications: true,
    aiRecommendations: true,
    knowledgeAssistant: true,
    aiConfirmation: true
  });
  const [testEmailStatus, setTestEmailStatus] = useState(null);
  const [isTestingEmail, setIsTestingEmail] = useState(false);

  const [draftType, setDraftType] = useState('High Priority Support Alert');
  const [draftContext, setDraftContext] = useState('{}');
  const [draftRecipient, setDraftRecipient] = useState('');
  const [recordOptions, setRecordOptions] = useState([]);
  const [selectedRecord, setSelectedRecord] = useState('');
  const [isSendingDraft, setIsSendingDraft] = useState(false);
  const [sendDraftSuccess, setSendDraftSuccess] = useState(false);
  const [isGeneratingDraft, setIsGeneratingDraft] = useState(false);
  const [draftResult, setDraftResult] = useState(null);
  const [draftError, setDraftError] = useState(null);
  const [automationConfig, setAutomationConfig] = useState({
    enabled: false,
    mode: 'DRY_RUN',
    interval_minutes: 60,
    test_email: '',
    rules: {
      support: true,
      leads: true,
      opportunities: true,
      renewals: true,
      churn: true
    }
  });
  const [isAdmin, setIsAdmin] = useState(false);
  const [isRunning, setIsRunning] = useState(false);
  const [runResult, setRunResult] = useState(null);

  useEffect(() => {
    // Fetch records for draft preview
    const fetchRecords = async () => {
      try {
        if (!user || !isAdmin) return;
        
        // We fetch candidates from the preview API.
        const res = await api.get('/api/automation/preview-candidates');
        if (res.data && res.data.data) {
          const allCands = res.data.data;
          const mappedType = draftType === 'High Churn Risk' ? 'High Churn Risk Alert' : draftType;
          const filtered = allCands.filter(c => c.type === mappedType);
          setRecordOptions(filtered);
        } else {
          setRecordOptions([]);
        }
      } catch (e) {
        console.error("Failed to fetch records", e);
      }
    };
    fetchRecords();
  }, [draftType, user, isAdmin]);

  useEffect(() => {
    if (!selectedRecord || !recordOptions.length) {
      setDraftContext('{}');
      setDraftRecipient('');
      return;
    }
    const rec = recordOptions.find(r => r.event_key === selectedRecord);
    if (!rec) return;

    setDraftContext(JSON.stringify(rec.context, null, 2));
    setDraftRecipient(rec.recipient_email || 'No recipient email available for this record.');
  }, [selectedRecord, recordOptions, draftType, user]);

  useEffect(() => {
    try {
      const saved = JSON.parse(localStorage.getItem('nexora_crm_prefs') || '{}');
      setPrefs({
        theme: saved.theme || 'light',
        density: saved.density || 'standard',
        defaultPage: (saved.defaultPage === '/' ? '/dashboard' : saved.defaultPage) || '/dashboard',
        taskReminders: saved.taskReminders ?? true,
        supportNotifications: saved.supportNotifications ?? true,
        aiRecommendationAlerts: saved.aiRecommendationAlerts ?? true,
        emailNotifications: saved.emailNotifications ?? true,
        aiRecommendations: saved.aiRecommendations ?? true,
        knowledgeAssistant: saved.knowledgeAssistant ?? true,
        aiConfirmation: saved.aiConfirmation ?? true
      });
      
      const adminCheck = effectiveRole === 'System Admin' || effectiveRole === 'Admin';
      setIsAdmin(adminCheck);

      if (user) {
        // Fetch email preferences
        api.get('/api/settings/email-preferences')
        .then(res => {
          if (res.data && typeof res.data.email_notifications === 'boolean') {
            setPrefs(p => ({ ...p, emailNotifications: res.data.email_notifications }));
          }
        })
        .catch(err => console.error("Failed to fetch email preferences", err));

        // Fetch automation config if admin
        if (adminCheck) {
          api.get('/api/automation/settings')
          .then(res => {
            if (res.data && res.data.status === 'success') {
              setAutomationConfig(res.data.data);
            }
          })
          .catch(err => console.error("Failed to fetch automation config", err));
        }
      }
    } catch (e) {}
  }, [effectiveRole]);

  useEffect(() => {
    const handleThemeSync = (e) => {
      const syncedTheme = e.detail || 'light';
      setPrefs(p => ({ ...p, theme: syncedTheme }));
    };
    window.addEventListener('nexora-theme-change', handleThemeSync);
    return () => window.removeEventListener('nexora-theme-change', handleThemeSync);
  }, []);

  const handleUpdate = (key, value) => {
    const newPrefs = { ...prefs, [key]: value };
    setPrefs(newPrefs);
    localStorage.setItem('nexora_crm_prefs', JSON.stringify(newPrefs));
    
    // Apply density immediately
    if (key === 'density') {
      document.body.setAttribute('data-density', value);
    }
    
    // Apply theme immediately
    if (key === 'theme') {
      document.documentElement.setAttribute('data-theme', value);
      window.dispatchEvent(new CustomEvent('nexora-theme-change', { detail: value }));
    }
    
    // Sync emailNotifications to backend
    if (key === 'emailNotifications') {
      if (user) {
        api.put('/api/settings/email-preferences', { email_notifications: value })
          .catch(err => console.error("Failed to update email preferences", err));
      }
    }
  };

  const testEmailConfiguration = async () => {
    let email = user?.email || "test@example.com";

    setIsTestingEmail(true);
    setTestEmailStatus(null);
    try {
      await api.post('/api/settings/test-email', { recipient_email: email });
      setTestEmailStatus("success");
    } catch (error) {
      setTestEmailStatus("error");
    } finally {
      setIsTestingEmail(false);
      setTimeout(() => setTestEmailStatus(null), 5000);
    }
  };

  const handleGenerateDraft = async () => {
    let parsedContext = {};
    try {
      parsedContext = JSON.parse(draftContext);
    } catch (e) {
      setDraftError("Invalid JSON in context field. Please check the context formatting.");
      return;
    }

    setIsGeneratingDraft(true);
    setDraftError(null);
    setDraftResult(null);

    try {
      const res = await api.post('/api/email/generate', {
        alert_type: draftType,
        context: parsedContext,
        recipient_name: 'Admin'
      });
      setDraftResult(res.data);
    } catch (error) {
      const status = error.response?.status;
      const rawDetail = error.response?.data?.detail || error.message || '';
      const detailStr = String(rawDetail).toLowerCase();

      if (
        status === 503 ||
        status === 429 ||
        detailStr.includes('503') ||
        detailStr.includes('unavailable') ||
        detailStr.includes('high demand') ||
        detailStr.includes('spikes in demand') ||
        detailStr.includes('rate limit') ||
        detailStr.includes('resource exhausted')
      ) {
        setDraftError("The AI model is currently experiencing high demand. Spikes in demand are usually temporary. Please try again in a moment.");
      } else if (rawDetail && typeof rawDetail === 'string' && !rawDetail.includes('{') && rawDetail.length < 150) {
        setDraftError(rawDetail);
      } else {
        setDraftError("Failed to generate draft. Please check your connection and try again.");
      }
    } finally {
      setIsGeneratingDraft(false);
    }
  };

  const handleAutomationUpdate = async (updates) => {
    const newConfig = { ...automationConfig, ...updates };
    setAutomationConfig(newConfig);

    if (user && isAdmin) {
      try {
        await api.post('/api/automation/settings', newConfig);
      } catch (err) {
        console.error("Failed to update automation config", err);
      }
    }
  };

  const handleAutomationRuleToggle = (ruleKey, checked) => {
    handleAutomationUpdate({
      rules: { ...automationConfig.rules, [ruleKey]: checked }
    });
  };

  const handleRunAutomation = async () => {
    if (!user || !isAdmin) return;

    setIsRunning(true);
    setRunResult(null);
    try {
      const res = await api.post('/api/automation/run');
      setRunResult(res.data.data);
    } catch (err) {
      setRunResult({ error: err.response?.data?.detail || err.message });
    } finally {
      setIsRunning(false);
    }
  };

  const LockedSetting = ({ icon, title, value }) => (
    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '12px 0', borderBottom: '1px solid var(--border-soft)' }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: '12px', opacity: 0.6 }}>
        <Icon name={icon} size={16} color="var(--ink-mute)" />
        <span style={{ fontSize: '13px', color: 'var(--ink)' }}>{title}</span>
      </div>
      <div style={{ fontSize: '13px', color: 'var(--ink-mute)', fontStyle: 'italic', background: 'var(--bg)', padding: '4px 10px', borderRadius: '4px' }}>
        {value}
      </div>
    </div>
  );

  const ToggleSetting = ({ icon, title, desc, prefKey, isLast, isOnOverride, onChangeOverride }) => {
    const isOn = isOnOverride !== undefined ? isOnOverride : !!prefs[prefKey];
    const handleChange = onChangeOverride || ((e) => handleUpdate(prefKey, e.target.checked));
    
    return (
    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '12px 0', borderBottom: isLast ? 'none' : '1px solid var(--border-soft)' }}>
      <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
        <Icon name={icon} size={16} color="var(--ink-mute)" />
        <div>
          <div style={{ fontSize: '13px', color: 'var(--ink)' }}>{title}</div>
          {desc && <div style={{ fontSize: '12px', color: 'var(--ink-soft)' }}>{desc}</div>}
        </div>
      </div>
      <label style={{ display: 'flex', alignItems: 'center', gap: '12px', cursor: 'pointer', position: 'relative' }}>
        <span style={{ fontSize: '12px', fontWeight: 600, color: isOn ? 'var(--brown)' : 'var(--ink-mute)', width: '28px', textAlign: 'right' }}>
          {isOn ? 'ON' : 'OFF'}
        </span>
        <input 
          type="checkbox" 
          checked={isOn} 
          onChange={handleChange} 
          className="toggle-input"
          style={{ position: 'absolute', opacity: 0, width: '100%', height: '100%', cursor: 'pointer', margin: 0, zIndex: 1 }} 
        />
        <div className="toggle-track" style={{
          position: 'relative', width: '40px', height: '22px', borderRadius: '11px',
          background: isOn ? 'var(--brown)' : 'var(--bg-soft)',
          border: `1px solid ${isOn ? 'var(--brown)' : 'var(--border)'}`,
          transition: 'all 0.25s ease'
        }}>
          <div style={{
            position: 'absolute', top: '1px', left: isOn ? '19px' : '1px',
            width: '18px', height: '18px', borderRadius: '50%', 
            background: isOn ? '#ffffff' : 'var(--ink-soft)',
            transition: 'all 0.25s cubic-bezier(0.4, 0.0, 0.2, 1)', 
            boxShadow: '0 1px 3px rgba(0,0,0,0.15)'
          }}></div>
        </div>
      </label>
    </div>
  )};

  return (
    <div className="page">
      <style>{`
        .toggle-input:focus-visible + .toggle-track {
          outline: 2px solid var(--brown);
          outline-offset: 2px;
        }
      `}</style>
      <PageHeader 
        title="Settings" 
        desc="Manage your application preferences and configuration."
      />
      <div style={{ padding: '0 28px 28px', maxWidth: '800px' }}>
        
        <div style={{ display: 'flex', flexDirection: 'column', gap: '24px' }}>
          
          <Card>
            <div style={{ padding: '16px 20px', borderBottom: '1px solid var(--border)', display: 'flex', alignItems: 'center', gap: '8px' }}>
              <Icon name="layout" size={16} color="var(--brown)" />
              <h3 style={{ margin: 0, fontSize: '14px', fontWeight: 600, color: 'var(--brown)' }}>Appearance</h3>
            </div>
            <div style={{ padding: '8px 20px 20px' }}>
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '12px 0', borderBottom: '1px solid var(--border-soft)' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                  <Icon name={prefs.theme === 'dark' ? 'moon' : 'sun'} size={16} color="var(--ink-mute)" />
                  <div>
                    <div style={{ fontSize: '13px', color: 'var(--ink)' }}>Theme Mode</div>
                    <div style={{ fontSize: '12px', color: 'var(--ink-soft)' }}>
                      {prefs.theme === 'dark' ? 'Warm Neutral Claymorphism' : 'Sky Blue Claymorphism'}
                    </div>
                  </div>
                </div>
                <select 
                  style={{ padding: '6px 12px', borderRadius: '8px', border: '1px solid var(--border)', fontSize: '13px', background: 'var(--white)', color: 'var(--ink)', cursor: 'pointer' }}
                  value={prefs.theme || 'light'}
                  onChange={e => handleUpdate('theme', e.target.value)}
                >
                  <option value="light">Day Mode (Sky Blue Clay)</option>
                  <option value="dark">Night Mode (Warm Neutral Clay)</option>
                </select>
              </div>

              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '12px 0' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                  <Icon name="menu" size={16} color="var(--ink-mute)" />
                  <div>
                    <div style={{ fontSize: '13px', color: 'var(--ink)' }}>Table Density</div>
                    <div style={{ fontSize: '12px', color: 'var(--ink-soft)' }}>Adjust data row spacing</div>
                  </div>
                </div>
                <select 
                  style={{ padding: '6px 12px', borderRadius: '8px', border: '1px solid var(--border)', fontSize: '13px', background: 'var(--white)', color: 'var(--ink)', cursor: 'pointer' }}
                  value={prefs.density}
                  onChange={e => handleUpdate('density', e.target.value)}
                >
                  <option value="compact">Compact</option>
                  <option value="standard">Standard</option>
                  <option value="comfortable">Comfortable</option>
                </select>
              </div>
            </div>
          </Card>

          <Card>
            <div style={{ padding: '16px 20px', borderBottom: '1px solid var(--border)', display: 'flex', alignItems: 'center', gap: '8px' }}>
              <Icon name="settings" size={16} color="var(--brown)" />
              <h3 style={{ margin: 0, fontSize: '14px', fontWeight: 600, color: 'var(--brown)' }}>CRM Preferences</h3>
            </div>
            <div style={{ padding: '8px 20px 20px' }}>
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '12px 0', borderBottom: '1px solid var(--border-soft)' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                  <Icon name="home" size={16} color="var(--ink-mute)" />
                  <div>
                    <div style={{ fontSize: '13px', color: 'var(--ink)' }}>Default Landing Page</div>
                    <div style={{ fontSize: '12px', color: 'var(--ink-soft)' }}>Where you go after logging in</div>
                  </div>
                </div>
                <select 
                  style={{ 
                    padding: '6px 12px', 
                    borderRadius: '4px', 
                    border: '1px solid var(--border)', 
                    fontSize: '13px', 
                    background: 'var(--white)', 
                    color: 'var(--ink)', 
                    colorScheme: prefs.theme === 'dark' ? 'dark' : 'light',
                    cursor: 'pointer' 
                  }}
                  value={prefs.defaultPage === '/' ? '/dashboard' : prefs.defaultPage}
                  onChange={e => handleUpdate('defaultPage', e.target.value)}
                >
                  <option style={{ background: 'var(--white)', color: 'var(--ink)' }} value="/dashboard">Dashboard</option>
                  <option style={{ background: 'var(--white)', color: 'var(--ink)' }} value="/companies">Companies</option>
                  <option style={{ background: 'var(--white)', color: 'var(--ink)' }} value="/customers">Customers</option>
                  <option style={{ background: 'var(--white)', color: 'var(--ink)' }} value="/leads">Leads</option>
                </select>
              </div>
              <LockedSetting icon="indianrupee" title="Currency" value="₹ INR" />
            </div>
          </Card>

          <Card>
            <div style={{ padding: '16px 20px', borderBottom: '1px solid var(--border)', display: 'flex', alignItems: 'center', gap: '8px' }}>
              <Icon name="bell" size={16} color="var(--brown)" />
              <h3 style={{ margin: 0, fontSize: '14px', fontWeight: 600, color: 'var(--brown)' }}>Notifications</h3>
            </div>
            <div style={{ padding: '8px 20px 20px' }}>
              <ToggleSetting icon="clock" title="Task & Follow-up Reminders" prefKey="taskReminders" />
              <ToggleSetting icon="alertcircle" title="Support Notifications" prefKey="supportNotifications" />
              <ToggleSetting icon="sparkles" title="AI Recommendation Alerts" prefKey="aiRecommendationAlerts" />
              <ToggleSetting icon="mail" title="Email Notifications" prefKey="emailNotifications" isLast={true} />
              
              <div style={{ padding: '16px 0 8px', marginTop: '8px', borderTop: '1px solid var(--border-soft)' }}>
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                  <div>
                    <div style={{ fontSize: '13px', color: 'var(--ink)' }}>Test Email Configuration</div>
                    <div style={{ fontSize: '12px', color: 'var(--ink-soft)' }}>Send a test email to your account email address</div>
                  </div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                    {testEmailStatus === 'success' && <span style={{ fontSize: '12px', color: 'green' }}>Test email sent!</span>}
                    {testEmailStatus === 'error' && <span style={{ fontSize: '12px', color: 'red' }}>Failed to send</span>}
                    <button 
                      onClick={testEmailConfiguration}
                      disabled={isTestingEmail}
                      style={{ 
                        padding: '6px 12px', 
                        borderRadius: '4px', 
                        border: '1px solid var(--border)', 
                        background: 'var(--white)',
                        fontSize: '12px',
                        cursor: isTestingEmail ? 'not-allowed' : 'pointer',
                        opacity: isTestingEmail ? 0.6 : 1
                      }}
                    >
                      {isTestingEmail ? 'Sending...' : 'Send Test'}
                    </button>
                  </div>
                </div>
              </div>
            </div>
          </Card>

          {isAdmin && (
          <Card>
            <div style={{ padding: '16px 20px', borderBottom: '1px solid var(--border)', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <Icon name="cpu" size={16} color="var(--brown)" />
                <h3 style={{ margin: 0, fontSize: '14px', fontWeight: 600, color: 'var(--brown)' }}>AI Automation (Admin Only)</h3>
              </div>
              <button 
                onClick={handleRunAutomation}
                disabled={isRunning}
                style={{ 
                  padding: '6px 12px', 
                  borderRadius: '4px', 
                  border: '1px solid var(--border)', 
                  background: 'var(--brown)',
                  color: 'white',
                  fontSize: '12px',
                  cursor: isRunning ? 'not-allowed' : 'pointer',
                  opacity: isRunning ? 0.7 : 1
                }}
              >
                {isRunning ? 'Running...' : 'Run Automation Now'}
              </button>
            </div>
            
            <div style={{ padding: '8px 20px 20px' }}>
              <ToggleSetting 
                icon="zap" 
                title="Automation Enabled" 
                desc="Turn background AI email generation ON/OFF globally."
                isOnOverride={automationConfig.enabled}
                onChangeOverride={(e) => handleAutomationUpdate({ enabled: e.target.checked })}
              />

              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '12px 0', borderBottom: '1px solid var(--border-soft)' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                  <Icon name="mail" size={16} color="var(--ink-mute)" />
                  <div>
                    <div style={{ fontSize: '13px', color: 'var(--ink)' }}>Email Mode</div>
                    <div style={{ fontSize: '12px', color: 'var(--ink-soft)' }}>DRY RUN will draft emails but won't send them</div>
                  </div>
                </div>
                <select 
                  style={{ 
                    padding: '6px 12px', 
                    borderRadius: '4px', 
                    border: '1px solid var(--border)', 
                    fontSize: '13px', 
                    background: 'var(--white)', 
                    color: 'var(--ink)', 
                    colorScheme: prefs.theme === 'dark' ? 'dark' : 'light',
                    cursor: 'pointer' 
                  }}
                  value={automationConfig.mode}
                  onChange={e => handleAutomationUpdate({ mode: e.target.value })}
                >
                  <option style={{ background: 'var(--white)', color: 'var(--ink)' }} value="DRY_RUN">DRY RUN</option>
                  <option style={{ background: 'var(--white)', color: 'var(--ink)' }} value="SEND">SEND</option>
                </select>
              </div>

              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '12px 0', borderBottom: '1px solid var(--border-soft)' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                  <Icon name="clock" size={16} color="var(--ink-mute)" />
                  <div>
                    <div style={{ fontSize: '13px', color: 'var(--ink)' }}>Automation Interval (Minutes)</div>
                  </div>
                </div>
                <input 
                  type="number"
                  min="5"
                  style={{ 
                    width: '80px', 
                    padding: '6px 12px', 
                    borderRadius: '4px', 
                    border: '1px solid var(--border)', 
                    fontSize: '13px',
                    background: 'var(--white)',
                    color: 'var(--ink)',
                    colorScheme: prefs.theme === 'dark' ? 'dark' : 'light'
                  }}
                  value={automationConfig.interval_minutes}
                  onChange={e => handleAutomationUpdate({ interval_minutes: parseInt(e.target.value) || 60 })}
                />
              </div>

              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', padding: '12px 0', borderBottom: '1px solid var(--border-soft)' }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                  <Icon name="users" size={16} color="var(--ink-mute)" />
                  <div>
                    <div style={{ fontSize: '13px', color: 'var(--ink)' }}>Test Recipient Email</div>
                    <div style={{ fontSize: '12px', color: 'var(--ink-soft)' }}>All real emails will be redirected here if specified</div>
                  </div>
                </div>
                <input 
                  type="email"
                  placeholder="admin@example.com"
                  style={{ 
                    width: '200px', 
                    padding: '6px 12px', 
                    borderRadius: '4px', 
                    border: '1px solid var(--border)', 
                    fontSize: '13px',
                    background: 'var(--white)',
                    color: 'var(--ink)',
                    colorScheme: prefs.theme === 'dark' ? 'dark' : 'light'
                  }}
                  value={automationConfig.test_email || ''}
                  onChange={e => handleAutomationUpdate({ test_email: e.target.value })}
                />
              </div>

              <div style={{ padding: '16px 0 8px', marginTop: '8px' }}>
                <h4 style={{ fontSize: '13px', color: 'var(--ink)', marginBottom: '12px' }}>Trigger Rules</h4>
                <ToggleSetting icon="alertcircle" title="High-Priority Support" isOnOverride={automationConfig.rules.support} onChangeOverride={e => handleAutomationRuleToggle('support', e.target.checked)} />
                <ToggleSetting icon="user" title="Leads Needing Follow-up" isOnOverride={automationConfig.rules.leads} onChangeOverride={e => handleAutomationRuleToggle('leads', e.target.checked)} />
                <ToggleSetting icon="briefcase" title="Opportunities Closing Soon" isOnOverride={automationConfig.rules.opportunities} onChangeOverride={e => handleAutomationRuleToggle('opportunities', e.target.checked)} />
                <ToggleSetting icon="calendar" title="Customer Renewals" isOnOverride={automationConfig.rules.renewals} onChangeOverride={e => handleAutomationRuleToggle('renewals', e.target.checked)} />
                <ToggleSetting icon="piechart" title="High Churn Risk" isOnOverride={automationConfig.rules.churn} onChangeOverride={e => handleAutomationRuleToggle('churn', e.target.checked)} isLast={true} />
              </div>

              <div style={{ marginTop: '16px', padding: '16px', background: 'var(--bg-soft)', borderRadius: '4px', border: '1px solid var(--border-soft)' }}>
                <h4 style={{ fontSize: '12px', fontWeight: 600, margin: '0 0 8px', color: 'var(--ink)' }}>Last Run Result</h4>
                {!runResult ? (
                  <div style={{ fontSize: '12px', color: 'var(--ink-soft)' }}>No automation run has been executed yet.</div>
                ) : runResult.error ? (
                  <div style={{ fontSize: '12px', color: 'red' }}>Error: {runResult.error}</div>
                ) : (
                  <div style={{ display: 'grid', gridTemplateColumns: 'repeat(2, 1fr)', gap: '8px', fontSize: '12px' }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between' }}><span style={{ color: 'var(--ink-soft)' }}>Detected:</span> <b>{runResult.detected ?? 0}</b></div>
                    <div style={{ display: 'flex', justifyContent: 'space-between' }}><span style={{ color: 'var(--ink-soft)' }}>Generated:</span> <b>{runResult.generated ?? 0}</b></div>
                    <div style={{ display: 'flex', justifyContent: 'space-between' }}><span style={{ color: 'var(--ink-soft)' }}>Sent:</span> <b>{runResult.sent ?? 0}</b></div>
                    <div style={{ display: 'flex', justifyContent: 'space-between' }}><span style={{ color: 'var(--ink-soft)' }}>Failed:</span> <b>{runResult.failed ?? 0}</b></div>
                    <div style={{ display: 'flex', justifyContent: 'space-between', gridColumn: '1 / -1' }}><span style={{ color: 'var(--ink-soft)' }}>Duplicates Skipped:</span> <b>{runResult.skipped_duplicates ?? 0}</b></div>
                  </div>
                )}
              </div>
            </div>
          </Card>
          )}

          <Card>
            <div style={{ padding: '16px 20px', borderBottom: '1px solid var(--border)', display: 'flex', alignItems: 'center', gap: '8px' }}>
              <Icon name="sparkles" size={16} color="var(--brown)" />
              <h3 style={{ margin: 0, fontSize: '14px', fontWeight: 600, color: 'var(--brown)' }}>AI Email Draft Preview</h3>
            </div>
            <div style={{ padding: '20px', display: 'flex', flexDirection: 'column', gap: '16px' }}>
              <div>
                <div style={{ fontSize: '13px', color: 'var(--ink)', marginBottom: '8px' }}>Draft Type</div>
                <select 
                  style={{ 
                    width: '100%', 
                    padding: '8px', 
                    borderRadius: '4px', 
                    border: '1px solid var(--border)', 
                    fontSize: '13px', 
                    background: 'var(--white)', 
                    color: 'var(--ink)',
                    colorScheme: prefs.theme === 'dark' ? 'dark' : 'light'
                  }}
                  value={draftType}
                  onChange={e => {
                    setDraftType(e.target.value);
                    setSelectedRecord('');
                    setDraftResult(null);
                  }}
                >
                  <option style={{ background: 'var(--white)', color: 'var(--ink)' }} value="High Priority Support Alert">High Priority Support Alert</option>
                  <option style={{ background: 'var(--white)', color: 'var(--ink)' }} value="Opportunity Closing Soon">Opportunity Closing Soon</option>
                  <option style={{ background: 'var(--white)', color: 'var(--ink)' }} value="High Churn Risk">High Churn Risk</option>
                  <option style={{ background: 'var(--white)', color: 'var(--ink)' }} value="New High-Value Lead">New High-Value Lead</option>
                  <option style={{ background: 'var(--white)', color: 'var(--ink)' }} value="AI Recommendation">AI Recommendation</option>
                </select>
              </div>
              {recordOptions.length > 0 && (
                <div>
                  <div style={{ fontSize: '13px', color: 'var(--ink)', marginBottom: '8px' }}>Select Real Record</div>
                  <select 
                    style={{ 
                      width: '100%', 
                      padding: '8px', 
                      borderRadius: '4px', 
                      border: '1px solid var(--border)', 
                      fontSize: '13px', 
                      background: 'var(--white)', 
                      color: 'var(--ink)',
                      colorScheme: prefs.theme === 'dark' ? 'dark' : 'light'
                    }}
                    value={selectedRecord}
                    onChange={e => {
                      setSelectedRecord(e.target.value);
                      setDraftResult(null);
                    }}
                  >
                    <option style={{ background: 'var(--white)', color: 'var(--ink)' }} value="">-- Select a record --</option>
                    {recordOptions.map(r => (
                      <option key={r.event_key} value={r.event_key} style={{ background: 'var(--white)', color: 'var(--ink)' }}>
                        {r.label}
                      </option>
                    ))}
                  </select>
                </div>
              )}
              <div>
                <div style={{ fontSize: '13px', color: 'var(--ink)', marginBottom: '8px' }}>Recipient Email</div>
                <input 
                  type="email"
                  style={{ 
                    width: '100%', 
                    padding: '8px', 
                    borderRadius: '4px', 
                    border: '1px solid var(--border)', 
                    fontSize: '13px',
                    background: 'var(--white)',
                    color: 'var(--ink)',
                    colorScheme: prefs.theme === 'dark' ? 'dark' : 'light'
                  }}
                  value={draftRecipient}
                  onChange={e => setDraftRecipient(e.target.value)}
                />
              </div>
              <div>
                <div style={{ fontSize: '13px', color: 'var(--ink)', marginBottom: '8px' }}>Structured Context (JSON)</div>
                <textarea 
                  style={{ 
                    width: '100%', 
                    padding: '8px', 
                    borderRadius: '4px', 
                    border: '1px solid var(--border)', 
                    fontSize: '13px', 
                    minHeight: '100px', 
                    fontFamily: 'monospace',
                    background: 'var(--white)',
                    color: 'var(--ink)',
                    colorScheme: prefs.theme === 'dark' ? 'dark' : 'light'
                  }}
                  value={draftContext}
                  onChange={e => setDraftContext(e.target.value)}
                />
              </div>
              {draftError && (
                <div 
                  role="alert"
                  style={{ 
                    padding: '12px 16px', 
                    borderRadius: '6px', 
                    background: 'var(--danger-bg)', 
                    border: '1px solid var(--danger)', 
                    color: 'var(--danger-text)', 
                    fontSize: '13px',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                    gap: '12px',
                    lineHeight: 1.4
                  }}
                >
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                    <Icon name="alertcircle" size={16} color="var(--danger-text)" />
                    <span>{draftError}</span>
                  </div>
                  <button
                    onClick={handleGenerateDraft}
                    disabled={isGeneratingDraft}
                    style={{
                      padding: '4px 12px',
                      borderRadius: '4px',
                      border: '1px solid var(--danger)',
                      background: 'transparent',
                      color: 'var(--danger-text)',
                      fontSize: '12px',
                      fontWeight: 600,
                      cursor: isGeneratingDraft ? 'not-allowed' : 'pointer',
                      whiteSpace: 'nowrap',
                      transition: 'all 0.15s ease'
                    }}
                  >
                    {isGeneratingDraft ? 'Retrying...' : 'Retry'}
                  </button>
                </div>
              )}
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'flex-end' }}>
                <button 
                  onClick={handleGenerateDraft}
                  disabled={isGeneratingDraft}
                  style={{ 
                    padding: '8px 16px', 
                    borderRadius: '4px', 
                    border: 'none', 
                    background: 'var(--brown)',
                    color: 'white',
                    fontSize: '13px',
                    cursor: isGeneratingDraft ? 'not-allowed' : 'pointer',
                    opacity: isGeneratingDraft ? 0.7 : 1
                  }}
                >
                  {isGeneratingDraft ? 'Generating...' : 'Generate Draft'}
                </button>
              </div>

              {draftResult && (
                <div style={{ marginTop: '16px', padding: '16px', background: 'var(--bg-soft)', borderRadius: '4px', border: '1px solid var(--border-soft)' }}>
                  <div style={{ marginBottom: '12px' }}>
                    <div style={{ fontSize: '12px', color: 'var(--ink-soft)', marginBottom: '4px' }}>Recipient</div>
                    <div style={{ fontSize: '14px', fontWeight: 600, color: 'var(--ink)' }}>{draftRecipient}</div>
                  </div>
                  <div style={{ marginBottom: '12px' }}>
                    <div style={{ fontSize: '12px', color: 'var(--ink-soft)', marginBottom: '4px' }}>Subject</div>
                    <div style={{ fontSize: '14px', fontWeight: 600, color: 'var(--ink)' }}>{draftResult.subject}</div>
                  </div>
                  <div style={{ marginBottom: '16px' }}>
                    <div style={{ fontSize: '12px', color: 'var(--ink-soft)', marginBottom: '4px' }}>Body (Text)</div>
                    <div style={{ fontSize: '13px', color: 'var(--ink)', whiteSpace: 'pre-wrap' }}>{draftResult.text_body}</div>
                  </div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
                    <button 
                      onClick={async () => {
                        setIsSendingDraft(true);
                        setSendDraftSuccess(false);
                        try {
                          await api.post('/api/email/send-draft', {
                            recipient_email: draftRecipient,
                            subject: draftResult.subject,
                            text_body: draftResult.text_body,
                            html_body: draftResult.html_body || '',
                            email_type: draftResult.email_type
                          });
                          setSendDraftSuccess(true);
                        } catch (err) {
                          alert("Failed to send: " + (err.response?.data?.detail || err.message));
                        } finally {
                          setIsSendingDraft(false);
                        }
                      }}
                      disabled={isSendingDraft}
                      style={{ 
                        padding: '8px 16px', 
                        borderRadius: '4px', 
                        border: 'none', 
                        background: 'var(--brown)',
                        color: 'white',
                        fontSize: '13px',
                        cursor: isSendingDraft ? 'not-allowed' : 'pointer',
                        opacity: isSendingDraft ? 0.7 : 1
                      }}
                    >
                      {isSendingDraft ? 'Sending...' : 'Send Email'}
                    </button>
                    {sendDraftSuccess && <span style={{ fontSize: '12px', color: 'green' }}>Draft sent successfully!</span>}
                  </div>
                </div>
              )}
            </div>
          </Card>

          <Card>
            <div style={{ padding: '16px 20px', borderBottom: '1px solid var(--border)', display: 'flex', alignItems: 'center', gap: '8px' }}>
              <Icon name="cpu" size={16} color="var(--brown)" />
              <h3 style={{ margin: 0, fontSize: '14px', fontWeight: 600, color: 'var(--brown)' }}>AI Preferences</h3>
            </div>
            <div style={{ padding: '8px 20px 20px' }}>
              <ToggleSetting icon="sparkles" title="AI Recommendations" prefKey="aiRecommendations" />
              <ToggleSetting icon="messagecircle" title="Knowledge Assistant" prefKey="knowledgeAssistant" />
              <ToggleSetting icon="shield" title="Require Confirmation for AI Actions" prefKey="aiConfirmation" isLast={true} />
            </div>
          </Card>

        </div>
      </div>
    </div>
  );
}
