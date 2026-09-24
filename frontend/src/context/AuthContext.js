import React, { createContext, useContext, useState, useEffect } from 'react';
import { authAPI, setAuthToken } from '../services/api';

const AuthContext = createContext(null);

export const useAuth = () => {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
};

export const AuthProvider = ({ children }) => {
  const [user, setUser] = useState(null);
  const [loading, setLoading] = useState(true);
  const [mustChangePassword, setMustChangePassword] = useState(false);

  useEffect(() => {
    const initAuth = async (retryCount = 0) => {
      try {
        const response = await authAPI.getMe();
        setUser(response.data);
        setMustChangePassword(response.data.must_change_password || false);
      } catch (error) {
        if (retryCount < 1 && error?.response?.status !== 401) {
          await new Promise(r => setTimeout(r, 500));
          return initAuth(retryCount + 1);
        }
        setUser(null);
      }
      setLoading(false);
    };
    initAuth();
  }, []);

  const login = async (email, password) => {
    const response = await authAPI.login(email, password);
    const { user: userData, access_token: token } = response.data;
    // Set the bearer token BEFORE returning so the dashboard's data calls carry
    // it immediately (independent of the cookie being committed).
    if (token) setAuthToken(token);
    setUser(userData);
    setMustChangePassword(userData.must_change_password || false);
    return userData;
  };

  const register = async (userData) => {
    const response = await authAPI.register(userData);
    const { user: newUser, access_token: token } = response.data;
    if (token) setAuthToken(token);
    setUser(newUser);
    setMustChangePassword(false);
    return newUser;
  };

  const completePasswordChange = async (newPassword) => {
    await authAPI.forceChangePassword(newPassword);
    setMustChangePassword(false);
    setUser(prev => prev ? { ...prev, must_change_password: false } : prev);
  };

  const refreshUser = async () => {
    try {
      const response = await authAPI.getMe();
      setUser(response.data);
    } catch {
      // Ignore refresh errors
    }
  };

  const logout = async () => {
    try {
      await authAPI.logout();
    } catch {
      // Ignore logout errors
    }
    setAuthToken(null);
    setUser(null);
    setMustChangePassword(false);
  };

  const value = {
    user,
    loading,
    login,
    register,
    logout,
    refreshUser,
    mustChangePassword,
    completePasswordChange,
    isAuthenticated: !!user,
    isAdmin: user?.role === 'admin',
    isAttendant: user?.role === 'attendant' || user?.role === 'admin',
    isUser: user?.role === 'user'
  };

  return (
    <AuthContext.Provider value={value}>
      {children}
    </AuthContext.Provider>
  );
};

export default AuthContext;
