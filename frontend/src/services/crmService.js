import api from '../api';

export const customerService = {
  getCustomers: (params) => api.get('/api/customers', { params }),
  getCustomer: (id) => api.get(`/api/customers/${id}`),
  getCustomer360: (id) => api.get(`/api/customers/${id}/360`),
  createCustomer: (data) => api.post('/api/customers', data),
  updateCustomer: (id, data) => api.put(`/api/customers/${id}`, data),
  deleteCustomer: (id) => api.delete(`/api/customers/${id}`),
  getCustomerStatuses: () => api.get('/api/customers/statuses/list'),
  getCustomerStats: () => api.get('/api/customers/stats'),
};

export const leadService = {
  getLeads: (params) => api.get('/api/leads', { params }),
  getLead: (id) => api.get(`/api/leads/${id}`),
  createLead: (data) => api.post('/api/leads', data),
  updateLead: (id, data) => api.put(`/api/leads/${id}`, data),
  deleteLead: (id) => api.delete(`/api/leads/${id}`),
  updateLeadStatus: (id, status) => api.patch(`/api/leads/${id}/status`, null, { params: { new_status: status } }),
  getLeadHistory: (id) => api.get(`/api/leads/${id}/history`),
  convertLead: (id, payload) => api.post(`/api/leads/${id}/convert`, null, { params: payload })
};

export const opportunityService = {
  getOpportunities: (params) => api.get('/api/opportunities', { params }),
  getOpportunity: (id) => api.get(`/api/opportunities/${id}`),
  getOpportunityHistory: (id) => api.get(`/api/opportunities/${id}/history`),
  getOpportunityProducts: (id) => api.get(`/api/opportunities/${id}/products`),
  createOpportunity: (data) => api.post('/api/opportunities', data),
  updateOpportunity: (id, data) => api.put(`/api/opportunities/${id}`, data),
  stageTransition: (id, data) => api.post(`/api/opportunities/${id}/stage-transition`, data),
  getOpportunityHealth: (id) => api.get(`/api/opportunities/${id}/health`),
  deleteOpportunity: (id) => api.delete(`/api/opportunities/${id}`)
};

export const companyService = {
  getCompanies: (params) => api.get('/api/companies', { params }),
  getCompany: (id) => api.get(`/api/companies/${id}`),
  getCompanyContacts: (id) => api.get(`/api/companies/${id}/contacts`),
  getCompanyLeads: (id) => api.get(`/api/companies/${id}/leads`),
  getCompanyOpportunities: (id) => api.get(`/api/companies/${id}/opportunities`),
  createCompany: (data) => api.post('/api/companies', data),
  updateCompany: (id, data) => api.put(`/api/companies/${id}`, data),
  deleteCompany: (id) => api.delete(`/api/companies/${id}`)
};

export const activityService = {
  getActivities: (params) => api.get('/api/activities', { params }),
  getActivitySummary: () => api.get('/api/activities/summary'),
  getActivity: (id) => api.get(`/api/activities/${id}`),
  createActivity: (data) => api.post('/api/activities', data),
  updateActivity: (id, data) => api.put(`/api/activities/${id}`, data),
  deleteActivity: (id) => api.delete(`/api/activities/${id}`),
  completeActivity: (id) => api.post(`/api/activities/${id}/complete`)
};

export const contactService = {
  getContacts: (params) => api.get('/api/contacts', { params }),
  getContact: (id) => api.get(`/api/contacts/${id}`),
  createContact: (data) => api.post('/api/contacts', data),
  updateContact: (id, data) => api.put(`/api/contacts/${id}`, data),
  deleteContact: (id) => api.delete(`/api/contacts/${id}`)
};

export const productService = {
  getProducts: (params) => api.get('/api/products', { params }),
  getProduct: (id) => api.get(`/api/products/${id}`),
  createProduct: (data) => api.post('/api/products', data),
  updateProduct: (id, data) => api.put(`/api/products/${id}`, data),
  deleteProduct: (id) => api.delete(`/api/products/${id}`)
};

export const transactionService = {
  getTransactionSummary: () => api.get('/api/transactions/summary'),
  getTransactions: (params) => api.get('/api/transactions', { params }),
  getTransaction: (id) => api.get(`/api/transactions/${id}`),
  createTransaction: (data) => api.post('/api/transactions', data),
  updateTransaction: (id, data) => api.put(`/api/transactions/${id}`, data),
  deleteTransaction: (id) => api.delete(`/api/transactions/${id}`)
};

export const campaignService = {
  getCampaigns: (params) => api.get('/api/campaigns', { params }),
  getCampaignSummary: () => api.get('/api/campaigns/summary'),
  getCampaign: (id) => api.get(`/api/campaigns/${id}`),
  createCampaign: (data) => api.post('/api/campaigns', data),
  updateCampaign: (id, data) => api.put(`/api/campaigns/${id}`, data),
  deleteCampaign: (id) => api.delete(`/api/campaigns/${id}`)
};

export const supportService = {
  getSupportCases: (params, config = {}) => api.get('/api/support', { params, ...config }),
  getSupportSummary: () => api.get('/api/support/summary'),
  getSupportCase: (id) => api.get(`/api/support/${id}`),
  createSupportCase: (data) => api.post('/api/support', data),
  updateSupportCase: (id, data) => api.put(`/api/support/${id}`, data),
  updateSupportCaseStatus: (id, status, score) => api.patch(`/api/support/${id}/status`, null, { params: { new_status: status, satisfaction_score: score } }),
  deleteSupportCase: (id) => api.delete(`/api/support/${id}`)
};

export const aiService = {
  chat: (message) => api.post('/api/chat', message)
};

export const analyticsService = {
  getDashboardKpis: (params) => api.get('/api/analytics/dashboard', { params }),
  getLeadFunnel: (params) => api.get('/api/analytics/leads/funnel', { params }),
  getOpportunityPipeline: (params) => api.get('/api/analytics/opportunities/pipeline', { params }),
  getRevenueByMonth: (params) => api.get('/api/analytics/revenue/monthly', { params }),
  getTopCustomers: (params) => api.get('/api/analytics/revenue/top-customers', { params }),
  getTopProducts: (params) => api.get('/api/analytics/revenue/top-products', { params }),
  getSupportSummary: (params) => api.get('/api/analytics/support/summary', { params }),
  getCompaniesByState: (params) => api.get('/api/analytics/companies/state', { params })
};

export const salesRepService = {
  getSalesReps: (params) => api.get('/api/sales_reps', { params }),
  getSalesRep: (id) => api.get(`/api/sales_reps/${id}`)
};

export const referenceService = {
  getIndustries: () => api.get('/api/industries'),
  getDepartments: () => api.get('/api/departments'),
  getLeadSources: () => api.get('/api/lead_sources')
};

export const lookupService = {
  getAllLookups: () => api.get('/api/lookups')
};

export const searchService = {
  globalSearch: (q) => api.get('/api/search', { params: { q } })
};

export const notificationService = {
  getNotifications: () => api.get('/api/notifications')
};

export const documentService = {
  listDocuments: (params) => api.get('/api/documents', { params }),
  uploadDocument: (formData) => api.post('/api/documents/upload', formData, {
    headers: { 'Content-Type': 'multipart/form-data' }
  }),
  deleteDocument: (docId) => api.delete(`/api/documents/${docId}`),
  getChunks: (docId) => api.get(`/api/documents/${docId}/chunks`)
};

export const aiAgentService = {
  ask: (message, sessionId = null) => {
    const payload = { role: 'user', content: message };
    if (sessionId) payload.session_id = sessionId;
    return api.post('/api/chat', payload);
  },
  getHistory: () => api.get('/api/chat/history'),
  deleteSession: (sessionId) => api.delete(`/api/chat/${sessionId}`)
};
