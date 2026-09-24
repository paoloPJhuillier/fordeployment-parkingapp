import React, { useState, useEffect } from 'react';
import { Link } from 'react-router-dom';
import { reportsAPI, usersAPI, buildingsAPI, reservationsAPI } from '../../services/api';
import useFeatures from '../../hooks/useFeatures';
import { Card, CardContent, CardHeader, CardTitle } from '../../components/ui/card';
import { Button } from '../../components/ui/button';
import { toast } from 'sonner';
import { 
  Users, Building2, Car, Calendar, TrendingUp, 
  ArrowUpRight, ArrowDownRight, BarChart3, Sparkles
} from 'lucide-react';
import { 
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
  PieChart, Pie, Cell, LineChart, Line, Legend
} from 'recharts';
import DatabaseHealthCard from '../../components/DatabaseHealthCard';

const AdminDashboard = () => {
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);
  const { ai_insights_enabled } = useFeatures();

  useEffect(() => {
    fetchData();
  }, []);

  const fetchData = async () => {
    try {
      const response = await reportsAPI.getStats({});
      setStats(response.data);
    } catch (error) {
      toast.error('Failed to load statistics');
    } finally {
      setLoading(false);
    }
  };

  const COLORS = ['#08263e', '#ec474e', '#518dca', '#10B981'];

  const pieData = stats ? [
    { name: 'Confirmed', value: stats.summary.confirmed },
    { name: 'Pending', value: stats.summary.pending },
    { name: 'Cancelled', value: stats.summary.cancelled }
  ] : [];

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-[#08263e]"></div>
      </div>
    );
  }

  return (
    <div className="space-y-6" data-testid="admin-dashboard">
      {/* Page Header */}
      <div className="flex items-center justify-between">
        <div>
          <h1 className="text-2xl font-bold text-gray-800">Dashboard</h1>
          <p className="text-gray-500">Overview of your parking system</p>
        </div>
        {ai_insights_enabled && (
          <Link to="/admin/reports">
            <Button 
              className="bg-[#08263e] hover:bg-[#051a2d] text-white rounded-full"
              data-testid="ai-insights-btn"
            >
              <Sparkles className="w-4 h-4 mr-2" />
              AI Insights
            </Button>
          </Link>
        )}
      </div>

      {/* Stats Cards */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <Card className="bg-gradient-to-br from-[#08263e] to-[#051a2d] text-white">
          <CardContent className="p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-white/70 text-sm">Total Users</p>
                <p className="text-3xl font-bold">{stats?.summary.total_users || 0}</p>
              </div>
              <Users className="w-8 h-8 text-[#ec474e]" />
            </div>
          </CardContent>
        </Card>

        <Card className="bg-white">
          <CardContent className="p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-gray-500 text-sm">Buildings</p>
                <p className="text-3xl font-bold text-[#08263e]">{stats?.summary.buildings_count || 0}</p>
              </div>
              <Building2 className="w-8 h-8 text-[#08263e]" />
            </div>
          </CardContent>
        </Card>

        <Card className="bg-white">
          <CardContent className="p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-gray-500 text-sm">Parking Slots</p>
                <p className="text-3xl font-bold text-[#08263e]">{stats?.summary.total_slots || 0}</p>
              </div>
              <Car className="w-8 h-8 text-[#08263e]" />
            </div>
          </CardContent>
        </Card>

        <Card className="bg-[#ec474e]">
          <CardContent className="p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-[#08263e]/70 text-sm">Occupancy Rate</p>
                <p className="text-3xl font-bold text-[#08263e]">{stats?.summary.occupancy_rate || 0}%</p>
              </div>
              <TrendingUp className="w-8 h-8 text-[#08263e]" />
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Charts Row */}
      <div className="grid lg:grid-cols-2 gap-6">
        {/* Reservations by Status */}
        <Card>
          <CardHeader>
            <CardTitle className="text-lg flex items-center gap-2">
              <BarChart3 className="w-5 h-5 text-[#08263e]" />
              Reservation Status Distribution
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="h-64">
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie
                    data={pieData}
                    cx="50%"
                    cy="50%"
                    innerRadius={60}
                    outerRadius={80}
                    paddingAngle={5}
                    dataKey="value"
                  >
                    {pieData.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                    ))}
                  </Pie>
                  <Tooltip />
                  <Legend />
                </PieChart>
              </ResponsiveContainer>
            </div>
          </CardContent>
        </Card>

        {/* Daily Breakdown */}
        <Card>
          <CardHeader>
            <CardTitle className="text-lg flex items-center gap-2">
              <Calendar className="w-5 h-5 text-[#08263e]" />
              Daily Reservations
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="h-64">
              {stats?.daily_breakdown?.length > 0 ? (
                <ResponsiveContainer width="100%" height="100%">
                  <BarChart data={stats.daily_breakdown.slice(-7)}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis dataKey="date" tickFormatter={(val) => val.slice(5)} />
                    <YAxis />
                    <Tooltip />
                    <Bar dataKey="confirmed" fill="#08263e" name="Confirmed" />
                    <Bar dataKey="cancelled" fill="#EF4444" name="Cancelled" />
                  </BarChart>
                </ResponsiveContainer>
              ) : (
                <div className="flex items-center justify-center h-full text-gray-400">
                  No data available
                </div>
              )}
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Building Stats */}
      {stats?.building_breakdown?.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="text-lg flex items-center gap-2">
              <Building2 className="w-5 h-5 text-[#08263e]" />
              Reservations by Building
            </CardTitle>
          </CardHeader>
          <CardContent>
            <div className="h-64">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={stats.building_breakdown} layout="vertical" margin={{ top: 5, right: 20, bottom: 5, left: 10 }}>
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis type="number" />
                  {/* QAT-DASHBOARD-008 fix: building names were overlapping/clipped.
                      Wider Y-axis + truncate-with-ellipsis tick keeps the chart
                      tidy; the tooltip still shows the full name on hover. */}
                  <YAxis
                    type="category"
                    dataKey="building_name"
                    width={180}
                    interval={0}
                    tick={{ fontSize: 12 }}
                    tickFormatter={(name) =>
                      typeof name === 'string' && name.length > 22 ? name.slice(0, 21) + '…' : name
                    }
                  />
                  <Tooltip />
                  <Legend />
                  <Bar dataKey="total" fill="#08263e" name="Total" />
                  <Bar dataKey="confirmed" fill="#ec474e" name="Confirmed" />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </CardContent>
        </Card>
      )}

      {/* Database Health (admin-only; shows active DB + per-collection counts + sync button) */}
      <DatabaseHealthCard />

      {/* Quick Actions */}
      <div className="grid md:grid-cols-3 gap-4">
        <Link to="/admin/users">
          <Card className="hover:shadow-lg transition-shadow cursor-pointer group">
            <CardContent className="p-4 flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 bg-[#08263e]/10 rounded-lg flex items-center justify-center">
                  <Users className="w-5 h-5 text-[#08263e]" />
                </div>
                <span className="font-medium">Manage Users</span>
              </div>
              <ArrowUpRight className="w-5 h-5 text-gray-400 group-hover:text-[#08263e] transition-colors" />
            </CardContent>
          </Card>
        </Link>

        <Link to="/admin/buildings">
          <Card className="hover:shadow-lg transition-shadow cursor-pointer group">
            <CardContent className="p-4 flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 bg-[#08263e]/10 rounded-lg flex items-center justify-center">
                  <Building2 className="w-5 h-5 text-[#08263e]" />
                </div>
                <span className="font-medium">Manage Buildings</span>
              </div>
              <ArrowUpRight className="w-5 h-5 text-gray-400 group-hover:text-[#08263e] transition-colors" />
            </CardContent>
          </Card>
        </Link>

        <Link to="/admin/reports">
          <Card className="hover:shadow-lg transition-shadow cursor-pointer group">
            <CardContent className="p-4 flex items-center justify-between">
              <div className="flex items-center gap-3">
                <div className="w-10 h-10 bg-[#08263e]/10 rounded-lg flex items-center justify-center">
                  <BarChart3 className="w-5 h-5 text-[#08263e]" />
                </div>
                <span className="font-medium">View Reports</span>
              </div>
              <ArrowUpRight className="w-5 h-5 text-gray-400 group-hover:text-[#08263e] transition-colors" />
            </CardContent>
          </Card>
        </Link>
      </div>
    </div>
  );
};

export default AdminDashboard;
