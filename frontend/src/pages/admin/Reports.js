import React, { useState, useEffect } from 'react';
import { reportsAPI, buildingsAPI, reservationsAPI } from '../../services/api';
import useFeatures from '../../hooks/useFeatures';
import { Button } from '../../components/ui/button';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '../../components/ui/card';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../../components/ui/select';
import { Calendar } from '../../components/ui/calendar';
import { Popover, PopoverContent, PopoverTrigger } from '../../components/ui/popover';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '../../components/ui/table';
import { Badge } from '../../components/ui/badge';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '../../components/ui/tabs';
import { toast } from 'sonner';
import {
  BarChart3, Calendar as CalendarIcon, Building2, Download,
  TrendingUp, Car, Sparkles, Clock, Trash2, ChevronDown, ChevronUp,
  Database, AlertTriangle, Lightbulb, Target
} from 'lucide-react';
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
  LineChart, Line, Legend, PieChart, Pie, Cell
} from 'recharts';
import { format, subDays, formatDistanceToNow } from 'date-fns';
import ReactMarkdown from 'react-markdown';

const Reports = () => {
  const [buildings, setBuildings] = useState([]);
  const [reservations, setReservations] = useState([]);
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);
  const [currentInsight, setCurrentInsight] = useState(null);
  const [insightHistory, setInsightHistory] = useState([]);
  const [loadingInsights, setLoadingInsights] = useState(false);
  const [expandedHistory, setExpandedHistory] = useState(null);
  const { ai_insights_enabled } = useFeatures();

  const [filters, setFilters] = useState({
    building_id: '',
    start_date: subDays(new Date(), 30),
    end_date: new Date()
  });

  useEffect(() => {
    fetchData();
    if (ai_insights_enabled) {
      fetchInsightHistory();
    }
  }, [ai_insights_enabled]);

  useEffect(() => {
    if (buildings.length > 0) {
      fetchStats();
      fetchReservations();
    }
  }, [filters, buildings]);

  const fetchData = async (retryCount = 0) => {
    try {
      const buildingsRes = await buildingsAPI.getAll();
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

  const fetchStats = async () => {
    try {
      const response = await reportsAPI.getStats({
        building_id: filters.building_id || undefined,
        start_date: format(filters.start_date, 'yyyy-MM-dd'),
        end_date: format(filters.end_date, 'yyyy-MM-dd')
      });
      setStats(response.data);
    } catch {
      toast.error('Failed to load report stats');
    }
  };

  const fetchReservations = async () => {
    try {
      const response = await reservationsAPI.getAll({
        building_id: filters.building_id || undefined
      });
      // QAT-ANALYTICS-016 fix: sort newest-first so 'Recent Reservations'
      // really shows the latest activity, regardless of backend insertion order.
      const sorted = [...(response.data || [])].sort((a, b) => {
        const ka = a.created_at || `${a.date} ${a.start_time}`;
        const kb = b.created_at || `${b.date} ${b.start_time}`;
        return kb.localeCompare(ka);
      });
      setReservations(sorted);
    } catch {
      // Reservations fetch failed silently
    }
  };

  // QAT-ANALYTICS-016 fix: refresh on focus / visibility change so coming back
  // to the Reports tab always picks up brand-new bookings without F5.
  useEffect(() => {
    const onFocus = () => { fetchStats(); fetchReservations(); };
    const onVis = () => { if (!document.hidden) onFocus(); };
    window.addEventListener('focus', onFocus);
    document.addEventListener('visibilitychange', onVis);
    return () => {
      window.removeEventListener('focus', onFocus);
      document.removeEventListener('visibilitychange', onVis);
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [filters]);

  const fetchInsightHistory = async () => {
    try {
      const response = await reportsAPI.getInsightsHistory(20);
      setInsightHistory(response.data);
    } catch {
      // Insight history fetch failed silently
    }
  };

  const generateInsights = async () => {
    setLoadingInsights(true);
    try {
      const response = await reportsAPI.generateAIInsights(filters.building_id || undefined);
      setCurrentInsight(response.data);
      fetchInsightHistory();
      toast.success('AI insights generated successfully');
    } catch (error) {
      toast.error('Failed to generate AI insights');
    } finally {
      setLoadingInsights(false);
    }
  };

  const deleteInsight = async (id) => {
    try {
      await reportsAPI.deleteInsight(id);
      setInsightHistory(prev => prev.filter(i => i.id !== id));
      if (currentInsight?.id === id) setCurrentInsight(null);
      toast.success('Insight deleted');
    } catch (error) {
      toast.error('Failed to delete insight');
    }
  };

  const exportToCSV = () => {
    const csv = [
      ['Date', 'Building', 'Floor', 'Slot', 'User', 'Vehicle', 'Status'],
      ...reservations.map(r => [
        r.date,
        r.building_name,
        r.floor_label,
        r.slot_label,
        r.user_name,
        r.vehicle_plate,
        r.status
      ])
    ].map(row => row.join(',')).join('\n');

    const blob = new Blob([csv], { type: 'text/csv' });
    const url = window.URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `parking_report_${format(new Date(), 'yyyy-MM-dd')}.csv`;
    a.click();
  };

  const COLORS = ['#08263e', '#ec474e', '#518dca'];

  const pieData = stats ? [
    { name: 'Confirmed', value: stats.summary.confirmed },
    { name: 'Pending', value: stats.summary.pending },
    { name: 'Cancelled', value: stats.summary.cancelled }
  ] : [];

  const getStatusColor = (status) => {
    switch (status) {
      case 'confirmed': return 'bg-green-100 text-green-800';
      case 'pending': return 'bg-yellow-100 text-yellow-800';
      case 'cancelled': return 'bg-red-100 text-red-800';
      default: return 'bg-gray-100 text-gray-800';
    }
  };

  const InsightDisplay = ({ insight, isCompact = false }) => {
    if (!insight) return null;
    const content = typeof insight === 'string' ? insight : insight.insights || insight.content;
    if (!content) return null;

    return (
      <div className={`prose prose-sm max-w-none ${isCompact ? 'text-sm' : ''}`}>
        <ReactMarkdown
          components={{
            p: ({ children }) => <p className="text-gray-700 leading-relaxed mb-3 last:mb-0">{children}</p>,
            strong: ({ children }) => <strong className="text-[#08263e] font-semibold">{children}</strong>,
            ol: ({ children }) => <ol className="space-y-3 list-none pl-0">{children}</ol>,
            ul: ({ children }) => <ul className="space-y-2 list-none pl-0">{children}</ul>,
            li: ({ children, ordered, index }) => (
              <li className="flex gap-3 items-start bg-white/60 rounded-lg p-3 border border-gray-100">
                <span className="flex-shrink-0 w-6 h-6 rounded-full bg-[#08263e] text-white text-xs flex items-center justify-center font-medium mt-0.5">
                  {typeof index === 'number' ? index + 1 : <Lightbulb className="w-3 h-3" />}
                </span>
                <span className="flex-1">{children}</span>
              </li>
            ),
          }}
        >
          {content}
        </ReactMarkdown>
      </div>
    );
  };

  const DataSnapshotBadges = ({ snapshot }) => {
    if (!snapshot) return null;
    return (
      <div className="flex flex-wrap gap-2" data-testid="insight-snapshot">
        <Badge variant="outline" className="text-xs gap-1 bg-white">
          <Database className="w-3 h-3" /> {snapshot.total_reservations} reservations
        </Badge>
        <Badge variant="outline" className="text-xs gap-1 bg-white text-green-700 border-green-200">
          <TrendingUp className="w-3 h-3" /> {snapshot.confirmed} confirmed
        </Badge>
        <Badge variant="outline" className="text-xs gap-1 bg-white text-red-700 border-red-200">
          <AlertTriangle className="w-3 h-3" /> {snapshot.no_shows} no-shows
        </Badge>
        <Badge variant="outline" className="text-xs gap-1 bg-white text-blue-700 border-blue-200">
          <Target className="w-3 h-3" /> {snapshot.occupancy_rate}% occupancy
        </Badge>
      </div>
    );
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-[#08263e]"></div>
      </div>
    );
  }

  return (
    <div className="space-y-6" data-testid="reports-page">
      {/* Page Header */}
      <div className="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-gray-800">Reports & Analytics</h1>
          <p className="text-gray-500">View parking trends and statistics</p>
        </div>
        <div className="flex gap-2">
          <Button
            variant="outline"
            onClick={exportToCSV}
            data-testid="export-btn"
          >
            <Download className="w-4 h-4 mr-2" />
            Export CSV
          </Button>
        </div>
      </div>

      {/* Filters */}
      <Card>
        <CardContent className="p-4">
          <div className="flex flex-col md:flex-row gap-4">
            <div className="flex-1">
              <Select
                value={filters.building_id || 'all'}
                onValueChange={(value) => setFilters({ ...filters, building_id: value === 'all' ? '' : value })}
              >
                <SelectTrigger data-testid="building-filter">
                  <Building2 className="w-4 h-4 mr-2" />
                  <SelectValue placeholder="All Buildings" />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="all">All Buildings</SelectItem>
                  {buildings.map((building) => (
                    <SelectItem key={building.id} value={building.id}>
                      {building.name}
                    </SelectItem>
                  ))}
                </SelectContent>
              </Select>
            </div>

            {/* PPA-54 final fix: two separate single-date pickers eliminate
                react-day-picker range-mode quirks (clicking inside an
                existing range emits onSelect(undefined), so the start date
                never updated). Each picker now commits its date on click. */}
            <Popover>
              <PopoverTrigger asChild>
                <Button variant="outline" className="justify-start" data-testid="start-date-btn">
                  <CalendarIcon className="w-4 h-4 mr-2" />
                  Start: {format(filters.start_date, 'MMM dd, yyyy')}
                </Button>
              </PopoverTrigger>
              <PopoverContent className="w-auto p-0" align="end">
                <Calendar
                  mode="single"
                  selected={filters.start_date}
                  onSelect={(date) => {
                    if (!date) return;
                    // If the new start is after current end, push end to match.
                    const newEnd = date > filters.end_date ? date : filters.end_date;
                    setFilters({ ...filters, start_date: date, end_date: newEnd });
                  }}
                  data-testid="start-date-calendar"
                />
              </PopoverContent>
            </Popover>

            <Popover>
              <PopoverTrigger asChild>
                <Button variant="outline" className="justify-start" data-testid="end-date-btn">
                  <CalendarIcon className="w-4 h-4 mr-2" />
                  End: {format(filters.end_date, 'MMM dd, yyyy')}
                </Button>
              </PopoverTrigger>
              <PopoverContent className="w-auto p-0" align="end">
                <Calendar
                  mode="single"
                  selected={filters.end_date}
                  onSelect={(date) => {
                    if (!date) return;
                    // If the new end is before current start, pull start back.
                    const newStart = date < filters.start_date ? date : filters.start_date;
                    setFilters({ ...filters, start_date: newStart, end_date: date });
                  }}
                  disabled={(date) => date < filters.start_date}
                  data-testid="end-date-calendar"
                />
              </PopoverContent>
            </Popover>
          </div>
        </CardContent>
      </Card>

      {/* Stats Overview */}
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
        <Card className="bg-gradient-to-br from-[#08263e] to-[#051a2d] text-white">
          <CardContent className="p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-white/70 text-sm">Total Reservations</p>
                <p className="text-3xl font-bold">{stats?.summary.total_reservations || 0}</p>
              </div>
              <BarChart3 className="w-8 h-8 text-[#ec474e]" />
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-gray-500 text-sm">Confirmed</p>
                <p className="text-3xl font-bold text-green-600">{stats?.summary.confirmed || 0}</p>
              </div>
              <TrendingUp className="w-8 h-8 text-green-600" />
            </div>
          </CardContent>
        </Card>

        <Card>
          <CardContent className="p-4">
            <div className="flex items-center justify-between">
              <div>
                <p className="text-gray-500 text-sm">Pending</p>
                <p className="text-3xl font-bold text-yellow-600">{stats?.summary.pending || 0}</p>
              </div>
              <CalendarIcon className="w-8 h-8 text-yellow-600" />
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
              <Car className="w-8 h-8 text-[#08263e]" />
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Charts */}
      <div className="grid lg:grid-cols-2 gap-6">
        <Card>
          <CardHeader>
            <CardTitle className="text-lg">Status Distribution</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="h-64">
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie data={pieData} cx="50%" cy="50%" innerRadius={60} outerRadius={80} paddingAngle={5} dataKey="value">
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

        <Card>
          <CardHeader>
            <CardTitle className="text-lg">Daily Reservations</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="h-64">
              {stats?.daily_breakdown?.length > 0 ? (
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart data={stats.daily_breakdown}>
                    <CartesianGrid strokeDasharray="3 3" />
                    <XAxis dataKey="date" tickFormatter={(val) => val.slice(5)} />
                    <YAxis />
                    <Tooltip />
                    <Legend />
                    <Line type="monotone" dataKey="total" stroke="#08263e" strokeWidth={2} name="Total" />
                    <Line type="monotone" dataKey="confirmed" stroke="#ec474e" strokeWidth={2} name="Confirmed" />
                  </LineChart>
                </ResponsiveContainer>
              ) : (
                <div className="flex items-center justify-center h-full text-gray-400">No data available</div>
              )}
            </div>
          </CardContent>
        </Card>
      </div>

      {/* Building Comparison */}
      {stats?.building_breakdown?.length > 0 && (
        <Card>
          <CardHeader>
            <CardTitle className="text-lg">Building Comparison</CardTitle>
          </CardHeader>
          <CardContent>
            <div className="h-64">
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={stats.building_breakdown} layout="vertical">
                  <CartesianGrid strokeDasharray="3 3" />
                  <XAxis type="number" />
                  <YAxis type="category" dataKey="building_name" width={150} />
                  <Tooltip />
                  <Legend />
                  <Bar dataKey="total" fill="#08263e" name="Total Reservations" />
                  <Bar dataKey="confirmed" fill="#ec474e" name="Confirmed" />
                </BarChart>
              </ResponsiveContainer>
            </div>
          </CardContent>
        </Card>
      )}

      {/* AI Insights Section — gated by /api/system/features.ai_insights_enabled */}
      {ai_insights_enabled && (
      <Card className="border-[#08263e]/20 overflow-hidden" data-testid="ai-insights-section">
        <CardHeader className="bg-gradient-to-r from-[#08263e] to-[#0a3554] text-white">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-3">
              <div className="w-10 h-10 rounded-lg bg-white/10 flex items-center justify-center">
                <Sparkles className="w-5 h-5 text-[#ec474e]" />
              </div>
              <div>
                <CardTitle className="text-lg text-white">AI-Powered Insights</CardTitle>
                <CardDescription className="text-white/60">
                  Generate intelligent analysis of your parking data
                </CardDescription>
              </div>
            </div>
            <Button
              onClick={generateInsights}
              disabled={loadingInsights}
              className="bg-[#ec474e] hover:bg-[#d63a40] text-white border-0"
              data-testid="generate-insights-btn"
            >
              {loadingInsights ? (
                <>
                  <div className="w-4 h-4 mr-2 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                  Analyzing...
                </>
              ) : (
                <>
                  <Sparkles className="w-4 h-4 mr-2" />
                  Generate Insights
                </>
              )}
            </Button>
          </div>
        </CardHeader>
        <CardContent className="p-0">
          <Tabs defaultValue="current" className="w-full">
            <TabsList className="w-full justify-start rounded-none border-b bg-gray-50/80 h-auto p-0">
              <TabsTrigger
                value="current"
                className="rounded-none border-b-2 border-transparent data-[state=active]:border-[#08263e] data-[state=active]:bg-transparent px-6 py-3 text-sm"
                data-testid="insights-current-tab"
              >
                Latest Insight
              </TabsTrigger>
              <TabsTrigger
                value="history"
                className="rounded-none border-b-2 border-transparent data-[state=active]:border-[#08263e] data-[state=active]:bg-transparent px-6 py-3 text-sm"
                data-testid="insights-history-tab"
              >
                History ({insightHistory.length})
              </TabsTrigger>
            </TabsList>

            <TabsContent value="current" className="p-6 mt-0">
              {currentInsight ? (
                <div className="space-y-4" data-testid="current-insight">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2 text-sm text-gray-500">
                      <Clock className="w-3.5 h-3.5" />
                      Generated {formatDistanceToNow(new Date(currentInsight.generated_at), { addSuffix: true })}
                      {currentInsight.building_name && (
                        <>
                          <span className="mx-1">for</span>
                          <Badge variant="outline" className="text-xs">{currentInsight.building_name}</Badge>
                        </>
                      )}
                    </div>
                  </div>
                  <DataSnapshotBadges snapshot={currentInsight.data_snapshot} />
                  <div className="bg-gradient-to-br from-gray-50 to-white rounded-xl p-5 border border-gray-100">
                    <InsightDisplay insight={currentInsight} />
                  </div>
                </div>
              ) : insightHistory.length > 0 ? (
                <div className="space-y-4" data-testid="latest-from-history">
                  <div className="flex items-center justify-between">
                    <div className="flex items-center gap-2 text-sm text-gray-500">
                      <Clock className="w-3.5 h-3.5" />
                      Generated {formatDistanceToNow(new Date(insightHistory[0].generated_at), { addSuffix: true })}
                      {insightHistory[0].building_name && (
                        <>
                          <span className="mx-1">for</span>
                          <Badge variant="outline" className="text-xs">{insightHistory[0].building_name}</Badge>
                        </>
                      )}
                    </div>
                  </div>
                  <DataSnapshotBadges snapshot={insightHistory[0].data_snapshot} />
                  <div className="bg-gradient-to-br from-gray-50 to-white rounded-xl p-5 border border-gray-100">
                    <InsightDisplay insight={insightHistory[0]} />
                  </div>
                </div>
              ) : (
                <div className="text-center py-12" data-testid="no-insights">
                  <div className="w-16 h-16 mx-auto mb-4 rounded-full bg-gray-100 flex items-center justify-center">
                    <Sparkles className="w-8 h-8 text-gray-300" />
                  </div>
                  <h3 className="text-lg font-semibold text-gray-600 mb-1">No insights yet</h3>
                  <p className="text-gray-400 text-sm mb-4">Click "Generate Insights" to analyze your parking data with AI</p>
                </div>
              )}
            </TabsContent>

            <TabsContent value="history" className="p-6 mt-0">
              {insightHistory.length === 0 ? (
                <div className="text-center py-12 text-gray-400" data-testid="no-history">
                  <Clock className="w-12 h-12 mx-auto mb-3 text-gray-300" />
                  <p>No insight history yet</p>
                </div>
              ) : (
                <div className="space-y-3" data-testid="insight-history-list">
                  {insightHistory.map((item) => (
                    <div
                      key={item.id}
                      className="border rounded-lg overflow-hidden transition-all hover:border-[#08263e]/30"
                      data-testid={`history-item-${item.id}`}
                    >
                      <div
                        className="flex items-center justify-between p-4 cursor-pointer bg-white hover:bg-gray-50/50"
                        onClick={() => setExpandedHistory(expandedHistory === item.id ? null : item.id)}
                      >
                        <div className="flex items-center gap-3">
                          <div className="w-8 h-8 rounded-full bg-[#08263e]/5 flex items-center justify-center flex-shrink-0">
                            <Sparkles className="w-4 h-4 text-[#08263e]" />
                          </div>
                          <div>
                            <div className="flex items-center gap-2">
                              <span className="font-medium text-sm text-gray-800">
                                {item.building_name || 'All Buildings'}
                              </span>
                              {item.data_snapshot && (
                                <Badge variant="outline" className="text-xs">
                                  {item.data_snapshot.total_reservations} reservations
                                </Badge>
                              )}
                            </div>
                            <div className="flex items-center gap-1.5 text-xs text-gray-400 mt-0.5">
                              <Clock className="w-3 h-3" />
                              {formatDistanceToNow(new Date(item.generated_at), { addSuffix: true })}
                              {item.generated_by_name && (
                                <span> by {item.generated_by_name}</span>
                              )}
                            </div>
                          </div>
                        </div>
                        <div className="flex items-center gap-2">
                          <Button
                            variant="ghost"
                            size="sm"
                            className="h-8 w-8 p-0 text-gray-400 hover:text-red-500"
                            onClick={(e) => { e.stopPropagation(); deleteInsight(item.id); }}
                            data-testid={`delete-insight-${item.id}`}
                          >
                            <Trash2 className="w-3.5 h-3.5" />
                          </Button>
                          {expandedHistory === item.id ? (
                            <ChevronUp className="w-4 h-4 text-gray-400" />
                          ) : (
                            <ChevronDown className="w-4 h-4 text-gray-400" />
                          )}
                        </div>
                      </div>
                      {expandedHistory === item.id && (
                        <div className="px-4 pb-4 border-t bg-gray-50/30">
                          <div className="pt-3 space-y-3">
                            <DataSnapshotBadges snapshot={item.data_snapshot} />
                            <InsightDisplay insight={item} isCompact />
                          </div>
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              )}
            </TabsContent>
          </Tabs>
        </CardContent>
      </Card>
      )}

      {/* Recent Reservations Table */}
      <Card>
        <CardHeader>
          <CardTitle className="text-lg">Recent Reservations</CardTitle>
          <CardDescription>Latest booking activities</CardDescription>
        </CardHeader>
        <CardContent className="p-0">
          <Table>
            <TableHeader>
              <TableRow>
                <TableHead>Date</TableHead>
                <TableHead>User</TableHead>
                <TableHead>Building</TableHead>
                <TableHead>Slot</TableHead>
                <TableHead>Vehicle</TableHead>
                <TableHead>Status</TableHead>
              </TableRow>
            </TableHeader>
            <TableBody>
              {reservations.length === 0 ? (
                <TableRow>
                  <TableCell colSpan={6} className="text-center py-8 text-gray-500">
                    No reservations found
                  </TableCell>
                </TableRow>
              ) : (
                reservations.slice(0, 10).map((res) => (
                  <TableRow key={res.id}>
                    <TableCell>{format(new Date(res.date), 'MMM dd, yyyy')}</TableCell>
                    <TableCell>{res.user_name}</TableCell>
                    <TableCell>{res.building_name}</TableCell>
                    <TableCell className="font-mono">{res.slot_label}</TableCell>
                    <TableCell className="font-mono">{res.vehicle_plate}</TableCell>
                    <TableCell>
                      <Badge className={getStatusColor(res.status)}>
                        {res.status}
                      </Badge>
                    </TableCell>
                  </TableRow>
                ))
              )}
            </TableBody>
          </Table>
        </CardContent>
      </Card>
    </div>
  );
};

export default Reports;
