import React, { useState, useEffect, useRef } from 'react';
import Modal from './Modal';
import Button from './Button';
import FormInput from './FormInput';
import { companyService, salesRepService, opportunityService } from '../../services/crmService';

export default function OpportunityEditModal({ isOpen, onClose, onSave, editingOpp = null, effectiveRole = '' }) {
  
  const initialFormState = {
    company_id: '',
    owner_rep_id: '',
    opportunity_name: '',
    forecast_category: 'Pipeline',
    deal_value_inr: '',
    probability_pct: '',
    expected_close_date: ''
  };

  const [formData, setFormData] = useState(initialFormState);
  const [submitting, setSubmitting] = useState(false);
  const [formError, setFormError] = useState('');

  // Dropdown states
  const [companySearch, setCompanySearch] = useState('');
  const [companyResults, setCompanyResults] = useState([]);
  const [companySearching, setCompanySearching] = useState(false);
  const companyTimeoutRef = useRef(null);

  const [repSearch, setRepSearch] = useState('');
  const [repResults, setRepResults] = useState([]);
  const [repSearching, setRepSearching] = useState(false);
  const repTimeoutRef = useRef(null);

  useEffect(() => {
    if (isOpen) {
      if (editingOpp) {
        setFormData({
          company_id: editingOpp.company_id || '',
          owner_rep_id: editingOpp.owner_rep_id || '',
          opportunity_name: editingOpp.opportunity_name || '',
          forecast_category: editingOpp.forecast_category || 'Pipeline',
          deal_value_inr: editingOpp.deal_value_inr || '',
          probability_pct: editingOpp.probability_pct || '',
          expected_close_date: editingOpp.expected_close_date || ''
        });
        
        // Fetch display names for initial search inputs
        const initDisplay = async () => {
          let compName = editingOpp.company_id;
          let repName = editingOpp.owner_rep_id;
          try {
            if (editingOpp.company_id) {
              const c = await companyService.getCompany(editingOpp.company_id);
              if (c.data?.company_name) compName = c.data.company_name;
            }
            if (editingOpp.owner_rep_id) {
              const r = await salesRepService.getSalesRep(editingOpp.owner_rep_id);
              if (r.data?.full_name) repName = r.data.full_name;
            }
          } catch(e) {}
          setCompanySearch(compName || '');
          setRepSearch(repName || '');
        };
        initDisplay();
      } else {
        setFormData(initialFormState);
        setCompanySearch('');
        setRepSearch('');
      }
      setCompanyResults([]);
      setRepResults([]);
      setFormError('');
    }
    // eslint-disable-next-line
  }, [isOpen, editingOpp]);

  const handleCompanySearch = (e) => {
    const val = e.target.value;
    setCompanySearch(val);
    if (companyTimeoutRef.current) clearTimeout(companyTimeoutRef.current);
    if (!val) {
      setCompanyResults([]);
      return;
    }
    setCompanySearching(true);
    companyTimeoutRef.current = setTimeout(() => {
      companyService.getCompanies({ search: val, limit: 10 })
        .then(res => setCompanyResults(res.data?.items || res.data || []))
        .finally(() => setCompanySearching(false));
    }, 400);
  };

  const selectCompany = (comp) => {
    setFormData({ ...formData, company_id: comp.company_id });
    setCompanySearch(comp.company_name || comp.company_id);
    setCompanyResults([]);
  };

  const handleRepSearch = (e) => {
    const val = e.target.value;
    setRepSearch(val);
    if (repTimeoutRef.current) clearTimeout(repTimeoutRef.current);
    if (!val) {
      setRepResults([]);
      return;
    }
    setRepSearching(true);
    repTimeoutRef.current = setTimeout(() => {
      salesRepService.getSalesReps({ search: val, limit: 10 })
        .then(res => setRepResults(res.data?.items || res.data || []))
        .finally(() => setRepSearching(false));
    }, 400);
  };

  const selectRep = (rep) => {
    setFormData({ ...formData, owner_rep_id: rep.rep_id });
    setRepSearch(rep.full_name || rep.rep_id);
    setRepResults([]);
  };

  const handleFormSubmit = async () => {
    if (!formData.company_id) {
      setFormError('Company selection is required');
      return;
    }
    if (!formData.owner_rep_id) {
      setFormError('Sales Representative is required');
      return;
    }
    if (formData.deal_value_inr === '' || formData.probability_pct === '') {
      setFormError('Deal Value and Probability are required');
      return;
    }
    
    setSubmitting(true);
    setFormError('');
    try {
      const payload = {
        ...formData,
        deal_value_inr: parseFloat(formData.deal_value_inr) || 0,
        probability_pct: parseFloat(formData.probability_pct) || 0,
      };

      if (editingOpp) {
        await opportunityService.updateOpportunity(editingOpp.opportunity_id, payload);
      } else {
        payload.pipeline_stage = 'Qualification';
        payload.close_outcome = null;
        await opportunityService.createOpportunity(payload);
      }
      onSave();
    } catch (err) {
      setFormError(err.response?.data?.detail || 'An error occurred during submission');
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <Modal 
      isOpen={isOpen} 
      onClose={() => !submitting && onClose()} 
      title={editingOpp ? 'Edit Opportunity' : 'New Opportunity'}
      footer={
        <>
          <Button variant="secondary" onClick={onClose} disabled={submitting}>Cancel</Button>
          <Button variant="primary" onClick={handleFormSubmit} disabled={submitting}>
            {submitting ? 'Saving...' : 'Save Opportunity'}
          </Button>
        </>
      }
    >
      {formError && <div className="err" style={{ marginBottom: '16px', color: 'var(--red)' }}>{formError}</div>}
      
      {/* Company Dropdown */}
      <div className="field" style={{ marginBottom: '16px' }}>
        <label style={{ display: 'block', marginBottom: '8px', fontWeight: 500, fontSize: '13px', color: 'var(--brown)' }}>Company *</label>
        <div style={{ position: 'relative' }}>
          <input 
            type="text" 
            placeholder="Search Company..." 
            value={companySearch}
            onChange={handleCompanySearch}
            disabled={!!editingOpp}
            style={{ width: '100%', padding: '10px 12px', borderRadius: '6px', border: '1px solid var(--gray-300)', fontSize: '14px', boxSizing: 'border-box' }}
          />
          {companySearching && <div style={{ position: 'absolute', right: '10px', top: '10px', fontSize: '12px', color: 'var(--gray-500)' }}>Searching...</div>}
          {companyResults.length > 0 && !editingOpp && (
            <ul style={{ position: 'absolute', zIndex: 10, width: '100%', background: 'white', border: '1px solid var(--gray-200)', borderRadius: '6px', marginTop: '4px', maxHeight: '150px', overflowY: 'auto', padding: 0, margin: 0, listStyle: 'none', boxShadow: '0 4px 6px rgba(0,0,0,0.1)' }}>
              {companyResults.map(c => (
                <li 
                  key={c.company_id} 
                  onClick={() => selectCompany(c)}
                  style={{ padding: '8px 12px', cursor: 'pointer', borderBottom: '1px solid var(--gray-100)', fontSize: '14px' }}
                >
                  {c.company_name} <span style={{ color: 'var(--gray-500)', fontSize: '12px' }}>({c.company_id})</span>
                </li>
              ))}
            </ul>
          )}
        </div>
      </div>

      {/* CSM Rep Dropdown */}
      <div className="field" style={{ marginBottom: '16px' }}>
        <label style={{ display: 'block', marginBottom: '8px', fontWeight: 500, fontSize: '13px', color: 'var(--brown)' }}>Sales Representative *</label>
        <div style={{ position: 'relative' }}>
          <input 
            type="text" 
            placeholder="Search Rep..." 
            value={repSearch}
            onChange={handleRepSearch}
            disabled={effectiveRole === 'Sales Rep'}
            style={{ width: '100%', padding: '10px 12px', borderRadius: '6px', border: '1px solid var(--gray-300)', fontSize: '14px', boxSizing: 'border-box', backgroundColor: effectiveRole === 'Sales Rep' ? 'var(--bg-light)' : 'white' }}
          />
          {repSearching && <div style={{ position: 'absolute', right: '10px', top: '10px', fontSize: '12px', color: 'var(--gray-500)' }}>Searching...</div>}
          {repResults.length > 0 && (
            <ul style={{ position: 'absolute', zIndex: 10, width: '100%', background: 'white', border: '1px solid var(--gray-200)', borderRadius: '6px', marginTop: '4px', maxHeight: '150px', overflowY: 'auto', padding: 0, margin: 0, listStyle: 'none', boxShadow: '0 4px 6px rgba(0,0,0,0.1)' }}>
              {repResults.map(r => (
                <li 
                  key={r.rep_id} 
                  onClick={() => selectRep(r)}
                  style={{ padding: '8px 12px', cursor: 'pointer', borderBottom: '1px solid var(--gray-100)', fontSize: '14px' }}
                >
                  {r.full_name} - {r.role} <span style={{ color: 'var(--gray-500)', fontSize: '12px' }}>({r.rep_id})</span>
                </li>
              ))}
            </ul>
          )}
        </div>
      </div>

      <FormInput label="Opportunity Name" value={formData.opportunity_name} onChange={e => setFormData({...formData, opportunity_name: e.target.value})} />

      <div style={{ display: 'flex', gap: '16px', marginBottom: '16px' }}>
        <div style={{ flex: 1 }}>
          <FormInput label="Deal Value (INR) *" type="number" required value={formData.deal_value_inr} onChange={e => setFormData({...formData, deal_value_inr: e.target.value})} />
        </div>
        <div style={{ flex: 1 }}>
          <FormInput label="Probability (%) *" type="number" required value={formData.probability_pct} onChange={e => setFormData({...formData, probability_pct: e.target.value})} />
        </div>
      </div>
      
      <div style={{ marginBottom: '16px' }}>
        <FormInput label="Expected Close Date" type="date" value={formData.expected_close_date} onChange={e => setFormData({...formData, expected_close_date: e.target.value})} />
      </div>
    </Modal>
  );
}
