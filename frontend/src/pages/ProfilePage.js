import React, { useState, useEffect, useRef } from 'react';
import { useNavigate, Link, useLocation } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { authAPI } from '../services/api';
import { Button } from '../components/ui/button';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '../components/ui/card';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Badge } from '../components/ui/badge';
import { toast } from 'sonner';
import {
  User, Building2, Shield, LogOut, Home, Plus, Calendar, Car,
  Clock, Save, RotateCcw, Lock
} from 'lucide-react';

const ProfilePage = () => {
  const { user, logout, refreshUser } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();

  const [startTime, setStartTime] = useState('');
  const [endTime, setEndTime] = useState('');
  const [saving, setSaving] = useState(false);
  const [hasChanges, setHasChanges] = useState(false);
  const [changingPw, setChangingPw] = useState(false);
  const currentPwRef = useRef(null);
  const newPwRef = useRef(null);
  const confirmPwRef = useRef(null);

  const handleChangePassword = async (e) => {
    e.preventDefault();
    const current = currentPwRef.current?.value || '';
    const newPw = newPwRef.current?.value || '';
    const confirm = confirmPwRef.current?.value || '';
    if (!current) { toast.error('Current password is required'); return; }
    if (newPw.length < 8) { toast.error('New password must be at least 8 characters'); return; }
    if (newPw !== confirm) { toast.error('Passwords do not match'); return; }
    setChangingPw(true);
    try {
      await authAPI.changePassword(current, newPw);
      toast.success('Password changed successfully');
      if (currentPwRef.current) currentPwRef.current.value = '';
      if (newPwRef.current) newPwRef.current.value = '';
      if (confirmPwRef.current) confirmPwRef.current.value = '';
    } catch (err) {
      toast.error(err.response?.data?.detail || 'Failed to change password');
    } finally { setChangingPw(false); }
  };

  useEffect(() => {
    if (user) {
      setStartTime(user.default_start_time || '');
      setEndTime(user.default_end_time || '');
    }
  }, [user]);

  useEffect(() => {
    const origStart = user?.default_start_time || '';
    const origEnd = user?.default_end_time || '';
    setHasChanges(startTime !== origStart || endTime !== origEnd);
  }, [startTime, endTime, user]);

  const handleSavePreferences = async () => {
    if (startTime && endTime && startTime >= endTime) {
      toast.error('End time must be after start time');
      return;
    }
    setSaving(true);
    try {
      await authAPI.updateBookingPreferences(startTime, endTime);
      if (refreshUser) await refreshUser();
      toast.success('Booking preferences saved');
      setHasChanges(false);
    } catch (error) {
      toast.error('Failed to save preferences');
    } finally {
      setSaving(false);
    }
  };

  const handleResetPreferences = async () => {
    setSaving(true);
    try {
      await authAPI.updateBookingPreferences('', '');
      setStartTime('');
      setEndTime('');
      if (refreshUser) await refreshUser();
      toast.success('Reset to building defaults');
      setHasChanges(false);
    } catch (error) {
      toast.error('Failed to reset preferences');
    } finally {
      setSaving(false);
    }
  };

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  const getRoleBadgeColor = (role) => {
    switch (role) {
      case 'admin': return 'bg-purple-100 text-purple-800';
      case 'attendant': return 'bg-blue-100 text-blue-800';
      default: return 'bg-green-100 text-green-800';
    }
  };

  return (
    <div className="min-h-screen bg-gray-50 pb-20 md:pb-8" data-testid="profile-page">
      {/* Header */}
      <header className="bg-[#08263e] text-white px-4 py-3 md:px-8">
        <div className="max-w-6xl mx-auto flex items-center gap-4">
          <Link to="/dashboard">
            <img
              src="/cl-logo.png"
              alt="Cebuana Lhuillier"
              className="h-8 w-auto brightness-0 invert cursor-pointer"
            />
          </Link>
          <div className="hidden md:block">
            <p className="text-xs text-white/70">My Profile</p>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-6xl mx-auto px-4 py-6 md:px-8 space-y-6">
        {/* Profile Card */}
        <Card>
          <CardHeader className="pb-4">
            <div className="flex items-center gap-4">
              <div className="w-20 h-20 bg-gradient-to-br from-[#08263e] to-[#051a2d] rounded-full flex items-center justify-center">
                <span className="text-3xl font-bold text-white">
                  {user?.first_name?.[0]}{user?.last_name?.[0]}
                </span>
              </div>
              <div>
                <CardTitle className="text-xl">
                  {user?.first_name} {user?.last_name}
                </CardTitle>
                <Badge className={getRoleBadgeColor(user?.role)}>
                  {user?.role === 'admin' ? 'Administrator' :
                   user?.role === 'attendant' ? 'Parking Attendant' : 'Employee'}
                </Badge>
              </div>
            </div>
          </CardHeader>
          <CardContent className="space-y-4">
            {user?.company && (
              <div className="flex items-center gap-3 text-gray-600">
                <Building2 className="w-5 h-5 text-gray-400" />
                <span>{user.company}</span>
              </div>
            )}
            <div className="flex items-center gap-3 text-gray-600">
              <Shield className="w-5 h-5 text-gray-400" />
              <span>Role: {user?.role}</span>
            </div>
          </CardContent>
        </Card>

        {/* Booking Preferences */}
        {user?.role === 'user' && (
          <Card data-testid="booking-preferences-card">
            <CardHeader className="pb-3">
              <div className="flex items-center gap-2">
                <Clock className="w-5 h-5 text-[#08263e]" />
                <div>
                  <CardTitle className="text-lg">Booking Preferences</CardTitle>
                  <CardDescription>Set your default parking hours. These will auto-fill when you make a reservation.</CardDescription>
                </div>
              </div>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label htmlFor="start-time" className="text-sm font-medium">Start Time</Label>
                  <Input
                    id="start-time"
                    type="time"
                    value={startTime}
                    onChange={(e) => setStartTime(e.target.value)}
                    className="font-mono"
                    data-testid="pref-start-time"
                  />
                </div>
                <div className="space-y-2">
                  <Label htmlFor="end-time" className="text-sm font-medium">End Time</Label>
                  <Input
                    id="end-time"
                    type="time"
                    value={endTime}
                    onChange={(e) => setEndTime(e.target.value)}
                    className="font-mono"
                    data-testid="pref-end-time"
                  />
                </div>
              </div>

              {!startTime && !endTime && (
                <p className="text-xs text-gray-400">Using building defaults. Set your own hours to override.</p>
              )}
              {startTime && endTime && (
                <div className="flex items-center gap-2 text-sm text-[#08263e] bg-[#08263e]/5 px-3 py-2 rounded-lg">
                  <Clock className="w-4 h-4" />
                  <span>Your bookings will default to <strong>{startTime}</strong> - <strong>{endTime}</strong></span>
                </div>
              )}

              <div className="flex gap-2 pt-1">
                <Button
                  onClick={handleSavePreferences}
                  disabled={saving || !hasChanges}
                  className="bg-[#08263e] hover:bg-[#051a2d] text-white"
                  data-testid="save-preferences-btn"
                >
                  <Save className="w-4 h-4 mr-2" />
                  {saving ? 'Saving...' : 'Save Preferences'}
                </Button>
                {(startTime || endTime) && (
                  <Button
                    variant="outline"
                    onClick={handleResetPreferences}
                    disabled={saving}
                    data-testid="reset-preferences-btn"
                  >
                    <RotateCcw className="w-4 h-4 mr-2" />
                    Reset to Defaults
                  </Button>
                )}
              </div>
            </CardContent>
          </Card>
        )}

        {/* Quick Actions */}
        <Card>
          <CardHeader>
            <CardTitle className="text-lg">Quick Actions</CardTitle>
          </CardHeader>
          <CardContent className="space-y-2">
            {user?.role === 'admin' && (
              <Button variant="outline" className="w-full justify-start" onClick={() => navigate('/admin')}>
                <Shield className="w-4 h-4 mr-2" />
                Go to Admin Dashboard
              </Button>
            )}
            {user?.role === 'attendant' && (
              <Button variant="outline" className="w-full justify-start" onClick={() => navigate('/attendant')}>
                <Shield className="w-4 h-4 mr-2" />
                Go to Attendant Dashboard
              </Button>
            )}
            <Button variant="outline" className="w-full justify-start" onClick={() => navigate('/vehicles')}>
              <Car className="w-4 h-4 mr-2" />
              Manage My Vehicles
            </Button>
            <Button variant="outline" className="w-full justify-start" onClick={() => navigate('/reservations')}>
              <Calendar className="w-4 h-4 mr-2" />
              View My Reservations
            </Button>
          </CardContent>
        </Card>

        {/* Logout */}
        {/* Change Password */}
        <Card>
          <CardHeader className="pb-3">
            <CardTitle className="text-base flex items-center gap-2"><Lock className="w-4 h-4" /> Change Password</CardTitle>
          </CardHeader>
          <CardContent>
            <form onSubmit={handleChangePassword} className="space-y-3">
              <div>
                <Label htmlFor="current-pw" className="text-sm">Current Password</Label>
                <Input id="current-pw" type="password" ref={currentPwRef} autoComplete="current-password" required data-testid="current-password-input" />
              </div>
              <div>
                <Label htmlFor="new-pw" className="text-sm">New Password</Label>
                <Input id="new-pw" type="password" ref={newPwRef} autoComplete="new-password" required data-testid="new-password-profile-input" />
              </div>
              <div>
                <Label htmlFor="confirm-pw" className="text-sm">Confirm New Password</Label>
                <Input id="confirm-pw" type="password" ref={confirmPwRef} autoComplete="new-password" required data-testid="confirm-password-profile-input" />
              </div>
              <Button type="submit" disabled={changingPw} className="w-full" data-testid="change-password-btn">
                {changingPw ? 'Changing...' : 'Change Password'}
              </Button>
            </form>
          </CardContent>
        </Card>

        <Button
          variant="outline"
          className="w-full text-red-500 hover:text-red-700 hover:bg-red-50"
          onClick={handleLogout}
          data-testid="profile-logout-btn"
        >
          <LogOut className="w-4 h-4 mr-2" />
          Sign Out
        </Button>
      </main>

      {/* Mobile Bottom Navigation */}
      <nav className="mobile-nav">
        <Link to="/dashboard" className={`mobile-nav-item ${location.pathname === '/dashboard' ? 'active' : ''}`}>
          <Home className="w-5 h-5" />
          <span className="text-xs">Home</span>
        </Link>
        <Link to="/book" className={`mobile-nav-item ${location.pathname === '/book' ? 'active' : ''}`}>
          <Plus className="w-5 h-5" />
          <span className="text-xs">Book</span>
        </Link>
        <Link to="/reservations" className={`mobile-nav-item ${location.pathname === '/reservations' ? 'active' : ''}`}>
          <Calendar className="w-5 h-5" />
          <span className="text-xs">Bookings</span>
        </Link>
        <Link to="/vehicles" className={`mobile-nav-item ${location.pathname === '/vehicles' ? 'active' : ''}`}>
          <Car className="w-5 h-5" />
          <span className="text-xs">Vehicles</span>
        </Link>
        <Link to="/profile" className={`mobile-nav-item ${location.pathname === '/profile' ? 'active' : ''}`}>
          <User className="w-5 h-5" />
          <span className="text-xs">Profile</span>
        </Link>
      </nav>
    </div>
  );
};

export default ProfilePage;
