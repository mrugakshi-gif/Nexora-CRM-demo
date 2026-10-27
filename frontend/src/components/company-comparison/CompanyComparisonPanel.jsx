import React, { useState, useEffect } from 'react';
import CompanySelector from './CompanySelector';
import CompanyComparisonTable from './CompanyComparisonTable';
import Icon from '../common/Icon';
import { referenceService, companyService, customerService, transactionService } from '../../services/crmService';
import { mlService } from '../../services/mlService';

export default function CompanyComparisonPanel({ companies, topCustomers, isFullPage = false }) {
  const [selectedCompanies, setSelectedCompanies] = useState([]);
  const [metrics, setMetrics] = useState({});
  const [industryMap, setIndustryMap] = useState({});
  const [isLoading, setIsLoading] = useState(false);
  const [hasError, setHasError] = useState(false);
  const [initialized, setInitialized] = useState(false);

  // Fetch reference industries for mapping industry_id -> industry_name
  useEffect(() => {
    let active = true;
    async function loadIndustries() {
      try {
        const res = await referenceService.getIndustries();
        const items = res.data?.items || res.data || [];
        const map = {};
        items.forEach(ind => {
          map[ind.industry_id] = ind.industry_name;
        });
        if (active) setIndustryMap(map);
      } catch (err) {
        console.warn("Failed to load industries reference data", err);
      }
    }
    loadIndustries();
    return () => { active = false; };
  }, []);

  // Initialize with exactly 3 default deterministic companies from topCustomers analytics
  useEffect(() => {
    let active = true;
    async function initDefaults() {
      if (initialized) return;

      const defaults = [];

      // 1. Try resolving top customer companies
      if (topCustomers && topCustomers.length > 0) {
        for (const tc of topCustomers) {
          if (defaults.length >= 3) break;
          const targetId = tc.company_id;
          const targetName = tc.company_name;

          let found = (companies || []).find(c => c && ((targetId && c.company_id === targetId) || (targetName && c.company_name === targetName)));

          if (!found && targetId) {
            try {
              const res = await companyService.getCompany(targetId);
              if (res.data) found = res.data;
            } catch (e) {
              console.warn(`Could not fetch company ${targetId}`, e);
            }
          }

          if (found && !defaults.some(d => d && d.company_id === found.company_id)) {
            defaults.push(found);
          }
        }
      }

      // 2. Fallback to available companies array if topCustomers resolution did not yield 3
      if (defaults.length < 3 && companies && companies.length > 0) {
        for (const c of companies) {
          if (c && !defaults.some(d => d && d.company_id === c.company_id)) {
            defaults.push(c);
          }
          if (defaults.length >= 3) break;
        }
      }

      if (active && defaults.length > 0) {
        setSelectedCompanies(defaults.slice(0, 3));
        setInitialized(true);
      }
    }

    initDefaults();
    return () => { active = false; };
  }, [companies, topCustomers, initialized]);

  const handleSelect = (company) => {
    if (selectedCompanies.length < 3 && !selectedCompanies.some(c => c.company_id === company.company_id)) {
      setSelectedCompanies([...selectedCompanies, company]);
    }
  };

  const handleRemove = (id) => {
    setSelectedCompanies(selectedCompanies.filter(c => c.company_id !== id));
  };

  useEffect(() => {
    let active = true;
    const fetchMetrics = async () => {
      if (selectedCompanies.length === 0) {
        if (active) setMetrics({});
        return;
      }

      setIsLoading(true);
      setHasError(false);
      const newMetrics = {};

      try {
        for (const company of selectedCompanies) {
          // A. COMPANY-LEVEL DATASET FIELDS
          const industryName = industryMap[company.industry_id] || company.sub_industry || company.industry_id || '—';
          const subIndustry = company.sub_industry || '—';
          const companySize = company.company_size_band || '—';
          const annualRevenueBand = company.annual_revenue_band_inr || '—';
          
          const locParts = [company.city, company.state].filter(Boolean);
          let locationStr = locParts.join(', ');
          if (company.region) {
            locationStr += locationStr ? ` (${company.region})` : company.region;
          }
          if (!locationStr) locationStr = '—';

          const companyType = company.company_type || '—';
          const foundedYear = company.founded_year ? String(Math.floor(company.founded_year)) : '—';
          const accountStatus = company.account_status || 'Prospect';

          // B. RELATED CRM COUNTS (Contacts, Leads, Opportunities)
          let contactsCount = 0;
          try {
            const contRes = await companyService.getCompanyContacts(company.company_id);
            contactsCount = (contRes.data || []).length;
          } catch (e) {
            console.warn("Could not fetch contacts for company", company.company_id);
          }

          let leadsCount = 0;
          try {
            const leadsRes = await companyService.getCompanyLeads(company.company_id);
            leadsCount = (leadsRes.data || []).length;
          } catch (e) {
            console.warn("Could not fetch leads for company", company.company_id);
          }

          let openOppsCount = 0;
          let openOppsVal = 0;
          let wonOppsCount = 0;
          let wonOppsVal = 0;
          try {
            const oppRes = await companyService.getCompanyOpportunities(company.company_id);
            const co_opps = oppRes.data?.items || oppRes.data || [];
            const openOpps = co_opps.filter(o => !['Closed Won', 'Closed Lost'].includes(o.stage || o.pipeline_stage));
            const wonOpps = co_opps.filter(o => (o.stage === 'Closed Won' || o.pipeline_stage === 'Closed Won'));

            openOppsCount = openOpps.length;
            openOppsVal = openOpps.reduce((sum, o) => sum + (o.deal_value_inr || o.expected_revenue || 0), 0);
            wonOppsCount = wonOpps.length;
            wonOppsVal = wonOpps.reduce((sum, o) => sum + (o.deal_value_inr || o.expected_revenue || 0), 0);
          } catch (e) {
            console.warn("Could not fetch opportunities for company", company.company_id);
          }

          // C. CUSTOMER & TRANSACTION METRICS
          let customer = null;
          try {
            const custRes = await customerService.getCustomers({ company_id: company.company_id });
            const items = custRes.data?.data || custRes.data?.items || custRes.data || [];
            customer = items.find(c => c.company_id === company.company_id) || null;
          } catch (e) {
            try {
              const custRes = await customerService.getCustomers({ search: company.company_name, limit: 10 });
              const items = custRes.data?.data || custRes.data?.items || custRes.data || [];
              customer = items.find(c => c.company_id === company.company_id) || null;
            } catch (err) {
              console.warn("Customer lookup failed for company", company.company_id);
            }
          }

          let revenue = 0;
          let orders = 0;
          if (customer) {
            let skip = 0;
            let allTxns = [];
            while (true) {
              const txRes = await transactionService.getTransactions({
                customer_id: customer.customer_id,
                limit: 200,
                skip: skip
              });
              const items = txRes.data?.data || txRes.data?.items || [];
              allTxns = [...allTxns, ...items];
              if (items.length < 200) {
                break;
              }
              skip += 200;
            }

            const paidTxns = allTxns.filter(t => t.payment_status === 'Paid');
            revenue = paidTxns.reduce((sum, t) => sum + (t.amount_inr || 0), 0);
            orders = paidTxns.length;
          }

          const tier = customer?.customer_tier || '—';
          const customerStatus = customer ? (customer.customer_status || 'Active') : accountStatus;

          // D. ML CHURN RISK
          let churnRisk = '—';
          if (customer) {
            try {
              const churnRes = await mlService.getCustomerChurn(customer.customer_id);
              const data = churnRes.data;
              if (data?.churn_probability !== undefined) {
                const prob = data.churn_probability;
                if (prob > 0.6) churnRisk = 'High';
                else if (prob > 0.3) churnRisk = 'Medium';
                else churnRisk = 'Low';
              } else if (data?.churn_risk) {
                churnRisk = data.churn_risk;
              } else if (data?.prediction !== undefined) {
                churnRisk = data.prediction === 1 ? 'High' : 'Low';
              }
            } catch (err) {
              console.warn("Churn ML prediction failed for customer", customer.customer_id);
              churnRisk = '—';
            }
          }

          newMetrics[company.company_id] = {
            industry: industryName,
            sub_industry: subIndustry,
            company_size: companySize,
            annual_revenue_band: annualRevenueBand,
            location: locationStr,
            company_type: companyType,
            founded_year: foundedYear,
            account_status: accountStatus,
            contacts_count: contactsCount,
            leads_count: leadsCount,
            open_opps_count: openOppsCount,
            open_opps_val: openOppsVal,
            won_opps_count: wonOppsCount,
            won_opps_val: wonOppsVal,
            tier: tier,
            customer_status: customerStatus,
            revenue: revenue,
            orders: orders,
            aov: orders > 0 ? (revenue / orders) : 0,
            churn_risk: churnRisk
          };
        }

        if (active) {
          setMetrics(newMetrics);
        }
      } catch (e) {
        console.error("Error fetching company comparison metrics:", e);
        if (active) setHasError(true);
      } finally {
        if (active) setIsLoading(false);
      }
    };

    fetchMetrics();
    return () => { active = false; };
  }, [selectedCompanies, industryMap]);

  return (
    <div className="card" style={{ padding: '24px 32px' }}>
      {/* Header */}
      <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', marginBottom: '20px', flexWrap: 'wrap', gap: '12px' }}>
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          <Icon name="bar-chart-2" size={28} color="var(--accent-primary)" stroke={2} />
          <div>
            <h2 className="section-title" style={{ fontSize: '22px', marginBottom: '4px', color: 'var(--heading-primary)' }}>Company Comparison</h2>
            <p style={{ color: 'var(--ink-mute)', fontSize: '14px', margin: 0 }}>Compare key metrics and dataset attributes across companies</p>
          </div>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
          <div style={{ padding: '6px 12px', background: 'var(--accent-primary)', border: '1px solid var(--border-soft)', borderRadius: '8px', fontSize: '14px', fontWeight: 600, color: '#ffffff', display: 'flex', alignItems: 'center', gap: '8px' }}>
            <Icon name="layers" size={16} /> {selectedCompanies.length} selected
          </div>
          <span style={{ fontSize: '13px', color: 'var(--ink-soft)' }}>(Max 3)</span>
        </div>
      </div>

      {/* Selected Companies Chips */}
      <div style={{ display: 'flex', flexWrap: 'wrap', gap: '12px', marginBottom: '16px' }}>
        {selectedCompanies.map(company => (
          <div key={company.company_id} style={{
            display: 'flex', alignItems: 'center', gap: '8px',
            padding: '6px 12px', background: 'var(--bg-subtle)',
            border: '1px solid var(--border)', borderRadius: '6px',
            fontSize: '14px', fontWeight: 700, color: 'var(--heading-primary)',
            boxShadow: '0 1px 2px rgba(0,0,0,0.05)'
          }}>
            <strong>{company.company_name}</strong>
            <button
              onClick={() => handleRemove(company.company_id)}
              style={{ background: 'none', border: 'none', cursor: 'pointer', display: 'flex', alignItems: 'center', padding: '2px', color: 'var(--ink-soft)' }}
              onMouseEnter={(e) => e.target.style.color = 'var(--danger)'}
              onMouseLeave={(e) => e.target.style.color = 'var(--ink-soft)'}
            >
              <Icon name="x" size={16} />
            </button>
          </div>
        ))}
      </div>

      {/* Search / Select Company */}
      <div style={{ marginBottom: '24px' }}>
        <CompanySelector
          companies={companies}
          selectedCompanies={selectedCompanies}
          onSelect={handleSelect}
        />
      </div>

      {hasError ? (
        <div style={{ padding: '40px 20px', textAlign: 'center', background: 'var(--bg-light)', borderRadius: '8px', border: '1px dashed var(--border)' }}>
          <p style={{ color: 'var(--danger)', fontSize: '14px', fontWeight: 500 }}>Unable to load comparison data.</p>
        </div>
      ) : isLoading ? (
        <div style={{ padding: '40px 20px', textAlign: 'center', color: 'var(--ink-mute)', fontSize: '14px' }}>
          Loading comparison metrics...
        </div>
      ) : (
        <>
          <div style={{ marginBottom: '24px' }}>
            <CompanyComparisonTable
              selectedCompanies={selectedCompanies}
              metrics={metrics}
            />
          </div>

          {!isFullPage && selectedCompanies.length >= 2 && (
            <div style={{ marginTop: '20px', textAlign: 'center' }}>
              <a href="/company-comparison" style={{
                color: 'var(--blue)', fontSize: '13px', fontWeight: 600, textDecoration: 'none'
              }}>
                View Full Comparison →
              </a>
            </div>
          )}
        </>
      )}
    </div>
  );
}
