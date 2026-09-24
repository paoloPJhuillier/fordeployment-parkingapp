import React, { useState, useEffect } from 'react';
import { useNavigate, Link, useLocation } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { reservationsAPI } from '../services/api';
import useFeatures from '../hooks/useFeatures';
import { Button } from '../components/ui/button';
import { Card, CardContent } from '../components/ui/card';
import { Badge } from '../components/ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../components/ui/tabs';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '../components/ui/dialog';
import { toast } from 'sonner';
import { 
  ArrowLeft, Calendar, Clock, Building2, Car, X,
  Home, Plus, User, MapPin, CheckCircle2, QrCode, 
  ChevronRight, XCircle, AlertTriangle
} from 'lucide-react';
import { format, isToday, isTomorrow, parseISO, isPast } from 'date-fns';

const ReservationsPage = () => {
  const { user } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [reservations, setReservations] = useState([]);
  const [loading, setLoading] = useState(true);
  const [qrDialogOpen, setQrDialogOpen] = useState(false);
  const [qrData, setQrData] = useState(null);  const [qrLoading, setQrLoading] = useState(false);
  const [selectedRes, setSelectedRes] = useState(null);
  const [cancellingId, setCancellingId] = useState(null);
  const [stats, setStats] = useState(null);
  const [checkingInId, setCheckingInId] = useState(null);
  const { attendant_mode_enabled, self_checkin_window_minutes } = useFeatures();

  useEffect(() => { fetchReservations(); fetchStats(); }, []);

  const fetchReservations = async () => {
    try {
      const response = await reservationsAPI.getAll({});
      setReservations(response.data);
    } catch (error) {
      toast.error('Failed to load reservations');
    } finally {
      setLoading(false);
    }
  };

  const fetchStats = async () => {
    try {
      const response = await reservationsAPI.getStats();
      setStats(response.data);
    } catch { }
  };

  const handleCancelReservation = async (reservationId) => {
    if (!window.confirm('Are you sure you want to cancel this reservation?')) return;
    setCancellingId(reservationId);
    try {
      await reservationsAPI.cancel(reservationId);
      toast.success('Reservation cancelled');
      fetchReservations();
    } catch (error) {
      toast.error('Failed to cancel reservation');
    } finally {
      setCancellingId(null);
    }
  };

  const handleSelfCheckin = async (reservationId) => {
    setCheckingInId(reservationId);
    try {
      await reservationsAPI.selfCheckin(reservationId);
      toast.success('Checked in — your slot is confirmed.');
      fetchReservations();
    } catch (error) {
      // 410 = window expired; 400 = too early; 403 = attendant mode on.
      // Show the server message verbatim because it carries the why.
      toast.error(error?.response?.data?.detail || 'Check-in failed');
    } finally {
      setCheckingInId(null);
    }
  };

  const handleViewQR = async (reservation) => {
    setSelectedRes(reservation);
    setQrDialogOpen(true);
    setQrLoading(true);
    try {
      const response = await reservationsAPI.getQRCode(reservation.id);
      setQrData(response.data.qr_code);
    } catch (error) {
      toast.error('Failed to load QR code');
    } finally {
      setQrLoading(false);
    }
  };

  const today = new Date().toISOString().split('T')[0];
  const activeReservations = reservations.filter(r => (r.status === 'pending' || r.status === 'confirmed') && r.date >= today);
  const pastReservations = reservations.filter(r => r.status === 'completed' || r.status === 'cancelled' || r.status === 'no_show' || ((r.status === 'pending' || r.status === 'confirmed') && r.date < today));

  // Group and sort by date
  const groupByDate = (items, ascending = true) => {
    const sorted = [...items].sort((a, b) => {
      const dateCompare = ascending 
        ? a.date.localeCompare(b.date) 
        : b.date.localeCompare(a.date);
      if (dateCompare !== 0) return dateCompare;
      return a.start_time.localeCompare(b.start_time);
    });

    const groups = [];
    let currentDate = null;
    let currentGroup = null;

    sorted.forEach(item => {
      if (item.date !== currentDate) {
        currentDate = item.date;
        currentGroup = { date: item.date, items: [] };
        groups.push(currentGroup);
      }
      currentGroup.items.push(item);
    });

    return groups;
  };

  const getDateLabel = (dateStr) => {
    const date = parseISO(dateStr);
    if (isToday(date)) return 'Today';
    if (isTomorrow(date)) return 'Tomorrow';
    return format(date, 'EEEE');
  };

  const getDateSub = (dateStr) => format(parseISO(dateStr), 'MMMM dd, yyyy');

  const isDatePast = (dateStr) => {
    const d = parseISO(dateStr);
    const today = new Date();
    today.setHours(0, 0, 0, 0);
    return d < today;
  };

  const statusConfig = {
    confirmed: { color: 'bg-emerald-500', badge: 'bg-emerald-50 text-emerald-700 border-emerald-200', label: 'Confirmed', icon: CheckCircle2 },
    pending: { color: 'bg-amber-400', badge: 'bg-amber-50 text-amber-700 border-amber-200', label: 'Reserved', icon: Clock },
    cancelled: { color: 'bg-gray-300', badge: 'bg-gray-100 text-gray-500 border-gray-200', label: 'Cancelled', icon: XCircle },
    no_show: { color: 'bg-red-400', badge: 'bg-red-50 text-red-700 border-red-200', label: 'No Show', icon: AlertTriangle },
    completed: { color: 'bg-blue-400', badge: 'bg-blue-50 text-blue-700 border-blue-200', label: 'Completed', icon: CheckCircle2 },
  };

  const getStatus = (s) => statusConfig[s] || statusConfig.pending;

  const activeGroups = groupByDate(activeReservations, true);
  const pastGroups = groupByDate(pastReservations, false);

  // Count upcoming today
  const todayCount = activeReservations.filter(r => isToday(parseISO(r.date))).length;

  const ReservationRow = ({ reservation, showActions = true }) => {
    const sc = getStatus(reservation.status);
    const StatusIcon = sc.icon;
    const canCancel = showActions && (reservation.status === 'pending' || reservation.status === 'confirmed');
    const canShowQR = showActions && (reservation.status === 'pending' || reservation.status === 'confirmed');

    // Self check-in: show only when (a) attendants are turned OFF system-wide,
    // (b) this is the parker's own pending reservation, (c) the current time
    // falls between start_time and start_time + window. We compute "now" each
    // render — it's cheap and avoids stale timestamps on long-open tabs.
    const canSelfCheckin = (() => {
      if (attendant_mode_enabled !== false) return false;
      if (!showActions) return false;
      if (reservation.status !== 'pending') return false;
      try {
        const start = new Date(`${reservation.date}T${reservation.start_time}:00Z`);
        const windowMin = self_checkin_window_minutes || 15;
        const expires = new Date(start.getTime() + windowMin * 60 * 1000);
        const now = new Date();
        return now >= start && now <= expires;
      } catch {
        return false;
      }
    })();

    return (
      <div 
        className="flex items-center gap-3 py-3 px-4 hover:bg-gray-50/80 transition-colors group" 
        data-testid={`reservation-row-${reservation.id}`}
      >
        {/* Time column */}
        <div className="w-20 shrink-0 text-center">
          <p className="text-sm font-semibold text-[#08263e] font-mono">{reservation.start_time}</p>
          <p className="text-[10px] text-gray-400">{reservation.end_time}</p>
        </div>

        {/* Status dot + connector */}
        <div className="flex flex-col items-center shrink-0">
          <div className={`w-3 h-3 rounded-full ${sc.color} ring-2 ring-white shadow-sm`}></div>
        </div>

        {/* Details */}
        <div className="flex-1 min-w-0">
          <div className="flex items-center gap-2">
            <span className="font-medium text-gray-800 text-sm truncate">{reservation.building_name}</span>
            <Badge className={`text-[10px] px-1.5 py-0 border ${sc.badge}`}>
              {sc.label}
            </Badge>
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
          {reservation.status === 'no_show' && reservation.no_show_at && (
            <p className="text-[10px] text-red-500 mt-0.5 flex items-center gap-1" data-testid={`no-show-time-${reservation.id}`}>
              <AlertTriangle className="w-3 h-3" />
              Tagged no-show at {(() => { try { return format(parseISO(reservation.no_show_at), 'MMM dd, h:mm a'); } catch { return reservation.no_show_at; } })()}
            </p>
          )}
        </div>

        {/* Actions */}
        <div className="flex items-center gap-1.5 shrink-0 opacity-80 group-hover:opacity-100 transition-opacity">
          {canSelfCheckin && (
            <Button
              size="sm"
              className="h-8 px-3 bg-emerald-600 hover:bg-emerald-700 text-white text-xs"
              onClick={() => handleSelfCheckin(reservation.id)}
              disabled={checkingInId === reservation.id}
              data-testid={`self-checkin-btn-${reservation.id}`}
              title="Confirm your arrival — your slot is held for a few minutes"
            >
              {checkingInId === reservation.id ? (
                <div className="w-3.5 h-3.5 border-2 border-white/40 border-t-white rounded-full animate-spin" />
              ) : (
                <>
                  <CheckCircle2 className="w-3.5 h-3.5 mr-1" />
                  Check in
                </>
              )}
            </Button>
          )}
          {canShowQR && (
            <Button
              variant="ghost"
              size="sm"
              className="h-8 w-8 p-0 text-[#08263e] hover:bg-[#08263e]/10"
              onClick={() => handleViewQR(reservation)}
              data-testid={`qr-btn-${reservation.id}`}
              title="View QR Code"
            >
              <QrCode className="w-4 h-4" />
            </Button>
          )}
          {canCancel && (
            <Button
              variant="ghost"
              size="sm"
              className="h-8 w-8 p-0 text-red-500 hover:bg-red-50"
              onClick={() => handleCancelReservation(reservation.id)}
              disabled={cancellingId === reservation.id}
              data-testid={`cancel-btn-${reservation.id}`}
              title="Cancel Booking"
            >
              {cancellingId === reservation.id 
                ? <div className="w-3.5 h-3.5 border-2 border-red-300 border-t-red-600 rounded-full animate-spin" />
                : <X className="w-4 h-4" />
              }
            </Button>
          )}
        </div>
      </div>
    );
  };

  const DateGroup = ({ dateStr, items, showActions = true }) => {
    const label = getDateLabel(dateStr);
    const sub = getDateSub(dateStr);
    const past = isDatePast(dateStr);
    const today = isToday(parseISO(dateStr));

    return (
      <div className="mb-5" data-testid={`date-group-${dateStr}`}>
        {/* Date header */}
        <div className={`flex items-center gap-3 mb-2 px-1 ${past && !today ? 'opacity-60' : ''}`}>
          <div className={`w-10 h-10 rounded-lg flex items-center justify-center shrink-0 ${
            today ? 'bg-[#08263e] text-white' : 'bg-gray-100 text-gray-600'
          }`}>
            <span className="text-sm font-bold">{format(parseISO(dateStr), 'dd')}</span>
          </div>
          <div>
            <p className={`text-sm font-semibold ${today ? 'text-[#08263e]' : 'text-gray-700'}`}>{label}</p>
            <p className="text-xs text-gray-400">{sub}</p>
          </div>
          <Badge variant="outline" className="ml-auto text-xs text-gray-500">
            {items.length} booking{items.length !== 1 ? 's' : ''}
          </Badge>
        </div>

        {/* Reservation rows */}
        <Card className={`overflow-hidden ${past && !today ? 'opacity-70' : ''}`}>
          <div className="divide-y divide-gray-100">
            {items.map((res) => (
              <ReservationRow key={res.id} reservation={res} showActions={showActions} />
            ))}
          </div>
        </Card>
      </div>
    );
  };

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-[#08263e]"></div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50 pb-20 md:pb-8" data-testid="reservations-page">
      {/* Header */}
      <header className="bg-[#08263e] text-white px-4 py-3 md:px-8">
        <div className="max-w-3xl mx-auto flex items-center justify-between">
          <div className="flex items-center gap-4">
            <Button variant="ghost" className="text-white hover:bg-white/20 p-2" onClick={() => navigate('/dashboard')}>
              <ArrowLeft className="w-5 h-5" />
            </Button>
            <Link to="/dashboard"><img src="/cl-logo.png" alt="Cebuana Lhuillier" className="h-8 w-auto brightness-0 invert cursor-pointer" /></Link>
            <div className="hidden md:block">
              <p className="text-xs text-white/70">My Reservations ({reservations.length})</p>
            </div>
          </div>
          <Button className="bg-[#ec474e] text-white hover:bg-[#d63a41] rounded-full" onClick={() => navigate('/book')} data-testid="new-booking-btn">
            <Plus className="w-4 h-4 mr-2" /> New Booking
          </Button>
        </div>
      </header>

      <main className="max-w-3xl mx-auto px-4 py-6 md:px-8">
        {/* Quick summary */}
        {activeReservations.length > 0 && (
          <div className="grid grid-cols-3 gap-3 mb-6">
            <Card className="bg-[#08263e] text-white border-none">
              <CardContent className="p-3 text-center">
                <p className="text-2xl font-bold">{todayCount}</p>
                <p className="text-[10px] text-white/60 uppercase tracking-wider">Today</p>
              </CardContent>
            </Card>
            <Card className="border-emerald-200 bg-emerald-50/50">
              <CardContent className="p-3 text-center">
                <p className="text-2xl font-bold text-emerald-700">{activeReservations.filter(r => r.status === 'confirmed').length}</p>
                <p className="text-[10px] text-emerald-600 uppercase tracking-wider">Confirmed</p>
              </CardContent>
            </Card>
            <Card className="border-amber-200 bg-amber-50/50">
              <CardContent className="p-3 text-center">
                <p className="text-2xl font-bold text-amber-700">{activeReservations.filter(r => r.status === 'pending').length}</p>
                <p className="text-[10px] text-amber-600 uppercase tracking-wider">Reserved</p>
              </CardContent>
            </Card>
          </div>
        )}

        <Tabs defaultValue="active" className="w-full">
          <TabsList className="grid w-full grid-cols-2 mb-6">
            <TabsTrigger value="active" data-testid="active-tab">
              Active ({activeReservations.length})
            </TabsTrigger>
            <TabsTrigger value="past" data-testid="past-tab">
              History ({pastReservations.length})
            </TabsTrigger>
          </TabsList>

          <TabsContent value="active">
            {activeGroups.length === 0 ? (
              <Card className="border-dashed border-2 border-gray-200">
                <CardContent className="p-12 text-center">
                  <Calendar className="w-16 h-16 mx-auto text-gray-300 mb-4" />
                  <h3 className="text-lg font-semibold text-gray-600 mb-2">No Active Reservations</h3>
                  <p className="text-gray-500 mb-4">Book a parking spot to get started</p>
                  <Button className="bg-[#08263e] hover:bg-[#051a2d] text-white rounded-full" onClick={() => navigate('/book')}>
                    <Plus className="w-4 h-4 mr-2" /> Book Now
                  </Button>
                </CardContent>
              </Card>
            ) : (
              <div>
                {activeGroups.map(group => (
                  <DateGroup key={group.date} dateStr={group.date} items={group.items} showActions={true} />
                ))}
              </div>
            )}
          </TabsContent>

          <TabsContent value="past">
            {/* Booking Stats Summary */}
            {stats && (
              <div className="grid grid-cols-5 gap-2 mb-6" data-testid="booking-stats">
                <Card className="bg-[#08263e] text-white border-none">
                  <CardContent className="p-2.5 text-center">
                    <p className="text-xl font-bold">{stats.total}</p>
                    <p className="text-[9px] text-white/60 uppercase tracking-wider">Total</p>
                  </CardContent>
                </Card>
                <Card className="border-emerald-200 bg-emerald-50/50">
                  <CardContent className="p-2.5 text-center">
                    <p className="text-xl font-bold text-emerald-700">{stats.confirmed}</p>
                    <p className="text-[9px] text-emerald-600 uppercase tracking-wider">Confirmed</p>
                  </CardContent>
                </Card>
                <Card className="border-blue-200 bg-blue-50/50">
                  <CardContent className="p-2.5 text-center">
                    <p className="text-xl font-bold text-blue-700">{stats.completed}</p>
                    <p className="text-[9px] text-blue-600 uppercase tracking-wider">Completed</p>
                  </CardContent>
                </Card>
                <Card className="border-gray-200 bg-gray-50/50">
                  <CardContent className="p-2.5 text-center">
                    <p className="text-xl font-bold text-gray-600">{stats.cancelled}</p>
                    <p className="text-[9px] text-gray-500 uppercase tracking-wider">Cancelled</p>
                  </CardContent>
                </Card>
                <Card className="border-red-200 bg-red-50/50">
                  <CardContent className="p-2.5 text-center">
                    <p className="text-xl font-bold text-red-600">{stats.no_show}</p>
                    <p className="text-[9px] text-red-500 uppercase tracking-wider">No-Show</p>
                  </CardContent>
                </Card>
              </div>
            )}

            {pastGroups.length === 0 ? (
              <Card className="border-dashed border-2 border-gray-200">
                <CardContent className="p-12 text-center">
                  <Clock className="w-16 h-16 mx-auto text-gray-300 mb-4" />
                  <h3 className="text-lg font-semibold text-gray-600 mb-2">No Past Reservations</h3>
                  <p className="text-gray-500">Your completed and cancelled bookings will appear here</p>
                </CardContent>
              </Card>
            ) : (
              <div>
                {pastGroups.map(group => (
                  <DateGroup key={group.date} dateStr={group.date} items={group.items} showActions={false} />
                ))}
              </div>
            )}
          </TabsContent>
        </Tabs>
      </main>

      {/* QR Code Dialog */}
      <Dialog open={qrDialogOpen} onOpenChange={setQrDialogOpen}>
        <DialogContent className="max-w-sm">
          <DialogHeader>
            <DialogTitle className="text-center">Parking QR Code</DialogTitle>
          </DialogHeader>
          {selectedRes && (
            <div className="space-y-4" data-testid="qr-dialog">
              <div className="bg-white rounded-xl p-4 flex items-center justify-center">
                {qrLoading ? (
                  <div className="w-48 h-48 flex items-center justify-center">
                    <div className="animate-spin rounded-full h-8 w-8 border-t-2 border-b-2 border-[#08263e]"></div>
                  </div>
                ) : qrData ? (
                  <img src={qrData} alt="QR Code" className="w-48 h-48" data-testid="qr-code-image" />
                ) : (
                  <div className="w-48 h-48 flex items-center justify-center text-gray-400">
                    <QrCode className="w-16 h-16" />
                  </div>
                )}
              </div>
              <div className="bg-gray-50 rounded-lg p-3 space-y-1 text-sm text-center">
                <p className="font-semibold text-[#08263e]">{selectedRes.building_name}</p>
                <p className="text-gray-600">{selectedRes.floor_label} - Slot {selectedRes.slot_label}</p>
                <p className="text-gray-600">{format(parseISO(selectedRes.date), 'MMM dd, yyyy')}</p>
                <p className="text-gray-600">{selectedRes.start_time} - {selectedRes.end_time}</p>
                <p className="font-mono font-bold text-[#08263e]">{selectedRes.vehicle_plate}</p>
              </div>
              <p className="text-xs text-center text-gray-400">Show this QR code to the parking attendant</p>
            </div>
          )}
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

export default ReservationsPage;
