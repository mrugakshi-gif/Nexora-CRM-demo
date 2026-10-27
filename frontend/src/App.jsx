import React, { Suspense, lazy } from 'react';
import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom';
import Login from './pages/Login';
import AppLayout from './components/layout/AppLayout';

const Dashboard = lazy(() => import('./pages/Dashboard'));
const Companies = lazy(() => import('./pages/Companies'));
const CompanyDetail = lazy(() => import('./pages/CompanyDetail'));
const Customers = lazy(() => import('./pages/Customers'));
const CustomerDetail = lazy(() => import('./pages/CustomerDetail'));
const Contacts = lazy(() => import('./pages/Contacts'));

const Leads = lazy(() => import('./pages/Leads'));
const Opportunities = lazy(() => import('./pages/Opportunities'));
const OpportunityDetail = lazy(() => import('./pages/OpportunityDetail'));
const Products = lazy(() => import('./pages/Products'));
const Transactions = lazy(() => import('./pages/Transactions'));
const Activities = lazy(() => import('./pages/Activities'));
const Campaigns = lazy(() => import('./pages/Campaigns'));
const Support = lazy(() => import('./pages/Support'));
const AiWorkspace = lazy(() => import('./pages/AiWorkspace'));
const MlInsights = lazy(() => import('./pages/MlInsights'));
const Reports = lazy(() => import('./pages/Reports'));
const Analytics = lazy(() => import('./pages/Analytics'));
const CompanyComparison = lazy(() => import('./pages/CompanyComparison'));
const Profile = lazy(() => import('./pages/Profile'));
const Settings = lazy(() => import('./pages/Settings'));

import { auth } from './services/firebase';
import { onAuthStateChanged } from 'firebase/auth';
import { useState, useEffect } from 'react';
import api from './api';
import { AuthContext } from './AuthContext';
import ErrorBoundary from './components/common/ErrorBoundary';

const PrivateRoute = ({ children }) => {
  const { user, loading } = React.useContext(AuthContext);
  if (loading) return <PageLoader />;
  return user ? children : <Navigate to="/login" />;
};

const RoleRoute = ({ children, allowedRoles }) => {
  const { effectiveRole, loading } = React.useContext(AuthContext);
  if (loading || !effectiveRole) return <PageLoader />;
  if (allowedRoles.includes(effectiveRole)) {
    return children;
  }
  return <Navigate to="/" replace />;
};

const PageLoader = () => (
  <div style={{ display: 'flex', height: '100%', alignItems: 'center', justifyContent: 'center', color: 'var(--ink-mute)' }}>
    Loading...
  </div>
);

const IndexRedirect = () => {
  try {
    const prefs = JSON.parse(localStorage.getItem('nexora_crm_prefs') || '{}');
    if (prefs.defaultPage && prefs.defaultPage !== '/' && prefs.defaultPage !== '/dashboard') {
      return <Navigate to={prefs.defaultPage} replace />;
    }
  } catch (e) {}
  return <Navigate to="/dashboard" replace />;
};

function App() {
  const [user, setUser] = useState(null);
  const [crmProfile, setCrmProfile] = useState(null);
  const [loading, setLoading] = useState(true);
  const [previewRole, setPreviewRole] = useState(null);

  useEffect(() => {
    try {
      const prefs = JSON.parse(localStorage.getItem('nexora_crm_prefs') || '{}');
      document.body.setAttribute('data-density', prefs.density || 'standard');
      document.documentElement.setAttribute('data-theme', prefs.theme || 'light');
    } catch (e) {
      document.body.setAttribute('data-density', 'standard');
      document.documentElement.setAttribute('data-theme', 'light');
    }

    const handleThemeChange = (e) => {
      const newTheme = e.detail || 'light';
      document.documentElement.setAttribute('data-theme', newTheme);
    };
    window.addEventListener('nexora-theme-change', handleThemeChange);

    const timeoutId = setTimeout(() => {
      console.warn('[AUTH] Firebase auth timed out — forcing loading=false');
      setLoading(false);
    }, 10000);

    const unsubscribe = onAuthStateChanged(auth, async (firebaseUser) => {
      clearTimeout(timeoutId);
      setUser(firebaseUser);
      if (firebaseUser) {
        try {
          const res = await api.get('/api/auth/me');
          setCrmProfile(res.data);
        } catch (e) {
          console.error("Failed to fetch CRM profile", e);
        }
      } else {
        setCrmProfile(null);
      }
      setLoading(false);
    });

    return () => {
      clearTimeout(timeoutId);
      unsubscribe();
      window.removeEventListener('nexora-theme-change', handleThemeChange);
    };
  }, []);

  const effectiveRole = previewRole || crmProfile?.effective_role;

  return (
    <AuthContext.Provider value={{ user, crmProfile, effectiveRole, previewRole, setPreviewRole, loading }}>
      <Router>
        <Suspense fallback={<PageLoader />}>
          <ErrorBoundary>
            <Routes>
              <Route path="/login" element={<Login />} />
              
              <Route path="/" element={<PrivateRoute><AppLayout /></PrivateRoute>}>
                <Route index element={<IndexRedirect />} />
                <Route path="dashboard" element={<Dashboard />} />
            
            <Route path="companies" element={<Companies />} />
            <Route path="companies/:id" element={<CompanyDetail />} />
            
            <Route path="customers" element={<Customers />} />
            <Route path="customers/:id" element={<CustomerDetail />} />
            
            <Route path="contacts" element={<Contacts />} />

            
            <Route path="leads" element={<Leads />} />
            
            <Route path="opportunities" element={<Opportunities />} />
            <Route path="opportunities/:id" element={<OpportunityDetail />} />
            
            <Route path="products" element={<Products />} />
            
            <Route path="transactions" element={<Transactions />} />
            
            <Route path="activities" element={<Activities />} />
            
            <Route path="campaigns" element={<Campaigns />} />
            
            <Route path="support" element={<Support />} />
            
            <Route path="ai-workspace" element={<AiWorkspace />} />
            
            {/* Fallback support for old path */}
            <Route path="ai-assistant" element={<Navigate to="/ai-workspace" replace />} />
            
            <Route path="ml-insights" element={<RoleRoute allowedRoles={['Admin', 'Manager']}><MlInsights /></RoleRoute>} />
            
            <Route path="reports" element={<RoleRoute allowedRoles={['Admin', 'Manager']}><Reports /></RoleRoute>} />
            
            <Route path="analytics" element={<RoleRoute allowedRoles={['Admin', 'Manager']}><Analytics /></RoleRoute>} />
            
            <Route path="company-comparison" element={<CompanyComparison />} />
            
            <Route path="profile" element={<Profile />} />
            
            <Route path="settings" element={<RoleRoute allowedRoles={['Admin']}><Settings /></RoleRoute>} />
          </Route>

          {/* Catch-all unknown routes -> redirect to home */}
          <Route path="*" element={<Navigate to="/" replace />} />
            </Routes>
          </ErrorBoundary>
        </Suspense>
      </Router>
    </AuthContext.Provider>
  );
}

export default App;
