import React, { useState, useEffect } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import Icon from '../components/common/Icon';
import Badge from '../components/common/Badge';
import { companyService, customerService, contactService, transactionService, supportService, activityService, opportunityService } from '../services/crmService';
import { mlService } from '../services/mlService';
import NoteModal from '../components/common/NoteModal';

// ─── Reusable card style helpers ──────────────────────────────────────────────
const card = {
  background: 'var(--white)',
  border: '1px solid var(--border)',
  borderRadius: '14px',
  overflow: 'hidden',
  boxShadow: '0 2px 8px rgba(0,0,0,0.03)',
};

const cardHead = {
  padding: '14px 20px',
  borderBottom: '1px solid var(--border-soft)',
  display: 'flex',
  justifyContent: 'space-between',
  alignItems: 'center',
};

const cardHeadTitle = {
  fontSize: '13.5px',
  fontWeight: 700,
  color: 'var(--heading-primary)',
  display: 'flex',
  alignItems: 'center',
  gap: '8px',
};

const cardBody = {
  padding: '0',
};

const infoRow = (border = true) => ({
  display: 'grid',
  gridTemplateColumns: '140px 1fr',
  gap: '8px',
  padding: '10px 20px',
  borderBottom: border ? '1px solid var(--border-soft)' : 'none',
  alignItems: 'center',
});

const label = {
  fontSize: '12px',
  color: 'var(--ink-mute)',
  fontWeight: 500,
};

const value = {
  fontSize: '13px',
  color: 'var(--brown)',
  fontWeight: 600,
};

const entityRow = {
  padding: '12px 20px',
  borderBottom: '1px solid var(--border-soft)',
  cursor: 'pointer',
  display: 'flex',
  flexDirection: 'column',
  gap: '4px',
  transition: 'background 0.15s',
};

// ─── Churn Risk Badge ─────────────────────────────────────────────────────────
function ChurnBadge({ churn }) {
  if (!churn) return <span style={{ color: 'var(--ink-mute)', fontSize: '13px' }}>—</span>;
  const pct = (churn.churn_probability * 100).toFixed(0);
  const isHigh = churn.prediction === 1;
  return (
    <span style={{
      background: isHigh ? 'rgba(176,80,58,.14)' : 'rgba(110,138,94,.15)',
      color: isHigh ? 'var(--danger)' : 'var(--success)',
      borderRadius: '999px',
      padding: '3px 10px',
      fontSize: '12px',
      fontWeight: 700,
    }}>
      {isHigh ? 'High' : 'Low'} · {pct}%
    </span>
  );
}

// ─── ML Segment Label ─────────────────────────────────────────────────────────
const SEGMENT_LABELS = {
  0: 'High Value',
  1: 'Growth',
  2: 'Standard',
  3: 'At Risk',
};
function segmentLabel(seg) {
  if (!seg) return '—';
  return SEGMENT_LABELS[seg.cluster_id] || `Cluster ${seg.cluster_id}`;
}

// ─── Metric mini-card ─────────────────────────────────────────────────────────
function MetricMini({ icon, label: lbl, value: val }) {
  return (
    <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', gap: '6px', flex: 1 }}>
      <div style={{ width: '36px', height: '36px', borderRadius: '10px', background: 'var(--ivory)', border: '1px solid var(--border-soft)', display: 'flex', alignItems: 'center', justifyContent: 'center' }}>
        <Icon name={icon} size={16} color="var(--brown)" stroke={1.8} />
      </div>
      <div style={{ fontSize: '12px', color: 'var(--ink-mute)', fontWeight: 500, textAlign: 'center', lineHeight: 1.3 }}>{lbl}</div>
      <div style={{ fontSize: '20px', fontWeight: 700, color: 'var(--heading-primary)', letterSpacing: '-0.5px' }}>{val}</div>
    </div>
  );
}

// ─── Avatar ──────────────────────────────────────────────────────────────────
function Avatar({ name }) {
  const initials = name ? name.substring(0, 2).toUpperCase() : 'NA';
  const colors = ['#7c5cbf', '#2e7d9f', '#c0673a', '#4a7a5c', '#8c6927'];
  const color = colors[initials.charCodeAt(0) % colors.length];
  return (
    <div style={{
      width: '30px', height: '30px', borderRadius: '50%',
      background: color, color: '#fff',
      display: 'flex', alignItems: 'center', justifyContent: 'center',
      fontSize: '11px', fontWeight: 700, flexShrink: 0,
    }}>
      {initials}
    </div>
  );
}

// ─── Status badge (customer) ──────────────────────────────────────────────────
function CustomerStatusBadge({ status }) {
  const map = {
    'Active': { bg: 'rgba(110,138,94,.15)', color: 'var(--success)' },
    'At Risk': { bg: 'rgba(192,138,62,.16)', color: 'var(--warning)' },
    'Paused': { bg: 'rgba(120,120,120,.13)', color: 'var(--ink-soft)' },
  };
  const s = map[status] || map['Active'];
  return (
    <span style={{ ...s, borderRadius: '999px', padding: '4px 12px', fontSize: '12px', fontWeight: 700, display: 'inline-flex', alignItems: 'center', gap: '5px' }}>
      <span style={{ width: '6px', height: '6px', borderRadius: '50%', background: s.color, flexShrink: 0 }} />
      {status} Customer
    </span>
  );
}

export default function CustomerDetail() {
  const { id } = useParams();
  const navigate = useNavigate();

  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  const [customer, setCustomer] = useState(null);
  const [company, setCompany] = useState(null);
  const [customer360, setCustomer360] = useState(null);
  const [contacts, setContacts] = useState([]);
  const [openOppCount, setOpenOppCount] = useState(0);
  const [segment, setSegment] = useState(null);
  const [churn, setChurn] = useState(null);
  const [isNoteModalOpen, setIsNoteModalOpen] = useState(false);

  const fetchCustomer360 = async () => {
    try {
      const c360Res = await customerService.getCustomer360(id);
      setCustomer360(c360Res.data);
    } catch (err) {
      console.error('Failed to reload customer 360:', err);
    }
  };

  useEffect(() => {
    async function loadAll() {
      setLoading(true);
      setError(null);
      try {
        // 1. Fetch customer record
        const custRes = await customerService.getCustomer(id);
        const cust = custRes.data;
        setCustomer(cust);

        // 2. Fetch company
        const compRes = await companyService.getCompany(cust.company_id);
        const comp = compRes.data;
        setCompany(comp);

        // Breadcrumb
        window.dispatchEvent(new CustomEvent('set-breadcrumb', {
          detail: [
            { label: 'Home', path: '/' },
            { label: 'Customers', path: '/customers' },
            { label: comp.company_name }
          ]
        }));

        // 3. Fetch customer 360 (transactions, support_cases, activities)
        const c360Res = await customerService.getCustomer360(id);
        setCustomer360(c360Res.data);

        // 4. Contacts for this company
        const contRes = await contactService.getContacts({ company_id: cust.company_id, page_size: 50 }).catch(() => ({ data: [] }));
        setContacts(contRes.data?.items || contRes.data?.data || contRes.data || []);

        // 5. Open opportunity count for key metrics
        const oppRes = await opportunityService.getOpportunities({ company_id: cust.company_id, page_size: 200 }).catch(() => ({ data: {} }));
        const opps = oppRes.data?.items || oppRes.data?.data || oppRes.data || [];
        const openOpps = opps.filter(o => !['Closed Won', 'Closed Lost', 'Closed'].includes(o.pipeline_stage));
        setOpenOppCount(openOpps.length);

        // 6. ML data — non-blocking
        try {
          const [segRes, churnRes] = await Promise.all([
            mlService.getCustomerSegment(id),
            mlService.getCustomerChurn(id)
          ]);
          setSegment(segRes.data);
          setChurn(churnRes.data);
        } catch (mlErr) {
          console.warn('ML data unavailable:', mlErr);
        }

      } catch (err) {
        console.error('Failed to load customer:', err);
        setError('Failed to load customer details.');
      } finally {
        setLoading(false);
      }
    }
    loadAll();
  }, [id]);

  if (loading) {
    return (
      <div style={{ padding: '40px 28px', display: 'flex', alignItems: 'center', justifyContent: 'center', color: 'var(--ink-mute)', fontSize: '14px' }}>
        <Icon name="loader" size={18} color="var(--brown)" style={{ marginRight: 10 }} /> Loading customer profile...
      </div>
    );
  }

  if (error) {
    return (
      <div style={{ padding: 28 }}>
        <div className="empty-state">
          <div className="empty-title">Error</div>
          <div className="empty-desc">{error}</div>
        </div>
      </div>
    );
  }

  if (!customer || !company) {
    return (
      <div style={{ padding: 28 }}>
        <div className="empty-state">
          <div className="empty-title">Not Found</div>
          <div className="empty-desc">Customer not found.</div>
        </div>
      </div>
    );
  }

  // ─── Derived data ────────────────────────────────────────────────────────────
  const transactions = customer360?.transactions || [];
  const supportCases = customer360?.support_cases || [];
  const activities = customer360?.activities || [];

  const totalRevenue = transactions.reduce((sum, t) => sum + (t.amount_inr || 0), 0);
  const avgTxValue = transactions.length > 0 ? (totalRevenue / transactions.length) : 0;
  const txCount = customer360?.transactions_count ?? transactions.length;
  const contactCount = contacts.length;

  const formatINR = (val) => {
    if (val >= 10000000) return `₹${(val / 10000000).toFixed(2)} Cr`;
    if (val >= 100000) return `₹${(val / 100000).toFixed(2)} L`;
    return `₹${Math.round(val).toLocaleString('en-IN')}`;
  };

  const formatDate = (dateStr) => {
    if (!dateStr) return '—';
    return new Date(dateStr).toLocaleDateString('en-IN', { day: '2-digit', month: 'short', year: 'numeric' });
  };

  const initials = company.company_name ? company.company_name.substring(0, 2).toUpperCase() : 'CO';
  const customerSinceLabel = customer.customer_since
    ? new Date(customer.customer_since).toLocaleString('default', { month: 'short', year: 'numeric' })
    : null;

  const aiSummary = `${company.company_name} is an ${customer.customer_status?.toLowerCase() || 'active'}, ${segmentLabel(segment)?.toLowerCase()}-tier enterprise customer in the ${company.industry_id || 'B2B'} industry. They have completed ${txCount} transactions, generating a total revenue of ${formatINR(totalRevenue)} with an average transaction value of ${formatINR(avgTxValue)}. The account shows ${contactCount > 10 ? 'strong' : 'consistent'} engagement with ${contactCount} contacts and consistent activity. The churn risk is ${churn?.prediction === 1 ? 'elevated' : 'low'}, indicating a ${churn?.prediction === 1 ? 'need for proactive outreach' : 'healthy and stable relationship with good growth potential'}.`;

  const aiInsight = churn?.prediction === 1
    ? 'This customer shows elevated churn risk signals. Immediate outreach by the CSM is recommended to address any concerns and reinforce the relationship.'
    : 'This customer demonstrates strong engagement and long-term potential. Consider identifying upsell opportunities in related product lines or services to increase account value.';

  // Customer health score: simple heuristic (80–95 if active/low churn, lower otherwise)
  const healthScore = churn
    ? Math.max(40, Math.min(99, Math.round(100 - (churn.churn_probability * 100) * 0.8 + (txCount > 30 ? 10 : txCount > 10 ? 5 : 0))))
    : customer.customer_status === 'Active' ? 82 : 55;

  return (
    <div className="page" style={{ background: 'var(--beige)', minHeight: '100vh' }}>
      <div style={{ padding: '20px 28px 32px' }}>

        {/* ── Back link ── */}
        <div
          style={{ display: 'inline-flex', alignItems: 'center', gap: '6px', fontSize: '12px', fontWeight: 600, color: 'var(--ink-mute)', cursor: 'pointer', marginBottom: '18px' }}
          onClick={() => navigate('/customers')}
        >
          <Icon name="chevronleft" size={14} color="currentColor" stroke={2.2} />
          Back to Customers
        </div>

        {/* ── Company Header Card ── */}
        <div style={{ ...card, padding: '22px 28px', display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '20px' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '18px' }}>
            {/* Avatar */}
            <div style={{
              width: '56px', height: '56px', borderRadius: '12px',
              background: 'var(--brown)', color: 'var(--ivory)',
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              fontSize: '20px', fontWeight: 700, flexShrink: 0,
              boxShadow: '0 4px 12px rgba(103,70,54,0.18)',
            }}>
              {initials}
            </div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '10px' }}>
              {/* Name + Badges */}
              <div style={{ display: 'flex', alignItems: 'center', gap: '10px', flexWrap: 'wrap' }}>
                <h1 style={{ margin: 0, fontSize: '22px', fontWeight: 700, color: 'var(--heading-primary)', letterSpacing: '-0.3px' }}>
                  {company.company_name}
                </h1>
                <CustomerStatusBadge status={customer.customer_status} />
                {customer.customer_tier && (
                  <span style={{ background: 'var(--ivory)', border: '1px solid var(--border)', borderRadius: '8px', padding: '3px 12px', fontSize: '12px', fontWeight: 600, color: 'var(--ink-soft)' }}>
                    {customer.customer_tier}
                  </span>
                )}
              </div>
              {/* Meta row */}
              <div style={{ display: 'flex', alignItems: 'center', gap: '16px', color: 'var(--ink-mute)', fontSize: '12.5px', fontWeight: 500, flexWrap: 'wrap' }}>
                {company.industry_id && (
                  <span style={{ display: 'flex', gap: 5, alignItems: 'center' }}>
                    <Icon name="buildingsmall" size={13} /> {company.industry_id}
                  </span>
                )}
                {(company.city || company.state) && (
                  <span style={{ display: 'flex', gap: 5, alignItems: 'center' }}>
                    <Icon name="mappin" size={13} /> {[company.city, company.state].filter(Boolean).join(', ')}
                  </span>
                )}
                {company.company_size_band && (
                  <span style={{ display: 'flex', gap: 5, alignItems: 'center' }}>
                    <Icon name="users" size={13} /> {company.company_size_band} employees
                  </span>
                )}
                {customerSinceLabel && (
                  <span style={{ display: 'flex', gap: 5, alignItems: 'center' }}>
                    <Icon name="calendar" size={13} /> Customer since {customerSinceLabel}
                  </span>
                )}
              </div>
            </div>
          </div>

          {/* Right side: health + action */}
          <div style={{ display: 'flex', alignItems: 'center', gap: '28px', flexShrink: 0 }}>
            <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-end', gap: '6px' }}>
              <span style={{ fontSize: '11px', fontWeight: 600, color: 'var(--ink-mute)' }}>Customer Health</span>
              <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
                <div style={{ width: '72px', height: '5px', background: 'var(--border-soft)', borderRadius: '3px', overflow: 'hidden' }}>
                  <div style={{ width: `${healthScore}%`, height: '100%', background: healthScore > 70 ? 'var(--success)' : healthScore > 50 ? 'var(--warning)' : 'var(--danger)', borderRadius: '3px' }} />
                </div>
                <span style={{ fontSize: '18px', fontWeight: 700, color: 'var(--brown)' }}>{healthScore}</span>
              </div>
            </div>
            <button
              style={{ background: 'var(--brown)', border: 'none', borderRadius: '9px', padding: '10px 18px', display: 'flex', alignItems: 'center', gap: '7px', fontSize: '13px', fontWeight: 600, color: 'var(--ivory)', cursor: 'pointer' }}
              onClick={() => setIsNoteModalOpen(true)}
            >
              <Icon name="filetext" size={14} color="var(--ivory)" /> New Note
            </button>
          </div>
        </div>

        {/* ── Row 1: Customer Information + Key Metrics ── */}
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: '20px', marginBottom: '20px' }}>

          {/* Customer Information */}
          <div style={card}>
            <div style={cardHead}>
              <div style={cardHeadTitle}>
                <Icon name="filetext" size={15} color="var(--brown)" stroke={1.9} />
                Customer Information
              </div>
            </div>
            <div style={cardBody}>
              <div style={infoRow()}>
                <span style={label}>Customer ID</span>
                <span style={{ ...value, fontFamily: 'monospace', fontSize: '12px' }}>{customer.customer_id}</span>
              </div>
              <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr' }}>
                <div style={{ padding: '10px 20px', borderBottom: '1px solid var(--border-soft)', borderRight: '1px solid var(--border-soft)' }}>
                  <div style={label}>Customer Tier</div>
                  <div style={{ ...value, marginTop: '3px' }}>{customer.customer_tier || '—'}</div>
                </div>
                <div style={{ padding: '10px 20px', borderBottom: '1px solid var(--border-soft)' }}>
                  <div style={label}>Renewal Date</div>
                  <div style={{ ...value, marginTop: '3px' }}>{formatDate(customer.renewal_date)}</div>
                </div>
                <div style={{ padding: '10px 20px', borderBottom: '1px solid var(--border-soft)', borderRight: '1px solid var(--border-soft)' }}>
                  <div style={label}>Contract Type</div>
                  <div style={{ ...value, marginTop: '3px' }}>{customer.contract_type || '—'}</div>
                </div>
                <div style={{ padding: '10px 20px', borderBottom: '1px solid var(--border-soft)' }}>
                  <div style={label}>CSM Rep ID</div>
                  <div style={{ ...value, marginTop: '3px', fontFamily: 'monospace', fontSize: '12px' }}>{customer.csm_rep_id || '—'}</div>
                </div>
                <div style={{ padding: '10px 20px', borderBottom: '1px solid var(--border-soft)', borderRight: '1px solid var(--border-soft)' }}>
                  <div style={label}>Customer Since</div>
                  <div style={{ ...value, marginTop: '3px' }}>{formatDate(customer.customer_since)}</div>
                </div>
                <div style={{ padding: '10px 20px', borderBottom: '1px solid var(--border-soft)' }}>
                  <div style={label}>ML Segment</div>
                  <div style={{ ...value, marginTop: '3px' }}>{segmentLabel(segment)}</div>
                </div>
              </div>
              <div style={infoRow(false)}>
                <span style={label}>Churn Risk</span>
                <ChurnBadge churn={churn} />
              </div>
            </div>
          </div>

          {/* Key Metrics */}
          <div style={card}>
            <div style={cardHead}>
              <div style={cardHeadTitle}>
                <Icon name="barchart" size={15} color="var(--brown)" stroke={1.9} />
                Key Metrics
              </div>
            </div>
            <div style={{ padding: '28px 20px', display: 'flex', gap: '16px', justifyContent: 'space-around' }}>
              <MetricMini icon="briefcase" label="Total Transactions" value={txCount} />
              <div style={{ width: '1px', background: 'var(--border-soft)', alignSelf: 'stretch' }} />
              <MetricMini icon="trendingup" label="Avg. Transaction Value" value={formatINR(avgTxValue)} />
              <div style={{ width: '1px', background: 'var(--border-soft)', alignSelf: 'stretch' }} />
              <MetricMini icon="target" label="Open Opportunities" value={openOppCount} />
              <div style={{ width: '1px', background: 'var(--border-soft)', alignSelf: 'stretch' }} />
              <MetricMini icon="users" label="Total Contacts" value={contactCount} />
            </div>
          </div>
        </div>

        {/* ── Row 2: AI Summary (full width) ── */}
        <div style={{ ...card, marginBottom: '20px', padding: '22px 24px', display: 'flex', flexDirection: 'column', gap: '14px' }}>
          <div style={{ fontSize: '14px', fontWeight: 700, color: 'var(--heading-primary)', display: 'flex', alignItems: 'center', gap: '8px' }}>
            <Icon name="sparkles" size={16} color="var(--accent-primary)" stroke={1.8} />
            AI Summary
          </div>
          <p style={{ margin: 0, fontSize: '13.5px', lineHeight: '1.7', color: 'var(--ink-soft)' }}>
            {aiSummary}
          </p>
          {/* AI Insight highlight */}
          <div style={{ background: 'var(--bg-subtle)', border: '1px solid var(--border-soft)', borderRadius: '10px', padding: '14px 18px', display: 'flex', gap: '12px', alignItems: 'flex-start' }}>
            <div style={{ width: '28px', height: '28px', borderRadius: '8px', background: 'var(--accent-tint)', display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0, marginTop: '1px' }}>
              <Icon name="sparkles" size={14} color="var(--accent-primary)" stroke={1.8} />
            </div>
            <div>
              <div style={{ fontSize: '12px', fontWeight: 700, color: 'var(--heading-primary)', marginBottom: '4px' }}>AI Insight</div>
              <div style={{ fontSize: '13px', lineHeight: '1.6', color: 'var(--ink-soft)' }}>{aiInsight}</div>
            </div>
          </div>
        </div>

        {/* ── Row 3: Contacts | Transactions | Activities | Support Cases ── */}
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(4, 1fr)', gap: '16px' }}>

          {/* Contacts */}
          <div style={card}>
            <div style={cardHead}>
              <div style={cardHeadTitle}>
                <Icon name="users" size={14} color="var(--brown)" />
                Contacts
              </div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <span style={{ fontSize: '13px', fontWeight: 700, color: 'var(--brown)' }}>{contactCount}</span>
                <Icon name="chevronright" size={14} color="var(--ink-mute)" />
              </div>
            </div>
            <div>
              {contacts.length === 0 ? (
                <div style={{ padding: '24px', textAlign: 'center', fontSize: '12px', color: 'var(--ink-mute)' }}>No contacts</div>
              ) : (
                contacts.slice(0, 3).map(c => (
                  <div
                    key={c.contact_id}
                    style={entityRow}
                    onClick={() => navigate(`/contacts/${c.contact_id}`)}
                    onMouseEnter={e => e.currentTarget.style.background = 'var(--beige)'}
                    onMouseLeave={e => e.currentTarget.style.background = 'transparent'}
                  >
                    <div style={{ display: 'flex', gap: '10px', alignItems: 'center' }}>
                      <Avatar name={c.full_name} />
                      <div>
                        <div style={{ fontSize: '13px', fontWeight: 600, color: 'var(--brown)' }}>{c.full_name}</div>
                        <div style={{ fontSize: '11.5px', color: 'var(--ink-mute)' }}>{c.job_title || '—'}</div>
                      </div>
                    </div>
                  </div>
                ))
              )}
            </div>
            {contacts.length > 0 && (
              <div
                style={{ padding: '12px 20px', fontSize: '12.5px', fontWeight: 600, color: 'var(--brown)', cursor: 'pointer', borderTop: '1px solid var(--border-soft)' }}
                onClick={() => navigate(`/contacts?company_id=${company?.company_id}`)}
              >
                View all contacts →
              </div>
            )}
          </div>

          {/* Transactions */}
          <div style={card}>
            <div style={cardHead}>
              <div style={cardHeadTitle}>
                <Icon name="creditcard" size={14} color="var(--brown)" />
                Transactions
              </div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <span style={{ fontSize: '13px', fontWeight: 700, color: 'var(--brown)' }}>{txCount}</span>
                <Icon name="chevronright" size={14} color="var(--ink-mute)" />
              </div>
            </div>
            <div>
              {transactions.length === 0 ? (
                <div style={{ padding: '24px', textAlign: 'center', fontSize: '12px', color: 'var(--ink-mute)' }}>No transactions</div>
              ) : (
                transactions.slice(0, 3).map(t => (
                  <div
                    key={t.transaction_id}
                    style={entityRow}
                    onMouseEnter={e => e.currentTarget.style.background = 'var(--beige)'}
                    onMouseLeave={e => e.currentTarget.style.background = 'transparent'}
                  >
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                      <div>
                        <div style={{ fontSize: '12.5px', fontWeight: 600, color: 'var(--brown)' }}>{t.invoice_number || t.transaction_id}</div>
                        <div style={{ fontSize: '11px', color: 'var(--ink-mute)', marginTop: '2px' }}>
                          {t.transaction_date ? new Date(t.transaction_date).toLocaleDateString('en-IN', { day: '2-digit', month: 'short', year: 'numeric' }) : '—'}
                        </div>
                      </div>
                      <div style={{ display: 'flex', flexDirection: 'column', alignItems: 'flex-end', gap: '3px' }}>
                        <span style={{ fontSize: '13px', fontWeight: 700, color: 'var(--brown)' }}>
                          {t.amount_inr != null ? `₹${t.amount_inr.toLocaleString('en-IN')}` : '—'}
                        </span>
                        <span style={{
                          background: t.payment_status === 'Paid' ? 'rgba(110,138,94,.15)' : 'rgba(192,138,62,.16)',
                          color: t.payment_status === 'Paid' ? 'var(--success)' : 'var(--warning)',
                          borderRadius: '999px', padding: '2px 8px', fontSize: '11px', fontWeight: 700
                        }}>
                          {t.payment_status || 'Pending'}
                        </span>
                      </div>
                    </div>
                  </div>
                ))
              )}
            </div>
            {transactions.length > 0 && (
              <div
                style={{ padding: '12px 20px', fontSize: '12.5px', fontWeight: 600, color: 'var(--brown)', cursor: 'pointer', borderTop: '1px solid var(--border-soft)' }}
                onClick={() => navigate(`/transactions?customer_id=${id}`)}
              >
                View all transactions →
              </div>
            )}
          </div>

          {/* Activities */}
          <div style={card}>
            <div style={cardHead}>
              <div style={cardHeadTitle}>
                <Icon name="activity" size={14} color="var(--brown)" />
                Activities
              </div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <span style={{ fontSize: '13px', fontWeight: 700, color: 'var(--brown)' }}>{customer360?.activities_count ?? activities.length}</span>
                <Icon name="chevronright" size={14} color="var(--ink-mute)" />
              </div>
            </div>
            <div>
              {activities.length === 0 ? (
                <div style={{ padding: '24px', textAlign: 'center', fontSize: '12px', color: 'var(--ink-mute)' }}>No activities</div>
              ) : (
                activities.slice(0, 4).map(a => {
                  const aType = (a.activity_type || '').toLowerCase();
                  const icon = aType.includes('call') ? 'phone' : aType.includes('email') ? 'mail' : aType.includes('meet') ? 'users' : 'file-text';
                  return (
                    <div
                      key={a.activity_id}
                      style={entityRow}
                      onMouseEnter={e => e.currentTarget.style.background = 'var(--beige)'}
                      onMouseLeave={e => e.currentTarget.style.background = 'transparent'}
                    >
                      <div style={{ display: 'flex', gap: '10px', alignItems: 'flex-start' }}>
                        <div style={{ width: '26px', height: '26px', borderRadius: '7px', background: 'var(--ivory)', border: '1px solid var(--border-soft)', display: 'flex', alignItems: 'center', justifyContent: 'center', flexShrink: 0, marginTop: '1px' }}>
                          <Icon name={icon} size={12} color="var(--brown)" stroke={1.8} />
                        </div>
                        <div>
                          <div style={{ fontSize: '12.5px', fontWeight: 600, color: 'var(--brown)' }}>{a.subject || a.activity_type || 'Activity'}</div>
                          <div style={{ fontSize: '11px', color: 'var(--ink-mute)', marginTop: '2px' }}>
                            {a.activity_date ? new Date(a.activity_date).toLocaleDateString('en-IN', { day: '2-digit', month: 'short', year: 'numeric' }) : '—'}
                          </div>
                        </div>
                      </div>
                    </div>
                  );
                })
              )}
            </div>
            {activities.length > 0 && (
              <div
                style={{ padding: '12px 20px', fontSize: '12.5px', fontWeight: 600, color: 'var(--brown)', cursor: 'pointer', borderTop: '1px solid var(--border-soft)' }}
                onClick={() => navigate(`/activities?customer_id=${id}`)}
              >
                View all activities →
              </div>
            )}
          </div>

          {/* Support Cases */}
          <div style={card}>
            <div style={cardHead}>
              <div style={cardHeadTitle}>
                <Icon name="lifebuoy" size={14} color="var(--brown)" />
                Support Cases
              </div>
              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                <span style={{ fontSize: '13px', fontWeight: 700, color: 'var(--brown)' }}>{customer360?.support_cases_count ?? supportCases.length}</span>
                <Icon name="chevronright" size={14} color="var(--ink-mute)" />
              </div>
            </div>
            <div>
              {supportCases.length === 0 ? (
                <div style={{ padding: '24px', textAlign: 'center', fontSize: '12px', color: 'var(--ink-mute)' }}>No support cases</div>
              ) : (
                supportCases.slice(0, 3).map(s => {
                  const statusMap = {
                    'Open': { bg: 'rgba(110,138,94,.15)', color: 'var(--success)' },
                    'In Progress': { bg: 'rgba(192,138,62,.16)', color: 'var(--warning)' },
                    'Resolved': { bg: 'rgba(120,120,120,.12)', color: 'var(--ink-soft)' },
                    'Closed': { bg: 'rgba(120,120,120,.12)', color: 'var(--ink-soft)' },
                  };
                  const stSt = statusMap[s.status] || statusMap['Open'];
                  return (
                    <div
                      key={s.case_id}
                      style={entityRow}
                      onMouseEnter={e => e.currentTarget.style.background = 'var(--beige)'}
                      onMouseLeave={e => e.currentTarget.style.background = 'transparent'}
                    >
                      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                        <div>
                          <div style={{ fontSize: '12px', fontWeight: 600, color: 'var(--ink-mute)', fontFamily: 'monospace' }}>{s.case_id}</div>
                          <div style={{ fontSize: '12.5px', fontWeight: 500, color: 'var(--brown)', marginTop: '2px' }}>{s.case_type || 'Support Request'}</div>
                        </div>
                        <span style={{ ...stSt, borderRadius: '999px', padding: '2px 9px', fontSize: '11px', fontWeight: 700, whiteSpace: 'nowrap' }}>
                          {s.status}
                        </span>
                      </div>
                    </div>
                  );
                })
              )}
            </div>
            {supportCases.length > 0 && (
              <div
                style={{ padding: '12px 20px', fontSize: '12.5px', fontWeight: 600, color: 'var(--brown)', cursor: 'pointer', borderTop: '1px solid var(--border-soft)' }}
                onClick={() => navigate(`/support?customer_id=${id}`)}
              >
                View all support cases →
              </div>
            )}
          </div>

        </div>
      </div>

      {isNoteModalOpen && (
        <NoteModal
          isOpen={isNoteModalOpen}
          onClose={() => setIsNoteModalOpen(false)}
          companyId={company.company_id}
          customerId={id}
          salesRepId={customer?.csm_rep_id}
          onSaved={fetchCustomer360}
        />
      )}
    </div>
  );
}
