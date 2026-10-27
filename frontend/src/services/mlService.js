import api from '../api';

export const mlService = {
  getLeadConversion: (leadId) => api.get(`/api/ml/leads/${leadId}/conversion`),
  getLeadScore: (leadId) => api.get(`/api/ml/leads/${leadId}/score`),
  getCustomerSegment: (customerId) => api.get(`/api/ml/customers/${customerId}/segment`),
  getCustomerChurn: (customerId) => api.get(`/api/ml/customers/${customerId}/churn`),
  getSalesForecast: () => api.get('/api/ml/sales/forecast'),
  getAggregateLeads: () => api.get('/api/ml/aggregate/leads'),
  getAggregateCustomerRisk: () => api.get('/api/ml/aggregate/customers/risk'),
  getAggregateCustomerSegments: () => api.get('/api/ml/aggregate/customers/segments')
};
