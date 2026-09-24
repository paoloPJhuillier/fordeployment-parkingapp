import React, { useState, useEffect } from 'react';
import { zonesAPI, usersAPI, buildingsAPI } from '../../services/api';
import { Button } from '../../components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '../../components/ui/card';
import { Input } from '../../components/ui/input';
import { Label } from '../../components/ui/label';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '../../components/ui/dialog';
import { Badge } from '../../components/ui/badge';
import { Checkbox } from '../../components/ui/checkbox';
import { toast } from 'sonner';
import { 
  Plus, MapPinned, Trash2, Users, Edit,
  Building2, Search, X, UserCheck, Shield
} from 'lucide-react';
import { HelpTip } from '../../components/ui/help-tip';

const ZoneManagement = () => {
  const [zones, setZones] = useState([]);
  const [users, setUsers] = useState([]);
  const [buildings, setBuildings] = useState([]);
  const [loading, setLoading] = useState(true);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [editingZone, setEditingZone] = useState(null);
  const [submitting, setSubmitting] = useState(false);
  const [userSearch, setUserSearch] = useState('');

  const [form, setForm] = useState({
    name: '',
    building_ids: [],
    user_ids: []
  });

  useEffect(() => { fetchData(); }, []);

  const fetchData = async (retryCount = 0) => {
    try {
      const [zonesRes, usersRes, buildingsRes] = await Promise.all([
        zonesAPI.getAll(),
        usersAPI.getAll(),
        buildingsAPI.getAll()
      ]);
      setZones(zonesRes.data);
      setUsers(usersRes.data.filter(u => u.role === 'user'));
      setBuildings(buildingsRes.data);
    } catch (error) {
      if (retryCount < 1 && error?.response?.status !== 403) {
        await new Promise(r => setTimeout(r, 800));
        return fetchData(retryCount + 1);
      }
      if (error?.response?.status !== 401) toast.error('Failed to load data');
    } finally {
      setLoading(false);
    }
  };

  const openCreateDialog = () => {
    setEditingZone(null);
    setForm({ name: '', building_ids: [], user_ids: [] });
    setUserSearch('');
    setDialogOpen(true);
  };

  const openEditDialog = (zone) => {
    setEditingZone(zone);
    setForm({
      name: zone.name,
      building_ids: [...(zone.building_ids || [])],
      user_ids: [...(zone.user_ids || [])]
    });
    setUserSearch('');
    setDialogOpen(true);
  };

  const toggleUser = (userId) => {
    setForm(prev => ({
      ...prev,
      user_ids: prev.user_ids.includes(userId)
        ? prev.user_ids.filter(id => id !== userId)
        : [...prev.user_ids, userId]
    }));
  };

  const toggleBuilding = (buildingId) => {
    setForm(prev => ({
      ...prev,
      building_ids: prev.building_ids.includes(buildingId)
        ? prev.building_ids.filter(id => id !== buildingId)
        : [...prev.building_ids, buildingId]
    }));
  };

  const selectAllFilteredUsers = () => {
    const filtered = getFilteredUsers();
    const allIds = filtered.map(u => u.id);
    const currentSet = new Set(form.user_ids);
    const allSelected = allIds.every(id => currentSet.has(id));
    if (allSelected) {
      setForm(prev => ({ ...prev, user_ids: prev.user_ids.filter(id => !allIds.includes(id)) }));
    } else {
      setForm(prev => ({ ...prev, user_ids: [...new Set([...prev.user_ids, ...allIds])] }));
    }
  };

  const getFilteredUsers = () => {
    if (!userSearch) return users;
    const term = userSearch.toLowerCase();
    return users.filter(u =>
      u.first_name.toLowerCase().includes(term) ||
      u.last_name.toLowerCase().includes(term) ||
      u.email.toLowerCase().includes(term) ||
      (u.company || '').toLowerCase().includes(term)
    );
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    if (!form.name) {
      toast.error('Zone name is required');
      return;
    }
    if (form.building_ids.length === 0) {
      toast.error('Select at least one building');
      return;
    }
    setSubmitting(true);
    try {
      if (editingZone) {
        await zonesAPI.update(editingZone.id, form);
        toast.success('Zone updated');
      } else {
        await zonesAPI.create(form);
        toast.success('Zone created');
      }
      setDialogOpen(false);
      fetchData();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to save zone');
    } finally {
      setSubmitting(false);
    }
  };

  const handleDelete = async (zoneId) => {
    if (!window.confirm('Delete this zone?')) return;
    try {
      await zonesAPI.delete(zoneId);
      toast.success('Zone deleted');
      fetchData();
    } catch (error) {
      toast.error('Failed to delete zone');
    }
  };

  const getBuildingName = (buildingId) => buildings.find(b => b.id === buildingId)?.name || null;
  const getBuildingExists = (buildingId) => buildings.some(b => b.id === buildingId);
  const getUserName = (userId) => {
    const u = users.find(u => u.id === userId);
    return u ? `${u.first_name} ${u.last_name}` : 'Unknown';
  };

  const getUserZoneMap = () => {
    const map = {};
    zones.forEach(z => {
      (z.user_ids || []).forEach(uid => {
        if (!map[uid]) map[uid] = new Set();
        (z.building_ids || []).forEach(bid => map[uid].add(bid));
      });
    });
    return map;
  };

  const userZoneMap = getUserZoneMap();
  const assignedUserCount = Object.keys(userZoneMap).length;
  const unassignedUsers = users.filter(u => !userZoneMap[u.id]);
  const filteredUsers = getFilteredUsers();

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-[#08263e]"></div>
      </div>
    );
  }

  return (
    <div className="space-y-6" data-testid="zone-management-page">
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-gray-800">Zone Management</h1>
          <p className="text-gray-500 flex items-center gap-1.5">Manage zones and building groups <HelpTip text="A zone groups multiple buildings together. Users assigned to a zone can book parking in any building within it. Booking outside your main building requires a reason." /></p>
        </div>
        <Button className="bg-[#08263e] hover:bg-[#051a2d] text-white" onClick={openCreateDialog} data-testid="add-zone-btn">
          <Plus className="w-4 h-4 mr-2" /> Create Zone
        </Button>
      </div>

      {/* Summary Cards */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <Card><CardContent className="p-4 text-center">
          <p className="text-sm text-gray-500">Total Zones</p>
          <p className="text-2xl font-bold text-[#08263e]" data-testid="stat-zones">{zones.length}</p>
        </CardContent></Card>
        <Card><CardContent className="p-4 text-center">
          <p className="text-sm text-gray-500">Buildings in Zones</p>
          <p className="text-2xl font-bold text-[#08263e]">{new Set(zones.flatMap(z => z.building_ids || [])).size}</p>
        </CardContent></Card>
        <Card><CardContent className="p-4 text-center">
          <p className="text-sm text-green-600">Assigned Users</p>
          <p className="text-2xl font-bold text-green-600">{assignedUserCount}</p>
        </CardContent></Card>
        <Card><CardContent className="p-4 text-center">
          <p className="text-sm text-orange-600">Unassigned Users</p>
          <p className="text-2xl font-bold text-orange-600" data-testid="stat-unassigned">{unassignedUsers.length}</p>
        </CardContent></Card>
      </div>

      {/* Unassigned Users Warning */}
      {unassignedUsers.length > 0 && (
        <Card className="border-orange-200 bg-orange-50/50">
          <CardContent className="p-4">
            <div className="flex items-start gap-3">
              <Shield className="w-5 h-5 text-orange-500 mt-0.5 shrink-0" />
              <div>
                <p className="font-medium text-gray-800 text-sm">
                  {unassignedUsers.length} user{unassignedUsers.length > 1 ? 's' : ''} not assigned to any zone
                </p>
                <p className="text-xs text-gray-500 mt-1">
                  Users without zone assignment can only book in their main building (if set) or buildings without zone restrictions.
                </p>
                <div className="flex flex-wrap gap-1 mt-2">
                  {unassignedUsers.slice(0, 5).map(u => (
                    <Badge key={u.id} variant="outline" className="text-xs bg-white">
                      {u.first_name} {u.last_name}
                    </Badge>
                  ))}
                  {unassignedUsers.length > 5 && (
                    <Badge variant="outline" className="text-xs bg-white">+{unassignedUsers.length - 5} more</Badge>
                  )}
                </div>
              </div>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Zone Cards */}
      {zones.length === 0 ? (
        <Card className="border-dashed border-2 border-gray-200">
          <CardContent className="p-12 text-center">
            <MapPinned className="w-16 h-16 mx-auto text-gray-300 mb-4" />
            <h3 className="text-lg font-semibold text-gray-600 mb-2">No Zones Configured</h3>
            <p className="text-gray-500 mb-1">Zones group buildings together and control user access.</p>
            <p className="text-sm text-gray-400 mb-4">Without zones, users can only book in their main building.</p>
            <Button className="bg-[#08263e] hover:bg-[#051a2d] text-white" onClick={openCreateDialog}>
              <Plus className="w-4 h-4 mr-2" /> Create First Zone
            </Button>
          </CardContent>
        </Card>
      ) : (
        <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
          {zones.map((zone) => (
            <Card key={zone.id} className="overflow-hidden" data-testid={`zone-card-${zone.id}`}>
              <CardHeader className="pb-3 bg-gradient-to-r from-[#08263e] to-[#518dca] text-white">
                <div className="flex items-start justify-between">
                  <div>
                    <CardTitle className="text-base">{zone.name}</CardTitle>
                    <p className="text-white/70 text-xs mt-1">
                      {(zone.building_ids || []).length} building{(zone.building_ids || []).length !== 1 ? 's' : ''}
                    </p>
                  </div>
                  <div className="flex gap-1">
                    <Button variant="ghost" size="sm" className="h-7 w-7 p-0 text-white/70 hover:text-white hover:bg-white/20"
                      onClick={() => openEditDialog(zone)} data-testid={`edit-zone-${zone.id}`}>
                      <Edit className="w-3.5 h-3.5" />
                    </Button>
                    <Button variant="ghost" size="sm" className="h-7 w-7 p-0 text-white/70 hover:text-red-300 hover:bg-red-500/20"
                      onClick={() => handleDelete(zone.id)} data-testid={`delete-zone-${zone.id}`}>
                      <Trash2 className="w-3.5 h-3.5" />
                    </Button>
                  </div>
                </div>
              </CardHeader>
              <CardContent className="p-4 space-y-3">
                {/* Buildings */}
                <div>
                  <p className="text-xs font-medium text-gray-500 mb-1.5">Buildings</p>
                  <div className="flex flex-wrap gap-1">
                    {(zone.building_ids || []).filter(bid => getBuildingExists(bid)).map(bid => (
                      <Badge key={bid} variant="outline" className="text-xs">
                        <Building2 className="w-3 h-3 mr-1 text-[#08263e]" />
                        {getBuildingName(bid)}
                      </Badge>
                    ))}
                    {(zone.building_ids || []).filter(bid => getBuildingExists(bid)).length === 0 && (
                      <p className="text-xs text-gray-400 italic">No buildings assigned</p>
                    )}
                  </div>
                </div>
                {/* Users */}
                <div className="flex items-center gap-2 text-sm text-gray-600">
                  <Users className="w-4 h-4 text-gray-400" />
                  <span>{(zone.user_ids || []).length} users assigned</span>
                </div>
                {(zone.user_ids || []).length > 0 && (
                  <div className="flex flex-wrap gap-1">
                    {(zone.user_ids || []).slice(0, 6).map((userId) => (
                      <Badge key={userId} variant="outline" className="text-xs" data-testid={`zone-user-badge-${userId}`}>
                        <UserCheck className="w-3 h-3 mr-1 text-green-500" />
                        {getUserName(userId)}
                      </Badge>
                    ))}
                    {(zone.user_ids || []).length > 6 && (
                      <Badge variant="outline" className="text-xs">+{(zone.user_ids || []).length - 6} more</Badge>
                    )}
                  </div>
                )}
                {(!zone.user_ids || zone.user_ids.length === 0) && (
                  <p className="text-xs text-gray-400 italic">No users assigned yet</p>
                )}
              </CardContent>
            </Card>
          ))}
        </div>
      )}

      {/* Create/Edit Dialog */}
      <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
        <DialogContent className="max-w-lg max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>{editingZone ? 'Edit Zone' : 'Create Zone'}</DialogTitle>
          </DialogHeader>
          <form onSubmit={handleSubmit} className="space-y-4 mt-2">
            <div className="space-y-2">
              <Label>Zone Name * <span className="text-xs text-gray-400">(max 25)</span></Label>
              <Input value={form.name} onChange={(e) => setForm({ ...form, name: e.target.value.slice(0, 25) })}
                placeholder="e.g., Downtown Campus, North Zone" required maxLength={25} data-testid="zone-name-input" />
            </div>

            {/* Buildings Multi-Select */}
            <div className="space-y-2">
              <Label>Buildings ({form.building_ids.length} selected) *</Label>
              <div className="border rounded-lg max-h-40 overflow-y-auto divide-y" data-testid="building-checklist">
                {buildings.length === 0 ? (
                  <p className="p-3 text-sm text-gray-400 text-center">No buildings available</p>
                ) : (
                  buildings.map(b => (
                    <label key={b.id}
                      className={`flex items-center gap-3 p-2.5 cursor-pointer hover:bg-gray-50 transition-colors ${
                        form.building_ids.includes(b.id) ? 'bg-blue-50/50' : ''
                      }`} data-testid={`building-checkbox-${b.id}`}>
                      <Checkbox
                        checked={form.building_ids.includes(b.id)}
                        onCheckedChange={() => toggleBuilding(b.id)}
                      />
                      <div className="flex-1 min-w-0">
                        <p className="text-sm font-medium truncate">{b.name}</p>
                        <p className="text-xs text-gray-500 truncate">{b.address}</p>
                      </div>
                    </label>
                  ))
                )}
              </div>
            </div>

            {/* Users Multi-Select */}
            <div className="space-y-2">
              <div className="flex items-center justify-between">
                <Label>Assign Users ({form.user_ids.length} selected)</Label>
                <Button type="button" variant="ghost" size="sm" className="text-xs text-[#08263e] h-7"
                  onClick={selectAllFilteredUsers} data-testid="select-all-users-btn">
                  {filteredUsers.every(u => form.user_ids.includes(u.id)) ? 'Deselect All' : 'Select All'}
                </Button>
              </div>

              <div className="relative">
                <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
                <Input placeholder="Search users..." value={userSearch}
                  onChange={(e) => setUserSearch(e.target.value)} className="pl-9" data-testid="zone-user-search" />
              </div>

              {form.user_ids.length > 0 && (
                <div className="flex flex-wrap gap-1">
                  {form.user_ids.slice(0, 10).map(uid => {
                    const u = users.find(u => u.id === uid);
                    return u ? (
                      <Badge key={uid} className="bg-[#08263e] text-white text-xs cursor-pointer hover:bg-red-600 transition-colors"
                        onClick={() => toggleUser(uid)} data-testid={`selected-user-${uid}`}>
                        {u.first_name} {u.last_name}
                        <X className="w-3 h-3 ml-1" />
                      </Badge>
                    ) : null;
                  })}
                  {form.user_ids.length > 10 && (
                    <Badge variant="outline" className="text-xs">+{form.user_ids.length - 10} more</Badge>
                  )}
                </div>
              )}

              <div className="border rounded-lg max-h-48 overflow-y-auto divide-y" data-testid="user-checklist">
                {filteredUsers.length === 0 ? (
                  <p className="p-3 text-sm text-gray-400 text-center">No users found</p>
                ) : (
                  filteredUsers.map(u => (
                    <label key={u.id}
                      className={`flex items-center gap-3 p-2.5 cursor-pointer hover:bg-gray-50 transition-colors ${
                        form.user_ids.includes(u.id) ? 'bg-blue-50/50' : ''
                      }`} data-testid={`user-checkbox-${u.id}`}>
                      <Checkbox
                        checked={form.user_ids.includes(u.id)}
                        onCheckedChange={() => toggleUser(u.id)}
                      />
                      <div className="flex-1 min-w-0">
                        <p className="text-sm font-medium truncate">{u.first_name} {u.last_name}</p>
                        <p className="text-xs text-gray-500 truncate">{u.email}</p>
                      </div>
                      {u.company && (
                        <span className="text-xs text-gray-400 shrink-0">{u.company}</span>
                      )}
                    </label>
                  ))
                )}
              </div>
            </div>

            <div className="flex gap-3 pt-4">
              <Button type="button" variant="outline" className="flex-1" onClick={() => setDialogOpen(false)}>Cancel</Button>
              <Button type="submit" className="flex-1 bg-[#08263e] hover:bg-[#051a2d] text-white" disabled={submitting}
                data-testid="save-zone-btn">
                {submitting ? 'Saving...' : (editingZone ? 'Update Zone' : 'Create Zone')}
              </Button>
            </div>
          </form>
        </DialogContent>
      </Dialog>
    </div>
  );
};

export default ZoneManagement;
