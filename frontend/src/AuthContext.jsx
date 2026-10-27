import { createContext, useContext } from 'react';

export const AuthContext = createContext({
  user: null,
  crmProfile: null,
  effectiveRole: null,
  previewRole: null,
  setPreviewRole: () => {},
  loading: true
});

export const useAuth = () => useContext(AuthContext);
