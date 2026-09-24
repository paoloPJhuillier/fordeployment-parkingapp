import React, { useState, useEffect, useCallback } from 'react';
import { useNavigate, useSearchParams, Link, useLocation } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { buildingsAPI, slotsAPI, vehiclesAPI, reservationsAPI, configAPI, zonesAPI, authAPI, waitlistAPI } from '../services/api';
import { Button } from '../components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../components/ui/select';
import { Calendar } from '../components/ui/calendar';
import { Label } from '../components/ui/label';
import { Input } from '../components/ui/input';
import { Badge } from '../components/ui/badge';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '../components/ui/dialog';
import { toast } from 'sonner';
import { 
  ArrowLeft, Calendar as CalendarIcon, Car, Building2, 
  MapPin, Clock, Check, Home, Plus, User, AlertTriangle, Image, Shield, ListOrdered, Bell, X
} from 'lucide-react';
import { format, addDays, isToday, isBefore, startOfDay } from 'date-fns';
import { cn } from '../lib/utils';
import { HelpTip } from '../components/ui/help-tip';
import { Tooltip, TooltipTrigger, TooltipContent, TooltipProvider } from '../components/ui/tooltip';

const API_URL = process.env.REACT_APP_BACKEND_URL || '';
const HOURS = Array.from({ length: 24 }, (_, i) => i); // 0 (12AM) to 23 (11PM)

const formatHour = (h) => {
  if (h === 0 || h === 24) return '12 AM';
  if (h === 12) return '12 PM';
  if (h > 12) return `${h - 12} PM`;
  return `${h} AM`;
};

// Helper to parse time string "HH:MM" to hour number
const parseTimeToHour = (timeStr) => {
  if (!timeStr) return null;
  const [h] = timeStr.split(':').map(Number);
  return isNaN(h) ? null : h;
};

const BookingPage = () => {
  const { user } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [searchParams] = useSearchParams();
  const preselectedBuilding = searchParams.get('building');

  const [buildings, setBuildings] = useState([]);
  const [vehicles, setVehicles] = useState([]);
  const [slots, setSlots] = useState([]);
  const [config, setConfig] = useState(null);
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const [allowedBuildingIds, setAllowedBuildingIds] = useState(null);
  const [freshUser, setFreshUser] = useState(null);

  // Waitlist state
  const [waitlistStatus, setWaitlistStatus] = useState(null);
  const [waitlistCount, setWaitlistCount] = useState(0);
  const [joiningWaitlist, setJoiningWaitlist] = useState(false);

  // Form state
  const [selectedBuilding, setSelectedBuilding] = useState(preselectedBuilding || '');
  const [selectedFloor, setSelectedFloor] = useState('');
  const [selectedDates, setSelectedDates] = useState([]);
  const [selectedSlot, setSelectedSlot] = useState(null);
  const [selectedHours, setSelectedHours] = useState([]);
  const [selectedVehicle, setSelectedVehicle] = useState('');
  const [reason, setReason] = useState('');
  const [vehicleDialogOpen, setVehicleDialogOpen] = useState(false);
  const [submittingVehicle, setSubmittingVehicle] = useState(false);
  const [newVehicle, setNewVehicle] = useState({ plate_number: '', make: '', model: '', color: '' });
  const [layoutImageOpen, setLayoutImageOpen] = useState(false);

  const userMainBuilding = freshUser?.main_building || user?.main_building;
  const userTags = freshUser?.tags || user?.tags || [];
  const isVip = userTags.includes('vip') || userTags.includes('group_head');
  const isExternalBooking = userMainBuilding && selectedBuilding && selectedBuilding !== userMainBuilding;

  const currentBuilding = buildings.find(b => b.id === selectedBuilding);
  const currentFloor = currentBuilding?.floors?.find(f => f.id === selectedFloor);
  const selectedSlotData = slots.find(s => s.id === selectedSlot);

  const visibleBuildings = allowedBuildingIds
    ? buildings.filter(b => allowedBuildingIds.has(b.id))
    : buildings;

  // Compute time from selected hours
  const startTime = selectedHours.length > 0 ? `${String(Math.min(...selectedHours)).padStart(2, '0')}:00` : '08:00';
  const endTime = selectedHours.length > 0 ? `${String(Math.max(...selectedHours) + 1).padStart(2, '0')}:00` : '18:00';

  // Compute hours that are GENUINELY bookable for a slot:
  // not booked AND not in the past (only for today) AND inside building hours.
  // Backend's slot.available_hours = 24 - booked_hours, which over-counts because
  // it doesn't subtract Past or Closed hours; user-facing labels should use this
  // helper so "Xh free" matches what they'll actually see in the hours grid.
  const getTrulyFreeHourCount = (slot) => {
    if (!slot?.timeline) return slot?.available_hours ?? 0;
    const now = new Date();
    const currentHour = now.getHours();
    const isAnyDateToday = selectedDates.some(d => isToday(d));
    const configStartHour = parseTimeToHour(config?.default_start_time) ?? 0;
    const configEndHour = parseTimeToHour(config?.default_end_time) ?? 24;
    return slot.timeline.reduce((n, t) => {
      const isPast = isAnyDateToday && t.hour <= currentHour;
      const isClosed = t.hour < configStartHour || t.hour >= configEndHour;
      return n + (!t.booked && !isPast && !isClosed ? 1 : 0);
    }, 0);
  };

  // Slot is effectively bookable only if backend says so AND there's at least
  // one truly-free hour. Drives both the slot tile (disabled state) and the
  // "All slots fully booked / Join Waitlist" banner.
  const isSlotBookable = (slot) => slot.is_available && getTrulyFreeHourCount(slot) > 0;
  const allSlotsFullyBooked = slots.length > 0 && slots.every(s => !isSlotBookable(s));
  const waitlistEnabled = config?.waitlist_enabled;

  useEffect(() => { fetchInitialData(); }, []);

  useEffect(() => {
    if (selectedBuilding && selectedDates.length > 0) {
      fetchSlots();
      fetchConfig();
    }
  }, [selectedBuilding, selectedDates, selectedFloor]);

  useEffect(() => {
    if (selectedBuilding && selectedDates.length > 0 && config?.waitlist_enabled) {
      fetchWaitlistInfo();
    }
  }, [selectedBuilding, selectedDates, config]);

  const fetchInitialData = async (retryCount = 0) => {
    try {
      const [buildingsRes, vehiclesRes, zoneBuildingsRes, meRes] = await Promise.all([
        buildingsAPI.getAll(),
        vehiclesAPI.getAll(),
        zonesAPI.getUserBuildings().catch(() => ({ data: { building_ids: [], zones: [] } })),
        authAPI.getMe().catch(() => ({ data: null }))
      ]);
      const allBuildings = buildingsRes.data;
      const zoneData = zoneBuildingsRes.data;
      const hasZones = (zoneData.zones || []).length > 0;
      const freshProfile = meRes.data;
      if (freshProfile) setFreshUser(freshProfile);
      if (hasZones) {
        const zoneBuildingIds = zoneData.building_ids || [];
        if (zoneBuildingIds.length > 0) setAllowedBuildingIds(new Set(zoneBuildingIds));
      }
      setBuildings(allBuildings);
      setVehicles(vehiclesRes.data);
      if (vehiclesRes.data.length > 0) setSelectedVehicle(vehiclesRes.data[0].id);
      const mainBldg = freshProfile?.main_building || user?.main_building;
      const targetBuilding = preselectedBuilding || mainBldg;
      if (targetBuilding) {
        const building = allBuildings.find(b => b.id === targetBuilding);
        if (building) {
          setSelectedBuilding(targetBuilding);
          if (building.floors?.length > 0) setSelectedFloor(building.floors[0].id);
        }
      }
    } catch (error) {
      if (retryCount < 1 && error?.response?.status !== 403) {
        await new Promise(r => setTimeout(r, 800));
        return fetchInitialData(retryCount + 1);
      }
      if (error?.response?.status !== 401) toast.error('Failed to load data');
    } finally {
      setLoading(false);
    }
  };

  const fetchSlots = async () => {
    if (!selectedBuilding || selectedDates.length === 0) return;
    try {
      if (selectedDates.length === 1) {
        const dateStr = format(selectedDates[0], 'yyyy-MM-dd');
        const response = await slotsAPI.getAvailable(selectedBuilding, dateStr, selectedFloor || undefined);
        setSlots(response.data);
        return;
      }

      // Multiple dates: fetch all in parallel, then merge conservatively
      const responses = await Promise.all(
        selectedDates.map(d =>
          slotsAPI.getAvailable(selectedBuilding, format(d, 'yyyy-MM-dd'), selectedFloor || undefined)
            .catch(() => ({ data: [] }))
        )
      );

      const allSlotMaps = responses.map(r => {
        const map = {};
        r.data.forEach(s => { map[s.id] = s; });
        return map;
      });

      const baseSlots = responses[0].data;

      const mergedSlots = baseSlots.map(baseSlot => {
        const allVersions = allSlotMaps.map(m => m[baseSlot.id]).filter(Boolean);
        if (allVersions.length === 0) return { ...baseSlot, is_available: false };

        // Available only if free on ALL selected dates
        const isAvailableOnAll = allVersions.every(s => s.is_available);

        // Per-date availability breakdown for tooltip
        const dateAvailability = selectedDates.map((d, idx) => ({
          label: format(d, 'EEE, MMM d'),
          available: allSlotMaps[idx]?.[baseSlot.id]?.is_available ?? false,
        }));

        // Timeline: an hour is booked if booked on ANY date
        const mergedTimeline = baseSlot.timeline?.map(block => {
          const isBookedOnAnyDate = allVersions.some(s => {
            const match = s.timeline?.find(t => t.hour === block.hour);
            return match?.booked;
          });
          return { ...block, booked: isBookedOnAnyDate };
        });

        // Use most restrictive availability hours
        const minAvailableHours = Math.min(...allVersions.map(s => s.available_hours ?? 24));
        const maxBookedHours = Math.max(...allVersions.map(s => s.booked_hours ?? 0));

        return {
          ...baseSlot,
          is_available: isAvailableOnAll,
          available_hours: minAvailableHours,
          booked_hours: maxBookedHours,
          timeline: mergedTimeline,
          dateAvailability,
        };
      });

      setSlots(mergedSlots);
    } catch {}
  };

  const fetchConfig = async () => {
    if (!selectedBuilding) return;
    try {
      const response = await configAPI.get(selectedBuilding);
      setConfig(response.data);
    } catch {}
  };

  const fetchWaitlistInfo = async () => {
    if (!selectedBuilding || selectedDates.length === 0) return;
    try {
      // Use the first selected date for waitlist status (waitlist is per-date)
      const dateStr = format(selectedDates[0], 'yyyy-MM-dd');
      const [statusRes, countRes] = await Promise.all([
        waitlistAPI.status(selectedBuilding, dateStr),
        waitlistAPI.count(selectedBuilding, dateStr),
      ]);
      setWaitlistStatus(statusRes.data);
      setWaitlistCount(countRes.data.count);
    } catch {}
  };

  const handleBuildingChange = (buildingId) => {
    setSelectedBuilding(buildingId);
    setSelectedFloor('');
    setSelectedSlot(null);
    setSelectedHours([]);
    setReason('');
    setWaitlistStatus(null);
    const building = buildings.find(b => b.id === buildingId);
    if (building?.floors?.length > 0) setSelectedFloor(building.floors[0].id);
  };

  const handleSlotClick = (slot) => {
    if (slot.is_available) {
      if (selectedSlot === slot.id) {
        setSelectedSlot(null);
        setSelectedHours([]);
      } else {
        setSelectedSlot(slot.id);
        // BUG FIX TCID-PARKING-RESERVATION-015: Auto-select default booking hours
        const userStartHour = parseTimeToHour(freshUser?.default_start_time || user?.default_start_time);
        const userEndHour = parseTimeToHour(freshUser?.default_end_time || user?.default_end_time);
        
        if (userStartHour !== null && userEndHour !== null && userEndHour > userStartHour) {
          // Get hours that are actually available
          const availableHours = [];
          const now = new Date();
          const currentHour = now.getHours();
          const isAnyDateToday = selectedDates.some(d => isToday(d));
          const configStartHour = parseTimeToHour(config?.default_start_time) ?? 0;
          const configEndHour = parseTimeToHour(config?.default_end_time) ?? 24;
          
          for (let h = userStartHour; h < userEndHour; h++) {
            // Check if hour is valid
            const isPastHour = isAnyDateToday && h <= currentHour;
            const isOutsideConfigHours = h < configStartHour || h >= configEndHour;
            const block = slot.timeline?.find(t => t.hour === h);
            const isBooked = block?.booked;
            
            if (!isPastHour && !isOutsideConfigHours && !isBooked) {
              availableHours.push(h);
            }
          }
          
          // Only set if we have a contiguous block
          if (availableHours.length > 0) {
            // Check if the available hours are contiguous
            const isContiguous = availableHours.every((h, i) => 
              i === 0 || h === availableHours[i - 1] + 1
            );
            if (isContiguous) {
              setSelectedHours(availableHours);
              return;
            }
          }
        }
        setSelectedHours([]);
      }
    }
  };

  const handleToggleHour = useCallback((hour) => {
    setSelectedHours(prev => {
      if (prev.includes(hour)) {
        return prev.filter(h => h !== hour);
      }
      const newHours = [...prev, hour].sort((a, b) => a - b);
      const min = Math.min(...newHours);
      const max = Math.max(...newHours);
      const contiguous = [];
      for (let h = min; h <= max; h++) contiguous.push(h);
      // Verify none of the contiguous hours are booked
      if (selectedSlotData?.timeline) {
        const blocked = contiguous.some(h => {
          const block = selectedSlotData.timeline.find(t => t.hour === h);
          return block?.booked;
        });
        if (blocked) {
          toast.error('Cannot select across booked hours');
          return prev;
        }
      }
      return contiguous;
    });
  }, [selectedSlotData]);

  const handleDateSelect = (dates) => {
    if (!dates) { setSelectedDates([]); return; }
    const datesArray = Array.isArray(dates) ? dates : [dates];
    if (isExternalBooking && !isVip && datesArray.length > 1) {
      toast.error('External building booking is limited to a single day');
      return;
    }
    if (datesArray.length > 7) {
      toast.error('Maximum 7 days allowed per booking');
      return;
    }
    setSelectedDates(datesArray);
    setSelectedSlot(null);
    setSelectedHours([]);
  };

  const handleJoinWaitlist = async () => {
    if (!selectedBuilding || selectedDates.length === 0) return;
    setJoiningWaitlist(true);
    try {
      const dateStr = format(selectedDates[0], 'yyyy-MM-dd');
      await waitlistAPI.join({
        building_id: selectedBuilding,
        preferred_date: dateStr,
        preferred_start_time: config?.default_start_time || '08:00',
        preferred_end_time: config?.default_end_time || '18:00',
      });
      toast.success('Added to waitlist! You\'ll be notified when a slot opens.');
      fetchWaitlistInfo();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to join waitlist');
    } finally {
      setJoiningWaitlist(false);
    }
  };

  const handleLeaveWaitlist = async () => {
    if (!waitlistStatus?.entry?.id) return;
    try {
      await waitlistAPI.leave(waitlistStatus.entry.id);
      toast.success('Removed from waitlist');
      fetchWaitlistInfo();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to leave waitlist');
    }
  };

  const handleSubmit = async () => {
    if (!selectedSlot || !selectedVehicle || selectedDates.length === 0) {
      toast.error('Please fill all required fields');
      return;
    }
    if (selectedHours.length === 0) {
      toast.error('Please select your parking hours');
      return;
    }
    if (isExternalBooking && !isVip && !reason.trim()) {
      toast.error('A reason is required when booking outside your main building');
      return;
    }
    setSubmitting(true);
    try {
      const reservationData = {
        slot_id: selectedSlot,
        vehicle_id: selectedVehicle,
        dates: selectedDates.map(d => format(d, 'yyyy-MM-dd')),
        start_time: startTime,
        end_time: endTime,
        reason: isExternalBooking ? reason : null
      };
      const response = await reservationsAPI.create(reservationData);
      if (response.data.count && response.data.count > 1) {
        toast.success(`Created ${response.data.count} reservations!`);
      } else {
        toast.success('Parking spot reserved successfully!');
      }
      navigate('/reservations');
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to create reservation');
    } finally {
      setSubmitting(false);
    }
  };

  const handleAddVehicleInline = async (e) => {
    e.preventDefault();
    if (!newVehicle.plate_number) { toast.error('Plate number is required'); return; }
    setSubmittingVehicle(true);
    try {
      const res = await vehiclesAPI.create(newVehicle);
      toast.success('Vehicle added!');
      setVehicleDialogOpen(false);
      setNewVehicle({ plate_number: '', make: '', model: '', color: '' });
      const vehiclesRes = await vehiclesAPI.getAll();
      setVehicles(vehiclesRes.data);
      setSelectedVehicle(res.data.id);
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to add vehicle');
    } finally {
      setSubmittingVehicle(false);
    }
  };

  const groupSlotsByRow = () => {
    const floorSlots = selectedFloor ? slots.filter(s => s.floor_id === selectedFloor) : slots;
    const rows = {};
    floorSlots.forEach(slot => {
      const row = slot.row || 0;
      if (!rows[row]) rows[row] = [];
      rows[row].push(slot);
    });
    return Object.entries(rows).sort(([a], [b]) => Number(a) - Number(b));
  };

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50">
        <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-[#08263e]"></div>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50 pb-20 md:pb-8" data-testid="booking-page">
      {/* Header */}
      <header className="bg-[#08263e] text-white px-4 py-3 md:px-8">
        <div className="max-w-6xl mx-auto flex items-center gap-4">
          <Button variant="ghost" className="text-white hover:bg-white/20 p-2" onClick={() => navigate('/dashboard')} data-testid="back-btn">
            <ArrowLeft className="w-5 h-5" />
          </Button>
          <Link to="/dashboard"><img src="/cl-logo.png" alt="Cebuana Lhuillier" className="h-8 w-auto brightness-0 invert cursor-pointer" /></Link>
          <div className="hidden md:block"><p className="text-xs text-white/70">Book Parking</p></div>
        </div>
      </header>

      <main className="max-w-6xl mx-auto px-4 py-6 md:px-8">
        <div className="grid lg:grid-cols-3 gap-6">
          {/* Left Column */}
          <div className="lg:col-span-1 space-y-4">
            {/* Building */}
            <Card>
              <CardHeader className="pb-3">
                <CardTitle className="text-base flex items-center gap-2">
                  <Building2 className="w-5 h-5 text-[#08263e]" /> Select Building
                </CardTitle>
              </CardHeader>
              <CardContent>
                <Select value={selectedBuilding} onValueChange={handleBuildingChange}>
                  <SelectTrigger data-testid="building-select"><SelectValue placeholder="Choose a building" /></SelectTrigger>
                  <SelectContent>
                    {visibleBuildings.map(b => (
                      <SelectItem key={b.id} value={b.id}>{b.name}{b.id === userMainBuilding && ' (Main)'}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
                {allowedBuildingIds && visibleBuildings.length === 0 && (
                  <p className="text-xs text-gray-500 mt-2">No buildings in your assigned zone.</p>
                )}
                {isExternalBooking && !isVip && (
                  <div className="mt-3 p-2.5 bg-amber-50 border border-amber-200 rounded-lg">
                    <p className="text-xs text-amber-800 flex items-center gap-1.5">
                      <AlertTriangle className="w-3.5 h-3.5 shrink-0" /> External: single-day only. Reason required.
                    </p>
                  </div>
                )}
              </CardContent>
            </Card>

            {/* Floor */}
            {currentBuilding && (
              <Card>
                <CardHeader className="pb-3">
                  <CardTitle className="text-base flex items-center gap-2">
                    <MapPin className="w-5 h-5 text-[#08263e]" /> Select Floor
                  </CardTitle>
                </CardHeader>
                <CardContent className="space-y-3">
                  <Select value={selectedFloor} onValueChange={(v) => { setSelectedFloor(v); setSelectedSlot(null); setSelectedHours([]); }}>
                    <SelectTrigger data-testid="floor-select"><SelectValue placeholder="Choose a floor" /></SelectTrigger>
                    <SelectContent>
                      {currentBuilding.floors?.map(f => <SelectItem key={f.id} value={f.id}>{f.label}</SelectItem>)}
                    </SelectContent>
                  </Select>
                  {currentFloor?.layout_image_url && (
                    <Button variant="outline" size="sm" className="w-full text-[#08263e]" onClick={() => setLayoutImageOpen(true)} data-testid="view-layout-btn">
                      <Image className="w-4 h-4 mr-2" /> View Floor Layout
                    </Button>
                  )}
                </CardContent>
              </Card>
            )}

            {/* Dates */}
            <Card>
              <CardHeader className="pb-3">
                <CardTitle className="text-base flex items-center gap-2">
                  <CalendarIcon className="w-5 h-5 text-[#08263e]" /> Select Dates
                  <HelpTip text="Select one or more dates for your booking." />
                  {selectedDates.length > 0 && <Badge variant="outline" className="ml-auto text-xs">{selectedDates.length} day{selectedDates.length > 1 ? 's' : ''}</Badge>}
                </CardTitle>
              </CardHeader>
              <CardContent>
                <Calendar
                  mode={isExternalBooking && !isVip ? "single" : "multiple"}
                  selected={isExternalBooking && !isVip ? selectedDates[0] : selectedDates}
                  onSelect={(val) => {
                    if (isExternalBooking && !isVip) handleDateSelect(val ? [val] : []);
                    else handleDateSelect(val || []);
                  }}
                  disabled={(date) => {
                    const today = new Date(); today.setHours(0,0,0,0);
                    return date < today || date > addDays(new Date(), config?.booking_window_days || 7);
                  }}
                  className="rounded-md border"
                  data-testid="date-calendar"
                />
                {selectedDates.length > 0 && (
                  <div className="mt-2 flex flex-wrap gap-1">
                    {selectedDates.map((d, i) => <Badge key={i} variant="secondary" className="text-xs">{format(d, 'MMM dd')}</Badge>)}
                  </div>
                )}
              </CardContent>
            </Card>

            {/* Vehicle */}
            <Card>
              <CardHeader className="pb-3">
                <CardTitle className="text-base flex items-center gap-2">
                  <Car className="w-5 h-5 text-[#08263e]" /> Select Vehicle
                </CardTitle>
              </CardHeader>
              <CardContent>
                {vehicles.length === 0 ? (
                  <div className="text-center py-4 space-y-3">
                    <div className="w-14 h-14 mx-auto bg-[#08263e]/10 rounded-full flex items-center justify-center"><Car className="w-7 h-7 text-[#08263e]" /></div>
                    <p className="text-sm font-medium text-gray-700">No vehicles registered</p>
                    <Button className="bg-[#ec474e] hover:bg-[#d63a41] text-white rounded-full w-full" onClick={() => setVehicleDialogOpen(true)} data-testid="booking-add-vehicle-btn">
                      <Plus className="w-4 h-4 mr-2" /> Add Vehicle
                    </Button>
                  </div>
                ) : (
                  <div className="space-y-3">
                    <Select value={selectedVehicle} onValueChange={setSelectedVehicle}>
                      <SelectTrigger data-testid="vehicle-select"><SelectValue placeholder="Choose a vehicle" /></SelectTrigger>
                      <SelectContent>
                        {vehicles.map(v => <SelectItem key={v.id} value={v.id}>{v.plate_number} - {v.make} {v.model}</SelectItem>)}
                      </SelectContent>
                    </Select>
                    <Button variant="ghost" size="sm" className="w-full text-[#08263e] hover:bg-[#08263e]/5 text-xs" onClick={() => setVehicleDialogOpen(true)} data-testid="booking-add-another-vehicle-btn">
                      <Plus className="w-3 h-3 mr-1" /> Add another vehicle
                    </Button>
                  </div>
                )}
              </CardContent>
            </Card>

            {/* External Reason */}
            {isExternalBooking && !isVip && (
              <Card className="border-amber-200">
                <CardHeader className="pb-3">
                  <CardTitle className="text-base flex items-center gap-2 text-amber-800">
                    <AlertTriangle className="w-5 h-5" /> Reason for External Booking
                  </CardTitle>
                </CardHeader>
                <CardContent>
                  <textarea className="w-full border rounded-md p-3 text-sm min-h-[80px] focus:outline-none focus:ring-2 focus:ring-[#08263e] resize-none" value={reason} onChange={(e) => setReason(e.target.value)} placeholder="Reason for booking outside your main building..." data-testid="external-reason-input" />
                </CardContent>
              </Card>
            )}
          </div>

          {/* Right Column — Parking Map */}
          <div className="lg:col-span-2 space-y-4">
            <Card>
              <CardHeader>
                <div className="flex items-center justify-between flex-wrap gap-2">
                  <CardTitle className="text-lg">
                    {currentBuilding ? `${currentBuilding.name} - Parking Map` : 'Select a Building'}
                  </CardTitle>
                  {slots.length > 0 && (
                    <div className="flex items-center gap-3 text-xs">
                      <div className="flex items-center gap-1"><div className="w-3 h-3 bg-green-100 border-2 border-green-400 rounded"></div><span>Available</span></div>
                      <div className="flex items-center gap-1"><div className="w-3 h-3 bg-gray-200 border-2 border-gray-300 rounded"></div><span>Occupied</span></div>
                      <div className="flex items-center gap-1"><div className="w-3 h-3 bg-[#08263e] rounded"></div><span>Selected</span></div>
                      {slots[0]?.is_dedicated_policy && (
                        <div className="flex items-center gap-1"><div className="w-3 h-3 bg-indigo-50 border-2 border-indigo-400 rounded"></div><span>Your Slot</span></div>
                      )}
                    </div>
                  )}
                </div>
              </CardHeader>
              <CardContent>
                {!selectedBuilding ? (
                  <div className="flex flex-col items-center justify-center h-64 text-gray-400">
                    <Building2 className="w-16 h-16 mb-4" /><p>Select a building to view parking slots</p>
                  </div>
                ) : selectedDates.length === 0 ? (
                  <div className="flex flex-col items-center justify-center h-64 text-gray-400">
                    <CalendarIcon className="w-16 h-16 mb-4" /><p>Select at least one date to view available slots</p>
                  </div>
                ) : slots.length === 0 ? (
                  <div className="flex flex-col items-center justify-center h-64 text-gray-400">
                    <Car className="w-16 h-16 mb-4" /><p>No parking slots found</p>
                  </div>
                ) : (
                  <div className="space-y-4">
                  {/* Multi-date availability note */}
                    {selectedDates.length > 1 && (
                      <div className="flex items-center gap-2 p-2.5 bg-blue-50 border border-blue-200 rounded-lg text-xs text-blue-700" data-testid="multidate-availability-note">
                        <CalendarIcon className="w-3.5 h-3.5 shrink-0" />
                        Showing combined availability across all <strong>{selectedDates.length} selected dates</strong>. A slot is available only if it's free on every date.
                      </div>
                    )}

                    {/* Policy banner */}
                    {slots[0]?.is_dedicated_policy && (
                      <div className="p-3 bg-indigo-50 border border-indigo-200 rounded-lg" data-testid="dedicated-policy-banner">
                        <p className="text-xs font-medium text-indigo-800 flex items-center gap-1.5">
                          <Shield className="w-3.5 h-3.5 shrink-0" /> Dedicated Slot Policy Active
                          {slots[0].is_open_floor ? <span className="ml-1 text-emerald-700 font-normal">- Open parking floor</span> : <span className="ml-1 font-normal">- Book your assigned slot only</span>}
                        </p>
                      </div>
                    )}

                    {/* Waitlist banner */}
                    {allSlotsFullyBooked && waitlistEnabled && (
                      <div className="p-4 bg-blue-50 border border-blue-200 rounded-lg" data-testid="waitlist-banner">
                        <div className="flex items-start gap-3">
                          <ListOrdered className="w-5 h-5 text-blue-600 shrink-0 mt-0.5" />
                          <div className="flex-1">
                            <p className="text-sm font-medium text-blue-800">All slots are fully booked</p>
                            <p className="text-xs text-blue-600 mt-1">
                              {waitlistCount > 0 ? `${waitlistCount} in queue.` : 'Be first in line!'} You'll be notified when a slot opens.
                            </p>
                            <div className="mt-3">
                              {waitlistStatus?.on_waitlist ? (
                                <div className="flex items-center gap-3">
                                  <Badge className="bg-blue-100 text-blue-800 border-blue-300">
                                    <Bell className="w-3 h-3 mr-1" /> Position #{waitlistStatus.entry?.position}
                                  </Badge>
                                  <Button variant="outline" size="sm" className="text-red-600 border-red-200 hover:bg-red-50" onClick={handleLeaveWaitlist} data-testid="leave-waitlist-btn">Leave</Button>
                                </div>
                              ) : (
                                <Button onClick={handleJoinWaitlist} disabled={joiningWaitlist} className="bg-blue-600 hover:bg-blue-700 text-white" data-testid="join-waitlist-btn">
                                  <ListOrdered className="w-4 h-4 mr-2" /> {joiningWaitlist ? 'Joining...' : 'Join Waitlist'}
                                </Button>
                              )}
                            </div>
                          </div>
                        </div>
                      </div>
                    )}

                    {/* Slot Grid */}
                    <div className="bg-gray-50 rounded-lg p-6">
                      <div className="text-center mb-6">
                        <div className="inline-block bg-[#08263e] text-white px-8 py-2 rounded-t-lg text-sm font-medium">ENTRY / EXIT</div>
                      </div>
                      <div className="space-y-4" data-testid="parking-map">
                        <TooltipProvider delayDuration={250}>
                        {groupSlotsByRow().map(([rowNum, rowSlots]) => (
                          <div key={rowNum} className="flex items-center gap-2">
                            <div className="w-8 text-center text-sm font-medium text-gray-500">
                              {String.fromCharCode(65 + Number(rowNum))}
                            </div>
                            <div className="flex-1 grid grid-cols-5 gap-2">
                              {rowSlots.map((slot) => {
                                const isAssigned = slot.is_user_assigned;
                                const isRestricted = slot.restriction_reason === 'not_assigned';
                                const isSelected = selectedSlot === slot.id;
                                const showDateTooltip = selectedDates.length > 1 && slot.dateAvailability?.length > 0;
                                // Truly-free hour count drives both the label and the disabled state.
                                const trulyFree = getTrulyFreeHourCount(slot);
                                const effectivelyBookable = slot.is_available && trulyFree > 0;
                                const slotBtn = (
                                  <button
                                    onClick={() => handleSlotClick(slot)}
                                    disabled={!effectivelyBookable}
                                    className={cn(
                                      "parking-slot relative w-full",
                                      effectivelyBookable ? "available" : "occupied",
                                      isSelected && "selected ring-2 ring-[#08263e] ring-offset-1",
                                      isAssigned && effectivelyBookable && !isSelected && "!border-indigo-400 !bg-indigo-50",
                                      isRestricted && "!bg-orange-50 !border-orange-200 opacity-60",
                                    )}
                                    style={showDateTooltip && !effectivelyBookable ? { pointerEvents: 'none' } : undefined}
                                    title={!showDateTooltip ? (isAssigned ? 'Your assigned slot' : isRestricted ? 'Not your assigned slot' : slot.label) : undefined}
                                    data-testid={`slot-${slot.id}`}
                                  >
                                    <div className="text-center">
                                      <span className="font-mono text-xs font-bold">{slot.label}</span>
                                      {isAssigned && effectivelyBookable && !isSelected && (
                                        <span className="block text-[9px] text-indigo-600 font-medium">YOURS</span>
                                      )}
                                      {effectivelyBookable && trulyFree < 24 && (
                                        <span className="block text-[9px] text-amber-600">{trulyFree}h free</span>
                                      )}
                                      {!effectivelyBookable && slot.is_available && (
                                        <span className="block text-[9px] text-gray-400">No hours left</span>
                                      )}
                                      {isSelected && <Check className="w-4 h-4 mx-auto mt-1 text-[#08263e]" />}
                                    </div>
                                  </button>
                                );
                                if (!showDateTooltip) {
                                  return <React.Fragment key={slot.id}>{slotBtn}</React.Fragment>;
                                }
                                return (
                                  <Tooltip key={slot.id}>
                                    <TooltipTrigger asChild>
                                      <span className={cn("block", !effectivelyBookable ? "cursor-default" : "cursor-pointer")}>
                                        {slotBtn}
                                      </span>
                                    </TooltipTrigger>
                                    <TooltipContent
                                      side="top"
                                      sideOffset={6}
                                      className="bg-white text-gray-800 border border-gray-200 shadow-xl p-2.5 text-left min-w-[148px] z-50"
                                      data-testid={`slot-tooltip-${slot.id}`}
                                    >
                                      <p className="font-semibold text-xs mb-1.5 text-[#08263e]">
                                        {slot.label} — per date
                                      </p>
                                      <div className="space-y-1">
                                        {slot.dateAvailability.map((d, i) => (
                                          <div
                                            key={i}
                                            className={cn(
                                              "flex items-center gap-1.5 text-[11px] font-medium",
                                              d.available ? "text-emerald-600" : "text-red-500"
                                            )}
                                          >
                                            {d.available
                                              ? <Check className="w-3 h-3 flex-shrink-0" />
                                              : <X className="w-3 h-3 flex-shrink-0" />}
                                            <span className="flex-1">{d.label}</span>
                                            <span className="text-[10px] opacity-60 ml-1">
                                              {d.available ? 'free' : 'booked'}
                                            </span>
                                          </div>
                                        ))}
                                      </div>
                                    </TooltipContent>
                                  </Tooltip>
                                );
                              })}
                            </div>
                          </div>
                        ))}
                        </TooltipProvider>
                      </div>
                    </div>
                  </div>
                )}
              </CardContent>
            </Card>

            {/* Timeline Panel — only shows when a slot is selected */}
            {selectedSlot && selectedSlotData && (
              <Card className="border-[#08263e]/20 shadow-md animate-fadeIn" data-testid="timeline-panel">
                <CardHeader className="pb-3">
                  <div className="flex items-center justify-between">
                    <CardTitle className="text-base flex items-center gap-2">
                      <Clock className="w-5 h-5 text-[#08263e]" />
                      Select Hours for <span className="text-[#08263e] font-bold">{selectedSlotData.label}</span>
                    </CardTitle>
                    <Button variant="ghost" size="sm" className="h-8 w-8 p-0 text-gray-400 hover:text-gray-600" onClick={() => { setSelectedSlot(null); setSelectedHours([]); }}>
                      <X className="w-4 h-4" />
                    </Button>
                  </div>
                  <p className="text-xs text-gray-500 mt-1">Tap the available hours you need. Select a contiguous block of time.</p>
                </CardHeader>
                <CardContent>
                  {/* Hour blocks */}
                  <div className="grid grid-cols-8 gap-1.5 sm:grid-cols-16" data-testid="hour-blocks">
                    {selectedSlotData.timeline?.map((block) => {
                      const isBooked = block.booked;
                      const isSelected = selectedHours.includes(block.hour);
                      
                      // BUG FIX TCID-PARKING-RESERVATION-013: Disable past hours for today
                      const now = new Date();
                      const currentHour = now.getHours();
                      const isAnyDateToday = selectedDates.some(d => isToday(d));
                      const isPastHour = isAnyDateToday && block.hour <= currentHour;
                      
                      // BUG FIX TCID-PARKING-CONFIG-013/014: Respect parking config hours
                      const configStartHour = parseTimeToHour(config?.default_start_time) ?? 0;
                      const configEndHour = parseTimeToHour(config?.default_end_time) ?? 24;
                      const isOutsideConfigHours = block.hour < configStartHour || block.hour >= configEndHour;
                      
                      const isDisabled = isBooked || isPastHour || isOutsideConfigHours;
                      const disabledReason = isPastHour ? 'Past' : isOutsideConfigHours ? 'Closed' : isBooked ? 'Taken' : null;
                      
                      return (
                        <button
                          key={block.hour}
                          onClick={() => !isDisabled && handleToggleHour(block.hour)}
                          disabled={isDisabled}
                          className={cn(
                            "flex flex-col items-center justify-center rounded-lg py-2.5 px-1 transition-all text-xs font-medium border",
                            isDisabled && "bg-gray-100 border-gray-200 text-gray-400 cursor-not-allowed",
                            !isDisabled && !isSelected && "bg-white border-emerald-200 text-emerald-700 hover:bg-emerald-50 hover:border-emerald-400 cursor-pointer",
                            isSelected && "bg-[#08263e] border-[#08263e] text-white shadow-sm",
                          )}
                          data-testid={`hour-${block.hour}`}
                        >
                          <span className="text-[11px] leading-none">{formatHour(block.hour)}</span>
                          {disabledReason && <span className="text-[8px] mt-0.5 text-gray-400">{disabledReason}</span>}
                        </button>
                      );
                    })}
                  </div>

                  {/* Legend */}
                  <div className="flex items-center gap-4 mt-4 text-[10px] text-gray-500">
                    <div className="flex items-center gap-1"><div className="w-2.5 h-2.5 rounded bg-white border border-emerald-300"></div> Available</div>
                    <div className="flex items-center gap-1"><div className="w-2.5 h-2.5 rounded bg-gray-100 border border-gray-200"></div> Taken</div>
                    <div className="flex items-center gap-1"><div className="w-2.5 h-2.5 rounded bg-[#08263e]"></div> Your selection</div>
                  </div>

                  {/* Booking summary */}
                  {selectedHours.length > 0 && (
                    <div className="mt-4 p-4 bg-[#08263e]/5 border border-[#08263e]/15 rounded-lg" data-testid="booking-summary">
                      <div className="flex items-center justify-between flex-wrap gap-3">
                        <div>
                          <p className="text-sm font-semibold text-[#08263e]">
                            {selectedSlotData.label} &middot; {formatHour(Math.min(...selectedHours))} - {formatHour(Math.max(...selectedHours) + 1)}
                          </p>
                          <p className="text-xs text-gray-500 mt-0.5">
                            {selectedHours.length} hour{selectedHours.length > 1 ? 's' : ''} &middot; {selectedDates.length} day{selectedDates.length > 1 ? 's' : ''}
                          </p>
                        </div>
                        <Button
                          onClick={handleSubmit}
                          disabled={submitting || !selectedVehicle}
                          className="bg-[#08263e] hover:bg-[#051a2d] text-white rounded-full px-6"
                          data-testid="confirm-booking-btn"
                        >
                          {submitting ? 'Booking...' : 'Confirm Booking'}
                        </Button>
                      </div>
                    </div>
                  )}
                </CardContent>
              </Card>
            )}
          </div>
        </div>
      </main>

      {/* Vehicle Dialog */}
      <Dialog open={vehicleDialogOpen} onOpenChange={setVehicleDialogOpen}>
        <DialogContent>
          <DialogHeader><DialogTitle>Add Your Vehicle</DialogTitle></DialogHeader>
          <p className="text-sm text-gray-500 -mt-2">Register your vehicle to continue with booking.</p>
          <form onSubmit={handleAddVehicleInline} className="space-y-4 mt-2">
            <div className="space-y-2">
              <Label htmlFor="bp_plate">Plate Number *</Label>
              <Input id="bp_plate" placeholder="ABC 1234" value={newVehicle.plate_number} onChange={(e) => setNewVehicle({ ...newVehicle, plate_number: e.target.value.toUpperCase() })} required className="font-mono uppercase" data-testid="booking-vehicle-plate-input" />
            </div>
            <div className="grid grid-cols-2 gap-4">
              <div className="space-y-2"><Label htmlFor="bp_make">Make</Label><Input id="bp_make" placeholder="Toyota" value={newVehicle.make} onChange={(e) => setNewVehicle({ ...newVehicle, make: e.target.value })} data-testid="booking-vehicle-make-input" /></div>
              <div className="space-y-2"><Label htmlFor="bp_model">Model</Label><Input id="bp_model" placeholder="Vios" value={newVehicle.model} onChange={(e) => setNewVehicle({ ...newVehicle, model: e.target.value })} data-testid="booking-vehicle-model-input" /></div>
            </div>
            <div className="space-y-2"><Label htmlFor="bp_color">Color</Label><Input id="bp_color" placeholder="White" value={newVehicle.color} onChange={(e) => setNewVehicle({ ...newVehicle, color: e.target.value })} data-testid="booking-vehicle-color-input" /></div>
            <div className="flex gap-3 pt-2">
              <Button type="button" variant="outline" className="flex-1" onClick={() => setVehicleDialogOpen(false)}>Cancel</Button>
              <Button type="submit" className="flex-1 bg-[#08263e] hover:bg-[#051a2d] text-white" disabled={submittingVehicle} data-testid="booking-save-vehicle-btn">{submittingVehicle ? 'Saving...' : 'Save & Continue'}</Button>
            </div>
          </form>
        </DialogContent>
      </Dialog>

      {/* Floor Layout Dialog */}
      <Dialog open={layoutImageOpen} onOpenChange={setLayoutImageOpen}>
        <DialogContent className="max-w-2xl">
          <DialogHeader><DialogTitle>{currentFloor?.label} - Floor Layout</DialogTitle></DialogHeader>
          {currentFloor?.layout_image_url && (
            <img src={`${API_URL}${currentFloor.layout_image_url}`} alt={`${currentFloor.label} layout`} className="w-full rounded-lg" data-testid="floor-layout-image" />
          )}
        </DialogContent>
      </Dialog>

      {/* Mobile Bottom Nav */}
      <nav className="mobile-nav">
        <Link to="/dashboard" className={`mobile-nav-item ${location.pathname === '/dashboard' ? 'active' : ''}`}><Home className="w-5 h-5" /><span className="text-xs">Home</span></Link>
        <Link to="/book" className={`mobile-nav-item ${location.pathname === '/book' ? 'active' : ''}`}><Plus className="w-5 h-5" /><span className="text-xs">Book</span></Link>
        <Link to="/reservations" className={`mobile-nav-item ${location.pathname === '/reservations' ? 'active' : ''}`}><CalendarIcon className="w-5 h-5" /><span className="text-xs">Bookings</span></Link>
        <Link to="/vehicles" className={`mobile-nav-item ${location.pathname === '/vehicles' ? 'active' : ''}`}><Car className="w-5 h-5" /><span className="text-xs">Vehicles</span></Link>
        <Link to="/profile" className={`mobile-nav-item ${location.pathname === '/profile' ? 'active' : ''}`}><User className="w-5 h-5" /><span className="text-xs">Profile</span></Link>
      </nav>
    </div>
  );
};

export default BookingPage;
