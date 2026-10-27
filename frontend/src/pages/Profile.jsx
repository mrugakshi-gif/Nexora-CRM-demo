import React, { useState, useEffect } from 'react';
import PageHeader from '../components/common/PageHeader';
import Card from '../components/common/Card';
import Icon from '../components/common/Icon';
import Badge from '../components/common/Badge';
import api from '../api';
import { auth } from '../services/firebase';
import { sendEmailVerification, verifyBeforeUpdateEmail, updateProfile } from 'firebase/auth';

export default function Profile() {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  
  // Edit Profile States
  const [isEditing, setIsEditing] = useState(false);
  const [editName, setEditName] = useState('');
  const [savingProfile, setSavingProfile] = useState(false);

  const [verificationStatus, setVerificationStatus] = useState('');
  
  // States for Email Update
  const [newEmail, setNewEmail] = useState('');
  const [updateEmailStatus, setUpdateEmailStatus] = useState('');

  useEffect(() => {
    fetchProfile();
  }, []);

  const fetchProfile = () => {
    api.get('/api/auth/me')
      .then(res => {
        setUser(res.data);
        setEditName(res.data.full_name || auth.currentUser?.displayName || '');
      })
      .catch(err => {
        console.error("Failed to load profile", err);
      })
      .finally(() => {
        setLoading(false);
      });
  };

  const handleSaveProfile = async () => {
    if (!editName.trim()) return;
    setSavingProfile(true);
    try {
      if (auth.currentUser) {
        await updateProfile(auth.currentUser, { displayName: editName.trim() });
      }
      const res = await api.put('/api/auth/me', { full_name: editName.trim() });
      setUser(res.data);
      setIsEditing(false);
    } catch (err) {
      console.error("Failed to update profile", err);
    } finally {
      setSavingProfile(false);
    }
  };

  const handleSendVerification = async () => {
    if (!auth.currentUser) {
      setVerificationStatus('No authenticated user found.');
      return;
    }
    
    try {
      setVerificationStatus('Sending...');
      await sendEmailVerification(auth.currentUser);
      setVerificationStatus('Verification email sent! Please check your inbox (or spam folder), click the link, and then log out and log back in.');
    } catch (error) {
      console.error("Error sending verification email:", error);
      setVerificationStatus(`Error: ${error.message}`);
    }
  };

  const handleUpdateEmail = async () => {
    if (!auth.currentUser) {
      setUpdateEmailStatus('No authenticated user found.');
      return;
    }
    if (!newEmail || !newEmail.includes('@')) {
      setUpdateEmailStatus('Please enter a valid email address.');
      return;
    }
    
    try {
      setUpdateEmailStatus('Initiating email update...');
      await verifyBeforeUpdateEmail(auth.currentUser, newEmail);
      setUpdateEmailStatus('Success! A verification email has been sent to your new address. Please click the link in that email to finalize the change.');
    } catch (error) {
      console.error("Error updating email:", error);
      setUpdateEmailStatus(`Error: ${error.message}`);
    }
  };

  const fbUser = auth.currentUser;
  const isVerified = fbUser?.emailVerified;
  
  // Clean fallback for display name instead of N/A
  const rawEmail = user?.email || fbUser?.email || 'user@example.com';
  const emailPrefix = rawEmail.split('@')[0];
  const formattedPrefix = emailPrefix.charAt(0).toUpperCase() + emailPrefix.slice(1);
  const displayName = user?.full_name || fbUser?.displayName || formattedPrefix;
  
  const crmModules = [
    { name: 'Dashboard', icon: 'pie-chart' },
    { name: 'Companies', icon: 'briefcase' },
    { name: 'Customers', icon: 'users' },
    { name: 'Leads', icon: 'target' },
    { name: 'Opportunities', icon: 'trending-up' },
    { name: 'Products', icon: 'package' },
    { name: 'Transactions', icon: 'dollar-sign' },
    { name: 'Support', icon: 'life-buoy' },
    { name: 'Analytics', icon: 'bar-chart-2' },
    { name: 'AI Workspace', icon: 'cpu' }
  ];

  return (
    <div className="page">
      <PageHeader 
        title="Profile" 
        desc="Your account details."
      />
      <div style={{ padding: '0 28px 28px', display: 'flex', flexDirection: 'column', gap: '24px', maxWidth: '1200px' }}>
        {loading ? (
          <p style={{ color: 'var(--ink-mute)' }}>Loading CRM profile...</p>
        ) : user ? (
          <>
            {/* Profile Header */}
            <div style={{ 
              display: 'flex', 
              alignItems: 'flex-start', 
              justifyContent: 'space-between',
              background: 'var(--white)',
              padding: '32px',
              borderRadius: '12px',
              border: '1px solid var(--border)',
              boxShadow: '0 2px 12px rgba(0,0,0,0.03)',
              flexWrap: 'wrap',
              gap: '24px'
            }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: '32px' }}>
                <div style={{ 
                  width: '96px', 
                  height: '96px', 
                  borderRadius: '50%', 
                  background: 'var(--brown)', 
                  color: 'var(--white)',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  fontSize: '40px',
                  fontWeight: '700',
                  flexShrink: 0,
                  boxShadow: '0 4px 12px rgba(0,0,0,0.1)'
                }}>
                  {displayName.charAt(0).toUpperCase()}
                </div>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '12px' }}>
                  <div>
                    <h1 style={{ margin: '0 0 4px 0', fontSize: '26px', color: 'var(--heading-primary)', fontWeight: '700', letterSpacing: '-0.5px' }}>
                      {displayName}
                    </h1>
                    <p style={{ margin: 0, color: 'var(--ink-mute)', fontSize: '15px', fontWeight: 500 }}>
                      {rawEmail}
                    </p>
                  </div>
                  <div style={{ display: 'flex', gap: '8px', flexWrap: 'wrap' }}>
                    <Badge text={user.role || 'Sales Rep'} color="primary" />
                    {isVerified ? (
                      <Badge text="Email Verified" color="success" />
                    ) : (
                      <Badge text="Unverified" color="danger" />
                    )}
                    {user.is_active !== false ? (
                      <Badge text="Active" color="success" />
                    ) : (
                      <Badge text="Inactive" color="danger" />
                    )}
                  </div>
                </div>
              </div>
              <button 
                className="btn btn-primary" 
                onClick={() => setIsEditing(!isEditing)}
                style={{ padding: '8px 16px', fontSize: '13px' }}
              >
                <Icon name={isEditing ? "x" : "edit-2"} size={16} /> 
                {isEditing ? "Cancel Edit" : "Edit Profile"}
              </button>
            </div>

            {/* Middle Grid */}
            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(340px, 1fr))', gap: '24px', alignItems: 'stretch' }}>
              
              {/* Personal Information Card */}
              <Card title="Personal Information" icon="user" style={{ height: '100%' }}>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '20px', padding: '8px 0' }}>
                  
                  <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
                    <div style={{ width: '40px', height: '40px', borderRadius: '10px', background: 'var(--bg-light)', display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'var(--brown)', flexShrink: 0 }}>
                      <Icon name="user" size={18} />
                    </div>
                    <div style={{ flex: 1 }}>
                      <div style={{ fontSize: '12px', fontWeight: 600, color: 'var(--ink-mute)', textTransform: 'uppercase', letterSpacing: '0.5px' }}>Full Name</div>
                      {isEditing ? (
                        <div style={{ display: 'flex', gap: '8px', marginTop: '4px' }}>
                          <input 
                            type="text"
                            value={editName}
                            onChange={(e) => setEditName(e.target.value)}
                            className="form-input"
                            style={{ padding: '4px 8px', fontSize: '14px', flex: 1 }}
                            autoFocus
                          />
                          <button 
                            className="btn btn-primary" 
                            style={{ padding: '4px 12px' }}
                            onClick={handleSaveProfile}
                            disabled={savingProfile}
                          >
                            Save
                          </button>
                        </div>
                      ) : (
                        <div style={{ fontSize: '14px', fontWeight: 600, color: 'var(--ink-dark)', marginTop: '2px' }}>{displayName}</div>
                      )}
                    </div>
                  </div>

                  <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
                    <div style={{ width: '40px', height: '40px', borderRadius: '10px', background: 'var(--bg-light)', display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'var(--brown)', flexShrink: 0 }}>
                      <Icon name="mail" size={18} />
                    </div>
                    <div>
                      <div style={{ fontSize: '12px', fontWeight: 600, color: 'var(--ink-mute)', textTransform: 'uppercase', letterSpacing: '0.5px' }}>Email Address</div>
                      <div style={{ fontSize: '14px', fontWeight: 600, color: 'var(--ink-dark)', marginTop: '2px' }}>{rawEmail}</div>
                    </div>
                  </div>
                  
                  <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
                    <div style={{ width: '40px', height: '40px', borderRadius: '10px', background: 'var(--bg-light)', display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'var(--brown)', flexShrink: 0 }}>
                      <Icon name="tag" size={18} />
                    </div>
                    <div>
                      <div style={{ fontSize: '12px', fontWeight: 600, color: 'var(--ink-mute)', textTransform: 'uppercase', letterSpacing: '0.5px' }}>Role</div>
                      <div style={{ fontSize: '14px', fontWeight: 600, color: 'var(--ink-dark)', marginTop: '2px' }}>{user.role || 'Sales Rep'}</div>
                    </div>
                  </div>

                </div>
              </Card>

              {/* Account Overview Card */}
              <Card title="Account Overview" icon="info" style={{ height: '100%' }}>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '20px', padding: '8px 0' }}>
                  
                  <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
                    <div style={{ width: '40px', height: '40px', borderRadius: '10px', background: 'var(--bg-light)', display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'var(--brown)', flexShrink: 0 }}>
                      <Icon name="hash" size={18} />
                    </div>
                    <div style={{ overflow: 'hidden' }}>
                      <div style={{ fontSize: '12px', fontWeight: 600, color: 'var(--ink-mute)', textTransform: 'uppercase', letterSpacing: '0.5px' }}>System User ID</div>
                      <div style={{ fontSize: '14px', fontWeight: 600, color: 'var(--ink-dark)', marginTop: '2px', textOverflow: 'ellipsis', overflow: 'hidden' }}>{user.user_id}</div>
                    </div>
                  </div>

                  <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
                    <div style={{ width: '40px', height: '40px', borderRadius: '10px', background: 'var(--bg-light)', display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'var(--brown)', flexShrink: 0 }}>
                      <Icon name="key" size={18} />
                    </div>
                    <div>
                      <div style={{ fontSize: '12px', fontWeight: 600, color: 'var(--ink-mute)', textTransform: 'uppercase', letterSpacing: '0.5px' }}>Auth Provider</div>
                      <div style={{ fontSize: '14px', fontWeight: 600, color: 'var(--ink-dark)', marginTop: '2px' }}>Firebase Identity</div>
                    </div>
                  </div>
                  
                  <div style={{ display: 'flex', alignItems: 'center', gap: '16px' }}>
                    <div style={{ width: '40px', height: '40px', borderRadius: '10px', background: 'var(--bg-light)', display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'var(--brown)', flexShrink: 0 }}>
                      <Icon name="calendar" size={18} />
                    </div>
                    <div>
                      <div style={{ fontSize: '12px', fontWeight: 600, color: 'var(--ink-mute)', textTransform: 'uppercase', letterSpacing: '0.5px' }}>Account Created</div>
                      <div style={{ fontSize: '14px', fontWeight: 600, color: 'var(--ink-dark)', marginTop: '2px' }}>
                        {user.created_at ? new Date(user.created_at).toLocaleDateString() : 'N/A'}
                      </div>
                    </div>
                  </div>

                </div>
              </Card>

              {/* Role & Access Card */}
              <Card title="Role & Access" icon="layers" style={{ height: '100%' }}>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '16px', padding: '4px 0' }}>
                  <p style={{ margin: 0, fontSize: '13px', color: 'var(--ink-mute)', lineHeight: '1.4' }}>
                    Available modules based on your current role:
                  </p>
                  
                  <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(130px, 1fr))', gap: '10px' }}>
                    {crmModules.map(module => (
                      <div key={module.name} style={{ 
                        display: 'flex', alignItems: 'center', gap: '8px', 
                        padding: '8px 12px', background: 'var(--bg-light)', 
                        border: '1px solid var(--border-soft)', borderRadius: '8px', 
                        fontSize: '12px', fontWeight: 600, color: 'var(--brown)'
                      }}>
                        <Icon name={module.icon} size={14} /> {module.name}
                      </div>
                    ))}
                  </div>
                </div>
              </Card>
            </div>

            {/* Bottom Row - Security Card (Full Width) */}
            <Card title="Security & Authentication" icon="lock">
              <div style={{ display: 'flex', flexWrap: 'wrap', gap: '32px', padding: '4px 0' }}>
                
                {!isVerified && (
                  <div style={{ flex: '1 1 300px', background: 'var(--bg-light)', padding: '20px', borderRadius: '10px', border: '1px solid var(--border)' }}>
                    <h4 style={{ margin: '0 0 8px 0', fontSize: '14px', color: 'var(--ink-dark)' }}>Email Not Verified</h4>
                    <p style={{ fontSize: '13px', color: 'var(--ink-mute)', margin: '0 0 16px 0', lineHeight: '1.4' }}>
                      Your email address has not been verified. Please verify your email to ensure secure access.
                    </p>
                    <button className="btn btn-primary" onClick={handleSendVerification} style={{ fontSize: '13px' }}>
                      Send Verification Email
                    </button>
                    {verificationStatus && (
                      <p style={{ marginTop: '12px', fontSize: '13px', color: 'var(--brown)', fontWeight: 500 }}>
                        {verificationStatus}
                      </p>
                    )}
                  </div>
                )}

                <div style={{ flex: '2 1 400px' }}>
                  <h4 style={{ margin: '0 0 8px 0', fontSize: '14px', color: 'var(--ink-dark)' }}>Change Login Email</h4>
                  <p style={{ fontSize: '13px', color: 'var(--ink-mute)', margin: '0 0 16px 0', maxWidth: '600px', lineHeight: '1.4' }}>
                    Update the email address you use to log into the CRM. A verification link will be sent to the new email to confirm ownership before the change takes effect.
                  </p>
                  <div style={{ display: 'flex', gap: '12px', alignItems: 'center', maxWidth: '400px' }}>
                    <input 
                      type="email" 
                      placeholder="New Email Address" 
                      value={newEmail}
                      onChange={(e) => setNewEmail(e.target.value)}
                      style={{
                        padding: '10px 14px',
                        border: '1px solid var(--border)',
                        borderRadius: '8px',
                        flex: 1,
                        fontSize: '14px',
                        background: 'var(--bg-light)'
                      }}
                    />
                    <button className="btn btn-primary" onClick={handleUpdateEmail} style={{ fontSize: '13px' }}>
                      Update Email
                    </button>
                  </div>
                  {updateEmailStatus && (
                    <p style={{ marginTop: '12px', fontSize: '13px', fontWeight: 500, color: updateEmailStatus.includes('Error') ? 'var(--status-error)' : 'var(--status-success)' }}>
                      {updateEmailStatus}
                    </p>
                  )}
                </div>

              </div>
            </Card>

          </>
        ) : (
          <div className="empty-state" style={{ marginTop: '20px' }}>
            <div className="empty-title">CRM Profile unavailable</div>
            <div className="empty-desc">
              Your CRM profile could not be loaded (likely due to missing email verification).
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
