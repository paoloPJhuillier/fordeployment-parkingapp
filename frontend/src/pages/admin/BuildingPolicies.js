import { useState, useEffect, useCallback } from 'react';
import { buildingsAPI, buildingPolicyAPI, slotRegistrationAPI } from '../../services/api';
import { Button } from '../../components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '../../components/ui/card';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../../components/ui/select';
import { Input } from '../../components/ui/input';
import { Label } from '../../components/ui/label';
import { Badge } from '../../components/ui/badge';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '../../components/ui/dialog';
import { toast } from 'sonner';
import { Shield, Building2, Users, Plus, Trash2, Car, Loader2, ToggleLeft, ToggleRight, ChevronDown, ChevronUp, CheckCircle2 } from 'lucide-react';

export default function BuildingPolicies() {
  const [buildings, setBuildings] = useState([]);
  const [policies, setPolicies] = useState([]);
  const [selectedBuilding, setSelectedBuilding] = useState('');
  const [currentPolicy, setCurrentPolicy] = useState(null);
  const [registrations, setRegistrations] = useState([]);
  const [loading, setLoading] = useState(true);
  const [users, setUsers] = useState([]);
  const [allVehicles, setAllVehicles] = useState([]);
  const [floors, setFloors] = useState([]);
  const [slots, setSlots] = useState([]);
  const [regDialogOpen, setRegDialogOpen] = useState(false);
  const [regForm, setRegForm] = useState({ slot_id: '', user_id: '', vehicle_plate: '', sticker_number: '' });
  const [expandedFloor, setExpandedFloor] = useState(null);
  const [zoneUserIds, setZoneUserIds] = useState(null);

  const fetchData = useCallback(async () => {
    try {
      const [bRes, pRes] = await Promise.allSettled([
        buildingsAPI.getAll(),
        buildingPolicyAPI.list(),
      ]);
      if (bRes.status === 'fulfilled') setBuildings(bRes.value.data);
      if (pRes.status === 'fulfilled') setPolicies(pRes.value.data);
    } catch {} finally { setLoading(false); }
  }, []);

  useEffect(() => { fetchData(); }, [fetchData]);

  useEffect(() => {
    if (!selectedBuilding) return;
    const loadBuildingData = async () => {
      try {
        const [polRes, regRes] = await Promise.allSettled([
          buildingPolicyAPI.get(selectedBuilding),
          slotRegistrationAPI.list({ building_id: selectedBuilding }),
        ]);
        if (polRes.status === 'fulfilled') setCurrentPolicy(polRes.value.data);
        if (regRes.status === 'fulfilled') setRegistrations(regRes.value.data);

        // Load floors and slots
        const building = buildings.find(b => b.id === selectedBuilding);
        if (building) {
          setFloors(building.floors || []);
          const allSlots = [];
          for (const floor of building.floors || []) {
            (floor.slots || []).forEach(s => allSlots.push({ ...s, floor_id: floor.id, floor_label: floor.label }));
          }
          setSlots(allSlots);
        }

        // Load zones to get user_ids for this building
        try {
          const zonesRes = await fetch(`${process.env.REACT_APP_BACKEND_URL}/api/zones`, { credentials: 'include' });
          const zones = await zonesRes.json();
          const matchingZones = (Array.isArray(zones) ? zones : []).filter(z =>
            (z.building_ids || []).includes(selectedBuilding)
          );
          const uids = new Set();
          matchingZones.forEach(z => (z.user_ids || []).forEach(uid => uids.add(uid)));
          setZoneUserIds(uids.size > 0 ? uids : null);
        } catch {
          setZoneUserIds(null);
        }
      } catch {}
    };
    loadBuildingData();
  }, [selectedBuilding, buildings]);

  useEffect(() => {
    const fetchUsersAndVehicles = async () => {
      try {
        const [usersRes, vehiclesRes] = await Promise.all([
          fetch(`${process.env.REACT_APP_BACKEND_URL}/api/users`, { credentials: 'include' }),
          fetch(`${process.env.REACT_APP_BACKEND_URL}/api/vehicles`, { credentials: 'include' }),
        ]);
        const usersData = await usersRes.json();
        const vehiclesData = await vehiclesRes.json();
        setUsers(Array.isArray(usersData) ? usersData : []);
        setAllVehicles(Array.isArray(vehiclesData) ? vehiclesData : []);
      } catch {}
    };
    fetchUsersAndVehicles();
  }, []);

  const handleTogglePolicy = async () => {
    try {
      if (!currentPolicy || !currentPolicy.id) {
        // Create new
        const res = await buildingPolicyAPI.create({
          building_id: selectedBuilding,
          enabled: true,
          max_users_per_slot: 5,
          open_floor_ids: [],
          requires_sticker: true,
        });
        setCurrentPolicy(res.data);
        toast.success('Dedicated slot policy enabled');
      } else {
        const res = await buildingPolicyAPI.update(selectedBuilding, { enabled: !currentPolicy.enabled });
        setCurrentPolicy(res.data);
        toast.success(res.data.enabled ? 'Policy enabled' : 'Policy disabled');
      }
      fetchData();
    } catch (e) {
      toast.error(e.response?.data?.detail || 'Failed to update policy');
    }
  };

  const handleUpdatePolicy = async (field, value) => {
    try {
      const res = await buildingPolicyAPI.update(selectedBuilding, { [field]: value });
      setCurrentPolicy(res.data);
      toast.success('Policy updated');
    } catch (e) {
      toast.error(e.response?.data?.detail || 'Failed to update');
    }
  };

  const toggleOpenFloor = async (floorId) => {
    const current = currentPolicy?.open_floor_ids || [];
    const updated = current.includes(floorId)
      ? current.filter(id => id !== floorId)
      : [...current, floorId];
    await handleUpdatePolicy('open_floor_ids', updated);
  };

  const handleCreateRegistration = async () => {
    try {
      await slotRegistrationAPI.create(regForm);
      toast.success('Slot registration created');
      setRegDialogOpen(false);
      setRegForm({ slot_id: '', user_id: '', vehicle_plate: '', sticker_number: '' });
      const res = await slotRegistrationAPI.list({ building_id: selectedBuilding });
      setRegistrations(res.data);
    } catch (e) {
      toast.error(e.response?.data?.detail || 'Failed to create registration');
    }
  };

  const handleDeleteRegistration = async (id) => {
    try {
      await slotRegistrationAPI.delete(id);
      toast.success('Registration revoked');
      const res = await slotRegistrationAPI.list({ building_id: selectedBuilding });
      setRegistrations(res.data);
    } catch (e) {
      toast.error('Failed to revoke registration');
    }
  };

  const policyEnabled = currentPolicy?.enabled && currentPolicy?.id;
  const buildingName = buildings.find(b => b.id === selectedBuilding)?.name || '';

  if (loading) return <div className="flex items-center justify-center h-64"><Loader2 className="w-6 h-6 animate-spin text-slate-400" /></div>;

  return (
    <div className="space-y-6" data-testid="building-policies-page">
      <div>
        <h1 className="text-2xl font-bold text-slate-800">Building Policies</h1>
        <p className="text-sm text-slate-500 mt-1">Configure dedicated slot policies and manage slot registrations per building.</p>
      </div>

      {/* Building Selector */}
      <Card>
        <CardContent className="pt-4">
          <Label className="text-xs text-slate-500 mb-1.5 block">Select Building</Label>
          <Select value={selectedBuilding} onValueChange={setSelectedBuilding}>
            <SelectTrigger data-testid="policy-building-select">
              <SelectValue placeholder="Choose a building to configure" />
            </SelectTrigger>
            <SelectContent>
              {buildings.map(b => {
                const hasPolicy = policies.some(p => p.building_id === b.id && p.enabled);
                return (
                  <SelectItem key={b.id} value={b.id}>
                    {b.name} {hasPolicy && '(Policy Active)'}
                  </SelectItem>
                );
              })}
            </SelectContent>
          </Select>
        </CardContent>
      </Card>

      {selectedBuilding && (
        <>
          {/* Policy Toggle & Config */}
          <Card>
            <CardHeader className="pb-3">
              <div className="flex items-center justify-between">
                <CardTitle className="text-base flex items-center gap-2">
                  <Shield className="w-5 h-5 text-indigo-600" />
                  Dedicated Slot Policy — {buildingName}
                </CardTitle>
                <Button
                  variant={policyEnabled ? "default" : "outline"}
                  size="sm"
                  onClick={handleTogglePolicy}
                  className={policyEnabled ? "bg-indigo-600 hover:bg-indigo-700" : ""}
                  data-testid="toggle-policy-btn"
                >
                  {policyEnabled ? <ToggleRight className="w-4 h-4 mr-1.5" /> : <ToggleLeft className="w-4 h-4 mr-1.5" />}
                  {policyEnabled ? 'Enabled' : 'Enable Policy'}
                </Button>
              </div>
            </CardHeader>
            {policyEnabled && (
              <CardContent className="space-y-4">
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <Label className="text-xs text-slate-500">Max Users per Slot</Label>
                    <Input
                      type="number"
                      min={1}
                      max={20}
                      value={currentPolicy?.max_users_per_slot || 5}
                      onChange={e => handleUpdatePolicy('max_users_per_slot', parseInt(e.target.value))}
                      data-testid="max-users-input"
                    />
                  </div>
                  <div className="flex items-end gap-2">
                    <div className="flex-1">
                      <Label className="text-xs text-slate-500">Requires Sticker</Label>
                      <Button
                        variant={currentPolicy?.requires_sticker ? "default" : "outline"}
                        size="sm"
                        className="w-full mt-1"
                        onClick={() => handleUpdatePolicy('requires_sticker', !currentPolicy?.requires_sticker)}
                        data-testid="requires-sticker-btn"
                      >
                        {currentPolicy?.requires_sticker ? 'Yes — Required' : 'No — Not Required'}
                      </Button>
                    </div>
                  </div>
                </div>

                {/* Open Floors */}
                <div>
                  <Label className="text-xs text-slate-500 mb-2 block">Open Parking Floors (exempt from strict slot assignment)</Label>
                  <div className="flex flex-wrap gap-2">
                    {floors.map(f => {
                      const isOpen = (currentPolicy?.open_floor_ids || []).includes(f.id);
                      return (
                        <Badge
                          key={f.id}
                          variant={isOpen ? "default" : "outline"}
                          className={`cursor-pointer transition-colors ${isOpen ? 'bg-emerald-600 hover:bg-emerald-700' : 'hover:bg-slate-100'}`}
                          onClick={() => toggleOpenFloor(f.id)}
                          data-testid={`floor-toggle-${f.id}`}
                        >
                          {f.label} {isOpen ? '(Open)' : ''}
                        </Badge>
                      );
                    })}
                  </div>
                </div>
                
                {/* Save Button */}
                <div className="pt-2 border-t">
                  <p className="text-xs text-green-600 flex items-center gap-1 mb-2">
                    <CheckCircle2 className="w-3 h-3" /> Changes are saved automatically
                  </p>
                </div>
              </CardContent>
            )}
          </Card>

          {/* Slot Registrations */}
          {policyEnabled && (
            <Card>
              <CardHeader className="pb-3">
                <div className="flex items-center justify-between">
                  <CardTitle className="text-base flex items-center gap-2">
                    <Users className="w-5 h-5 text-indigo-600" />
                    Slot Registrations
                    <Badge variant="secondary">{registrations.length}</Badge>
                  </CardTitle>
                  <Button size="sm" onClick={() => setRegDialogOpen(true)} data-testid="add-registration-btn">
                    <Plus className="w-4 h-4 mr-1" /> Register User
                  </Button>
                </div>
              </CardHeader>
              <CardContent>
                {floors.filter(f => !(currentPolicy?.open_floor_ids || []).includes(f.id)).map(floor => {
                  const floorSlots = slots.filter(s => s.floor_id === floor.id);
                  const floorRegs = registrations.filter(r => r.floor_id === floor.id);
                  const isExpanded = expandedFloor === floor.id;
                  return (
                    <div key={floor.id} className="mb-3">
                      <button
                        className="w-full flex items-center justify-between p-2.5 bg-slate-50 rounded-lg hover:bg-slate-100 transition-colors"
                        onClick={() => setExpandedFloor(isExpanded ? null : floor.id)}
                        data-testid={`expand-floor-${floor.id}`}
                      >
                        <div className="flex items-center gap-2">
                          <Building2 className="w-4 h-4 text-slate-500" />
                          <span className="text-sm font-medium">{floor.label}</span>
                          <Badge variant="outline" className="text-xs">{floorSlots.length} slots</Badge>
                          <Badge variant="secondary" className="text-xs">{floorRegs.length} registered</Badge>
                        </div>
                        {isExpanded ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
                      </button>
                      {isExpanded && (
                        <div className="mt-2 space-y-2 pl-4">
                          {floorSlots.map(slot => {
                            const slotRegs = registrations.filter(r => r.slot_id === slot.id);
                            return (
                              <div key={slot.id} className="border rounded-lg p-3">
                                <div className="flex items-center justify-between mb-2">
                                  <span className="text-sm font-mono font-bold text-slate-700">{slot.label}</span>
                                  <span className="text-xs text-slate-400">{slotRegs.length}/{currentPolicy?.max_users_per_slot || 5} users</span>
                                </div>
                                {slotRegs.length === 0 ? (
                                  <p className="text-xs text-slate-400 italic">No registrations</p>
                                ) : (
                                  <div className="space-y-1">
                                    {slotRegs.map(reg => (
                                      <div key={reg.id} className="flex items-center justify-between py-1 px-2 bg-slate-50 rounded text-xs">
                                        <div className="flex items-center gap-2">
                                          <span className="font-medium">{reg.user_name || reg.user_id}</span>
                                          <span className="text-slate-400">|</span>
                                          <Car className="w-3 h-3 text-slate-400" />
                                          <span>{reg.vehicle_plate}</span>
                                          {reg.sticker_number && (
                                            <>
                                              <span className="text-slate-400">|</span>
                                              <Badge variant="outline" className="text-[10px] px-1.5 py-0">{reg.sticker_number}</Badge>
                                            </>
                                          )}
                                        </div>
                                        <Button
                                          variant="ghost"
                                          size="sm"
                                          className="h-6 w-6 p-0 text-red-400 hover:text-red-600"
                                          onClick={() => handleDeleteRegistration(reg.id)}
                                          data-testid={`revoke-reg-${reg.id}`}
                                        >
                                          <Trash2 className="w-3 h-3" />
                                        </Button>
                                      </div>
                                    ))}
                                  </div>
                                )}
                              </div>
                            );
                          })}
                        </div>
                      )}
                    </div>
                  );
                })}

                {/* Open floors info */}
                {floors.filter(f => (currentPolicy?.open_floor_ids || []).includes(f.id)).length > 0 && (
                  <div className="mt-4 p-3 bg-emerald-50 border border-emerald-200 rounded-lg">
                    <p className="text-xs font-medium text-emerald-800">
                      Open Parking Floors (no strict assignment):
                    </p>
                    <div className="flex flex-wrap gap-1 mt-1">
                      {floors.filter(f => (currentPolicy?.open_floor_ids || []).includes(f.id)).map(f => (
                        <Badge key={f.id} className="bg-emerald-100 text-emerald-800 text-xs">{f.label}</Badge>
                      ))}
                    </div>
                  </div>
                )}
              </CardContent>
            </Card>
          )}
        </>
      )}

      {/* Registration Dialog */}
      <Dialog open={regDialogOpen} onOpenChange={setRegDialogOpen}>
        <DialogContent>
          <DialogHeader>
            <DialogTitle>Register User to Slot</DialogTitle>
          </DialogHeader>
          <div className="space-y-4">
            <div>
              <Label>Floor & Slot</Label>
              <Select value={regForm.slot_id} onValueChange={v => setRegForm(p => ({ ...p, slot_id: v }))}>
                <SelectTrigger data-testid="reg-slot-select">
                  <SelectValue placeholder="Select a slot" />
                </SelectTrigger>
                <SelectContent>
                  {floors.filter(f => !(currentPolicy?.open_floor_ids || []).includes(f.id)).map(floor => (
                    slots.filter(s => s.floor_id === floor.id).map(slot => {
                      const count = registrations.filter(r => r.slot_id === slot.id).length;
                      const max = currentPolicy?.max_users_per_slot || 5;
                      return (
                        <SelectItem key={slot.id} value={slot.id} disabled={count >= max}>
                          {floor.label} — {slot.label} ({count}/{max})
                        </SelectItem>
                      );
                    })
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div>
              <Label>User</Label>
              <Select value={regForm.user_id} onValueChange={v => setRegForm(p => ({ ...p, user_id: v, vehicle_plate: '' }))}>
                <SelectTrigger data-testid="reg-user-select">
                  <SelectValue placeholder="Select a user" />
                </SelectTrigger>
                <SelectContent>
                  {users.filter(u => u.role === 'user' && (!zoneUserIds || zoneUserIds.has(u.id))).map(u => (
                    <SelectItem key={u.id} value={u.id}>{u.first_name} {u.last_name} ({u.email})</SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>
            <div>
              <Label>Vehicle</Label>
              {(() => {
                const userVehicles = allVehicles.filter(v => v.user_id === regForm.user_id);
                if (!regForm.user_id) return <p className="text-xs text-slate-400 mt-1">Select a user first</p>;
                if (userVehicles.length === 0) return <p className="text-xs text-amber-600 mt-1">This user has no registered vehicles.</p>;
                return (
                  <Select value={regForm.vehicle_plate} onValueChange={v => setRegForm(p => ({ ...p, vehicle_plate: v }))}>
                    <SelectTrigger data-testid="reg-vehicle-select">
                      <SelectValue placeholder="Select a vehicle" />
                    </SelectTrigger>
                    <SelectContent>
                      {userVehicles.map(v => (
                        <SelectItem key={v.id} value={v.plate_number}>
                          {v.plate_number} — {v.make} {v.model} {v.color ? `(${v.color})` : ''}
                        </SelectItem>
                      ))}
                    </SelectContent>
                  </Select>
                );
              })()}
            </div>
            <div>
              <Label>Parking Sticker Number {currentPolicy?.requires_sticker ? '*' : '(optional)'}</Label>
              <Input
                value={regForm.sticker_number}
                onChange={e => setRegForm(p => ({ ...p, sticker_number: e.target.value }))}
                placeholder="e.g., PSB-001"
                data-testid="reg-sticker-input"
                required={currentPolicy?.requires_sticker}
              />
              {currentPolicy?.requires_sticker && !regForm.sticker_number && (
                <p className="text-xs text-amber-600 mt-1">Sticker number is required for this building's policy</p>
              )}
            </div>
            <Button
              className="w-full"
              onClick={handleCreateRegistration}
              disabled={!regForm.slot_id || !regForm.user_id || !regForm.vehicle_plate || (currentPolicy?.requires_sticker && !regForm.sticker_number)}
              data-testid="submit-registration-btn"
            >
              Register
            </Button>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
}
