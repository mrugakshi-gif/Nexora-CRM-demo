import api from '../api';

export const healthService = {
    getAccountHealth: async (customerId) => {
        const response = await api.get(`/api/health/account/${customerId}`);
        return response.data;
    },

    getCompanyHealth: async (companyId) => {
        const response = await api.get(`/api/health/company/${companyId}`);
        return response.data;
    },

    getProductHealth: async (productId) => {
        const response = await api.get(`/api/health/product/${productId}`);
        return response.data;
    },

    getDealHealth: async (opportunityId) => {
        const response = await api.get(`/api/health/deal/${opportunityId}`);
        return response.data;
    },

    getAccountHealthSummary: async (period = 'all_time') => {
        const response = await api.get(`/api/health/account/summary?period=${period}`);
        return response.data;
    },

    getCompanyHealthSummary: async (period = 'all_time') => {
        const response = await api.get(`/api/health/company/summary?period=${period}`);
        return response.data;
    },

    getProductHealthSummary: async (period = 'all_time') => {
        const response = await api.get(`/api/health/product/summary?period=${period}`);
        return response.data;
    }
};
