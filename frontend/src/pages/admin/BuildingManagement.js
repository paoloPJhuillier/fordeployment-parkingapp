import React, { useState, useEffect, useRef } from 'react';
import { buildingsAPI, slotsAPI } from '../../services/api';
import { Button } from '../../components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '../../components/ui/card';
import { Input } from '../../components/ui/input';
import { Label } from '../../components/ui/label';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../../components/ui/tabs';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from '../../components/ui/dialog';
import { Accordion, AccordionContent, AccordionItem, AccordionTrigger } from '../../components/ui/accordion';
import { Badge } from '../../components/ui/badge';
import { toast } from 'sonner';
import { 
  Plus, Building2, MapPin, Layers, Trash2, Check, X, Pencil, Grid3x3, Upload, Image, Search, ParkingSquare
} from 'lucide-react';
import { HelpTip } from '../../components/ui/help-tip';

const API_URL = process.env.REACT_APP_BACKEND_URL || '';

const BuildingManagement = () => {
  const [buildings, setBuildings] = useState([]);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState('');
  const [dialogOpen, setDialogOpen] = useState(false);
  const [addFloorDialogOpen, setAddFloorDialogOpen] = useState(false);
  const [addSlotsDialogOpen, setAddSlotsDialogOpen] = useState(false);
  const [selectedBuildingId, setSelectedBuildingId] = useState(null);
  const [selectedFloorId, setSelectedFloorId] = useState(null);
  const [submitting, setSubmitting] = useState(false);
  const [editingSlotId, setEditingSlotId] = useState(null);
  const [editSlotLabel, setEditSlotLabel] = useState('');
  const [uploadingLayout, setUploadingLayout] = useState(null);

  const [newBuilding, setNewBuilding] = useState({ name: '', address_line_1: '', address_line_2: '', total_floors: 1, slots_per_floor: 10, slot_prefix: '' });
  const [newFloor, setNewFloor] = useState({ label: '', slot_count: 10, slot_prefix: '', slot_labels_raw: '', mode: 'prefix' });
  const [bulkSlots, setBulkSlots] = useState({ slot_count: 5, slot_prefix: '', slot_labels_raw: '', mode: 'prefix' });
  const [editBuildingDialogOpen, setEditBuildingDialogOpen] = useState(false);
  const [editingBuilding, setEditingBuilding] = useState(null);
  const slotLabelInputRef = useRef(null);

  useEffect(() => { fetchBuildings(); }, []);

  // QAT-BUILDING-MANAGEMENT-027 fix: refresh slot statuses when this tab/window
  // regains focus (and on a 30-second poll while visible) so slot colors
  // (Available -> Reserved) update without a manual reload after a reservation
  // is created elsewhere.
  useEffect(() => {
    const onFocus = () => fetchBuildings();
    const onVisibility = () => { if (!document.hidden) fetchBuildings(); };
    window.addEventListener('focus', onFocus);
    document.addEventListener('visibilitychange', onVisibility);
    const interval = setInterval(() => {
      if (!document.hidden) fetchBuildings();
    }, 30000);
    return () => {
      window.removeEventListener('focus', onFocus);
      document.removeEventListener('visibilitychange', onVisibility);
      clearInterval(interval);
    };
  }, []);

  const fetchBuildings = async () => {
    try {
      const response = await buildingsAPI.getAll();
      setBuildings(response.data);
    } catch { toast.error('Failed to load buildings'); }
    finally { setLoading(false); }
  };

  const getPreviewLabels = (prefix, count, start = 1) => {
    const labels = [];
    for (let i = 0; i < Math.min(count, 20); i++) labels.push(`${prefix}${start + i}`);
    if (count > 20) labels.push(`...+${count - 20} more`);
    return labels;
  };

  const parseCustomLabels = (raw) => raw.split(/[,\n]/).map(s => s.trim()).filter(Boolean);

  const handleCreateBuilding = async (e) => {
    e.preventDefault();
    setSubmitting(true);
    try {
      await buildingsAPI.create({ 
        name: newBuilding.name, 
        address_line_1: newBuilding.address_line_1, 
        address_line_2: newBuilding.address_line_2, 
        total_floors: newBuilding.total_floors, 
        slots_per_floor: newBuilding.slots_per_floor, 
        slot_prefix: newBuilding.slot_prefix || null 
      });
      toast.success('Building created');
      setDialogOpen(false);
      setNewBuilding({ name: '', address_line_1: '', address_line_2: '', total_floors: 1, slots_per_floor: 10, slot_prefix: '' });
      fetchBuildings();
    } catch (error) { toast.error(error.response?.data?.detail || 'Failed to create building'); }
    finally { setSubmitting(false); }
  };

  const handleEditBuilding = (building) => {
    setEditingBuilding({
      id: building.id,
      name: building.name,
      address_line_1: building.address_line_1 || '',
      address_line_2: building.address_line_2 || '',
    });
    setEditBuildingDialogOpen(true);
  };

  const handleUpdateBuilding = async (e) => {
    e.preventDefault();
    if (!editingBuilding) return;
    setSubmitting(true);
    try {
      await buildingsAPI.update(editingBuilding.id, {
        name: editingBuilding.name,
        address_line_1: editingBuilding.address_line_1,
        address_line_2: editingBuilding.address_line_2,
      });
      toast.success('Building updated');
      setEditBuildingDialogOpen(false);
      setEditingBuilding(null);
      fetchBuildings();
    } catch (error) { toast.error(error.response?.data?.detail || 'Failed to update building'); }
    finally { setSubmitting(false); }
  };

  const handleAddFloor = async (e) => {
    e.preventDefault();
    if (!selectedBuildingId) return;
    setSubmitting(true);
    try {
      const payload = { label: newFloor.label, building_id: selectedBuildingId, slot_count: newFloor.mode === 'prefix' ? newFloor.slot_count : 0 };
      if (newFloor.mode === 'prefix') { payload.slot_prefix = newFloor.slot_prefix || null; payload.slot_count = newFloor.slot_count; }
      else {
        const labels = parseCustomLabels(newFloor.slot_labels_raw);
        if (labels.length === 0) { toast.error('Enter at least one slot label'); setSubmitting(false); return; }
        payload.slot_labels = labels; payload.slot_count = labels.length;
      }
      await buildingsAPI.addFloor(selectedBuildingId, payload);
      toast.success('Floor added');
      setAddFloorDialogOpen(false);
      setNewFloor({ label: '', slot_count: 10, slot_prefix: '', slot_labels_raw: '', mode: 'prefix' });
      fetchBuildings();
    } catch (error) { toast.error(error.response?.data?.detail || 'Failed to add floor'); }
    finally { setSubmitting(false); }
  };

  const handleAddSlots = async (e) => {
    e.preventDefault();
    if (!selectedFloorId) return;
    setSubmitting(true);
    try {
      const payload = {};
      if (bulkSlots.mode === 'prefix') { payload.slot_count = bulkSlots.slot_count; payload.slot_prefix = bulkSlots.slot_prefix || null; }
      else {
        const labels = parseCustomLabels(bulkSlots.slot_labels_raw);
        if (labels.length === 0) { toast.error('Enter at least one slot label'); setSubmitting(false); return; }
        payload.slot_labels = labels;
      }
      const res = await slotsAPI.addToFloor(selectedFloorId, payload);
      toast.success(res.data.message);
      setAddSlotsDialogOpen(false);
      setBulkSlots({ slot_count: 5, slot_prefix: '', slot_labels_raw: '', mode: 'prefix' });
      fetchBuildings();
    } catch (error) { toast.error(error.response?.data?.detail || 'Failed to add slots'); }
    finally { setSubmitting(false); }
  };

  const handleRenameSlot = async (slotId) => {
    if (!editSlotLabel.trim()) { toast.error('Label cannot be empty'); return; }
    try { await slotsAPI.rename(slotId, editSlotLabel.trim()); toast.success('Slot renamed'); setEditingSlotId(null); fetchBuildings(); }
    catch { toast.error('Failed to rename slot'); }
  };

  const handleDeleteSlot = async (slotId) => {
    if (!window.confirm('Delete this slot?')) return;
    try { await slotsAPI.delete(slotId); toast.success('Slot deleted'); fetchBuildings(); }
    catch (error) { toast.error(error.response?.data?.detail || 'Failed to delete slot'); }
  };

  const handleToggleSlotStatus = async (slot) => {
    const newStatus = slot.status === 'maintenance' ? 'available' : 'maintenance';
    const action = newStatus === 'maintenance' ? 'block' : 'unblock';
    try {
      await slotsAPI.updateStatus(slot.id, newStatus);
      toast.success(`Slot ${slot.label} ${action}ed`);
      fetchBuildings();
    } catch (error) {
      toast.error(error.response?.data?.detail || `Failed to ${action} slot`);
    }
  };

  const handleDeleteBuilding = async (buildingId) => {
    if (!window.confirm('Delete this building and all its floors/slots?')) return;
    try { await buildingsAPI.delete(buildingId); toast.success('Building deleted'); fetchBuildings(); }
    catch { toast.error('Failed to delete building'); }
  };

  const handleUploadLayout = async (floorId, file) => {
    setUploadingLayout(floorId);
    try { await buildingsAPI.uploadFloorLayout(floorId, file); toast.success('Floor layout image uploaded'); fetchBuildings(); }
    catch (error) { toast.error(error.response?.data?.detail || 'Failed to upload layout'); }
    finally { setUploadingLayout(null); }
  };

  const handleDeleteLayout = async (floorId) => {
    try { await buildingsAPI.deleteFloorLayout(floorId); toast.success('Layout image removed'); fetchBuildings(); }
    catch { toast.error('Failed to remove layout'); }
  };

  const getSlotStatusCounts = (floor) => {
    const available = floor.slots?.filter(s => s.status === 'available').length || 0;
    const blocked = floor.slots?.filter(s => s.status === 'maintenance').length || 0;
    return { available, blocked, total: floor.slots?.length || 0 };
  };

  // Summary stats
  const totalFloors = buildings.reduce((sum, b) => sum + (b.floors?.length || 0), 0);
  const totalSlots = buildings.reduce((sum, b) => sum + (b.floors || []).reduce((s, f) => s + (f.slots?.length || 0), 0), 0);
  const availableSlots = buildings.reduce((sum, b) => sum + (b.floors || []).reduce((s, f) => s + (f.slots?.filter(sl => sl.status === 'available').length || 0), 0), 0);

  const filteredBuildings = buildings.filter(b =>
    b.name.toLowerCase().includes(searchTerm.toLowerCase()) ||
    b.address.toLowerCase().includes(searchTerm.toLowerCase())
  );

  const SlotNamingUI = ({ data, setData, existingCount = 0 }) => (
    <div className="space-y-4 border rounded-lg p-4 bg-gray-50">
      <Label className="text-sm font-semibold text-gray-700">Slot Naming</Label>
      <Tabs value={data.mode} onValueChange={(val) => setData({ ...data, mode: val })}>
        <TabsList className="grid w-full grid-cols-2">
          <TabsTrigger value="prefix" data-testid="mode-prefix">Prefix + Number</TabsTrigger>
          <TabsTrigger value="custom" data-testid="mode-custom">Custom Labels</TabsTrigger>
        </TabsList>
        <TabsContent value="prefix" className="space-y-3 mt-3">
          <div className="grid grid-cols-2 gap-3">
            <div className="space-y-1"><Label className="text-xs text-gray-500">Prefix</Label>
              <Input value={data.slot_prefix} onChange={(e) => setData({ ...data, slot_prefix: e.target.value })} placeholder="e.g. A-, B1-" data-testid="slot-prefix-input" /></div>
            <div className="space-y-1"><Label className="text-xs text-gray-500">Number of Slots</Label>
              <Input type="number" min="1" max="200" value={data.slot_count} onChange={(e) => setData({ ...data, slot_count: parseInt(e.target.value) || 1 })} data-testid="slot-count-input" /></div>
          </div>
          {data.slot_prefix && data.slot_count > 0 && (
            <div className="space-y-1"><Label className="text-xs text-gray-500">Preview</Label>
              <div className="flex flex-wrap gap-1.5">
                {getPreviewLabels(data.slot_prefix, data.slot_count, existingCount + 1).map((l, i) => (
                  <span key={i} className="px-2 py-0.5 bg-white border rounded text-xs font-mono text-[#08263e]">{l}</span>))}
              </div></div>)}
        </TabsContent>
        <TabsContent value="custom" className="space-y-3 mt-3">
          <div className="space-y-1"><Label className="text-xs text-gray-500">Enter slot labels (comma or newline separated)</Label>
            <textarea className="w-full border rounded-md p-2 text-sm font-mono min-h-[80px] focus:outline-none focus:ring-2 focus:ring-[#08263e]" value={data.slot_labels_raw} onChange={(e) => setData({ ...data, slot_labels_raw: e.target.value })} placeholder={"VIP-01, VIP-02\nEV-01, EV-02"} data-testid="custom-labels-input" /></div>
          {data.slot_labels_raw && (
            <div className="space-y-1"><Label className="text-xs text-gray-500">Preview ({parseCustomLabels(data.slot_labels_raw).length} slots)</Label>
              <div className="flex flex-wrap gap-1.5">
                {parseCustomLabels(data.slot_labels_raw).map((l, i) => (
                  <span key={i} className="px-2 py-0.5 bg-white border rounded text-xs font-mono text-[#08263e]">{l}</span>))}
              </div></div>)}
        </TabsContent>
      </Tabs>
    </div>
  );

  if (loading) {
    return (<div className="flex items-center justify-center h-64"><div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-[#08263e]"></div></div>);
  }

  return (
    <div className="space-y-6" data-testid="building-management-page">
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-gray-800">Building Management</h1>
          <p className="text-gray-500 flex items-center gap-1.5">{buildings.length} buildings configured <HelpTip text="Add buildings, configure floors with layout images, and manage parking slots per floor." /></p>
        </div>
        <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
          <DialogTrigger asChild>
            <Button className="bg-[#08263e] hover:bg-[#051a2d] text-white" data-testid="add-building-btn"><Plus className="w-4 h-4 mr-2" /> Add Building</Button>
          </DialogTrigger>
          <DialogContent className="max-w-lg max-h-[90vh] overflow-y-auto">
            <DialogHeader><DialogTitle>Add New Building</DialogTitle></DialogHeader>
            <form onSubmit={handleCreateBuilding} className="space-y-4 mt-4">
              <div className="space-y-2">
                <Label>Building Name * <span className="text-xs text-gray-400">(max 30 chars)</span></Label>
                <Input value={newBuilding.name} onChange={(e) => setNewBuilding({ ...newBuilding, name: e.target.value.slice(0, 30) })} placeholder="e.g., Cebuana Tower A" required maxLength={30} data-testid="building-name-input" />
              </div>
              <div className="space-y-2">
                <Label>Address Line 1 * <span className="text-xs text-gray-400">(max 30 chars)</span></Label>
                <Input value={newBuilding.address_line_1} onChange={(e) => setNewBuilding({ ...newBuilding, address_line_1: e.target.value.slice(0, 30) })} placeholder="e.g., 123 Ayala Avenue" required maxLength={30} data-testid="building-address-line1-input" />
              </div>
              <div className="space-y-2">
                <Label>Address Line 2 <span className="text-xs text-gray-400">(max 30 chars)</span></Label>
                <Input value={newBuilding.address_line_2} onChange={(e) => setNewBuilding({ ...newBuilding, address_line_2: e.target.value.slice(0, 30) })} placeholder="e.g., Makati City, Metro Manila" maxLength={30} data-testid="building-address-line2-input" />
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2"><Label>Floors</Label><Input type="number" min="1" max="50" value={newBuilding.total_floors} onChange={(e) => setNewBuilding({ ...newBuilding, total_floors: parseInt(e.target.value) || 1 })} data-testid="building-floors-input" /></div>
                <div className="space-y-2"><Label>Slots/Floor</Label><Input type="number" min="1" max="200" value={newBuilding.slots_per_floor} onChange={(e) => setNewBuilding({ ...newBuilding, slots_per_floor: parseInt(e.target.value) || 10 })} data-testid="building-slots-input" /></div>
              </div>
              <div className="space-y-2"><Label>Slot Prefix</Label><Input value={newBuilding.slot_prefix} onChange={(e) => setNewBuilding({ ...newBuilding, slot_prefix: e.target.value })} placeholder="e.g. A-, P1-" data-testid="building-slot-prefix-input" /></div>
              <div className="flex gap-3 pt-4">
                <Button type="button" variant="outline" className="flex-1" onClick={() => setDialogOpen(false)}>Cancel</Button>
                <Button type="submit" className="flex-1 bg-[#08263e] hover:bg-[#051a2d] text-white" disabled={submitting} data-testid="save-building-btn">{submitting ? 'Creating...' : 'Create Building'}</Button>
              </div>
            </form>
          </DialogContent>
        </Dialog>
      </div>

      {/* Summary Stats */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <Card><CardContent className="p-4 text-center">
          <div className="flex items-center justify-center gap-2 mb-1"><Building2 className="w-4 h-4 text-[#08263e]" /></div>
          <p className="text-2xl font-bold text-[#08263e]" data-testid="total-buildings">{buildings.length}</p>
          <p className="text-xs text-gray-500">Buildings</p>
        </CardContent></Card>
        <Card><CardContent className="p-4 text-center">
          <div className="flex items-center justify-center gap-2 mb-1"><Layers className="w-4 h-4 text-[#518dca]" /></div>
          <p className="text-2xl font-bold text-[#518dca]" data-testid="total-floors">{totalFloors}</p>
          <p className="text-xs text-gray-500">Floors</p>
        </CardContent></Card>
        <Card><CardContent className="p-4 text-center">
          <div className="flex items-center justify-center gap-2 mb-1"><ParkingSquare className="w-4 h-4 text-gray-600" /></div>
          <p className="text-2xl font-bold text-gray-700" data-testid="total-slots">{totalSlots}</p>
          <p className="text-xs text-gray-500">Total Slots</p>
        </CardContent></Card>
        <Card><CardContent className="p-4 text-center">
          <div className="flex items-center justify-center gap-2 mb-1"><Check className="w-4 h-4 text-green-600" /></div>
          <p className="text-2xl font-bold text-green-600" data-testid="available-slots">{availableSlots}</p>
          <p className="text-xs text-gray-500">Available</p>
        </CardContent></Card>
      </div>

      {/* Search */}
      {buildings.length > 0 && (
        <div className="relative">
          <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-gray-400" />
          <Input placeholder="Search buildings by name or address..." value={searchTerm} onChange={(e) => setSearchTerm(e.target.value)} className="pl-10" data-testid="search-buildings-input" />
        </div>
      )}

      {/* Floor & Slots Dialogs */}
      <Dialog open={addFloorDialogOpen} onOpenChange={setAddFloorDialogOpen}>
        <DialogContent className="max-w-lg max-h-[90vh] overflow-y-auto">
          <DialogHeader><DialogTitle>Add New Floor</DialogTitle></DialogHeader>
          <form onSubmit={handleAddFloor} className="space-y-4 mt-4">
            <div className="space-y-2">
              <Label>Floor Label * <span className="text-xs text-gray-400">(max 16 chars)</span></Label>
              <Input value={newFloor.label} onChange={(e) => setNewFloor({ ...newFloor, label: e.target.value.slice(0, 16) })} placeholder="e.g., Basement 2" required maxLength={16} data-testid="floor-label-input" />
            </div>
            <SlotNamingUI data={newFloor} setData={setNewFloor} />
            <div className="flex gap-3 pt-4">
              <Button type="button" variant="outline" className="flex-1" onClick={() => setAddFloorDialogOpen(false)}>Cancel</Button>
              <Button type="submit" className="flex-1 bg-[#08263e] hover:bg-[#051a2d] text-white" disabled={submitting} data-testid="save-floor-btn">{submitting ? 'Adding...' : 'Add Floor'}</Button>
            </div>
          </form>
        </DialogContent>
      </Dialog>

      <Dialog open={addSlotsDialogOpen} onOpenChange={setAddSlotsDialogOpen}>
        <DialogContent className="max-w-lg max-h-[90vh] overflow-y-auto">
          <DialogHeader><DialogTitle>Add Slots to Floor</DialogTitle></DialogHeader>
          <form onSubmit={handleAddSlots} className="space-y-4 mt-4">
            <SlotNamingUI data={bulkSlots} setData={setBulkSlots} />
            <div className="flex gap-3 pt-4">
              <Button type="button" variant="outline" className="flex-1" onClick={() => setAddSlotsDialogOpen(false)}>Cancel</Button>
              <Button type="submit" className="flex-1 bg-[#08263e] hover:bg-[#051a2d] text-white" disabled={submitting} data-testid="save-bulk-slots-btn">{submitting ? 'Adding...' : 'Add Slots'}</Button>
            </div>
          </form>
        </DialogContent>
      </Dialog>

      {/* Buildings List */}
      {filteredBuildings.length === 0 && buildings.length === 0 ? (
        <Card className="border-dashed border-2 border-gray-200">
          <CardContent className="p-12 text-center">
            <Building2 className="w-16 h-16 mx-auto text-gray-300 mb-4" />
            <h3 className="text-lg font-semibold text-gray-600 mb-2">No Buildings</h3>
            <p className="text-gray-500 mb-4">Add your first building to start</p>
            <Button className="bg-[#08263e] hover:bg-[#051a2d] text-white" onClick={() => setDialogOpen(true)}><Plus className="w-4 h-4 mr-2" /> Add Building</Button>
          </CardContent>
        </Card>
      ) : filteredBuildings.length === 0 ? (
        <Card className="border-dashed border-2 border-gray-200">
          <CardContent className="p-8 text-center">
            <Search className="w-12 h-12 mx-auto text-gray-300 mb-3" />
            <p className="text-gray-500">No buildings match your search</p>
          </CardContent>
        </Card>
      ) : (
        <div className="grid gap-6">
          {filteredBuildings.map((building) => {
            const bFloors = building.floors?.length || 0;
            const bSlots = (building.floors || []).reduce((s, f) => s + (f.slots?.length || 0), 0);
            const bAvail = (building.floors || []).reduce((s, f) => s + (f.slots?.filter(sl => sl.status === 'available').length || 0), 0);

            return (
              <Card key={building.id} className="overflow-hidden" data-testid={`building-card-${building.id}`}>
                <CardHeader className="bg-gradient-to-r from-[#08263e] to-[#0a3152] text-white">
                  <div className="flex items-start justify-between">
                    <div className="flex items-center gap-3">
                      <div className="w-12 h-12 bg-white/15 rounded-lg flex items-center justify-center">
                        <Building2 className="w-7 h-7" />
                      </div>
                      <div>
                        <CardTitle className="text-xl break-words">{building.name}</CardTitle>
                        <p className="text-white/70 text-sm flex items-center gap-1 mt-1 break-words"><MapPin className="w-4 h-4 flex-shrink-0" /> {building.address || `${building.address_line_1 || ''}${building.address_line_2 ? ', ' + building.address_line_2 : ''}`}</p>
                      </div>
                    </div>
                    <div className="flex items-center gap-2">
                      <Button variant="ghost" size="sm" className="text-white/70 hover:text-white hover:bg-white/20"
                        onClick={() => handleEditBuilding(building)}
                        data-testid={`edit-building-btn-${building.id}`}><Pencil className="w-4 h-4" /></Button>
                      <Button variant="ghost" size="sm" className="text-white/70 hover:text-white hover:bg-white/20"
                        onClick={() => { setSelectedBuildingId(building.id); setAddFloorDialogOpen(true); }}
                        data-testid={`add-floor-btn-${building.id}`}><Plus className="w-4 h-4 mr-1" /> Add Floor</Button>
                      <Button variant="ghost" size="sm" className="text-white/70 hover:text-white hover:bg-red-500/20"
                        onClick={() => handleDeleteBuilding(building.id)}
                        data-testid={`delete-building-btn-${building.id}`}><Trash2 className="w-4 h-4" /></Button>
                    </div>
                  </div>
                  {/* Building-level stats */}
                  <div className="flex gap-4 mt-3 text-xs text-white/80">
                    <span>{bFloors} floor{bFloors !== 1 ? 's' : ''}</span>
                    <span>{bSlots} slot{bSlots !== 1 ? 's' : ''}</span>
                    <span className="text-green-300">{bAvail} available</span>
                  </div>
                </CardHeader>

                <CardContent className="p-0">
                  {building.floors?.length > 0 ? (
                    <Accordion type="single" collapsible>
                      {building.floors.map((floor) => {
                        const { available, total } = getSlotStatusCounts(floor);
                        return (
                          <AccordionItem key={floor.id} value={floor.id}>
                            <AccordionTrigger className="px-4 hover:no-underline">
                              <div className="flex items-center justify-between w-full pr-4">
                                <div className="flex items-center gap-3">
                                  <div className="w-8 h-8 bg-[#08263e]/10 rounded-lg flex items-center justify-center"><Layers className="w-4 h-4 text-[#08263e]" /></div>
                                  <span className="font-medium">{floor.label}</span>
                                  {floor.layout_image_url && (
                                    <Badge variant="outline" className="text-xs text-green-600 border-green-200"><Image className="w-3 h-3 mr-1" /> Layout</Badge>
                                  )}
                                </div>
                                <div className="flex items-center gap-2">
                                  <Badge variant="outline" className="bg-green-50 text-green-700">{available} available</Badge>
                                  <Badge variant="outline">{total} total</Badge>
                                </div>
                              </div>
                            </AccordionTrigger>
                            <AccordionContent>
                              <div className="px-4 pb-4 space-y-4">
                                {/* Floor Layout Image */}
                                <div className="flex items-center gap-3 p-3 bg-gray-50 rounded-lg">
                                  <Image className="w-5 h-5 text-gray-400 shrink-0" />
                                  <div className="flex-1">
                                    <p className="text-sm font-medium text-gray-700">Floor Layout Image</p>
                                    <p className="text-xs text-gray-500">Upload a reference image for this floor</p>
                                  </div>
                                  {floor.layout_image_url ? (
                                    <div className="flex gap-2">
                                      <a href={`${API_URL}${floor.layout_image_url}`} target="_blank" rel="noreferrer" className="text-xs text-[#08263e] hover:underline">View</a>
                                      <Button variant="ghost" size="sm" className="h-7 text-xs text-red-600" onClick={() => handleDeleteLayout(floor.id)}>Remove</Button>
                                    </div>
                                  ) : (
                                    <>
                                      <input type="file" accept="image/*" className="hidden"
                                        onChange={(e) => { if (e.target.files[0]) handleUploadLayout(floor.id, e.target.files[0]); }}
                                        id={`layout-input-${floor.id}`} />
                                      <Button variant="outline" size="sm" className="h-7 text-xs" disabled={uploadingLayout === floor.id}
                                        onClick={() => document.getElementById(`layout-input-${floor.id}`)?.click()}
                                        data-testid={`upload-layout-btn-${floor.id}`}>
                                        <Upload className="w-3 h-3 mr-1" />{uploadingLayout === floor.id ? 'Uploading...' : 'Upload'}
                                      </Button>
                                    </>
                                  )}
                                </div>

                                {/* Slots Grid */}
                                <div className="bg-gray-50 rounded-lg p-4">
                                  <div className="grid grid-cols-5 md:grid-cols-10 gap-2">
                                    {floor.slots?.map((slot) => (
                                      <div key={slot.id} className="group relative">
                                        {editingSlotId === slot.id ? (
                                          <div className="flex flex-col gap-1">
                                            <Input value={editSlotLabel} onChange={(e) => setEditSlotLabel(e.target.value.toUpperCase())} className="h-8 text-xs font-mono text-center uppercase px-1" autoFocus
                                              onKeyDown={(e) => { if (e.key === 'Enter') handleRenameSlot(slot.id); if (e.key === 'Escape') setEditingSlotId(null); }}
                                              data-testid={`edit-slot-input-${slot.id}`} />
                                            <div className="flex gap-1">
                                              <Button size="sm" variant="ghost" className="h-6 w-6 p-0 text-green-600" onClick={() => handleRenameSlot(slot.id)}><Check className="w-3 h-3" /></Button>
                                              <Button size="sm" variant="ghost" className="h-6 w-6 p-0 text-gray-400" onClick={() => setEditingSlotId(null)}><X className="w-3 h-3" /></Button>
                                            </div>
                                          </div>
                                        ) : (
                                          <div className="relative group/slot">
                                            <div
                                              className={`aspect-square rounded-lg flex flex-col items-center justify-center gap-0.5 text-xs font-mono cursor-pointer transition-all overflow-hidden p-1
                                                ${slot.status === 'available'
                                                  ? 'bg-green-100 border-2 border-green-300 text-green-700 hover:border-[#08263e] hover:ring-1 hover:ring-[#08263e]'
                                                  : slot.status === 'maintenance'
                                                    ? 'bg-red-50 border-2 border-red-300 text-red-700'
                                                    : 'bg-gray-200 border-2 border-gray-300 text-gray-500'}`}
                                              onClick={() => { setEditingSlotId(slot.id); setEditSlotLabel(slot.label); }}
                                              title={slot.status === 'maintenance' ? `${slot.label} — Blocked` : slot.label}
                                              data-testid={`slot-${slot.id}`}>
                                              <span className="truncate px-0.5 max-w-full leading-tight">{slot.label}</span>
                                              {slot.status === 'maintenance' && <span className="text-[8px] font-semibold uppercase tracking-wider opacity-90 leading-none" data-testid={`slot-blocked-${slot.id}`}>Blocked</span>}
                                            </div>
                                            {/* Hover action buttons */}
                                            <div className="absolute -top-2 -right-2 hidden group-hover/slot:flex gap-0.5 z-10">
                                              <Button
                                                size="sm" variant="ghost"
                                                className={`h-5 w-5 p-0 rounded-full shadow-sm ${slot.status === 'maintenance' ? 'bg-green-500 hover:bg-green-600 text-white' : 'bg-yellow-500 hover:bg-yellow-600 text-white'}`}
                                                onClick={(e) => { e.stopPropagation(); handleToggleSlotStatus(slot); }}
                                                title={slot.status === 'maintenance' ? 'Unblock slot' : 'Block slot'}
                                                data-testid={`toggle-slot-${slot.id}`}>
                                                {slot.status === 'maintenance' ? <Check className="w-2.5 h-2.5" /> : <X className="w-2.5 h-2.5" />}
                                              </Button>
                                              <Button
                                                size="sm" variant="ghost"
                                                className="h-5 w-5 p-0 rounded-full bg-red-500 hover:bg-red-600 text-white shadow-sm"
                                                onClick={(e) => { e.stopPropagation(); handleDeleteSlot(slot.id); }}
                                                title="Delete slot"
                                                data-testid={`delete-slot-${slot.id}`}>
                                                <Trash2 className="w-2.5 h-2.5" />
                                              </Button>
                                            </div>
                                          </div>
                                        )}
                                      </div>
                                    ))}
                                  </div>
                                  <div className="flex items-center justify-between mt-4 pt-3 border-t border-gray-200">
                                    <div className="flex items-center gap-4 text-xs text-gray-500">
                                      <div className="flex items-center gap-1"><div className="w-3 h-3 bg-green-100 border border-green-300 rounded"></div><span>Available</span></div>
                                      <div className="flex items-center gap-1"><div className="w-3 h-3 bg-gray-200 border border-gray-300 rounded"></div><span>Reserved</span></div>
                                      <div className="flex items-center gap-1"><div className="w-3 h-3 bg-red-50 border border-red-300 rounded"></div><span>Blocked</span></div>
                                    </div>
                                    <Button variant="outline" size="sm" className="text-[#08263e] border-[#08263e]/30 hover:bg-[#08263e]/5"
                                      onClick={() => { setSelectedFloorId(floor.id); setAddSlotsDialogOpen(true); }}
                                      data-testid={`add-slots-btn-${floor.id}`}><Grid3x3 className="w-3 h-3 mr-1" /> Add Slots</Button>
                                  </div>
                                </div>
                              </div>
                            </AccordionContent>
                          </AccordionItem>
                        );
                      })}
                    </Accordion>
                  ) : (
                    <div className="p-8 text-center text-gray-500">
                      <Layers className="w-12 h-12 mx-auto text-gray-300 mb-3" />
                      <p>No floors configured</p>
                      <Button variant="outline" size="sm" className="mt-2"
                        onClick={() => { setSelectedBuildingId(building.id); setAddFloorDialogOpen(true); }}>Add First Floor</Button>
                    </div>
                  )}
                </CardContent>
              </Card>
            );
          })}
        </div>
      )}

      {/* Edit Building Dialog */}
      <Dialog open={editBuildingDialogOpen} onOpenChange={setEditBuildingDialogOpen}>
        <DialogContent className="max-w-lg">
          <DialogHeader><DialogTitle>Edit Building</DialogTitle></DialogHeader>
          <form onSubmit={handleUpdateBuilding} className="space-y-4 mt-4">
            <div className="space-y-2">
              <Label>Building Name * <span className="text-xs text-gray-400">(max 30 chars)</span></Label>
              <Input value={editingBuilding?.name || ''} onChange={(e) => setEditingBuilding({ ...editingBuilding, name: e.target.value.slice(0, 30) })} placeholder="e.g., Cebuana Tower A" required maxLength={30} data-testid="edit-building-name-input" />
            </div>
            <div className="space-y-2">
              <Label>Address Line 1 * <span className="text-xs text-gray-400">(max 30 chars)</span></Label>
              <Input value={editingBuilding?.address_line_1 || ''} onChange={(e) => setEditingBuilding({ ...editingBuilding, address_line_1: e.target.value.slice(0, 30) })} placeholder="e.g., 123 Ayala Avenue" required maxLength={30} data-testid="edit-building-address-line1-input" />
            </div>
            <div className="space-y-2">
              <Label>Address Line 2 <span className="text-xs text-gray-400">(max 30 chars)</span></Label>
              <Input value={editingBuilding?.address_line_2 || ''} onChange={(e) => setEditingBuilding({ ...editingBuilding, address_line_2: e.target.value.slice(0, 30) })} placeholder="e.g., Makati City, Metro Manila" maxLength={30} data-testid="edit-building-address-line2-input" />
            </div>
            <div className="flex gap-3 pt-4">
              <Button type="button" variant="outline" className="flex-1" onClick={() => setEditBuildingDialogOpen(false)}>Cancel</Button>
              <Button type="submit" className="flex-1 bg-[#08263e] hover:bg-[#051a2d] text-white" disabled={submitting} data-testid="update-building-btn">{submitting ? 'Updating...' : 'Update Building'}</Button>
            </div>
          </form>
        </DialogContent>
      </Dialog>
    </div>
  );
};

export default BuildingManagement;
