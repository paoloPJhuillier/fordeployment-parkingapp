import React, { useState, useEffect } from 'react';
import { useNavigate, Link, useLocation } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { vehiclesAPI, buildingsAPI, reservationsAPI, zonesAPI } from '../services/api';
import { Button } from '../components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Badge } from '../components/ui/badge';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '../components/ui/dialog';
import { toast } from 'sonner';
import { 
  Car, Calendar, MapPin, Plus, LogOut, User, 
  Home, Clock, Building2, ChevronRight, X, ArrowRight, CheckCircle2, QrCode, History
} from 'lucide-react';
import { format, parseISO, isToday, isTomorrow } from 'date-fns';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../components/ui/tabs';
import { HelpTip } from '../components/ui/help-tip';
import NotificationBell from '../components/NotificationBell';

const UserDashboard = () => {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [vehicles, setVehicles] = useState([]);
  const [reservations, setReservations] = useState([]);
  const [buildings, setBuildings] = useState([]);
  const [allowedBuildingIds, setAllowedBuildingIds] = useState(null);
  const [loading, setLoading] = useState(true);
  const [vehicleDialogOpen, setVehicleDialogOpen] = useState(false);
  const [submittingVehicle, setSubmittingVehicle] = useState(false);
  const [newVehicle, setNewVehicle] = useState({ plate_number: '', make: '', model: '', color: '' });
  const [qrDialogOpen, setQrDialogOpen] = useState(false);
  const [qrData, setQrData] = useState(null);
  const [qrLoading, setQrLoading] = useState(false);
  const [stats, setStats] = useState(null);

  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async (retryCount = 0) => {
    try {
      const [vehiclesRes, reservationsRes, buildingsRes, zoneBuildingsRes] = await Promise.all([
        vehiclesAPI.getAll(),
        reservationsAPI.getAll({}),
        buildingsAPI.getAll(),
        zonesAPI.getUserBuildings().catch(() => ({ data: { building_ids: [], zones: [] } }))
      ]);
      setVehicles(vehiclesRes.data);
      setReservations(reservationsRes.data);
      setBuildings(buildingsRes.data);

      reservationsAPI.getStats().then(res => setStats(res.data)).catch(() => {});

      const zoneData = zoneBuildingsRes.data;
      const hasZones = (zoneData.zones || []).length > 0;
      if (hasZones && (zoneData.building_ids || []).length > 0) {
        setAllowedBuildingIds(new Set(zoneData.building_ids));
      }
    } catch (error) {
      if (retryCount < 1 && error?.response?.status !== 403) {
        await new Promise(r => setTimeout(r, 800));
        return fetchData(retryCount + 1);
      }
      if (error?.response?.status !== 401) {
        toast.error('Failed to load data');
      }
    } finally {
      setLoading(false);
    }
  };

  const handleAddVehicle = async (e) => {
    e.preventDefault();
    if (!newVehicle.plate_number) { toast.error('Plate number is required'); return; }
    setSubmittingVehicle(true);
    try {
      await vehiclesAPI.create(newVehicle);
      toast.success('Vehicle added! You can now book a parking spot.');
      setVehicleDialogOpen(false);
      setNewVehicle({ plate_number: '', make: '', model: '', color: '' });
      fetchData();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to add vehicle');
    } finally {
      setSubmittingVehicle(false);
    }
  };

  const handleCancelReservation = async (reservationId) => {
    // Show confirmation dialog before cancelling
    if (!window.confirm('Are you sure you want to cancel this booking reservation? This action cannot be undone.')) {
      return;
    }
    try {
      await reservationsAPI.cancel(reservationId);
      toast.success('Reservation cancelled');
      fetchData();
    } catch (error) {
      toast.error('Failed to cancel reservation');
    }
  };

  const handleViewQR = async (reservation) => {
    setQrDialogOpen(true);
    setQrData(null);
    setQrLoading(true);
    try {
      const response = await reservationsAPI.getQRCode(reservation.id);
      setQrData(response.data.qr_code);
    } catch {
      toast.error('Failed to load QR code');
    } finally {
      setQrLoading(false);
    }
  };

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  const today = new Date().toISOString().split('T')[0];

  const activeReservations = reservations
    .filter(r => (r.status === 'pending' || r.status === 'confirmed') && r.date >= today)
    .sort((a, b) => {
      const dateCompare = a.date.localeCompare(b.date);
      if (dateCompare !== 0) return dateCompare;
      return a.start_time.localeCompare(b.start_time);
    });

  const pastReservations = reservations
    .filter(r => r.status === 'cancelled' || r.status === 'no_show' || r.status === 'completed' || ((r.status === 'pending' || r.status === 'confirmed') && r.date < today))
    .sort((a, b) => b.date.localeCompare(a.date) || b.start_time.localeCompare(a.start_time));

  const getStatusColor = (status) => {
    switch (status) {
      case 'confirmed': return 'bg-green-100 text-green-800';
      case 'pending': return 'bg-yellow-100 text-yellow-800';
      case 'cancelled': return 'bg-red-100 text-red-800';
      default: return 'bg-gray-100 text-gray-800';
    }
  };

  const getStatusLabel = (status) => {
    switch (status) {
      case 'pending': return 'Reserved';
      case 'no_show': return 'No-Show';
      default: return status.charAt(0).toUpperCase() + status.slice(1);
    }
  };

  // Onboarding steps
  const hasVehicle = vehicles.length > 0;
  const hasBooking = reservations.length > 0;
  const isNewUser = !hasVehicle && !hasBooking;

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-[#08263e]"></div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50 pb-20 md:pb-8" data-testid="user-dashboard">
      {/* Header */}
      <header className="bg-[#08263e] text-white px-4 py-3 md:px-8">
        <div className="max-w-6xl mx-auto flex items-center justify-between">
          <div className="flex items-center gap-3">
            <Link to="/dashboard">
              <img 
                src="/cl-logo.png" 
                alt="Cebuana Lhuillier" 
                className="h-8 w-auto brightness-0 invert cursor-pointer"
              />
            </Link>
            <div className="hidden md:block">
              <p className="text-xs text-white/70">Welcome, {user?.first_name}</p>
            </div>
          </div>
          <div className="flex items-center gap-1">
            <NotificationBell />
            <Link to="/profile">
              <Button
                variant="ghost"
                className="text-white hover:bg-white/20"
                data-testid="profile-link"
                title="My Profile & Preferences"
              >
                <User className="w-5 h-5" />
              </Button>
            </Link>
            <Button 
              variant="ghost" 
              className="text-white hover:bg-white/20"
              onClick={handleLogout}
              data-testid="logout-btn"
            >
              <LogOut className="w-5 h-5" />
            </Button>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-6xl mx-auto px-4 py-6 md:px-8 space-y-6">

        {/* Onboarding Banner - shown when user has no vehicles */}
        {isNewUser && (
          <Card className="overflow-hidden border-0 shadow-lg animate-fadeIn" data-testid="onboarding-banner">
            <div className="bg-gradient-to-r from-[#08263e] to-[#518dca] p-6 md:p-8 text-white">
              <h2 className="text-2xl md:text-3xl font-bold mb-2">
                Welcome, {user?.first_name}!
              </h2>
              <p className="text-white/80 mb-6 max-w-lg">
                Let's get you set up. Follow these steps to start reserving your parking spot.
              </p>
              
              <div className="flex flex-col sm:flex-row gap-4">
                {/* Step 1 */}
                <div className="flex-1 bg-white/10 backdrop-blur-sm rounded-xl p-4 border border-white/20">
                  <div className="flex items-center gap-3 mb-2">
                    <div className="w-8 h-8 rounded-full bg-[#ec474e] flex items-center justify-center text-sm font-bold shrink-0">1</div>
                    <span className="font-semibold">Register Your Vehicle</span>
                  </div>
                  <p className="text-white/70 text-sm mb-3">Add your vehicle details to start booking parking spots.</p>
                  <Button 
                    className="w-full bg-white text-[#08263e] hover:bg-white/90 font-semibold rounded-full"
                    onClick={() => setVehicleDialogOpen(true)}
                    data-testid="onboarding-add-vehicle-btn"
                  >
                    <Car className="w-4 h-4 mr-2" />
                    Add Vehicle
                  </Button>
                </div>
                
                {/* Step 2 */}
                <div className="flex-1 bg-white/5 rounded-xl p-4 border border-white/10 opacity-60">
                  <div className="flex items-center gap-3 mb-2">
                    <div className="w-8 h-8 rounded-full bg-white/20 flex items-center justify-center text-sm font-bold shrink-0">2</div>
                    <span className="font-semibold">Book a Parking Spot</span>
                  </div>
                  <p className="text-white/70 text-sm mb-3">Choose a building, pick a date, and select your spot.</p>
                  <Button 
                    className="w-full bg-white/20 text-white/60 rounded-full cursor-not-allowed"
                    disabled
                  >
                    <MapPin className="w-4 h-4 mr-2" />
                    Add vehicle first
                  </Button>
                </div>
              </div>
            </div>
          </Card>
        )}

        {/* Vehicle prompt - shown when user has no vehicles but has been around */}
        {!hasVehicle && !isNewUser && (
          <Card className="border-[#ec474e]/30 bg-red-50/50 animate-fadeIn" data-testid="vehicle-prompt">
            <CardContent className="p-4 flex items-center gap-4">
              <div className="w-10 h-10 bg-[#ec474e] rounded-full flex items-center justify-center shrink-0">
                <Car className="w-5 h-5 text-white" />
              </div>
              <div className="flex-1">
                <p className="font-semibold text-gray-800">Register a vehicle to book parking</p>
                <p className="text-sm text-gray-500">You need at least one vehicle to make a reservation.</p>
              </div>
              <Button 
                className="bg-[#ec474e] hover:bg-[#d63a41] text-white rounded-full shrink-0"
                onClick={() => setVehicleDialogOpen(true)}
                data-testid="prompt-add-vehicle-btn"
              >
                <Plus className="w-4 h-4 mr-2" />
                Add Vehicle
              </Button>
            </CardContent>
          </Card>
        )}

        {/* Ready to book - shown after adding first vehicle but no bookings yet */}
        {hasVehicle && !hasBooking && (
          <Card className="border-green-200 bg-green-50/50 animate-fadeIn" data-testid="ready-to-book-banner">
            <CardContent className="p-4 flex items-center gap-4">
              <div className="w-10 h-10 bg-green-500 rounded-full flex items-center justify-center shrink-0">
                <CheckCircle2 className="w-5 h-5 text-white" />
              </div>
              <div className="flex-1">
                <p className="font-semibold text-gray-800">You're all set!</p>
                <p className="text-sm text-gray-500">Your vehicle is registered. Book your first parking spot now.</p>
              </div>
              <Button 
                className="bg-[#08263e] hover:bg-[#051a2d] text-white rounded-full shrink-0"
                onClick={() => navigate('/book')}
                data-testid="ready-book-now-btn"
              >
                Book Now
                <ArrowRight className="w-4 h-4 ml-2" />
              </Button>
            </CardContent>
          </Card>
        )}

        {/* Quick Stats */}
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <Card className="bg-gradient-to-br from-[#08263e] to-[#051a2d] text-white">
            <CardContent className="p-4">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-white/70 text-sm flex items-center gap-1">Active Bookings <HelpTip text="Pending and confirmed reservations" side="bottom" /></p>
                  <p className="text-3xl font-bold">{activeReservations.length}</p>
                </div>
                <Calendar className="w-8 h-8 text-[#ec474e]" />
              </div>
            </CardContent>
          </Card>
          
          <Card className="bg-white">
            <CardContent className="p-4">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-gray-500 text-sm">My Vehicles</p>
                  <p className="text-3xl font-bold text-[#08263e]">{vehicles.length}</p>
                </div>
                <Car className="w-8 h-8 text-[#08263e]" />
              </div>
            </CardContent>
          </Card>
          
          <Card className="bg-white">
            <CardContent className="p-4">
              <div className="flex items-center justify-between">
                <div>
                  <p className="text-gray-500 text-sm flex items-center gap-1">Buildings <HelpTip text="Buildings available in your zone for parking" /></p>
                  <p className="text-3xl font-bold text-[#08263e]">{allowedBuildingIds ? buildings.filter(b => allowedBuildingIds.has(b.id)).length : buildings.length}</p>
                </div>
                <Building2 className="w-8 h-8 text-[#08263e]" />
              </div>
            </CardContent>
          </Card>
          
          <Card className={hasVehicle ? "bg-[#ec474e] cursor-pointer hover:bg-[#d63a41] transition-colors" : "bg-gray-200"}>
            <CardContent className="p-4" onClick={() => hasVehicle ? navigate('/book') : setVehicleDialogOpen(true)}>
              <div className="flex items-center justify-between" data-testid="quick-book-link">
                <div>
                  <p className={`text-sm ${hasVehicle ? 'text-white/80' : 'text-gray-500'} flex items-center gap-1`}>
                    {hasVehicle ? 'Quick Book' : 'Setup Required'}
                    <HelpTip text={hasVehicle ? 'Book a new parking spot' : 'Register a vehicle to start booking'} side="bottom" />
                  </p>
                  <p className={`text-lg font-bold ${hasVehicle ? 'text-white' : 'text-gray-600'}`}>
                    {hasVehicle ? 'Reserve Now' : 'Add Vehicle'}
                  </p>
                </div>
                {hasVehicle ? (
                  <Plus className="w-8 h-8 text-white" />
                ) : (
                  <Car className="w-8 h-8 text-gray-400" />
                )}
              </div>
            </CardContent>
          </Card>
        </div>

        {/* Reservations with Active/History Tabs */}
        <section>
          <Tabs defaultValue="active" className="w-full">
            <div className="flex items-center justify-between mb-4">
              <h2 className="text-xl font-bold text-gray-800">My Reservations</h2>
              <TabsList className="bg-gray-100" data-testid="dashboard-reservation-tabs">
                <TabsTrigger value="active" className="text-xs data-[state=active]:bg-[#08263e] data-[state=active]:text-white" data-testid="dashboard-active-tab">
                  Active ({activeReservations.length})
                </TabsTrigger>
                <TabsTrigger value="history" className="text-xs data-[state=active]:bg-[#08263e] data-[state=active]:text-white" data-testid="dashboard-history-tab">
                  <History className="w-3 h-3 mr-1" /> History ({pastReservations.length})
                </TabsTrigger>
              </TabsList>
            </div>

            <TabsContent value="active">
              {activeReservations.length === 0 ? (
                <Card className="border-dashed border-2 border-gray-200">
                  <CardContent className="p-8 text-center">
                    <Calendar className="w-12 h-12 mx-auto text-gray-300 mb-3" />
                    <p className="text-gray-500 mb-1">No active reservations</p>
                    {hasVehicle ? (
                      <Button 
                        className="mt-3 bg-[#ec474e] hover:bg-[#d63a41] text-white rounded-full"
                        onClick={() => navigate('/book')}
                        data-testid="book-now-btn"
                      >
                        Book a Spot
                      </Button>
                    ) : (
                      <p className="text-sm text-gray-400">Add a vehicle first to start booking</p>
                    )}
                  </CardContent>
                </Card>
              ) : (
                <div className="space-y-4">
                  {(() => {
                    const groups = [];
                    let currentDate = null;
                    let currentGroup = null;
                    activeReservations.slice(0, 8).forEach(res => {
                      if (res.date !== currentDate) {
                        currentDate = res.date;
                        currentGroup = { date: res.date, items: [] };
                        groups.push(currentGroup);
                      }
                      currentGroup.items.push(res);
                    });

                    return groups.map(group => {
                      const dateObj = parseISO(group.date);
                      const dayLabel = isToday(dateObj) ? 'Today' : isTomorrow(dateObj) ? 'Tomorrow' : format(dateObj, 'EEEE');
                      return (
                        <div key={group.date} data-testid={`dashboard-date-group-${group.date}`}>
                          <div className="flex items-center gap-2.5 mb-2">
                            <div className={`w-9 h-9 rounded-lg flex items-center justify-center text-sm font-bold shrink-0 ${
                              isToday(dateObj) ? 'bg-[#08263e] text-white' : 'bg-gray-100 text-gray-600'
                            }`}>
                              {format(dateObj, 'dd')}
                            </div>
                            <div>
                              <p className={`text-sm font-semibold ${isToday(dateObj) ? 'text-[#08263e]' : 'text-gray-700'}`}>{dayLabel}</p>
                              <p className="text-[11px] text-gray-400">{format(dateObj, 'MMMM dd, yyyy')}</p>
                            </div>
                          </div>
                          <Card className="overflow-hidden">
                            <div className="divide-y divide-gray-100">
                              {group.items.map(reservation => (
                                <div key={reservation.id} className="flex items-center gap-3 py-3 px-4 hover:bg-gray-50/80 transition-colors group" data-testid={`reservation-card-${reservation.id}`}>
                                  <div className="w-16 shrink-0 text-center">
                                    <p className="text-sm font-semibold text-[#08263e] font-mono">{reservation.start_time}</p>
                                    <p className="text-[10px] text-gray-400">{reservation.end_time}</p>
                                  </div>
                                  <div className={`w-2.5 h-2.5 rounded-full shrink-0 ring-2 ring-white shadow-sm ${
                                    reservation.status === 'confirmed' ? 'bg-emerald-500' : 'bg-amber-400'
                                  }`} />
                                  <div className="flex-1 min-w-0">
                                    <div className="flex items-center gap-2">
                                      <span className="font-medium text-gray-800 text-sm truncate">{reservation.building_name || 'Building'}</span>
                                      <Badge className={`text-[10px] px-1.5 py-0 border ${
                                        reservation.status === 'confirmed'
                                          ? 'bg-emerald-50 text-emerald-700 border-emerald-200'
                                          : 'bg-amber-50 text-amber-700 border-amber-200'
                                      }`}>{getStatusLabel(reservation.status)}</Badge>
                                    </div>
                                    <div className="flex items-center gap-3 mt-0.5 text-xs text-gray-500">
                                      <span className="flex items-center gap-1">
                                        <MapPin className="w-3 h-3" />
                                        {reservation.floor_label} - <span className="font-mono font-semibold text-gray-700">{reservation.slot_label}</span>
                                      </span>
                                      <span className="flex items-center gap-1">
                                        <Car className="w-3 h-3" />
                                        <span className="font-mono">{reservation.vehicle_plate}</span>
                                      </span>
                                    </div>
                                  </div>
                                  <div className="flex items-center gap-1 shrink-0">
                                    <Button variant="ghost" size="sm" className="h-8 w-8 p-0 text-[#08263e] hover:bg-[#08263e]/10 opacity-60 group-hover:opacity-100"
                                      onClick={() => handleViewQR(reservation)} data-testid={`dashboard-qr-btn-${reservation.id}`} title="View QR Code">
                                      <QrCode className="w-4 h-4" />
                                    </Button>
                                    <Button variant="ghost" size="sm" className="h-8 w-8 p-0 text-red-500 hover:bg-red-50 opacity-60 group-hover:opacity-100"
                                      onClick={() => handleCancelReservation(reservation.id)} data-testid={`cancel-reservation-${reservation.id}`} title="Cancel">
                                      <X className="w-4 h-4" />
                                    </Button>
                                  </div>
                                </div>
                              ))}
                            </div>
                          </Card>
                        </div>
                      );
                    });
                  })()}
                </div>
              )}
            </TabsContent>

            <TabsContent value="history">
              {/* History Stats */}
              {stats && (
                <div className="grid grid-cols-5 gap-2 mb-4" data-testid="dashboard-history-stats">
                  <div className="bg-[#08263e] text-white rounded-lg p-2 text-center">
                    <p className="text-lg font-bold">{stats.total}</p>
                    <p className="text-[9px] text-white/60 uppercase">Total</p>
                  </div>
                  <div className="bg-emerald-50 border border-emerald-200 rounded-lg p-2 text-center">
                    <p className="text-lg font-bold text-emerald-700">{stats.confirmed}</p>
                    <p className="text-[9px] text-emerald-600 uppercase">Confirmed</p>
                  </div>
                  <div className="bg-blue-50 border border-blue-200 rounded-lg p-2 text-center">
                    <p className="text-lg font-bold text-blue-700">{stats.completed}</p>
                    <p className="text-[9px] text-blue-600 uppercase">Completed</p>
                  </div>
                  <div className="bg-gray-50 border border-gray-200 rounded-lg p-2 text-center">
                    <p className="text-lg font-bold text-gray-600">{stats.cancelled}</p>
                    <p className="text-[9px] text-gray-500 uppercase">Cancelled</p>
                  </div>
                  <div className="bg-red-50 border border-red-200 rounded-lg p-2 text-center">
                    <p className="text-lg font-bold text-red-600">{stats.no_show}</p>
                    <p className="text-[9px] text-red-500 uppercase">No-Show</p>
                  </div>
                </div>
              )}

              {pastReservations.length === 0 ? (
                <Card className="border-dashed border-2 border-gray-200">
                  <CardContent className="p-8 text-center">
                    <History className="w-12 h-12 mx-auto text-gray-300 mb-3" />
                    <p className="text-gray-500">No past reservations yet</p>
                  </CardContent>
                </Card>
              ) : (
                <div className="space-y-2">
                  {pastReservations.slice(0, 10).map(reservation => {
                    const dateObj = parseISO(reservation.date);
                    const statusStyles = {
                      cancelled: 'bg-gray-100 text-gray-600 border-gray-200',
                      no_show: 'bg-red-50 text-red-600 border-red-200',
                      completed: 'bg-emerald-50 text-emerald-600 border-emerald-200',
                    };
                    return (
                      <Card key={reservation.id} className="overflow-hidden opacity-80 hover:opacity-100 transition-opacity" data-testid={`history-card-${reservation.id}`}>
                        <div className="flex items-center gap-3 py-3 px-4">
                          <div className="w-16 shrink-0 text-center">
                            <p className="text-sm font-semibold text-gray-600 font-mono">{reservation.start_time}</p>
                            <p className="text-[10px] text-gray-400">{format(dateObj, 'MMM dd')}</p>
                          </div>
                          <div className="flex-1 min-w-0">
                            <div className="flex items-center gap-2">
                              <span className="font-medium text-gray-700 text-sm truncate">{reservation.building_name || 'Building'}</span>
                              <Badge className={`text-[10px] px-1.5 py-0 border ${statusStyles[reservation.status] || 'bg-gray-100 text-gray-500 border-gray-200'}`}>{getStatusLabel(reservation.status)}</Badge>
                            </div>
                            <div className="flex items-center gap-3 mt-0.5 text-xs text-gray-400">
                              <span>{reservation.floor_label} - {reservation.slot_label}</span>
                              <span>{reservation.vehicle_plate}</span>
                            </div>
                          </div>
                        </div>
                      </Card>
                    );
                  })}
                  {pastReservations.length > 10 && (
                    <Link to="/reservations" className="block text-center text-sm text-[#08263e] font-medium py-2 hover:underline" data-testid="view-full-history-link">
                      View full history ({pastReservations.length} total)
                    </Link>
                  )}
                </div>
              )}
            </TabsContent>
          </Tabs>
        </section>

        {/* My Vehicles */}
        <section>
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-xl font-bold text-gray-800">My Vehicles</h2>
            <Link to="/vehicles" className="text-[#08263e] text-sm font-medium flex items-center gap-1">
              Manage <ChevronRight className="w-4 h-4" />
            </Link>
          </div>
          
          {vehicles.length === 0 ? (
            <Card className="border-dashed border-2 border-gray-200">
              <CardContent className="p-8 text-center">
                <Car className="w-12 h-12 mx-auto text-gray-300 mb-3" />
                <p className="text-gray-500">No vehicles registered</p>
                <Button 
                  className="mt-4 bg-[#ec474e] hover:bg-[#d63a41] text-white rounded-full"
                  onClick={() => setVehicleDialogOpen(true)}
                  data-testid="vehicles-section-add-btn"
                >
                  <Plus className="w-4 h-4 mr-2" />
                  Add Vehicle
                </Button>
              </CardContent>
            </Card>
          ) : (
            <div className="grid gap-4 md:grid-cols-3">
              {vehicles.slice(0, 3).map((vehicle) => (
                <Card key={vehicle.id} className="bg-white hover:shadow-lg transition-shadow cursor-pointer" 
                  onClick={() => navigate('/book')}
                  data-testid={`vehicle-card-${vehicle.id}`}>
                  <CardContent className="p-4">
                    <div className="flex items-center gap-3">
                      <div className="w-12 h-12 bg-[#08263e]/10 rounded-lg flex items-center justify-center">
                        <Car className="w-6 h-6 text-[#08263e]" />
                      </div>
                      <div className="flex-1 min-w-0">
                        <p className="font-mono font-bold text-lg text-[#08263e]">{vehicle.plate_number}</p>
                        <p className="text-sm text-gray-500">
                          {[vehicle.color, vehicle.make, vehicle.model].filter(Boolean).join(' ') || 'Vehicle'}
                        </p>
                      </div>
                      <ArrowRight className="w-4 h-4 text-gray-400" />
                    </div>
                  </CardContent>
                </Card>
              ))}
            </div>
          )}
        </section>

        {/* Available Buildings */}
        <section>
          <h2 className="text-xl font-bold text-gray-800 mb-4">Available Buildings</h2>
          {(() => {
            const visibleBuildings = allowedBuildingIds
              ? buildings.filter(b => allowedBuildingIds.has(b.id))
              : buildings;
            
            return visibleBuildings.length === 0 ? (
              <Card className="border-dashed border-2 border-gray-200">
                <CardContent className="p-8 text-center">
                  <Building2 className="w-12 h-12 mx-auto text-gray-300 mb-3" />
                  <p className="text-gray-500">No buildings assigned to your zone</p>
                  <p className="text-sm text-gray-400 mt-1">Contact your admin to be assigned to a zone</p>
                </CardContent>
              </Card>
            ) : (
              <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
                {visibleBuildings.map((building) => (
                  <Card key={building.id} className="hover:shadow-lg transition-shadow cursor-pointer" 
                    onClick={() => hasVehicle ? navigate(`/book?building=${building.id}`) : setVehicleDialogOpen(true)}
                    data-testid={`building-card-${building.id}`}
                  >
                    <CardContent className="p-4">
                      <div className="flex items-start gap-3">
                        <div className="w-12 h-12 bg-[#ec474e] rounded-lg flex items-center justify-center shrink-0">
                          <Building2 className="w-6 h-6 text-white" />
                        </div>
                        <div className="flex-1 min-w-0">
                          <h3 className="font-semibold text-gray-800 truncate">{building.name}</h3>
                          <p className="text-sm text-gray-500 flex items-center gap-1 mt-1">
                            <MapPin className="w-4 h-4 shrink-0" />
                            <span className="truncate">{building.address}</span>
                          </p>
                          <div className="flex items-center gap-4 mt-2 text-xs text-gray-500">
                            <span>{building.total_floors} floors</span>
                            <span>{building.floors?.reduce((acc, f) => acc + f.slots.length, 0) || 0} slots</span>
                          </div>
                          {!hasVehicle && (
                            <p className="text-xs text-[#ec474e] mt-2 font-medium">Add a vehicle to book here</p>
                          )}
                        </div>
                      </div>
                    </CardContent>
                  </Card>
                ))}
              </div>
            );
          })()}
        </section>
      </main>

      {/* Add Vehicle Dialog */}
      <Dialog open={vehicleDialogOpen} onOpenChange={setVehicleDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Add Your Vehicle</DialogTitle>
          </DialogHeader>
          <p className="text-sm text-gray-500 -mt-2">Register your vehicle to start booking parking spots.</p>
          <form onSubmit={handleAddVehicle} className="space-y-4 mt-2">
            <div className="space-y-2">
              <Label htmlFor="plate_number">Plate Number *</Label>
              <Input 
                id="plate_number" 
                placeholder="ABC 1234" 
                value={newVehicle.plate_number} 
                onChange={(e) => setNewVehicle({ ...newVehicle, plate_number: e.target.value.toUpperCase() })} 
                required 
                className="font-mono uppercase" 
                data-testid="dashboard-vehicle-plate-input" 
              />
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2">
                <Label htmlFor="make">Make</Label>
                <Input id="make" placeholder="Toyota" value={newVehicle.make} onChange={(e) => setNewVehicle({ ...newVehicle, make: e.target.value })} data-testid="dashboard-vehicle-make-input" />
              </div>
              <div className="space-y-2">
                <Label htmlFor="model">Model</Label>
                <Input id="model" placeholder="Vios" value={newVehicle.model} onChange={(e) => setNewVehicle({ ...newVehicle, model: e.target.value })} data-testid="dashboard-vehicle-model-input" />
              </div>
            </div>
            <div className="space-y-2">
              <Label htmlFor="color">Color</Label>
              <Input id="color" placeholder="White" value={newVehicle.color} onChange={(e) => setNewVehicle({ ...newVehicle, color: e.target.value })} data-testid="dashboard-vehicle-color-input" />
            </div>
            <div className="flex gap-3 pt-2">
              <Button type="button" variant="outline" className="flex-1" onClick={() => setVehicleDialogOpen(false)}>Cancel</Button>
              <Button type="submit" className="flex-1 bg-[#08263e] hover:bg-[#051a2d] text-white" disabled={submittingVehicle} data-testid="dashboard-save-vehicle-btn">
                {submittingVehicle ? 'Saving...' : 'Save Vehicle'}
              </Button>
            </div>
          </form>
        </DialogContent>
      </Dialog>

      {/* QR Code Dialog */}
      <Dialog open={qrDialogOpen} onOpenChange={setQrDialogOpen}>
        <DialogContent className="max-w-xs">
          <DialogHeader>
            <DialogTitle>Booking QR Code</DialogTitle>
          </DialogHeader>
          <div className="flex items-center justify-center py-4">
            {qrLoading ? (
              <div className="w-48 h-48 flex items-center justify-center">
                <div className="animate-spin rounded-full h-8 w-8 border-t-2 border-b-2 border-[#08263e]" />
              </div>
            ) : qrData ? (
              <img src={qrData} alt="QR Code" className="w-48 h-48" data-testid="dashboard-qr-code-image" />
            ) : (
              <p className="text-gray-500 text-sm">Failed to load QR code</p>
            )}
          </div>
          <p className="text-xs text-center text-gray-400">Present this QR code to the parking attendant</p>
        </DialogContent>
      </Dialog>

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

export default UserDashboard;
