import React, { useState, useEffect, useRef } from 'react';
import { useNavigate, Link } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';
import { reservationsAPI } from '../../services/api';
import { Button } from '../../components/ui/button';
import { Card, CardContent } from '../../components/ui/card';
import { Badge } from '../../components/ui/badge';
import { Calendar } from '../../components/ui/calendar';
import { Popover, PopoverContent, PopoverTrigger } from '../../components/ui/popover';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '../../components/ui/dialog';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../../components/ui/select';
import { Input } from '../../components/ui/input';
import { toast } from 'sonner';
import { 
  LogOut, Calendar as CalendarIcon, Car, Building2, 
  Clock, User, CheckCircle2, MapPin, ChevronLeft, ChevronRight,
  AlertOctagon, XCircle, Filter, QrCode
} from 'lucide-react';
import { format, addDays, subDays, isAfter, startOfDay } from 'date-fns';
import { cn } from '../../lib/utils';

const AttendantDashboard = () => {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const [reservations, setReservations] = useState([]);
  const [buildings, setBuildings] = useState([]);
  const [loading, setLoading] = useState(true);
  const [selectedDate, setSelectedDate] = useState(new Date());
  const [selectedBuilding, setSelectedBuilding] = useState('all');
  const [confirmDialogOpen, setConfirmDialogOpen] = useState(false);
  const [noShowDialogOpen, setNoShowDialogOpen] = useState(false);
  const [selectedReservation, setSelectedReservation] = useState(null);
  const [submitting, setSubmitting] = useState(false);
  const [qrScanOpen, setQrScanOpen] = useState(false);
  const [scanPhase, setScanPhase] = useState('scanning'); // scanning | processing | success | error
  const [scanMode, setScanMode] = useState('camera'); // camera | manual
  const [scanResult, setScanResult] = useState(null);
  const [scanError, setScanError] = useState('');
  const [qrToken, setQrToken] = useState('');
  const scannerRef = useRef(null);
  const SCANNER_DIV_ID = 'qr-scanner-video';

  useEffect(() => {
    reservationsAPI.getAttendantBuildings()
      .then(res => setBuildings(res.data))
      .catch(() => {});
  }, []);

  useEffect(() => { fetchReservations(); }, [selectedDate, selectedBuilding]);

  const fetchReservations = async () => {
    setLoading(true);
    try {
      const dateStr = format(selectedDate, 'yyyy-MM-dd');
      const buildingId = selectedBuilding === 'all' ? undefined : selectedBuilding;
      const response = await reservationsAPI.getDailyReservations(dateStr, buildingId);
      setReservations(response.data);
    } catch {
      toast.error('Failed to load reservations');
    } finally {
      setLoading(false);
    }
  };

  const handleLogout = () => { logout(); navigate('/login'); };
  const goToPreviousDay = () => setSelectedDate(subDays(selectedDate, 1));
  const goToNextDay = () => setSelectedDate(addDays(selectedDate, 1));

  // ── QR Scanner ──────────────────────────────────────────────────────────
  const stopScanner = async () => {
    if (scannerRef.current) {
      try {
        if (scannerRef.current.isScanning) await scannerRef.current.stop();
        scannerRef.current.clear();
      } catch {}
      scannerRef.current = null;
    }
  };

  const startScanner = async () => {
    try {
      const { Html5Qrcode } = await import('html5-qrcode');
      const el = document.getElementById(SCANNER_DIV_ID);
      if (!el) return;
      scannerRef.current = new Html5Qrcode(SCANNER_DIV_ID);
      await scannerRef.current.start(
        { facingMode: 'environment' },
        { fps: 12, qrbox: { width: 220, height: 220 }, aspectRatio: 1 },
        (decodedText) => handleQRDetected(decodedText),
        () => {}
      );
    } catch (e) {
      setScanError('Camera access denied or unavailable. Use manual entry.');
      setScanMode('manual');
    }
  };

  const handleQRDetected = async (decodedText) => {
    await stopScanner();
    setScanPhase('processing');
    try {
      // QR content: https://...app.../scan/{token}
      const parts = decodedText.split('/scan/');
      const token = parts.length > 1 ? parts[parts.length - 1].trim() : decodedText.trim();
      const scanRes = await reservationsAPI.scanQR(token);
      const reservation = scanRes.data;
      if (reservation.status !== 'confirmed') {
        await reservationsAPI.confirmReservation(reservation.reservation_id);
      }
      setScanResult({ ...reservation, alreadyConfirmed: reservation.status === 'confirmed' });
      setScanPhase('success');
      fetchReservations();
    } catch (e) {
      setScanError(e.response?.data?.detail || 'QR code not recognised. Please try again.');
      setScanPhase('error');
    }
  };

  const handleManualScan = async (e) => {
    e.preventDefault();
    const token = qrToken.trim();
    if (!token) { toast.error('Please enter a QR token'); return; }
    await handleQRDetected(token);
  };

  const closeScanDialog = async () => {
    await stopScanner();
    setQrScanOpen(false);
  };

  const resetScanner = () => {
    setScanPhase('scanning');
    setScanMode('camera');
    setScanResult(null);
    setScanError('');
    setQrToken('');
  };

  // Start/stop scanner based on dialog state
  useEffect(() => {
    if (qrScanOpen && scanPhase === 'scanning' && scanMode === 'camera') {
      const t = setTimeout(startScanner, 350);
      return () => clearTimeout(t);
    }
    if (!qrScanOpen) stopScanner();
  }, [qrScanOpen, scanPhase, scanMode]); // eslint-disable-line react-hooks/exhaustive-deps

  const openScanDialog = () => { resetScanner(); setQrScanOpen(true); };
  // ────────────────────────────────────────────────────────────────────────

  const handleConfirmReservation = async () => {
    if (!selectedReservation) return;
    setSubmitting(true);
    try {
      await reservationsAPI.confirm(selectedReservation.id, null);
      toast.success('Reservation confirmed');
      setConfirmDialogOpen(false);
      setSelectedReservation(null);
      fetchReservations();
    } catch {
      toast.error('Failed to confirm reservation');
    } finally {
      setSubmitting(false);
    }
  };

  const handleReportNoShow = async () => {
    if (!selectedReservation) return;
    setSubmitting(true);
    try {
      await reservationsAPI.reportNoShow(selectedReservation.id);
      toast.success('No-show reported');
      setNoShowDialogOpen(false);
      setSelectedReservation(null);
      fetchReservations();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to report no-show');
    } finally {
      setSubmitting(false);
    }
  };

  const pendingCount = reservations.filter(r => r.status === 'pending').length;
  const confirmedCount = reservations.filter(r => r.status === 'confirmed').length;
  const noShowCount = reservations.filter(r => r.status === 'no_show' || r.no_show_reported).length;

  const getStatusConfig = (status, noShow) => {
    if (noShow || status === 'no_show') return { color: 'bg-red-100 text-red-800 border-red-200', icon: XCircle, label: 'No Show' };
    switch (status) {
      case 'confirmed': return { color: 'bg-green-100 text-green-800 border-green-200', icon: CheckCircle2, label: 'Confirmed' };
      case 'pending': return { color: 'bg-yellow-100 text-yellow-800 border-yellow-200', icon: Clock, label: 'Reserved' };
      case 'cancelled': return { color: 'bg-gray-100 text-gray-500 border-gray-200', icon: XCircle, label: 'Cancelled' };
      default: return { color: 'bg-gray-100 text-gray-800 border-gray-200', icon: Clock, label: status };
    }
  };

  return (
    <div className="min-h-screen bg-gray-50" data-testid="attendant-dashboard">
      <header className="bg-[#08263e] text-white px-4 py-3 md:px-8">
        <div className="max-w-4xl mx-auto flex items-center justify-between">
          <div className="flex items-center gap-3">
            <Link to="/attendant"><img src="/cl-logo.png" alt="Cebuana Lhuillier" className="h-8 w-auto brightness-0 invert cursor-pointer" /></Link>
            <div className="hidden md:block">
              <p className="text-xs text-white/70">Attendant: {user?.first_name} {user?.last_name}</p>
            </div>
          </div>
          <div className="flex items-center gap-2">
            <Button variant="ghost" size="sm" className="text-white hover:bg-white/20" onClick={openScanDialog} data-testid="scan-qr-btn">
              <QrCode className="w-5 h-5 mr-1" />
              <span className="text-sm hidden sm:inline">Scan QR</span>
            </Button>
            <Button variant="ghost" className="text-white hover:bg-white/20" onClick={handleLogout} data-testid="attendant-logout-btn">
              <LogOut className="w-5 h-5" />
            </Button>
          </div>
        </div>
      </header>

      <main className="max-w-4xl mx-auto px-4 py-6 md:px-8 space-y-6">
        {/* Date Selector + Building Filter */}
        <Card>
          <CardContent className="p-4 space-y-3">
            <div className="flex items-center justify-between">
              <Button variant="ghost" size="sm" onClick={goToPreviousDay} data-testid="prev-day-btn">
                <ChevronLeft className="w-5 h-5" />
              </Button>
              <Popover>
                <PopoverTrigger asChild>
                  <Button variant="outline" className="min-w-[200px]" data-testid="date-selector">
                    <CalendarIcon className="w-4 h-4 mr-2" />
                    {format(selectedDate, 'EEEE, MMMM dd, yyyy')}
                  </Button>
                </PopoverTrigger>
                <PopoverContent className="w-auto p-0" align="center">
                  <Calendar mode="single" selected={selectedDate} onSelect={(date) => date && setSelectedDate(date)} initialFocus />
                </PopoverContent>
              </Popover>
              {format(selectedDate, 'yyyy-MM-dd') !== format(new Date(), 'yyyy-MM-dd') && (
                <Button variant="outline" size="sm" className="text-xs font-medium" onClick={() => setSelectedDate(new Date())} data-testid="go-to-today-btn">
                  Today
                </Button>
              )}
              <Button variant="ghost" size="sm" onClick={goToNextDay} data-testid="next-day-btn">
                <ChevronRight className="w-5 h-5" />
              </Button>
            </div>
            {buildings.length > 1 && (
              <div className="flex items-center gap-2">
                <Filter className="w-4 h-4 text-gray-400 shrink-0" />
                <Select value={selectedBuilding} onValueChange={setSelectedBuilding}>
                  <SelectTrigger className="flex-1" data-testid="building-filter-select">
                    <SelectValue placeholder="Filter by Building" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="all">All Buildings</SelectItem>
                    {buildings.map(b => (
                      <SelectItem key={b.id} value={b.id}>{b.name}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            )}
          </CardContent>
        </Card>

        {/* Stats */}
        <div className="grid grid-cols-3 gap-4">
          <Card className="bg-yellow-50 border-yellow-200">
            <CardContent className="p-4 text-center">
              <p className="text-yellow-700 text-sm">Reserved</p>
              <p className="text-3xl font-bold text-yellow-800" data-testid="pending-count">{pendingCount}</p>
            </CardContent>
          </Card>
          <Card className="bg-green-50 border-green-200">
            <CardContent className="p-4 text-center">
              <p className="text-green-700 text-sm">Confirmed</p>
              <p className="text-3xl font-bold text-green-800" data-testid="confirmed-count">{confirmedCount}</p>
            </CardContent>
          </Card>
          <Card className="bg-red-50 border-red-200">
            <CardContent className="p-4 text-center">
              <p className="text-red-700 text-sm">No Shows</p>
              <p className="text-3xl font-bold text-red-800" data-testid="no-show-count">{noShowCount}</p>
            </CardContent>
          </Card>
        </div>

        {/* Reservations */}
        <div className="space-y-4">
          <h2 className="text-lg font-semibold text-gray-800">
            Reservations for {format(selectedDate, 'MMM dd, yyyy')}
            {selectedBuilding !== 'all' && (
              <span className="text-sm font-normal text-gray-500 ml-2">
                - {buildings.find(b => b.id === selectedBuilding)?.name}
              </span>
            )}
          </h2>
          
          {loading ? (
            <div className="flex items-center justify-center py-12">
              <div className="animate-spin rounded-full h-8 w-8 border-t-2 border-b-2 border-[#08263e]"></div>
            </div>
          ) : reservations.length === 0 ? (
            <Card className="border-dashed border-2 border-gray-200">
              <CardContent className="p-8 text-center">
                <CalendarIcon className="w-12 h-12 mx-auto text-gray-300 mb-3" />
                <p className="text-gray-500">No reservations for this date</p>
              </CardContent>
            </Card>
          ) : (
            <div className="space-y-3">
              {reservations.map((reservation) => {
                const statusConfig = getStatusConfig(reservation.status, reservation.no_show_reported);
                const StatusIcon = statusConfig.icon;
                const isFutureDate = isAfter(startOfDay(selectedDate), startOfDay(new Date()));
                const canConfirm = reservation.status === 'pending' && !isFutureDate;
                // BUG FIX TCID-PARKING-ATTENDANT-001: Don't allow no-show for confirmed reservations
                const canReportNoShow = reservation.status === 'pending' && !reservation.no_show_reported && !isFutureDate;
                
                return (
                  <Card key={reservation.id} className={cn("overflow-hidden transition-all", canConfirm && "ring-2 ring-yellow-300")} data-testid={`reservation-${reservation.id}`}>
                    <CardContent className="p-4">
                      <div className="flex items-start justify-between gap-4">
                        <div className="flex-1 space-y-2">
                          <Badge className={cn("border", statusConfig.color)}>
                            <StatusIcon className="w-3 h-3 mr-1" />
                            {statusConfig.label}
                          </Badge>
                          <div className="space-y-1">
                            <div className="flex items-center gap-2 text-sm">
                              <User className="w-4 h-4 text-gray-400" />
                              <span className="font-medium">{reservation.user_name}</span>
                            </div>
                            <div className="flex items-center gap-2 text-sm text-gray-600">
                              <Car className="w-4 h-4 text-gray-400" />
                              <span className="font-mono font-bold">{reservation.vehicle_plate}</span>
                            </div>
                            <div className="flex items-center gap-2 text-sm text-gray-600">
                              <Building2 className="w-4 h-4 text-gray-400" />
                              <span>{reservation.building_name}</span>
                            </div>
                            <div className="flex items-center gap-2 text-sm text-gray-600">
                              <MapPin className="w-4 h-4 text-gray-400" />
                              <span>{reservation.floor_label} - Slot <span className="font-mono font-bold">{reservation.slot_label}</span></span>
                            </div>
                            <div className="flex items-center gap-2 text-sm text-gray-600">
                              <Clock className="w-4 h-4 text-gray-400" />
                              <span>{reservation.start_time} - {reservation.end_time}</span>
                            </div>
                          </div>
                        </div>
                        <div className="flex flex-col gap-2 shrink-0">
                          {canConfirm && (
                            <Button className="bg-[#08263e] hover:bg-[#051a2d] text-white" onClick={() => { setSelectedReservation(reservation); setConfirmDialogOpen(true); }} data-testid={`confirm-btn-${reservation.id}`}>
                              <CheckCircle2 className="w-4 h-4 mr-2" /> Confirm
                            </Button>
                          )}
                          {canReportNoShow && (
                            <Button variant="outline" className="text-red-600 border-red-200 hover:bg-red-50" onClick={() => { setSelectedReservation(reservation); setNoShowDialogOpen(true); }} data-testid={`no-show-btn-${reservation.id}`}>
                              <AlertOctagon className="w-4 h-4 mr-2" /> No Show
                            </Button>
                          )}
                        </div>
                      </div>
                    </CardContent>
                  </Card>
                );
              })}
            </div>
          )}
        </div>
      </main>

      {/* QR Scanner Dialog */}
      <Dialog open={qrScanOpen} onOpenChange={(open) => { if (!open) closeScanDialog(); }}>
        <DialogContent className="max-w-sm p-0 overflow-hidden rounded-xl">
          <DialogHeader className="px-5 pt-5 pb-3">
            <DialogTitle className="flex items-center gap-2 text-[#08263e]">
              <QrCode className="w-5 h-5" /> Scan QR Code
            </DialogTitle>
          </DialogHeader>

          {/* ── SCANNING PHASE ── */}
          {scanPhase === 'scanning' && (
            <div className="px-5 pb-5 space-y-3">
              {scanMode === 'camera' ? (
                <>
                  <p className="text-sm text-gray-500 text-center">Point the camera at the parker's QR code</p>
                  {/* Camera viewport */}
                  <div className="relative w-full rounded-lg overflow-hidden bg-black" style={{ aspectRatio: '1/1' }}>
                    <div id={SCANNER_DIV_ID} className="w-full h-full" />
                    {/* Scanning animation overlay */}
                    <div className="absolute inset-0 pointer-events-none">
                      <div className="absolute inset-0 flex items-center justify-center">
                        <div className="relative w-[220px] h-[220px]">
                          {/* Corner brackets */}
                          <div className="absolute top-0 left-0 w-8 h-8 border-t-[3px] border-l-[3px] border-[#4ade80] rounded-tl" />
                          <div className="absolute top-0 right-0 w-8 h-8 border-t-[3px] border-r-[3px] border-[#4ade80] rounded-tr" />
                          <div className="absolute bottom-0 left-0 w-8 h-8 border-b-[3px] border-l-[3px] border-[#4ade80] rounded-bl" />
                          <div className="absolute bottom-0 right-0 w-8 h-8 border-b-[3px] border-r-[3px] border-[#4ade80] rounded-br" />
                          {/* Scan line */}
                          <div className="absolute left-0 right-0 h-0.5 bg-[#4ade80] opacity-80 animate-[scan-line_2s_linear_infinite]" style={{ top: '50%' }} />
                        </div>
                      </div>
                    </div>
                  </div>
                  <p className="text-center text-xs text-gray-400">
                    Camera not working?{' '}
                    <button className="text-[#08263e] underline font-medium" onClick={() => setScanMode('manual')}>
                      Enter token manually
                    </button>
                  </p>
                </>
              ) : (
                /* Manual fallback */
                <form onSubmit={handleManualScan} className="space-y-3">
                  <p className="text-sm text-gray-500">Enter the QR token shown on the parker's reservation screen.</p>
                  <Input
                    placeholder="Paste QR token here"
                    value={qrToken}
                    onChange={e => setQrToken(e.target.value)}
                    autoFocus
                    data-testid="qr-token-input"
                  />
                  <div className="flex gap-2">
                    <Button type="button" variant="outline" className="flex-1" onClick={() => setScanMode('camera')}>
                      Use Camera
                    </Button>
                    <Button type="submit" className="flex-1 bg-[#08263e] hover:bg-[#051a2d] text-white" data-testid="qr-scan-submit-btn">
                      Look Up
                    </Button>
                  </div>
                </form>
              )}
            </div>
          )}

          {/* ── PROCESSING PHASE ── */}
          {scanPhase === 'processing' && (
            <div className="px-5 pb-8 flex flex-col items-center gap-4 pt-2">
              <div className="w-14 h-14 rounded-full bg-blue-50 flex items-center justify-center animate-pulse">
                <QrCode className="w-8 h-8 text-blue-500" />
              </div>
              <p className="text-sm font-medium text-gray-700">Looking up reservation…</p>
            </div>
          )}

          {/* ── SUCCESS PHASE ── */}
          {scanPhase === 'success' && scanResult && (
            <div className="px-5 pb-5 space-y-4">
              <div className="flex flex-col items-center gap-2 pt-1">
                <div className="w-14 h-14 bg-green-100 rounded-full flex items-center justify-center">
                  <CheckCircle2 className="w-9 h-9 text-green-600" />
                </div>
                <h3 className="text-base font-bold text-gray-900">
                  {scanResult.alreadyConfirmed ? 'Already Confirmed' : 'Reservation Confirmed!'}
                </h3>
                <p className="text-xs text-gray-400">
                  {scanResult.alreadyConfirmed ? 'This reservation was already checked in.' : 'Parker has been successfully checked in.'}
                </p>
              </div>
              <div className="bg-gray-50 border border-gray-100 rounded-lg p-3 space-y-2 text-sm" data-testid="scan-result-card">
                <div className="flex items-center gap-2 text-gray-700">
                  <User className="w-4 h-4 text-gray-400 shrink-0" />
                  <span className="font-medium">{scanResult.user_name || scanResult.user_email || '—'}</span>
                </div>
                {scanResult.vehicle_plate && (
                  <div className="flex items-center gap-2 text-gray-700">
                    <Car className="w-4 h-4 text-gray-400 shrink-0" />
                    <span>{scanResult.vehicle_plate}</span>
                  </div>
                )}
                <div className="flex items-center gap-2 text-gray-700">
                  <MapPin className="w-4 h-4 text-gray-400 shrink-0" />
                  <span>{[scanResult.building_name, scanResult.floor_label, scanResult.slot_label].filter(Boolean).join(' • ')}</span>
                </div>
                <div className="flex items-center gap-2 text-gray-700">
                  <Clock className="w-4 h-4 text-gray-400 shrink-0" />
                  <span>{scanResult.date} · {scanResult.start_time}–{scanResult.end_time}</span>
                </div>
              </div>
              <Button className="w-full bg-[#08263e] hover:bg-[#051a2d] text-white" onClick={closeScanDialog} data-testid="scan-done-btn">
                Done
              </Button>
            </div>
          )}

          {/* ── ERROR PHASE ── */}
          {scanPhase === 'error' && (
            <div className="px-5 pb-5 space-y-4 text-center">
              <div className="w-14 h-14 bg-red-100 rounded-full flex items-center justify-center mx-auto mt-1">
                <XCircle className="w-9 h-9 text-red-500" />
              </div>
              <div>
                <h3 className="text-sm font-bold text-gray-900">Scan Failed</h3>
                <p className="text-xs text-gray-500 mt-1">{scanError}</p>
              </div>
              <div className="flex gap-2">
                <Button variant="outline" className="flex-1" onClick={() => { resetScanner(); }} data-testid="scan-retry-btn">
                  Try Again
                </Button>
                <Button variant="outline" className="flex-1" onClick={() => { setScanPhase('scanning'); setScanMode('manual'); setScanError(''); }} data-testid="scan-manual-fallback-btn">
                  Enter Manually
                </Button>
              </div>
            </div>
          )}
        </DialogContent>
      </Dialog>

      {/* Scan line animation */}
      <style>{`
        @keyframes scan-line {
          0%   { top: 5%; }
          50%  { top: 95%; }
          100% { top: 5%; }
        }
        #${SCANNER_DIV_ID} video { width: 100% !important; height: 100% !important; object-fit: cover; }
        #${SCANNER_DIV_ID} img { display: none !important; }
      `}</style>

      {/* Confirm Dialog */}
      <Dialog open={confirmDialogOpen} onOpenChange={setConfirmDialogOpen}>
        <DialogContent>
          <DialogHeader><DialogTitle>Confirm Reservation</DialogTitle></DialogHeader>
          {selectedReservation && (
            <div className="space-y-4 mt-4">
              <div className="bg-gray-50 rounded-lg p-4 space-y-2">
                <p className="font-medium">{selectedReservation.user_name}</p>
                <p className="text-sm text-gray-600"><span className="font-mono font-bold">{selectedReservation.vehicle_plate}</span></p>
                <p className="text-sm text-gray-600">{selectedReservation.building_name} - {selectedReservation.floor_label} - Slot {selectedReservation.slot_label}</p>
              </div>
              <div className="flex gap-3">
                <Button variant="outline" className="flex-1" onClick={() => setConfirmDialogOpen(false)}>Cancel</Button>
                <Button className="flex-1 bg-[#08263e] hover:bg-[#051a2d] text-white" onClick={handleConfirmReservation} disabled={submitting} data-testid="confirm-reservation-btn">
                  {submitting ? 'Confirming...' : 'Confirm Arrival'}
                </Button>
              </div>
            </div>
          )}
        </DialogContent>
      </Dialog>

      {/* No-Show Dialog */}
      <Dialog open={noShowDialogOpen} onOpenChange={setNoShowDialogOpen}>
        <DialogContent>
          <DialogHeader><DialogTitle>Report No-Show</DialogTitle></DialogHeader>
          {selectedReservation && (
            <div className="space-y-4 mt-4">
              <div className="bg-red-50 border border-red-200 rounded-lg p-4 space-y-2">
                <p className="text-sm text-red-800 font-medium">Are you sure you want to report this reservation as a no-show?</p>
                <div className="text-sm text-gray-700 space-y-1">
                  <p><strong>{selectedReservation.user_name}</strong></p>
                  <p className="font-mono">{selectedReservation.vehicle_plate}</p>
                  <p>{selectedReservation.building_name} - Slot {selectedReservation.slot_label}</p>
                  <p>{selectedReservation.start_time} - {selectedReservation.end_time}</p>
                </div>
              </div>
              <div className="flex gap-3">
                <Button variant="outline" className="flex-1" onClick={() => setNoShowDialogOpen(false)}>Cancel</Button>
                <Button className="flex-1 bg-red-600 hover:bg-red-700 text-white" onClick={handleReportNoShow} disabled={submitting} data-testid="confirm-no-show-btn">
                  {submitting ? 'Reporting...' : 'Report No-Show'}
                </Button>
              </div>
            </div>
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
};

export default AttendantDashboard;
