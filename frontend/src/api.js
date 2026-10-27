import axios from 'axios';
import { auth } from './services/firebase';

const api = axios.create({
  baseURL: '',
});

api.interceptors.request.use(async (config) => {
  await auth.authStateReady();
  const user = auth.currentUser;
  let token = null;
  if (user) {
    token = await user.getIdToken();
    config.headers.Authorization = `Bearer ${token}`;
  }
    
  return config;
});

api.interceptors.response.use(
  (response) => response,
  (error) => {
    // Redirect to login on 401 only if not already on /login.
    // This prevents infinite redirect loops and handles expired/missing tokens
    // gracefully instead of leaving the app stuck on a loading state.
    if (error.response?.status === 401 && window.location.pathname !== '/login') {
      console.warn('[AUTH] 401 Unauthorized — redirecting to /login');
      window.location.href = '/login';
    }
    return Promise.reject(error);
  }
);

export default api;
