import React, { useState, useEffect, useCallback } from 'react';
import { eventBlocksAPI, buildingsAPI, slotsAPI } from '../../services/api';
import { Button } from '../../components/ui/button';
import { Input } from '../../components/ui/input';
import { Label } from '../../components/ui/label';
import { Card, CardContent, CardHeader, CardTitle } from '../../components/ui/card';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from '../../components/ui/dialog';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../../components/ui/select';
import { Textarea } from '../../components/ui/textarea';
import { toast } from 'sonner';
import { ShieldBan, Plus, Trash2, CalendarOff, Car } from 'lucide-react';

const EventBlocking = () => {
  const [events, setEvents] = useState([]);
  const [buildings, setBuildings] = useState([]);
  const [slots, setSlots] = useState([]);
  const [loading, setLoading] = useState(true);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [filterBuilding, setFilterBuilding] = useState('');

  const [form, setForm] = useState({
    building_id: '', floor_id: '', date: '', start_time: '08:00', end_time: '18:00',
    reason: '', slot_ids: [], vehicle_plates: {},
  });

  useEffect(() => { loadData(); }, []);

  const loadData = async () => {
    try {
      const [evRes, bldRes] = await Promise.all([eventBlocksAPI.list(), buildingsAPI.getAll()]);
      setEvents(evRes.data);
      setBuildings(bldRes.data);
    } catch { toast.error('Failed to load data'); }
    finally { setLoading(false); }
  };

  const selectedBuilding = buildings.find(b => b.id === form.building_id);
  const floors = selectedBuilding?.floors || [];

  // Auto-select first floor when building changes
  useEffect(() => {
    if (form.building_id && floors.length > 0 && !floors.find(f => f.id === form.floor_id)) {
      setForm(f => ({ ...f, floor_id: floors[0].id, slot_ids: [], vehicle_plates: {} }));
    }
  }, [form.building_id, floors, form.floor_id]);

  const fetchSlots = useCallback(async () => {
    if (!form.building_id || !form.date || !form.floor_id) { setSlots([]); return; }
    try {
      const res = await slotsAPI.getAvailable(form.building_id, form.date, form.floor_id);
      setSlots(res.data);
    } catch { setSlots([]); }
  }, [form.building_id, form.date, form.floor_id]);

  useEffect(() => { fetchSlots(); }, [fetchSlots]);

  const toggleSlot = (slotId) => {
    setForm(f => {
      const ids = f.slot_ids.includes(slotId) ? f.slot_ids.filter(id => id !== slotId) : [...f.slot_ids, slotId];
      return { ...f, slot_ids: ids };
    });
  };

  const setPlate = (slotId, plate) => {
    setForm(f => ({ ...f, vehicle_plates: { ...f.vehicle_plates, [slotId]: plate } }));
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!form.building_id || !form.floor_id || !form.date || !form.reason.trim()) {
      toast.error('Building, floor, date, and reason are required'); return;
    }
    if (form.slot_ids.length === 0) { toast.error('Select at least one slot from the map'); return; }
    setSubmitting(true);
    try {
      const plates = form.slot_ids.map(sid => form.vehicle_plates[sid] || null);
      await eventBlocksAPI.create({
        building_id: form.building_id, floor_id: form.floor_id,
        slot_ids: form.slot_ids, date: form.date,
        start_time: form.start_time, end_time: form.end_time,
        reason: form.reason.trim(),
        vehicle_plates: plates.some(p => p) ? plates : null,
      });
      toast.success(`Event block created — ${form.slot_ids.length} slot(s) blocked`);
      setDialogOpen(false);
      resetForm();
      loadData();
    } catch (err) { toast.error(err.response?.data?.detail || 'Failed to create event block'); }
    finally { setSubmitting(false); }
  };

  const handleDelete = async (id) => {
    if (!window.confirm('Remove this event block? Associated reservations will be cancelled.')) return;
    try {
      await eventBlocksAPI.delete(id);
      toast.success('Event block removed');
      loadData();
    } catch { toast.error('Failed to remove event block'); }
  };

  const resetForm = () => {
    setForm({ building_id: '', floor_id: '', date: '', start_time: '08:00', end_time: '18:00', reason: '', slot_ids: [], vehicle_plates: {} });
    setSlots([]);
  };

  // Group slots into rows for the parking map (same as BookingPage)
  const groupSlotsByRow = () => {
    const rows = {};
    slots.forEach(slot => {
      const match = slot.label.match(/(\d+)/);
      const rowNum = match ? Math.floor((parseInt(match[1]) - 1) / 5) : 0;
      if (!rows[rowNum]) rows[rowNum] = [];
      rows[rowNum].push(slot);
    });
    return Object.entries(rows).sort(([a], [b]) => Number(a) - Number(b));
  };

  const filtered = filterBuilding && filterBuilding !== 'all' ? events.filter(e => e.building_id === filterBuilding) : events;

  if (loading) return <div className="flex justify-center py-20"><div className="animate-spin rounded-full h-8 w-8 border-b-2 border-sky-600" /></div>;

  return (
    <div className="space-y-6" data-testid="event-blocking-page">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Event Blocking</h1>
          <p className="text-sm text-gray-500 mt-1">Block parking slots for events or maintenance</p>
        </div>
        <Dialog open={dialogOpen} onOpenChange={(v) => { setDialogOpen(v); if (!v) resetForm(); }}>
          <DialogTrigger asChild>
            <Button data-testid="create-event-block-btn"><Plus className="w-4 h-4 mr-2" />Block Slots</Button>
          </DialogTrigger>
          <DialogContent className="max-w-3xl max-h-[90vh] overflow-y-auto">
            <DialogHeader><DialogTitle>Block Slots for Event</DialogTitle></DialogHeader>
            <form onSubmit={handleSubmit} className="space-y-4">
              {/* Building & Floor */}
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <Label>Building *</Label>
                  <Select value={form.building_id} onValueChange={v => {
                    setForm(f => ({ ...f, building_id: v, floor_id: '', slot_ids: [], vehicle_plates: {} }));
                  }}>
                    <SelectTrigger data-testid="event-building-select"><SelectValue placeholder="Select building" /></SelectTrigger>
                    <SelectContent>{buildings.map(b => <SelectItem key={b.id} value={b.id}>{b.name}</SelectItem>)}</SelectContent>
                  </Select>
                </div>
                <div>
                  <Label>Floor *</Label>
                  <Select value={form.floor_id} onValueChange={v => setForm(f => ({ ...f, floor_id: v, slot_ids: [], vehicle_plates: {} }))} disabled={!form.building_id}>
                    <SelectTrigger data-testid="event-floor-select"><SelectValue placeholder="Select floor" /></SelectTrigger>
                    <SelectContent>{floors.map(f => <SelectItem key={f.id} value={f.id}>{f.label}</SelectItem>)}</SelectContent>
                  </Select>
                </div>
              </div>

              {/* Date & Time */}
              <div className="grid grid-cols-3 gap-4">
                <div>
                  <Label>Date *</Label>
                  <Input type="date" value={form.date} onChange={e => setForm(f => ({ ...f, date: e.target.value, slot_ids: [], vehicle_plates: {} }))} data-testid="event-date-input" />
                </div>
                <div>
                  <Label>Start Time</Label>
                  <Input type="time" value={form.start_time} onChange={e => setForm(f => ({ ...f, start_time: e.target.value }))} />
                </div>
                <div>
                  <Label>End Time</Label>
                  <Input type="time" value={form.end_time} onChange={e => setForm(f => ({ ...f, end_time: e.target.value }))} />
                </div>
              </div>

              {/* Reason */}
              <div>
                <Label>Reason *</Label>
                <Textarea placeholder="e.g. Company event, VIP parking, construction..." value={form.reason} onChange={e => setForm(f => ({ ...f, reason: e.target.value }))} data-testid="event-reason-input" />
              </div>

              {/* Slot Map */}
              <div>
                <Label className="mb-2 block">Select Slots * {form.slot_ids.length > 0 && <span className="text-sky-600">({form.slot_ids.length} selected)</span>}</Label>
                {!form.building_id || !form.date ? (
                  <div className="flex flex-col items-center justify-center h-40 text-gray-400 bg-gray-50 rounded-lg border border-dashed">
                    <Car className="w-10 h-10 mb-2" />
                    <p className="text-sm">{!form.building_id ? 'Select a building first' : 'Select a date to view slots'}</p>
                  </div>
                ) : slots.length === 0 ? (
                  <div className="flex flex-col items-center justify-center h-40 text-gray-400 bg-gray-50 rounded-lg border border-dashed">
                    <Car className="w-10 h-10 mb-2" />
                    <p className="text-sm">No slots found for this floor</p>
                  </div>
                ) : (
                  <div className="bg-gray-50 rounded-lg p-4 border">
                    {/* Legend */}
                    <div className="flex items-center gap-4 text-xs mb-3 flex-wrap">
                      <div className="flex items-center gap-1"><div className="w-3 h-3 bg-green-100 border-2 border-green-400 rounded"></div>Available</div>
                      <div className="flex items-center gap-1"><div className="w-3 h-3 bg-gray-200 border-2 border-gray-300 rounded"></div>Occupied</div>
                      <div className="flex items-center gap-1"><div className="w-3 h-3 bg-sky-600 rounded"></div>Selected</div>
                      <div className="flex items-center gap-1"><div className="w-3 h-3 bg-yellow-100 border-2 border-yellow-400 rounded"></div>Maintenance</div>
                      <div className="flex items-center gap-1"><div className="w-3 h-3 bg-amber-100 border-2 border-amber-500 rounded"></div>Event Blocked</div>
                    </div>
                    {/* Entry */}
                    <div className="text-center mb-4">
                      <div className="inline-block bg-[#08263e] text-white px-6 py-1.5 rounded-t-lg text-xs font-medium">ENTRY / EXIT</div>
                    </div>
                    {/* Slot grid */}
                    <div className="space-y-2" data-testid="event-slot-map">
                      {groupSlotsByRow().map(([rowNum, rowSlots]) => (
                        <div key={rowNum} className="flex items-center gap-2">
                          <div className="w-6 text-center text-xs font-medium text-gray-500">
                            {String.fromCharCode(65 + Number(rowNum))}
                          </div>
                          <div className="flex-1 grid grid-cols-5 gap-1.5">
                            {rowSlots.map(slot => {
                              const isSelected = form.slot_ids.includes(slot.id);
                              const isOccupied = !slot.is_available;
                              const isMaintenance = slot.status === 'maintenance';
                              const isEventBlocked = !!slot.is_event_blocked;
                              const lockedReason = isMaintenance ? 'Maintenance' : isEventBlocked ? (slot.event_block_reason || 'Event blocked') : null;
                              return (
                                <button key={slot.id} type="button"
                                  onClick={() => !isMaintenance && !isEventBlocked && toggleSlot(slot.id)}
                                  disabled={isMaintenance || isEventBlocked}
                                  title={lockedReason || ''}
                                  data-testid={`event-slot-${slot.label}`}
                                  className={`relative p-2 rounded-md border text-center transition-all text-xs font-medium
                                    ${isMaintenance ? 'bg-yellow-50 border-yellow-300 text-yellow-600 cursor-not-allowed'
                                      : isEventBlocked ? 'bg-amber-50 border-amber-500 text-amber-700 cursor-not-allowed'
                                      : isSelected ? 'bg-sky-600 border-sky-600 text-white ring-2 ring-sky-300'
                                      : isOccupied ? 'bg-gray-100 border-gray-300 text-gray-500'
                                      : 'bg-green-50 border-green-300 text-green-800 hover:border-sky-400 cursor-pointer'}`}>
                                  <div className="text-[11px]">{slot.label}</div>
                                  {isEventBlocked && <div className="text-[9px] text-amber-600 mt-0.5">Blocked</div>}
                                  {isOccupied && !isMaintenance && !isEventBlocked && !isSelected && <div className="text-[9px] text-gray-400 mt-0.5">Booked</div>}
                                  {isSelected && <div className="absolute -top-1 -right-1 w-3.5 h-3.5 bg-sky-700 rounded-full flex items-center justify-center text-[8px] text-white font-bold">{form.slot_ids.indexOf(slot.id) + 1}</div>}
                                </button>
                              );
                            })}
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                )}
              </div>

              {/* Vehicle plates (optional) */}
              {form.slot_ids.length > 0 && (
                <div>
                  <Label className="flex items-center gap-1"><Car className="w-4 h-4" /> Vehicle Plates (optional per slot)</Label>
                  <div className="grid grid-cols-2 gap-2 mt-2">
                    {form.slot_ids.map(sid => {
                      const sl = slots.find(s => s.id === sid);
                      return (
                        <div key={sid} className="flex items-center gap-2">
                          <span className="text-xs font-medium w-14 text-gray-600">{sl?.label}</span>
                          <Input placeholder="Plate #" className="h-8 text-sm" value={form.vehicle_plates[sid] || ''}
                            onChange={e => setPlate(sid, e.target.value)} />
                        </div>
                      );
                    })}
                  </div>
                </div>
              )}

              <div className="flex justify-end gap-2 pt-2">
                <Button type="button" variant="outline" onClick={() => { setDialogOpen(false); resetForm(); }}>Cancel</Button>
                <Button type="submit" disabled={submitting} data-testid="submit-event-block-btn">
                  {submitting ? 'Blocking...' : `Block ${form.slot_ids.length || ''} Slot${form.slot_ids.length !== 1 ? 's' : ''}`}
                </Button>
              </div>
            </form>
          </DialogContent>
        </Dialog>
      </div>

      {/* Filter */}
      <div className="flex items-center gap-3">
        <Label className="text-sm">Filter by building:</Label>
        <Select value={filterBuilding} onValueChange={setFilterBuilding}>
          <SelectTrigger className="w-56"><SelectValue placeholder="All buildings" /></SelectTrigger>
          <SelectContent>
            <SelectItem value="all">All buildings</SelectItem>
            {buildings.map(b => <SelectItem key={b.id} value={b.id}>{b.name}</SelectItem>)}
          </SelectContent>
        </Select>
      </div>

      {/* Event blocks list */}
      {filtered.length === 0 ? (
        <Card><CardContent className="py-12 text-center text-gray-500">
          <CalendarOff className="w-10 h-10 mx-auto mb-3 text-gray-300" />
          <p className="font-medium">No event blocks found</p>
          <p className="text-sm mt-1">Click "Block Slots" to reserve parking slots for an event.</p>
        </CardContent></Card>
      ) : (
        <div className="space-y-3">
          {filtered.map(ev => (
            <Card key={ev.id} data-testid={`event-block-${ev.id}`}>
              <CardHeader className="pb-2">
                <div className="flex items-start justify-between">
                  <div className="flex items-center gap-2">
                    <ShieldBan className="w-5 h-5 text-amber-600" />
                    <CardTitle className="text-base">{ev.reason}</CardTitle>
                  </div>
                  <Button variant="ghost" size="sm" onClick={() => handleDelete(ev.id)} data-testid={`delete-event-${ev.id}`}>
                    <Trash2 className="w-4 h-4 text-red-500" />
                  </Button>
                </div>
              </CardHeader>
              <CardContent className="pt-0">
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-3 text-sm text-gray-600">
                  <div><span className="font-medium">Building:</span> {ev.building_name}</div>
                  <div><span className="font-medium">Floor:</span> {ev.floor_label}</div>
                  <div><span className="font-medium">Date:</span> {ev.date}</div>
                  <div><span className="font-medium">Time:</span> {ev.start_time}–{ev.end_time}</div>
                </div>
                <div className="mt-2 flex items-center gap-2 flex-wrap">
                  <span className="text-xs font-medium text-gray-500">Slots:</span>
                  {(ev.slot_labels || []).map((sl, i) => (
                    <span key={i} className="inline-flex items-center gap-1 px-2 py-0.5 rounded-full text-xs bg-amber-50 text-amber-700 border border-amber-200">
                      {sl}
                      {ev.vehicle_plates?.[i] && <span className="text-amber-500">({ev.vehicle_plates[i]})</span>}
                    </span>
                  ))}
                </div>
                <div className="mt-2 text-xs text-gray-400">Created by {ev.created_by_name} on {new Date(ev.created_at).toLocaleDateString()}</div>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  );
};

export default EventBlocking;
