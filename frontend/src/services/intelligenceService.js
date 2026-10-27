import api from '../api';

export const intelligenceService = {
  getRetentionNextBestActions: async (periodStr = 'this_year') => {
    return api.get(`/api/intelligence/next-best-actions/retention?period=${periodStr}`);
  }
};
