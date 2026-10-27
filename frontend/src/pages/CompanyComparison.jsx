import React, { useState, useEffect } from 'react';
import PageHeader from '../components/common/PageHeader';
import CompanyComparisonPanel from '../components/company-comparison/CompanyComparisonPanel';
import CustomerComparisonPanel from '../components/company-comparison/CustomerComparisonPanel';
import LeadComparisonPanel from '../components/company-comparison/LeadComparisonPanel';
import ProductComparisonPanel from '../components/company-comparison/ProductComparisonPanel';
import { companyService, opportunityService, customerService, leadService } from '../services/crmService';
import api from '../api';

export default function CompanyComparison() {
  const [companies, setCompanies] = useState([]);
  const [opportunities, setOpportunities] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);

  useEffect(() => {
    async function fetchData() {
      try {
        const [compRes, oppRes] = await Promise.all([
          companyService.getCompanies(),
          opportunityService.getOpportunities()
        ]);
        setCompanies(compRes.data?.items || compRes.data || []);
        setOpportunities(oppRes.data?.items || oppRes.data || []);
      } catch (err) {
        console.error("Error fetching comparison data", err);
        setError("Unable to load data. Please try again.");
      } finally {
        setLoading(false);
      }
    }
    fetchData();
  }, []);

  return (
    <div className="page">
      <PageHeader
        title="Comparison"
        desc="Compare companies, customers, leads, and products side-by-side using real-time CRM data."
      />
      <div style={{ display: 'flex', flexDirection: 'column', gap: '32px', padding: '0 28px 28px' }}>
        {loading ? (
          <div style={{ padding: '40px', textAlign: 'center', color: 'var(--ink-mute)' }}>Loading data...</div>
        ) : error ? (
          <div style={{ padding: '40px', textAlign: 'center', color: 'var(--danger)' }}>{error}</div>
        ) : (
          <>
            <CompanyComparisonPanel
              companies={companies}
              opportunities={opportunities}
              isFullPage={true}
            />
            <CustomerComparisonPanel />
            <LeadComparisonPanel />
            <ProductComparisonPanel />
          </>
        )}
      </div>
    </div>
  );
}
