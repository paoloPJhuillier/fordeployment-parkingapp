import React from "react";
import "@/App.css";
import { BrowserRouter, Routes, Route, Navigate } from "react-router-dom";
import { Toaster } from "@/components/ui/sonner";
import { AuthProvider, useAuth } from "./context/AuthContext";

// Pages
import LoginPage from "./pages/LoginPage";
import UserDashboard from "./pages/UserDashboard";
import BookingPage from "./pages/BookingPage";
import VehiclesPage from "./pages/VehiclesPage";
import ReservationsPage from "./pages/ReservationsPage";
import ProfilePage from "./pages/ProfilePage";
import ScanPage from "./pages/ScanPage";

// Admin Pages
import AdminLayout from "./pages/admin/AdminLayout";
import AdminDashboard from "./pages/admin/AdminDashboard";
import UserManagement from "./pages/admin/UserManagement";
import BuildingManagement from "./pages/admin/BuildingManagement";
import ZoneManagement from "./pages/admin/ZoneManagement";
import ParkingConfig from "./pages/admin/ParkingConfig";
import Reports from "./pages/admin/Reports";
import AttendantManagement from "./pages/admin/AttendantManagement";
import AdminReservations from "./pages/admin/AdminReservations";
import AdminSettings from "./pages/admin/AdminSettings";
import Documentation from "./pages/admin/Documentation";
import BuildingPolicies from "./pages/admin/BuildingPolicies";
import EventBlocking from "./pages/admin/EventBlocking";

// Attendant Pages
import AttendantDashboard from "./pages/attendant/AttendantDashboard";

import ForcePasswordChange from "./pages/ForcePasswordChange";

// Protected Route Component
const ProtectedRoute = ({ children, allowedRoles }) => {
  const { user, loading, isAuthenticated, mustChangePassword } = useAuth();
  
  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-[#08263e]"></div>
      </div>
    );
  }
  
  if (!isAuthenticated) {
    return <Navigate to="/login" replace />;
  }

  if (mustChangePassword) {
    return <ForcePasswordChange />;
  }
  
  if (allowedRoles && !allowedRoles.includes(user?.role)) {
    if (user?.role === 'admin') {
      return <Navigate to="/admin" replace />;
    } else if (user?.role === 'attendant') {
      return <Navigate to="/attendant" replace />;
    }
    return <Navigate to="/dashboard" replace />;
  }
  
  return children;
};

// Public Route - redirects to dashboard if already logged in
const PublicRoute = ({ children }) => {
  const { isAuthenticated, loading, user } = useAuth();
  
  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-[#08263e]"></div>
      </div>
    );
  }
  
  if (isAuthenticated) {
    if (user?.role === 'admin') {
      return <Navigate to="/admin" replace />;
    } else if (user?.role === 'attendant') {
      return <Navigate to="/attendant" replace />;
    }
    return <Navigate to="/dashboard" replace />;
  }
  
  return children;
};

function AppRoutes() {
  return (
    <Routes>
      {/* Public Routes */}
      <Route path="/login" element={
        <PublicRoute>
          <LoginPage />
        </PublicRoute>
      } />
      
      {/* User Routes */}
      <Route path="/dashboard" element={
        <ProtectedRoute allowedRoles={['user', 'admin', 'attendant']}>
          <UserDashboard />
        </ProtectedRoute>
      } />
      
      <Route path="/book" element={
        <ProtectedRoute allowedRoles={['user', 'admin']}>
          <BookingPage />
        </ProtectedRoute>
      } />
      
      <Route path="/vehicles" element={
        <ProtectedRoute allowedRoles={['user', 'admin']}>
          <VehiclesPage />
        </ProtectedRoute>
      } />
      
      <Route path="/reservations" element={
        <ProtectedRoute allowedRoles={['user', 'admin']}>
          <ReservationsPage />
        </ProtectedRoute>
      } />
      
      <Route path="/profile" element={
        <ProtectedRoute allowedRoles={['user', 'admin', 'attendant']}>
          <ProfilePage />
        </ProtectedRoute>
      } />
      
      {/* Admin Routes */}
      <Route path="/admin" element={
        <ProtectedRoute allowedRoles={['admin']}>
          <AdminLayout>
            <AdminDashboard />
          </AdminLayout>
        </ProtectedRoute>
      } />
      
      <Route path="/admin/users" element={
        <ProtectedRoute allowedRoles={['admin']}>
          <AdminLayout>
            <UserManagement />
          </AdminLayout>
        </ProtectedRoute>
      } />
      
      <Route path="/admin/reservations" element={
        <ProtectedRoute allowedRoles={['admin']}>
          <AdminLayout>
            <AdminReservations />
          </AdminLayout>
        </ProtectedRoute>
      } />
      
      <Route path="/admin/buildings" element={
        <ProtectedRoute allowedRoles={['admin']}>
          <AdminLayout>
            <BuildingManagement />
          </AdminLayout>
        </ProtectedRoute>
      } />
      
      <Route path="/admin/zones" element={
        <ProtectedRoute allowedRoles={['admin']}>
          <AdminLayout>
            <ZoneManagement />
          </AdminLayout>
        </ProtectedRoute>
      } />
      
      <Route path="/admin/parking-config" element={
        <ProtectedRoute allowedRoles={['admin']}>
          <AdminLayout>
            <ParkingConfig />
          </AdminLayout>
        </ProtectedRoute>
      } />
      
      <Route path="/admin/building-policies" element={
        <ProtectedRoute allowedRoles={['admin']}>
          <AdminLayout>
            <BuildingPolicies />
          </AdminLayout>
        </ProtectedRoute>
      } />
      
      <Route path="/admin/event-blocking" element={
        <ProtectedRoute allowedRoles={['admin']}>
          <AdminLayout>
            <EventBlocking />
          </AdminLayout>
        </ProtectedRoute>
      } />
      
      <Route path="/admin/reports" element={
        <ProtectedRoute allowedRoles={['admin']}>
          <AdminLayout>
            <Reports />
          </AdminLayout>
        </ProtectedRoute>
      } />
      
      <Route path="/admin/attendants" element={
        <ProtectedRoute allowedRoles={['admin']}>
          <AdminLayout>
            <AttendantManagement />
          </AdminLayout>
        </ProtectedRoute>
      } />
      
      <Route path="/admin/settings" element={
        <ProtectedRoute allowedRoles={['admin']}>
          <AdminLayout>
            <AdminSettings />
          </AdminLayout>
        </ProtectedRoute>
      } />
      
      <Route path="/admin/docs" element={
        <ProtectedRoute allowedRoles={['admin']}>
          <AdminLayout>
            <Documentation />
          </AdminLayout>
        </ProtectedRoute>
      } />
      
      {/* Attendant Routes */}
      <Route path="/attendant" element={
        <ProtectedRoute allowedRoles={['attendant', 'admin']}>
          <AttendantDashboard />
        </ProtectedRoute>
      } />
      
      {/* QR Scan Route (public) */}
      <Route path="/scan/:qrToken" element={<ScanPage />} />
      
      {/* Default redirect */}
      <Route path="/" element={<Navigate to="/login" replace />} />
      <Route path="*" element={<Navigate to="/login" replace />} />
    </Routes>
  );
}

function App() {
  return (
    <div className="App">
      <BrowserRouter>
        <AuthProvider>
          <AppRoutes />
          <Toaster position="top-right" richColors />
        </AuthProvider>
      </BrowserRouter>
    </div>
  );
}

export default App;
