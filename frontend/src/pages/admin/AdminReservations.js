import React, { useState, useEffect } from 'react';
import { reservationsAPI, buildingsAPI } from '../../services/api';
import { Button } from '../../components/ui/button';
import { Card, CardContent } from '../../components/ui/card';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../../components/ui/select';
import { Input } from '../../components/ui/input';
import { Badge } from '../../components/ui/badge';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '../../components/ui/table';
import { toast } from 'sonner';
import { 
  Calendar, Search, Filter, Building2, X, Clock, 
  User, CheckCircle2, XCircle, AlertCircle, AlertOctagon, ChevronLeft, ChevronRight
} from 'lucide-react';
import { format } from 'date-fns';

const PAGE_SIZE = 20;

const AdminReservations = () => {
  const [reservations, setReservations] = useState([]);
  const [buildings, setBuildings] = useState([]);
  const [loading, setLoading] = useState(true);
  const [currentPage, setCurrentPage] = useState(1);
  const [filters, setFilters] = useState({
    building_id: 'all',
    status: 'all',
    date: ''
  });
  const [searchTerm, setSearchTerm] = useState('');

  useEffect(() => { fetchData(); }, []);
  useEffect(() => { fetchReservations(); setCurrentPage(1); }, [filters]);
  useEffect(() => { setCurrentPage(1); }, [searchTerm]);

  const fetchData = async (retryCount = 0) => {
    try {
      const buildingsRes = await buildingsAPI.getAll();
      setBuildings(buildingsRes.data);
      await fetchReservations();
    } catch (error) {
      if (retryCount < 1 && error?.response?.status !== 403) {
        await new Promise(r => setTimeout(r, 800));
        return fetchData(retryCount + 1);
      }
      if (error?.response?.status !== 401) toast.error('Failed to load data');
    }
  };

  const fetchReservations = async () => {
    setLoading(true);
    try {
      const params = {};
      if (filters.building_id !== 'all') params.building_id = filters.building_id;
      if (filters.status !== 'all') params.status = filters.status;
      if (filters.date) params.date = filters.date;
      const response = await reservationsAPI.adminGetAll(params);
      setReservations(response.data);
    } catch {
      toast.error('Failed to load reservations');
    } finally {
      setLoading(false);
    }
  };

  const handleCancel = async (reservationId) => {
    if (!window.confirm('Are you sure you want to cancel this reservation?')) return;
    try {
      await reservationsAPI.adminCancel(reservationId);
      toast.success('Reservation cancelled');
      fetchReservations();
    } catch (error) {
      toast.error(error.response?.data?.detail || 'Failed to cancel');
    }
  };

  const getStatusConfig = (status) => {
    switch (status) {
      case 'confirmed': return { color: 'bg-green-100 text-green-800', icon: CheckCircle2 };
      case 'pending': return { color: 'bg-yellow-100 text-yellow-800', icon: Clock };      case 'cancelled': return { color: 'bg-gray-100 text-gray-600', icon: XCircle };
      case 'completed': return { color: 'bg-blue-100 text-blue-800', icon: CheckCircle2 };
      case 'no_show': return { color: 'bg-red-100 text-red-800', icon: AlertOctagon };
      default: return { color: 'bg-gray-100 text-gray-800', icon: AlertCircle };
    }
  };

  const filteredReservations = reservations.filter(r => {
    if (!searchTerm) return true;
    const term = searchTerm.toLowerCase();
    return (
      (r.user_name || '').toLowerCase().includes(term) ||
      (r.vehicle_plate || '').toLowerCase().includes(term) ||
      (r.building_name || '').toLowerCase().includes(term) ||
      (r.slot_label || '').toLowerCase().includes(term)
    );
  });

  // Pagination
  const totalPages = Math.ceil(filteredReservations.length / PAGE_SIZE);
  const paginatedReservations = filteredReservations.slice(
    (currentPage - 1) * PAGE_SIZE,
    currentPage * PAGE_SIZE
  );

  const stats = {
    total: reservations.length,
    pending: reservations.filter(r => r.status === 'pending').length,
    confirmed: reservations.filter(r => r.status === 'confirmed').length,
    cancelled: reservations.filter(r => r.status === 'cancelled').length,
    completed: reservations.filter(r => r.status === 'completed').length,
    no_show: reservations.filter(r => r.status === 'no_show').length
  };

  if (loading && reservations.length === 0) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-[#08263e]"></div>
      </div>
    );
  }

  return (
    <div className="space-y-6" data-testid="admin-reservations-page">
      <div>
        <h1 className="text-2xl font-bold text-gray-800">Reservation Management</h1>
        <p className="text-gray-500">View and manage all parking reservations</p>
      </div>

      {/* Stats - 6 cards */}
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4">
        <Card><CardContent className="p-4 text-center">
          <p className="text-xs text-gray-500">Total</p>
          <p className="text-2xl font-bold text-[#08263e]" data-testid="stat-total">{stats.total}</p>
        </CardContent></Card>
        <Card><CardContent className="p-4 text-center">
          <p className="text-xs text-yellow-600">Reserved</p>
          <p className="text-2xl font-bold text-yellow-600" data-testid="stat-pending">{stats.pending}</p>
        </CardContent></Card>
        <Card><CardContent className="p-4 text-center">
          <p className="text-xs text-green-600">Confirmed</p>
          <p className="text-2xl font-bold text-green-600" data-testid="stat-confirmed">{stats.confirmed}</p>
        </CardContent></Card>
        <Card><CardContent className="p-4 text-center">
          <p className="text-xs text-blue-600">Completed</p>
          <p className="text-2xl font-bold text-blue-600" data-testid="stat-completed">{stats.completed}</p>
        </CardContent></Card>
        <Card><CardContent className="p-4 text-center">
          <p className="text-xs text-red-600">No Show</p>
          <p className="text-2xl font-bold text-red-600" data-testid="stat-no-show">{stats.no_show}</p>
        </CardContent></Card>
        <Card><CardContent className="p-4 text-center">
          <p className="text-xs text-gray-500">Cancelled</p>
          <p className="text-2xl font-bold text-gray-500" data-testid="stat-cancelled">{stats.cancelled}</p>
        </CardContent></Card>
      </div>

      {/* Filters */}
      <Card>
        <CardContent className="p-4">
          <div className="flex flex-col md:flex-row gap-4">
            <div className="flex-1 relative">
              <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-gray-400" />
              <Input
                placeholder="Search by user, vehicle plate, building..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="pl-10"
                data-testid="search-reservations-input"
              />
            </div>
            <Select value={filters.building_id} onValueChange={(val) => setFilters(f => ({ ...f, building_id: val }))}>
              <SelectTrigger className="w-full md:w-56" data-testid="filter-building">
                <Building2 className="w-4 h-4 mr-2 text-gray-500" />
                <SelectValue placeholder="All Buildings" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Buildings</SelectItem>
                {buildings.map(b => (
                  <SelectItem key={b.id} value={b.id}>{b.name}</SelectItem>
                ))}
              </SelectContent>
            </Select>
            <Select value={filters.status} onValueChange={(val) => setFilters(f => ({ ...f, status: val }))}>
              <SelectTrigger className="w-full md:w-44" data-testid="filter-status">
                <Filter className="w-4 h-4 mr-2 text-gray-500" />
                <SelectValue placeholder="All Status" />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="all">All Status</SelectItem>
                <SelectItem value="pending">Reserved</SelectItem>
                <SelectItem value="confirmed">Confirmed</SelectItem>
                <SelectItem value="completed">Completed</SelectItem>
                <SelectItem value="no_show">No Show</SelectItem>
                <SelectItem value="cancelled">Cancelled</SelectItem>
              </SelectContent>
            </Select>
            <Input
              type="date"
              value={filters.date}
              onChange={(e) => setFilters(f => ({ ...f, date: e.target.value }))}
              className="w-full md:w-44"
              data-testid="filter-date"
            />
          </div>
        </CardContent>
      </Card>

      {/* Table */}
      <Card>
        <CardContent className="p-0">
          <div className="overflow-x-auto">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>User</TableHead>
                  <TableHead>Building / Slot</TableHead>
                  <TableHead>Date</TableHead>
                  <TableHead>Time</TableHead>
                  <TableHead>Vehicle</TableHead>
                  <TableHead>Status</TableHead>
                  <TableHead className="text-right">Actions</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {paginatedReservations.length === 0 ? (
                  <TableRow>
                    <TableCell colSpan={7} className="text-center py-12 text-gray-500">
                      <Calendar className="w-12 h-12 mx-auto text-gray-300 mb-3" />
                      <p>No reservations found</p>
                    </TableCell>
                  </TableRow>
                ) : (
                  paginatedReservations.map((res) => {
                    const statusConfig = getStatusConfig(res.status);
                    const StatusIcon = statusConfig.icon;
                    // PPA-62 UI fix: only allow Cancel for upcoming/today reservations.
                    // Backend already refuses past cancellations; this hides the button
                    // so admins don't see a useless Cancel control on historical rows.
                    const todayStr = new Date().toISOString().split('T')[0];
                    const isPastDate = res.date < todayStr;
                    const canCancel = (res.status === 'pending' || res.status === 'confirmed') && !isPastDate;
                    return (
                      <TableRow key={res.id} data-testid={`reservation-row-${res.id}`}>
                        <TableCell>
                          <div className="flex items-center gap-2">
                            <div className="w-8 h-8 bg-[#08263e]/10 rounded-full flex items-center justify-center">
                              <User className="w-4 h-4 text-[#08263e]" />
                            </div>
                            <span className="font-medium text-sm">{res.user_name || 'Unknown'}</span>
                          </div>
                        </TableCell>
                        <TableCell>
                          <div className="text-sm">
                            <p className="font-medium">{res.building_name}</p>
                            <p className="text-gray-500">{res.floor_label} - Slot {res.slot_label}</p>
                          </div>
                        </TableCell>
                        <TableCell className="text-sm">
                          {format(new Date(res.date), 'MMM dd, yyyy')}
                        </TableCell>
                        <TableCell className="text-sm text-gray-600">
                          {res.start_time} - {res.end_time}
                        </TableCell>
                        <TableCell>
                          <span className="font-mono text-sm">{res.vehicle_plate}</span>
                        </TableCell>
                        <TableCell>
                          <Badge className={statusConfig.color}>
                            <StatusIcon className="w-3 h-3 mr-1" />
                            {res.status === 'no_show' ? 'No Show' : res.status === 'pending' ? 'Reserved' : res.status}
                          </Badge>
                          {res.status === 'no_show' && res.no_show_at && (
                            <p className="text-[10px] text-red-500 mt-1" data-testid={`admin-no-show-time-${res.id}`}>
                              {(() => { try { return format(new Date(res.no_show_at), 'MMM dd, h:mm a'); } catch { return ''; } })()}
                            </p>
                          )}
                        </TableCell>
                        <TableCell className="text-right">
                          {canCancel && (
                            <Button
                              variant="outline"
                              size="sm"
                              className="text-red-600 border-red-200 hover:bg-red-50 hover:text-red-700"
                              onClick={() => handleCancel(res.id)}
                              data-testid={`admin-cancel-${res.id}`}
                            >
                              <X className="w-3 h-3 mr-1" />
                              Cancel
                            </Button>
                          )}
                        </TableCell>
                      </TableRow>
                    );
                  })
                )}
              </TableBody>
            </Table>
          </div>
          {/* Pagination */}
          {totalPages > 1 && (
            <div className="flex items-center justify-between px-4 py-3 border-t">
              <p className="text-sm text-gray-500">
                Showing {((currentPage - 1) * PAGE_SIZE) + 1}-{Math.min(currentPage * PAGE_SIZE, filteredReservations.length)} of {filteredReservations.length}
              </p>
              <div className="flex items-center gap-2">
                <Button variant="outline" size="sm" onClick={() => setCurrentPage(p => Math.max(1, p - 1))} disabled={currentPage === 1} data-testid="pagination-prev">
                  <ChevronLeft className="w-4 h-4" />
                </Button>
                <span className="text-sm text-gray-700">Page {currentPage} of {totalPages}</span>
                <Button variant="outline" size="sm" onClick={() => setCurrentPage(p => Math.min(totalPages, p + 1))} disabled={currentPage === totalPages} data-testid="pagination-next">
                  <ChevronRight className="w-4 h-4" />
                </Button>
              </div>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
};

export default AdminReservations;
