import React, { useState, useEffect, useRef } from 'react';
import { usersAPI, buildingsAPI, zonesAPI, templatesAPI } from '../../services/api';
import { Button } from '../../components/ui/button';
import { Card, CardContent } from '../../components/ui/card';
import { Input } from '../../components/ui/input';
import { Label } from '../../components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../../components/ui/select';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from '../../components/ui/dialog';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '../../components/ui/table';
import { Badge } from '../../components/ui/badge';
import { Checkbox } from '../../components/ui/checkbox';
import { toast } from 'sonner';
import { 
  Plus, Upload, Search, Trash2, Edit, FileSpreadsheet,
  Download, Filter, MoreHorizontal, ShieldOff, ShieldCheck,
  Building2, Star, Tag, KeyRound, ChevronLeft, ChevronRight,
  MapPinned, CheckSquare, Users
} from 'lucide-react';
import { HelpTip } from '../../components/ui/help-tip';
import { DropdownMenu, DropdownMenuContent, DropdownMenuItem, DropdownMenuTrigger } from '../../components/ui/dropdown-menu';

const AVAILABLE_TAGS = ['vip', 'group_head'];
const PAGE_SIZE = 15;

const UserManagement = () => {
  const [users, setUsers] = useState([]);
  const [buildings, setBuildings] = useState([]);
  const [loading, setLoading] = useState(true);
  const [searchTerm, setSearchTerm] = useState('');
  const [roleFilter, setRoleFilter] = useState('all');
  const [currentPage, setCurrentPage] = useState(1);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [uploadDialogOpen, setUploadDialogOpen] = useState(false);
  const [mainBuildingDialogOpen, setMainBuildingDialogOpen] = useState(false);
  const [tagsDialogOpen, setTagsDialogOpen] = useState(false);
  const [editingUser, setEditingUser] = useState(null);
  const [selectedUser, setSelectedUser] = useState(null);
  const [submitting, setSubmitting] = useState(false);
  const fileInputRef = useRef(null);

  const [formData, setFormData] = useState({
    email: '', password: 'Changeme1', first_name: '', last_name: '',
    company: 'Cebuana Lhuillier', role: 'user', job_family: '',
    assigned_buildings: [], main_building: null, tags: [],
    default_start_time: '', default_end_time: ''
  });
  const [uploadFile, setUploadFile] = useState(null);
  const [defaultPassword, setDefaultPassword] = useState('changeme123');
  const [selectedMainBuilding, setSelectedMainBuilding] = useState('');
  const [selectedTags, setSelectedTags] = useState([]);
  const [resetPasswordDialogOpen, setResetPasswordDialogOpen] = useState(false);
  const [resetPassword, setResetPassword] = useState('Changeme1');
  const [zones, setZones] = useState([]);
  const [companyFilter, setCompanyFilter] = useState('all');
  const [zoneFilter, setZoneFilter] = useState('all');
  const [buildingFilter, setBuildingFilter] = useState('all');
  const [selectedUserIds, setSelectedUserIds] = useState(new Set());
  const [bulkBuildingDialogOpen, setBulkBuildingDialogOpen] = useState(false);
  const [bulkZoneDialogOpen, setBulkZoneDialogOpen] = useState(false);
  const [bulkBuilding, setBulkBuilding] = useState('');
  const [bulkZone, setBulkZone] = useState('');

  useEffect(() => { fetchData(); }, []);
  useEffect(() => { setCurrentPage(1); setSelectedUserIds(new Set()); }, [searchTerm, roleFilter, companyFilter, zoneFilter, buildingFilter]);

  const fetchData = async (retryCount = 0) => {
    try {
      const [usersRes, buildingsRes, zonesRes] = await Promise.all([
        usersAPI.getAll(), buildingsAPI.getAll(), zonesAPI.getAll()
      ]);
      setUsers(usersRes.data);
      setBuildings(buildingsRes.data);
      setZones(zonesRes.data);
    } catch (error) {
      if (retryCount < 1 && error?.response?.status !== 403) {
        await new Promise(r => setTimeout(r, 800));
        return fetchData(retryCount + 1);
      }
      if (error?.response?.status !== 401) toast.error('Failed to load data');
    }
    finally { setLoading(false); }
  };

  const handleSubmit = async (e) => {
    e.preventDefault();
    setSubmitting(true);
    try {
      if (editingUser) {
        await usersAPI.update(editingUser.id, {
          email: formData.email, first_name: formData.first_name, last_name: formData.last_name,
          company: formData.company, role: formData.role, job_family: formData.job_family,
          assigned_buildings: formData.assigned_buildings, main_building: formData.main_building, tags: formData.tags
        });
        toast.success('User updated successfully');
      } else {
        await usersAPI.create(formData);
        toast.success('User created successfully');
      }
      setDialogOpen(false);
      resetForm();
      fetchData();
    } catch (error) { toast.error(error.response?.data?.detail || 'Operation failed'); }
    finally { setSubmitting(false); }
  };

  const handleBulkUpload = async () => {
    if (!uploadFile) { toast.error('Please select a file'); return; }
    setSubmitting(true);
    try {
      const response = await usersAPI.bulkUpload(uploadFile, defaultPassword);
      toast.success(`Upload complete: ${response.data.created} created, ${response.data.skipped} skipped`);
      setUploadDialogOpen(false);
      setUploadFile(null);
      fetchData();
    } catch (error) { toast.error(error.response?.data?.detail || 'Upload failed'); }
    finally { setSubmitting(false); }
  };

  const handleDelete = async (userId) => {
    if (!window.confirm('Are you sure you want to delete this user?')) return;
    try { await usersAPI.delete(userId); toast.success('User deleted'); fetchData(); }
    catch { toast.error('Failed to delete user'); }
  };

  const handleToggleBlock = async (user) => {
    const action = user.is_blocked ? 'unblock' : 'block';
    if (!window.confirm(`Are you sure you want to ${action} ${user.first_name} ${user.last_name}?`)) return;
    try {
      if (user.is_blocked) { await usersAPI.unblock(user.id); toast.success(`${user.first_name} has been unblocked`); }
      else { await usersAPI.block(user.id); toast.success(`${user.first_name} has been blocked`); }
      fetchData();
    } catch (error) { toast.error(error.response?.data?.detail || `Failed to ${action} user`); }
  };

  const handleEdit = (user) => {
    setEditingUser(user);
    setFormData({
      email: user.email, password: '', first_name: user.first_name, last_name: user.last_name,
      company: user.company || '', role: user.role, job_family: user.job_family || '',
      assigned_buildings: user.assigned_buildings || [], main_building: user.main_building || null, tags: user.tags || [],
      default_start_time: user.default_start_time || '', default_end_time: user.default_end_time || ''
    });
    setDialogOpen(true);
  };

  const handleResetPassword = async () => {
    if (!selectedUser) return;
    setSubmitting(true);
    try {
      await usersAPI.resetPassword(selectedUser.id, resetPassword);
      toast.success(`Password reset for ${selectedUser.first_name}. They will be prompted to change it on next login.`);
      setResetPasswordDialogOpen(false);
    } catch (error) { toast.error(error.response?.data?.detail || 'Failed to reset password'); }
    finally { setSubmitting(false); }
  };

  const handleAssignMainBuilding = async () => {
    if (!selectedUser) return;
    setSubmitting(true);
    try {
      await usersAPI.assignMainBuilding(selectedUser.id, selectedMainBuilding || null);
      toast.success('Main building assigned');
      setMainBuildingDialogOpen(false);
      fetchData();
    } catch (error) { toast.error(error.response?.data?.detail || 'Failed to assign building'); }
    finally { setSubmitting(false); }
  };

  const handleUpdateTags = async () => {
    if (!selectedUser) return;
    setSubmitting(true);
    try {
      await usersAPI.updateTags(selectedUser.id, selectedTags);
      toast.success('Tags updated');
      setTagsDialogOpen(false);
      fetchData();
    } catch (error) { toast.error(error.response?.data?.detail || 'Failed to update tags'); }
    finally { setSubmitting(false); }
  };

  const resetForm = () => {
    setEditingUser(null);
    setFormData({
      email: '', password: 'Changeme1', first_name: '', last_name: '',
      company: 'Cebuana Lhuillier', role: 'user', job_family: '',
      assigned_buildings: [], main_building: null, tags: [],
      default_start_time: '', default_end_time: ''
    });
  };

  const downloadTemplate = async () => {
    try {
      const response = await templatesAPI.downloadUsers();
      const url = window.URL.createObjectURL(new Blob([response.data]));
      const a = document.createElement('a'); a.href = url; a.download = 'users_template.csv'; a.click();
      window.URL.revokeObjectURL(url);
    } catch { toast.error('Failed to download template'); }
  };

  // Build lookup maps
  const getUserZone = (userId) => zones.find(z => (z.user_ids || []).includes(userId));
  const getBuildingName = (bid) => buildings.find(b => b.id === bid)?.name || 'Unknown';
  const companies = [...new Set(users.map(u => u.company).filter(Boolean))].sort();

  const filteredUsers = users.filter(user => {
    const fullName = `${user.first_name} ${user.last_name}`.toLowerCase();
    const matchesSearch = !searchTerm || user.email.toLowerCase().includes(searchTerm.toLowerCase()) ||
      user.first_name.toLowerCase().includes(searchTerm.toLowerCase()) ||
      user.last_name.toLowerCase().includes(searchTerm.toLowerCase()) ||
      fullName.includes(searchTerm.toLowerCase()) ||
      (user.company || '').toLowerCase().includes(searchTerm.toLowerCase());
    const matchesRole = roleFilter === 'all' || user.role === roleFilter;
    const matchesCompany = companyFilter === 'all' || 
      (companyFilter === 'none' && !user.company) ||
      user.company === companyFilter;
    const matchesZone = zoneFilter === 'all' ||
      (zoneFilter === 'none' && !getUserZone(user.id)) ||
      (getUserZone(user.id)?.id === zoneFilter);
    const matchesBuilding = buildingFilter === 'all' ||
      (buildingFilter === 'none' && !user.main_building) ||
      user.main_building === buildingFilter;
    return matchesSearch && matchesRole && matchesCompany && matchesZone && matchesBuilding;
  });

  // Selection helpers
  const toggleSelectUser = (userId) => {
    setSelectedUserIds(prev => {
      const next = new Set(prev);
      if (next.has(userId)) next.delete(userId); else next.add(userId);
      return next;
    });
  };
  const toggleSelectAll = () => {
    if (selectedUserIds.size === paginatedUsers.length) {
      setSelectedUserIds(new Set());
    } else {
      setSelectedUserIds(new Set(paginatedUsers.map(u => u.id)));
    }
  };
  const selectAllFiltered = () => setSelectedUserIds(new Set(filteredUsers.map(u => u.id)));

  // Bulk actions
  const handleBulkSetBuilding = async () => {
    if (selectedUserIds.size === 0) return;
    setSubmitting(true);
    try {
      const res = await usersAPI.bulkSetBuilding([...selectedUserIds], bulkBuilding || null);
      toast.success(res.data.message);
      setBulkBuildingDialogOpen(false);
      setSelectedUserIds(new Set());
      fetchData();
    } catch (error) { toast.error(error.response?.data?.detail || 'Failed'); }
    finally { setSubmitting(false); }
  };
  const handleBulkAssignZone = async () => {
    if (selectedUserIds.size === 0 || !bulkZone) return;
    setSubmitting(true);
    try {
      const res = await usersAPI.bulkAssignZone([...selectedUserIds], bulkZone);
      toast.success(res.data.message);
      setBulkZoneDialogOpen(false);
      setSelectedUserIds(new Set());
      fetchData();
    } catch (error) { toast.error(error.response?.data?.detail || 'Failed'); }
    finally { setSubmitting(false); }
  };

  const totalPages = Math.max(1, Math.ceil(filteredUsers.length / PAGE_SIZE));
  const safePage = Math.min(currentPage, totalPages);
  const paginatedUsers = filteredUsers.slice((safePage - 1) * PAGE_SIZE, safePage * PAGE_SIZE);

  const getRoleBadgeColor = (role) => {
    switch (role) {
      case 'admin': return 'bg-purple-100 text-purple-800';
      case 'attendant': return 'bg-blue-100 text-blue-800';
      default: return 'bg-gray-100 text-gray-800';
    }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-[#08263e]"></div>
      </div>
    );
  }

  return (
    <div className="space-y-6" data-testid="user-management-page">
      {/* Page Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-gray-800">User Management</h1>
          <p className="text-gray-500 flex items-center gap-1.5">{users.length} total users <HelpTip text="Manage employees, attendants, and admin accounts. Use bulk upload for importing multiple users at once." /></p>
        </div>
        <div className="flex gap-2">
          <Dialog open={uploadDialogOpen} onOpenChange={setUploadDialogOpen}>
            <DialogTrigger asChild>
              <Button variant="outline" data-testid="bulk-upload-btn"><Upload className="w-4 h-4 mr-2" /> Bulk Upload</Button>
            </DialogTrigger>
            <DialogContent>
              <DialogHeader><DialogTitle>Bulk Upload Users</DialogTitle></DialogHeader>
              <div className="space-y-4 mt-4">
                <p className="text-xs text-gray-500">Upload CSV/Excel with columns: <span className="font-medium">email, first_name, last_name, company, role</span>. Optional: <span className="font-medium">main_building</span> (building name), <span className="font-medium">zone</span> (zone name).</p>
                <div className="border-2 border-dashed border-gray-200 rounded-lg p-6 text-center">
                  <FileSpreadsheet className="w-12 h-12 mx-auto text-gray-400 mb-3" />
                  <p className="text-sm text-gray-500 mb-2">Upload CSV or Excel file</p>
                  <input ref={fileInputRef} type="file" accept=".csv,.xlsx,.xls" onChange={(e) => setUploadFile(e.target.files[0])} className="hidden" />
                  <Button variant="outline" onClick={() => fileInputRef.current?.click()} data-testid="select-file-btn">Select File</Button>
                  {uploadFile && <p className="mt-2 text-sm text-[#08263e] font-medium">{uploadFile.name}</p>}
                </div>
                <div className="space-y-2">
                  <Label>Default Password</Label>
                  <Input value={defaultPassword} onChange={(e) => setDefaultPassword(e.target.value)} data-testid="default-password-input" />
                </div>
                <div className="flex gap-2">
                  <Button variant="outline" onClick={downloadTemplate} className="flex-1"><Download className="w-4 h-4 mr-2" /> Template</Button>
                  <Button onClick={handleBulkUpload} className="flex-1 bg-[#08263e] hover:bg-[#051a2d] text-white" disabled={!uploadFile || submitting} data-testid="upload-btn">
                    {submitting ? 'Uploading...' : 'Upload'}
                  </Button>
                </div>
              </div>
            </DialogContent>
          </Dialog>
          <Dialog open={dialogOpen} onOpenChange={(open) => {
            // QAT-USER-MANAGEMENT-030 fix: also reset on OPEN so the Add-User
            // flow never inherits state from a previous Edit-User interaction.
            if (open) resetForm();
            setDialogOpen(open);
            if (!open) resetForm();
          }}>
            <DialogTrigger asChild>
              <Button
                className="bg-[#08263e] hover:bg-[#051a2d] text-white"
                data-testid="add-user-btn"
                onClick={resetForm}
              ><Plus className="w-4 h-4 mr-2" /> Add User</Button>
            </DialogTrigger>
            <DialogContent className="max-w-md max-h-[90vh] overflow-y-auto">
              <DialogHeader><DialogTitle>{editingUser ? 'Edit User' : 'Add New User'}</DialogTitle></DialogHeader>
              <form onSubmit={handleSubmit} className="space-y-4 mt-4">
                <div className="grid grid-cols-2 gap-4">
                  <div className="space-y-2">
                    <Label>First Name * <span className="text-xs text-gray-400">(max 30)</span></Label>
                    <Input value={formData.first_name} onChange={(e) => setFormData({ ...formData, first_name: e.target.value.slice(0, 30) })} required maxLength={30} data-testid="user-firstname-input" />
                  </div>
                  <div className="space-y-2">
                    <Label>Last Name * <span className="text-xs text-gray-400">(max 30)</span></Label>
                    <Input value={formData.last_name} onChange={(e) => setFormData({ ...formData, last_name: e.target.value.slice(0, 30) })} required maxLength={30} data-testid="user-lastname-input" />
                  </div>
                </div>
                <div className="space-y-2"><Label>Email *</Label><Input type="email" value={formData.email} onChange={(e) => setFormData({ ...formData, email: e.target.value })} required data-testid="user-email-input" /></div>
                {!editingUser && (
                  <div className="space-y-2">
                    <Label className="flex items-center gap-1.5">Temporary Password * <HelpTip text="This is a one-time password. The user will be prompted to create their own password on first login." /></Label>
                    <Input type="text" value={formData.password} onChange={(e) => setFormData({ ...formData, password: e.target.value })} required data-testid="user-password-input" />
                  </div>
                )}
                <div className="space-y-2">
                  <Label>Company <span className="text-xs text-gray-400">(max 30)</span></Label>
                  <Input value={formData.company} onChange={(e) => setFormData({ ...formData, company: e.target.value.slice(0, 30) })} maxLength={30} data-testid="user-company-input" />
                </div>
                <div className="space-y-2">
                  <Label>Role *</Label>
                  <Select value={formData.role} onValueChange={(value) => setFormData({ ...formData, role: value })}>
                    <SelectTrigger data-testid="user-role-select"><SelectValue /></SelectTrigger>
                    <SelectContent>
                      <SelectItem value="user">User (Employee)</SelectItem>
                      <SelectItem value="attendant">Parking Attendant</SelectItem>
                      <SelectItem value="admin">Administrator</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
                <div className="space-y-2">
                  <Label>Job Family</Label>
                  <Select value={formData.job_family || 'none'} onValueChange={(val) => setFormData({ ...formData, job_family: val === 'none' ? null : val })}>
                    <SelectTrigger data-testid="user-job-family-select"><SelectValue placeholder="Select job family" /></SelectTrigger>
                    <SelectContent>
                      <SelectItem value="none">-- None --</SelectItem>
                      <SelectItem value="Department Head">Department Head</SelectItem>
                      <SelectItem value="Division Head">Division Head</SelectItem>
                    </SelectContent>
                  </Select>
                </div>
                <div className="space-y-2">
                  <Label>Main Building</Label>
                  <Select value={formData.main_building || 'none'} onValueChange={(val) => setFormData({ ...formData, main_building: val === 'none' ? null : val })}>
                    <SelectTrigger data-testid="user-main-building-select"><SelectValue placeholder="Select main building" /></SelectTrigger>
                    <SelectContent>
                      <SelectItem value="none">-- None --</SelectItem>
                      {buildings.map(b => <SelectItem key={b.id} value={b.id}>{b.name}</SelectItem>)}
                    </SelectContent>
                  </Select>
                </div>
                <div className="space-y-2">
                  <Label>Tags</Label>
                  <div className="flex gap-3">
                    {AVAILABLE_TAGS.map(tag => (
                      <label key={tag} className="flex items-center gap-2 cursor-pointer">
                        <Checkbox checked={formData.tags.includes(tag)} onCheckedChange={(checked) => {
                          setFormData(prev => ({ ...prev, tags: checked ? [...prev.tags, tag] : prev.tags.filter(t => t !== tag) }));
                        }} />
                        <span className="text-sm capitalize">{tag.replace('_', ' ')}</span>
                      </label>
                    ))}
                  </div>
                </div>
                {formData.role === 'attendant' && (
                  <div className="space-y-2">
                    <Label>Assigned Buildings</Label>
                    <Select value={formData.assigned_buildings[0] || ''} onValueChange={(value) => setFormData({ ...formData, assigned_buildings: [value] })}>
                      <SelectTrigger><SelectValue placeholder="Select building" /></SelectTrigger>
                      <SelectContent>{buildings.map(b => <SelectItem key={b.id} value={b.id}>{b.name}</SelectItem>)}</SelectContent>
                    </Select>
                  </div>
                )}
                {formData.role === 'user' && (
                  <div className="space-y-2">
                    <Label>Default Booking Hours</Label>
                    <div className="grid grid-cols-2 gap-3">
                      <div className="space-y-1">
                        <span className="text-xs text-gray-500">Start Time</span>
                        <Input type="time" value={formData.default_start_time} onChange={(e) => setFormData({ ...formData, default_start_time: e.target.value })} data-testid="user-start-time" />
                      </div>
                      <div className="space-y-1">
                        <span className="text-xs text-gray-500">End Time</span>
                        <Input type="time" value={formData.default_end_time} onChange={(e) => setFormData({ ...formData, default_end_time: e.target.value })} data-testid="user-end-time" />
                      </div>
                    </div>
                    <p className="text-xs text-gray-400">Leave blank to use building defaults</p>
                  </div>
                )}
                <div className="flex gap-3 pt-4">
                  <Button type="button" variant="outline" className="flex-1" onClick={() => setDialogOpen(false)}>Cancel</Button>
                  <Button type="submit" className="flex-1 bg-[#08263e] hover:bg-[#051a2d] text-white" disabled={submitting} data-testid="save-user-btn">
                    {submitting ? 'Saving...' : editingUser ? 'Update' : 'Create'}
                  </Button>
                </div>
              </form>
            </DialogContent>
          </Dialog>
        </div>
      </div>

      {/* Filters */}
      <Card>
        <CardContent className="p-4">
          <div className="flex flex-col gap-3">
            <div className="flex flex-col md:flex-row gap-3">
              <div className="flex-1 relative">
                <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-gray-400" />
                <Input placeholder="Search by name, email, company..." value={searchTerm} onChange={(e) => setSearchTerm(e.target.value)} className="pl-10" data-testid="search-users-input" />
              </div>
              <Select value={roleFilter} onValueChange={setRoleFilter}>
                <SelectTrigger className="w-full md:w-40" data-testid="role-filter">
                  <Filter className="w-4 h-4 mr-2 text-gray-500" /><SelectValue placeholder="Role" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All Roles</SelectItem>
                  <SelectItem value="user">Users</SelectItem>
                  <SelectItem value="attendant">Attendants</SelectItem>
                  <SelectItem value="admin">Admins</SelectItem>
                </SelectContent>
              </Select>
              <Select value={companyFilter} onValueChange={setCompanyFilter}>
                <SelectTrigger className="w-full md:w-48" data-testid="company-filter">
                  <SelectValue placeholder="Company" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All Companies</SelectItem>
                  <SelectItem value="none">No Company / Unassigned</SelectItem>
                  {companies.map(c => <SelectItem key={c} value={c}>{c}</SelectItem>)}
                </SelectContent>
              </Select>
              <Select value={zoneFilter} onValueChange={setZoneFilter}>
                <SelectTrigger className="w-full md:w-48" data-testid="zone-filter">
                  <MapPinned className="w-4 h-4 mr-2 text-gray-500" /><SelectValue placeholder="Zone" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All Zones</SelectItem>
                  <SelectItem value="none">No Zone</SelectItem>
                  {zones.map(z => <SelectItem key={z.id} value={z.id}>{z.name}</SelectItem>)}
                </SelectContent>
              </Select>
              <Select value={buildingFilter} onValueChange={setBuildingFilter}>
                <SelectTrigger className="w-full md:w-48" data-testid="building-filter">
                  <Building2 className="w-4 h-4 mr-2 text-gray-500" /><SelectValue placeholder="Main Building" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All Buildings</SelectItem>
                  <SelectItem value="none">No Building</SelectItem>
                  {buildings.map(b => <SelectItem key={b.id} value={b.id}>{b.name}</SelectItem>)}
                </SelectContent>
              </Select>
            </div>
            <div className="flex items-center justify-between text-sm text-gray-500">
              <span>{filteredUsers.length} users found</span>
              {(companyFilter !== 'all' || zoneFilter !== 'all' || buildingFilter !== 'all') && (
                <Button variant="ghost" size="sm" onClick={() => { setCompanyFilter('all'); setZoneFilter('all'); setBuildingFilter('all'); setRoleFilter('all'); setSearchTerm(''); }}>Clear Filters</Button>
              )}
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Bulk Actions Bar */}
      {selectedUserIds.size > 0 && (
        <Card className="border-[#08263e] bg-[#08263e]/5">
          <CardContent className="p-3 flex items-center justify-between">
            <div className="flex items-center gap-3">
              <CheckSquare className="w-5 h-5 text-[#08263e]" />
              <span className="text-sm font-medium">{selectedUserIds.size} user{selectedUserIds.size > 1 ? 's' : ''} selected</span>
              {selectedUserIds.size < filteredUsers.length && (
                <Button variant="link" size="sm" className="text-xs p-0 h-auto" onClick={selectAllFiltered}>
                  Select all {filteredUsers.length} filtered
                </Button>
              )}
            </div>
            <div className="flex gap-2">
              <Button size="sm" variant="outline" onClick={() => { setBulkBuilding(''); setBulkBuildingDialogOpen(true); }} data-testid="bulk-set-building-btn">
                <Building2 className="w-4 h-4 mr-1" /> Set Main Building
              </Button>
              <Button size="sm" variant="outline" onClick={() => { setBulkZone(''); setBulkZoneDialogOpen(true); }} data-testid="bulk-assign-zone-btn">
                <MapPinned className="w-4 h-4 mr-1" /> Assign to Zone
              </Button>
              <Button size="sm" variant="ghost" onClick={() => setSelectedUserIds(new Set())}>Clear</Button>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Users Table */}
      <Card>
        <CardContent className="p-0">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead className="w-10">
                  <Checkbox
                    checked={paginatedUsers.length > 0 && selectedUserIds.size === paginatedUsers.length}
                    onCheckedChange={toggleSelectAll}
                    data-testid="select-all-checkbox"
                  />
                </TableHead>
                <TableHead>Name</TableHead>
                <TableHead>Email</TableHead>
                <TableHead>Company</TableHead>
                <TableHead>Job Family</TableHead>
                <TableHead>Role</TableHead>
                <TableHead>Main Building</TableHead>
                <TableHead>Zone</TableHead>
                <TableHead>Created</TableHead>
                <TableHead>Status</TableHead>
                <TableHead className="text-right">Actions</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {paginatedUsers.length === 0 ? (
                <TableRow><TableCell colSpan={11} className="text-center py-8 text-gray-500">No users found</TableCell></TableRow>
              ) : (
                paginatedUsers.map((user) => {
                  const userZone = getUserZone(user.id);
                  return (
                  <TableRow key={user.id} data-testid={`user-row-${user.id}`} className={`${user.is_blocked ? 'bg-red-50/50' : ''} ${selectedUserIds.has(user.id) ? 'bg-blue-50/50' : ''}`}>
                    <TableCell>
                      <Checkbox
                        checked={selectedUserIds.has(user.id)}
                        onCheckedChange={() => toggleSelectUser(user.id)}
                        data-testid={`select-user-${user.id}`}
                      />
                    </TableCell>
                    <TableCell className="font-medium">
                      <div>{user.first_name} {user.last_name}</div>
                      <div className="flex gap-1 mt-0.5">
                        {(user.tags || []).map(tag => (
                          <Badge key={tag} className="bg-amber-100 text-amber-800 text-[10px] capitalize px-1 py-0"><Star className="w-2.5 h-2.5 mr-0.5" />{tag.replace('_', ' ')}</Badge>
                        ))}
                      </div>
                    </TableCell>
                    <TableCell className="text-sm">{user.email}</TableCell>
                    <TableCell className="text-sm text-gray-600">{user.company || <span className="text-gray-400">-</span>}</TableCell>
                    <TableCell className="text-sm text-gray-600">{user.job_family || <span className="text-gray-400">-</span>}</TableCell>
                    <TableCell><Badge className={getRoleBadgeColor(user.role)}>{user.role}</Badge></TableCell>
                    <TableCell>
                      {user.main_building ? (
                        <Badge variant="outline" className="text-xs"><Building2 className="w-3 h-3 mr-1" />{getBuildingName(user.main_building)}</Badge>
                      ) : (<span className="text-xs text-gray-400">Not set</span>)}
                    </TableCell>
                    <TableCell>
                      {userZone ? (
                        <Badge variant="outline" className="text-xs bg-indigo-50 text-indigo-700"><MapPinned className="w-3 h-3 mr-1" />{userZone.name}</Badge>
                      ) : (<span className="text-xs text-gray-400">None</span>)}
                    </TableCell>
                    <TableCell className="text-xs text-gray-500">
                      {user.created_at ? new Date(user.created_at).toLocaleDateString() : '-'}
                      {user.updated_at && <div className="text-[10px] text-gray-400">edited {new Date(user.updated_at).toLocaleDateString()}</div>}
                    </TableCell>
                    <TableCell>
                      {user.is_blocked ? (
                        <Badge className="bg-red-100 text-red-800" data-testid={`blocked-badge-${user.id}`}><ShieldOff className="w-3 h-3 mr-1" /> Blocked</Badge>
                      ) : (<Badge className="bg-green-100 text-green-800"><ShieldCheck className="w-3 h-3 mr-1" /> Active</Badge>)}
                    </TableCell>
                    <TableCell className="text-right">
                      <DropdownMenu>
                        <DropdownMenuTrigger asChild>
                          <Button variant="ghost" size="sm" data-testid={`user-actions-${user.id}`}><MoreHorizontal className="w-4 h-4" /></Button>
                        </DropdownMenuTrigger>
                        <DropdownMenuContent align="end">
                          <DropdownMenuItem onClick={() => handleEdit(user)}><Edit className="w-4 h-4 mr-2" /> Edit</DropdownMenuItem>
                          <DropdownMenuItem onClick={() => { setSelectedUser(user); setSelectedMainBuilding(user.main_building || ''); setMainBuildingDialogOpen(true); }}>
                            <Building2 className="w-4 h-4 mr-2" /> Set Main Building
                          </DropdownMenuItem>
                          <DropdownMenuItem onClick={() => { setSelectedUser(user); setSelectedTags(user.tags || []); setTagsDialogOpen(true); }}>
                            <Tag className="w-4 h-4 mr-2" /> Manage Tags
                          </DropdownMenuItem>
                          <DropdownMenuItem onClick={() => { setSelectedUser(user); setResetPassword('Changeme1'); setResetPasswordDialogOpen(true); }} data-testid={`reset-password-${user.id}`}>
                            <KeyRound className="w-4 h-4 mr-2" /> Reset Password
                          </DropdownMenuItem>
                          {user.role !== 'admin' && (
                            <DropdownMenuItem onClick={() => handleToggleBlock(user)} data-testid={`toggle-block-${user.id}`}>
                              {user.is_blocked ? (<><ShieldCheck className="w-4 h-4 mr-2 text-green-600" /><span className="text-green-600">Unblock</span></>) : (<><ShieldOff className="w-4 h-4 mr-2 text-orange-600" /><span className="text-orange-600">Block</span></>)}
                            </DropdownMenuItem>
                          )}
                          <DropdownMenuItem onClick={() => handleDelete(user.id)} className="text-red-600"><Trash2 className="w-4 h-4 mr-2" /> Delete</DropdownMenuItem>
                        </DropdownMenuContent>
                      </DropdownMenu>
                    </TableCell>
                  </TableRow>
                  );
                })
              )}
            </TableBody>
          </Table>

          {/* Pagination */}
          {filteredUsers.length > PAGE_SIZE && (
            <div className="flex items-center justify-between px-4 py-3 border-t" data-testid="user-pagination">
              <p className="text-sm text-gray-500">
                Showing {(safePage - 1) * PAGE_SIZE + 1}-{Math.min(safePage * PAGE_SIZE, filteredUsers.length)} of {filteredUsers.length} users
              </p>
              <div className="flex items-center gap-2">
                <Button variant="outline" size="sm" onClick={() => setCurrentPage(p => Math.max(1, p - 1))} disabled={safePage <= 1} data-testid="prev-page-btn">
                  <ChevronLeft className="w-4 h-4" />
                </Button>
                {Array.from({ length: totalPages }, (_, i) => i + 1)
                  .filter(p => p === 1 || p === totalPages || Math.abs(p - safePage) <= 1)
                  .reduce((acc, p, i, arr) => {
                    if (i > 0 && p - arr[i - 1] > 1) acc.push('...');
                    acc.push(p);
                    return acc;
                  }, [])
                  .map((item, i) => item === '...' ? (
                    <span key={`ellipsis-${i}`} className="px-1 text-gray-400">...</span>
                  ) : (
                    <Button key={item} variant={item === safePage ? 'default' : 'outline'} size="sm"
                      className={item === safePage ? 'bg-[#08263e] text-white hover:bg-[#051a2d]' : ''}
                      onClick={() => setCurrentPage(item)} data-testid={`page-${item}`}>
                      {item}
                    </Button>
                  ))}
                <Button variant="outline" size="sm" onClick={() => setCurrentPage(p => Math.min(totalPages, p + 1))} disabled={safePage >= totalPages} data-testid="next-page-btn">
                  <ChevronRight className="w-4 h-4" />
                </Button>
              </div>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Main Building Dialog */}
      <Dialog open={mainBuildingDialogOpen} onOpenChange={setMainBuildingDialogOpen}>
        <DialogContent className="max-w-sm">
          <DialogHeader><DialogTitle>Set Main Building</DialogTitle></DialogHeader>
          {selectedUser && (
            <div className="space-y-4 mt-2">
              <p className="text-sm text-gray-500">Assign a main building for <strong>{selectedUser.first_name} {selectedUser.last_name}</strong></p>
              <Select value={selectedMainBuilding || 'none'} onValueChange={(val) => setSelectedMainBuilding(val === 'none' ? null : val)}>
                <SelectTrigger data-testid="main-building-select"><SelectValue /></SelectTrigger>
                <SelectContent>
                  <SelectItem value="none">-- No Main Building --</SelectItem>
                  {buildings.map(b => <SelectItem key={b.id} value={b.id}>{b.name}</SelectItem>)}
                </SelectContent>
              </Select>
              <div className="flex gap-3">
                <Button variant="outline" className="flex-1" onClick={() => setMainBuildingDialogOpen(false)}>Cancel</Button>
                <Button className="flex-1 bg-[#08263e] hover:bg-[#051a2d] text-white" onClick={handleAssignMainBuilding} disabled={submitting} data-testid="save-main-building-btn">
                  {submitting ? 'Saving...' : 'Save'}
                </Button>
              </div>
            </div>
          )}
        </DialogContent>
      </Dialog>

      {/* Tags Dialog */}
      <Dialog open={tagsDialogOpen} onOpenChange={setTagsDialogOpen}>
        <DialogContent className="max-w-sm">
          <DialogHeader><DialogTitle>Manage User Tags</DialogTitle></DialogHeader>
          {selectedUser && (
            <div className="space-y-4 mt-2">
              <p className="text-sm text-gray-500">Set tags for <strong>{selectedUser.first_name} {selectedUser.last_name}</strong></p>
              <div className="space-y-3">
                {AVAILABLE_TAGS.map(tag => (
                  <label key={tag} className="flex items-center gap-3 p-3 border rounded-lg cursor-pointer hover:bg-gray-50">
                    <Checkbox checked={selectedTags.includes(tag)} onCheckedChange={(checked) => {
                      setSelectedTags(prev => checked ? [...prev, tag] : prev.filter(t => t !== tag));
                    }} />
                    <div>
                      <p className="text-sm font-medium capitalize">{tag.replace('_', ' ')}</p>
                      <p className="text-xs text-gray-500">
                        {tag === 'vip' && 'Special booking privileges, can book multi-day in external buildings'}
                        {tag === 'group_head' && 'Group head with extended booking access'}
                      </p>
                    </div>
                  </label>
                ))}
              </div>
              <div className="flex gap-3">
                <Button variant="outline" className="flex-1" onClick={() => setTagsDialogOpen(false)}>Cancel</Button>
                <Button className="flex-1 bg-[#08263e] hover:bg-[#051a2d] text-white" onClick={handleUpdateTags} disabled={submitting} data-testid="save-tags-btn">
                  {submitting ? 'Saving...' : 'Save Tags'}
                </Button>
              </div>
            </div>
          )}
        </DialogContent>
      </Dialog>

      {/* Reset Password Dialog */}
      <Dialog open={resetPasswordDialogOpen} onOpenChange={setResetPasswordDialogOpen}>
        <DialogContent className="max-w-sm">
          <DialogHeader><DialogTitle>Reset Password</DialogTitle></DialogHeader>
          {selectedUser && (
            <div className="space-y-4 mt-2">
              <p className="text-sm text-gray-500">Set a new temporary password for <strong>{selectedUser.first_name} {selectedUser.last_name}</strong></p>
              <div className="space-y-2">
                <Label>New Temporary Password</Label>
                <Input type="text" value={resetPassword} onChange={(e) => setResetPassword(e.target.value)} data-testid="reset-password-input" />
                <p className="text-xs text-gray-400">User will be required to change this on next login</p>
              </div>
              <div className="flex gap-3">
                <Button variant="outline" className="flex-1" onClick={() => setResetPasswordDialogOpen(false)}>Cancel</Button>
                <Button className="flex-1 bg-[#ec474e] hover:bg-[#d63a41] text-white" onClick={handleResetPassword} disabled={submitting || resetPassword.length < 8} data-testid="confirm-reset-password-btn">
                  {submitting ? 'Resetting...' : 'Reset Password'}
                </Button>
              </div>
            </div>
          )}
        </DialogContent>
      </Dialog>

      {/* Bulk Set Main Building Dialog */}
      <Dialog open={bulkBuildingDialogOpen} onOpenChange={setBulkBuildingDialogOpen}>
        <DialogContent className="max-w-sm">
          <DialogHeader><DialogTitle>Set Main Building</DialogTitle></DialogHeader>
          <div className="space-y-4 mt-2">
            <p className="text-sm text-gray-500">Set main building for <strong>{selectedUserIds.size} selected user{selectedUserIds.size > 1 ? 's' : ''}</strong></p>
            <Select value={bulkBuilding || 'none'} onValueChange={setBulkBuilding}>
              <SelectTrigger data-testid="bulk-building-select"><SelectValue placeholder="Select building" /></SelectTrigger>
              <SelectContent>
                <SelectItem value="none">-- Remove Main Building --</SelectItem>
                {buildings.map(b => <SelectItem key={b.id} value={b.id}>{b.name}</SelectItem>)}
              </SelectContent>
            </Select>
            <div className="flex gap-3">
              <Button variant="outline" className="flex-1" onClick={() => setBulkBuildingDialogOpen(false)}>Cancel</Button>
              <Button className="flex-1 bg-[#08263e] hover:bg-[#051a2d] text-white" onClick={handleBulkSetBuilding} disabled={submitting} data-testid="confirm-bulk-building-btn">
                {submitting ? 'Updating...' : 'Apply'}
              </Button>
            </div>
          </div>
        </DialogContent>
      </Dialog>

      {/* Bulk Assign Zone Dialog */}
      <Dialog open={bulkZoneDialogOpen} onOpenChange={setBulkZoneDialogOpen}>
        <DialogContent className="max-w-sm">
          <DialogHeader><DialogTitle>Assign to Zone</DialogTitle></DialogHeader>
          <div className="space-y-4 mt-2">
            <p className="text-sm text-gray-500">Add <strong>{selectedUserIds.size} selected user{selectedUserIds.size > 1 ? 's' : ''}</strong> to a zone</p>
            <Select value={bulkZone} onValueChange={setBulkZone}>
              <SelectTrigger data-testid="bulk-zone-select"><SelectValue placeholder="Select zone" /></SelectTrigger>
              <SelectContent>
                {zones.map(z => <SelectItem key={z.id} value={z.id}>{z.name}</SelectItem>)}
              </SelectContent>
            </Select>
            <div className="flex gap-3">
              <Button variant="outline" className="flex-1" onClick={() => setBulkZoneDialogOpen(false)}>Cancel</Button>
              <Button className="flex-1 bg-[#08263e] hover:bg-[#051a2d] text-white" onClick={handleBulkAssignZone} disabled={submitting || !bulkZone} data-testid="confirm-bulk-zone-btn">
                {submitting ? 'Assigning...' : 'Assign'}
              </Button>
            </div>
          </div>
        </DialogContent>
      </Dialog>
    </div>
  );
};

export default UserManagement;
