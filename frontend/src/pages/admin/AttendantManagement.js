import React, { useState, useEffect, useRef } from 'react';
import { usersAPI, buildingsAPI } from '../../services/api';
import { Button } from '../../components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '../../components/ui/card';
import { Input } from '../../components/ui/input';
import { Label } from '../../components/ui/label';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from '../../components/ui/dialog';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '../../components/ui/table';
import { Badge } from '../../components/ui/badge';
import { Checkbox } from '../../components/ui/checkbox';
import { toast } from 'sonner';
import { Plus, UserCog, Trash2, Edit, Building2 } from 'lucide-react';
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger } from '../../components/ui/dropdown-menu';
import { MoreHorizontal } from 'lucide-react';

const AttendantManagement = () => {
  const [attendants, setAttendants] = useState([]);
  const [buildings, setBuildings] = useState([]);
  const [loading, setLoading] = useState(true);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [editingAttendant, setEditingAttendant] = useState(null);
  const [submitting, setSubmitting] = useState(false);
  const attendantPasswordRef = useRef(null);

  const [formData, setFormData] = useState({
    email: '',
    first_name: '',
    last_name: '',
    company: 'Cebuana Lhuillier',
    role: 'attendant',
    assigned_buildings: []
  });

  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async (retryCount = 0) => {
    try {
      const [usersRes, buildingsRes] = await Promise.all([
        usersAPI.getAll(),
        buildingsAPI.getAll()
      ]);
      setAttendants(usersRes.data.filter(u => u.role === 'attendant'));
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

  const handleSubmit = async (e) => {
    e.preventDefault();
    setSubmitting(true);
    try {
      if (editingAttendant) {
        await usersAPI.update(editingAttendant.id, {
          email: formData.email,
          first_name: formData.first_name,
          last_name: formData.last_name,
          company: formData.company,
          role: 'attendant',
          assigned_buildings: formData.assigned_buildings
        });
        toast.success('Attendant updated successfully');
      } else {
        const password = attendantPasswordRef.current?.value || '';
        await usersAPI.create({ ...formData, password, role: 'attendant' });
        if (attendantPasswordRef.current) attendantPasswordRef.current.value = '';
        toast.success('Attendant created successfully');
      }
      setDialogOpen(false);
      resetForm();
      fetchData();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Operation failed');
    } finally {
      setSubmitting(false);
    }
  };

  const handleDelete = async (attendantId) => {
    if (!window.confirm('Are you sure you want to delete this attendant?')) return;
    
    try {
      await usersAPI.delete(attendantId);
      toast.success('Attendant deleted');
      fetchData();
    } catch (error) {
      toast.error('Failed to delete attendant');
    }
  };

  const handleEdit = (attendant) => {
    setEditingAttendant(attendant);
    setFormData({
      email: attendant.email,
      first_name: attendant.first_name,
      last_name: attendant.last_name,
      company: attendant.company || '',
      role: 'attendant',
      assigned_buildings: attendant.assigned_buildings || []
    });
    setDialogOpen(true);
  };

  const resetForm = () => {
    setEditingAttendant(null);
    if (attendantPasswordRef.current) attendantPasswordRef.current.value = '';
    setFormData({
      email: '',
      first_name: '',
      last_name: '',
      company: 'Cebuana Lhuillier',
      role: 'attendant',
      assigned_buildings: []
    });
  };

  const getBuildingNames = (buildingIds) => {
    return buildingIds?.map(id => buildings.find(b => b.id === id)?.name).filter(Boolean).join(', ') || 'None';
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-[#08263e]"></div>
      </div>
    );
  }

  return (
    <div className="space-y-6" data-testid="attendant-management-page">
      {/* Page Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-gray-800">Parking Attendants</h1>
          <p className="text-gray-500">{attendants.length} attendants configured</p>
        </div>
        
        <Dialog open={dialogOpen} onOpenChange={(open) => { setDialogOpen(open); if (!open) resetForm(); }}>
          <DialogTrigger asChild>
            <Button className="bg-[#08263e] hover:bg-[#051a2d] text-white" data-testid="add-attendant-btn">
              <Plus className="w-4 h-4 mr-2" />
              Add Attendant
            </Button>
          </DialogTrigger>
          <DialogContent>
            <DialogHeader>
              <DialogTitle>{editingAttendant ? 'Edit Attendant' : 'Add New Attendant'}</DialogTitle>
            </DialogHeader>
            <form onSubmit={handleSubmit} className="space-y-4 mt-4">
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label>First Name * <span className="text-xs text-gray-400">(max 30)</span></Label>
                  <Input
                    value={formData.first_name}
                    onChange={(e) => setFormData({ ...formData, first_name: e.target.value.slice(0, 30) })}
                    required
                    maxLength={30}
                    data-testid="attendant-firstname-input"
                  />
                </div>
                <div className="space-y-2">
                  <Label>Last Name * <span className="text-xs text-gray-400">(max 30)</span></Label>
                  <Input
                    value={formData.last_name}
                    onChange={(e) => setFormData({ ...formData, last_name: e.target.value.slice(0, 30) })}
                    required
                    maxLength={30}
                    data-testid="attendant-lastname-input"
                  />
                </div>
              </div>
              
              <div className="space-y-2">
                <Label>Email *</Label>
                <Input
                  type="email"
                  value={formData.email}
                  onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                  required
                  data-testid="attendant-email-input"
                />
              </div>
              
              {!editingAttendant && (
                <div className="space-y-2">
                  <Label>Password *</Label>
                  <Input
                    type="password"
                    ref={attendantPasswordRef}
                    autoComplete="new-password"
                    required
                    data-testid="attendant-password-input"
                  />
                </div>
              )}
              
              <div className="space-y-2">
                <Label>Assigned Buildings *</Label>
                <div className="border rounded-md p-3 max-h-48 overflow-y-auto space-y-2" data-testid="attendant-buildings-checklist">
                  {buildings.map((building) => (
                    <div key={building.id} className="flex items-center space-x-2">
                      <Checkbox
                        id={`building-${building.id}`}
                        checked={formData.assigned_buildings.includes(building.id)}
                        onCheckedChange={(checked) => {
                          if (checked) {
                            setFormData({ ...formData, assigned_buildings: [...formData.assigned_buildings, building.id] });
                          } else {
                            setFormData({ ...formData, assigned_buildings: formData.assigned_buildings.filter(id => id !== building.id) });
                          }
                        }}
                        data-testid={`building-checkbox-${building.id}`}
                      />
                      <label
                        htmlFor={`building-${building.id}`}
                        className="text-sm font-medium leading-none peer-disabled:cursor-not-allowed peer-disabled:opacity-70 cursor-pointer"
                      >
                        {building.name}
                      </label>
                    </div>
                  ))}
                </div>
                {formData.assigned_buildings.length > 0 && (
                  <div className="flex flex-wrap gap-1 mt-2">
                    {formData.assigned_buildings.map(id => (
                      <Badge key={id} variant="secondary" className="text-xs">
                        {buildings.find(b => b.id === id)?.name}
                      </Badge>
                    ))}
                  </div>
                )}
              </div>
              
              <div className="flex gap-3 pt-4">
                <Button type="button" variant="outline" className="flex-1" onClick={() => setDialogOpen(false)}>
                  Cancel
                </Button>
                <Button 
                  type="submit" 
                  className="flex-1 bg-[#08263e] hover:bg-[#051a2d] text-white" 
                  disabled={submitting || (!editingAttendant && formData.assigned_buildings.length === 0)} 
                  data-testid="save-attendant-btn"
                >
                  {submitting ? 'Saving...' : editingAttendant ? 'Update' : 'Create'}
                </Button>
              </div>
              {!editingAttendant && formData.assigned_buildings.length === 0 && (
                <p className="text-xs text-red-500 text-center">Please select an assigned building</p>
              )}
            </form>
          </DialogContent>
        </Dialog>
      </div>

      {/* Attendants List */}
      {attendants.length === 0 ? (
        <Card className="border-dashed border-2 border-gray-200">
          <CardContent className="p-12 text-center">
            <UserCog className="w-16 h-16 mx-auto text-gray-300 mb-4" />
            <h3 className="text-lg font-semibold text-gray-600 mb-2">No Attendants Configured</h3>
            <p className="text-gray-500 mb-4">Add parking attendants to manage daily operations</p>
            <Button 
              className="bg-[#08263e] hover:bg-[#051a2d] text-white"
              onClick={() => setDialogOpen(true)}
            >
              <Plus className="w-4 h-4 mr-2" />
              Add Attendant
            </Button>
          </CardContent>
        </Card>
      ) : (
        <Card>
          <CardContent className="p-0">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Name</TableHead>
                  <TableHead>Email</TableHead>
                  <TableHead>Assigned Building</TableHead>
                  <TableHead className="text-right">Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {attendants.map((attendant) => (
                  <TableRow key={attendant.id} data-testid={`attendant-row-${attendant.id}`}>
                    <TableCell className="font-medium">
                      <div className="flex items-center gap-3">
                        <div className="w-10 h-10 bg-[#08263e]/10 rounded-full flex items-center justify-center">
                          <UserCog className="w-5 h-5 text-[#08263e]" />
                        </div>
                        <span>{attendant.first_name} {attendant.last_name}</span>
                      </div>
                    </TableCell>
                    <TableCell>{attendant.email}</TableCell>
                    <TableCell>
                      <div className="flex items-center gap-2">
                        <Building2 className="w-4 h-4 text-gray-400" />
                        <span>{getBuildingNames(attendant.assigned_buildings) || 'Not assigned'}</span>
                      </div>
                    </TableCell>
                    <TableCell className="text-right">
                      <DropdownMenu>
                        <DropdownMenuTrigger asChild>
                          <Button variant="ghost" size="sm">
                            <MoreHorizontal className="w-4 h-4" />
                          </Button>
                        </DropdownMenuTrigger>
                        <DropdownMenuContent align="end">
                          <DropdownMenuItem onClick={() => handleEdit(attendant)}>
                            <Edit className="w-4 h-4 mr-2" />
                            Edit
                          </DropdownMenuItem>
                          <DropdownMenuItem 
                            onClick={() => handleDelete(attendant.id)}
                            className="text-red-600"
                          >
                            <Trash2 className="w-4 h-4 mr-2" />
                            Delete
                          </DropdownMenuItem>
                        </DropdownMenuContent>
                      </DropdownMenu>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </CardContent>
        </Card>
      )}
    </div>
  );
};

export default AttendantManagement;
