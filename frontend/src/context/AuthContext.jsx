import { createContext, useContext, useState, useEffect } from 'react';
import { api, getAuthToken, setAuthToken } from '../services/api';

const AuthContext = createContext();

export function AuthProvider({ children }) {
  const [currentUser, setCurrentUser] = useState(null);
  const [workspaces, setWorkspaces] = useState([]);
  const [activeWorkspace, setActiveWorkspace] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    initAuth();
  }, []);

  const initAuth = async () => {
    const token = getAuthToken();
    if (token) {
      try {
        const user = await api.auth.getMe();
        setCurrentUser(user);
        await fetchWorkspaces();
      } catch (err) {
        console.warn('Invalid token', err);
        setAuthToken(null);
        setCurrentUser(null);
      }
    }
    setLoading(false);
  };

  const fetchWorkspaces = async () => {
    try {
      const list = await api.workspaces.list();
      setWorkspaces(list || []);
      if (list && list.length > 0) {
        setActiveWorkspace((prev) => {
          if (prev && list.some(w => w.id === prev.id)) return prev;
          return list[0];
        });
      } else {
        setActiveWorkspace(null);
      }
    } catch (err) {
      console.error('Failed to fetch workspaces', err);
    }
  };

  const login = async (data) => {
    const res = await api.auth.login(data);
    setAuthToken(res.access_token);
    setCurrentUser(res.user);
    await fetchWorkspaces();
  };

  const register = async (data) => {
    const res = await api.auth.register(data);
    setAuthToken(res.access_token);
    setCurrentUser(res.user);
    await fetchWorkspaces();
  };

  const loginWithGoogle = async (token) => {
    const res = await api.auth.googleLogin(token);
    setAuthToken(res.access_token);
    setCurrentUser(res.user);
    await fetchWorkspaces();
  };

  const logout = () => {
    setAuthToken(null);
    setCurrentUser(null);
    setWorkspaces([]);
    setActiveWorkspace(null);
  };

  const createWorkspace = async (name) => {
    const newWs = await api.workspaces.create({ name });
    await fetchWorkspaces();
    setActiveWorkspace(newWs);
    return newWs;
  };

  return (
    <AuthContext.Provider value={{
      currentUser,
      loading,
      workspaces,
      activeWorkspace,
      setActiveWorkspace,
      login,
      loginWithGoogle,
      register,
      logout,
      createWorkspace
    }}>
      {children}
    </AuthContext.Provider>
  );
}

export const useAuth = () => useContext(AuthContext);
