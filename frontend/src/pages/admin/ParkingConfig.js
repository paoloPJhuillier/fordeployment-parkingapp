import React, { useState, useEffect } from 'react';
import { configAPI, buildingsAPI } from '../../services/api';
import { Button } from '../../components/ui/button';
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from '../../components/ui/card';
import { Input } from '../../components/ui/input';
import { Label } from '../../components/ui/label';
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '../../components/ui/select';
import { Switch } from '../../components/ui/switch';
import { toast } from 'sonner';
import { Settings, Clock, Calendar, Save, Building2, AlertOctagon, ListOrdered } from 'lucide-react';
import { HelpTip } from '../../components/ui/help-tip';

const ParkingConfig = () => {
  const [buildings, setBuildings] = useState([]);
  const [selectedBuilding, setSelectedBuilding] = useState('');
  const [config, setConfig] = useState(null);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);

  const [formData, setFormData] = useState({
    release_time: '06:00',
    default_start_time: '08:00',
    default_end_time: '18:00',
    booking_window_days: 7,
    no_show_release_enabled: false,
    no_show_release_minutes: 30,
    waitlist_enabled: false,
    waitlist_notification_window_minutes: 15,
    main_building_exclusive: false,
  });

  useEffect(() => { fetchBuildings(); }, []);
  useEffect(() => { if (selectedBuilding) fetchConfig(); }, [selectedBuilding]);

  const fetchBuildings = async () => {
    try {
      const response = await buildingsAPI.getAll();
      setBuildings(response.data);
      if (response.data.length > 0) setSelectedBuilding(response.data[0].id);
    } catch { toast.error('Failed to load buildings'); }
    finally { setLoading(false); }
  };

  const fetchConfig = async () => {
    try {
      const response = await configAPI.get(selectedBuilding);
      setConfig(response.data);
      setFormData({
        release_time: response.data.release_time,
        default_start_time: response.data.default_start_time,
        default_end_time: response.data.default_end_time,
        booking_window_days: response.data.booking_window_days,
        no_show_release_enabled: response.data.no_show_release_enabled || false,
        no_show_release_minutes: response.data.no_show_release_minutes || 30,
        waitlist_enabled: response.data.waitlist_enabled || false,
        waitlist_notification_window_minutes: response.data.waitlist_notification_window_minutes || 15,
        main_building_exclusive: response.data.main_building_exclusive || false,
      });
    } catch { /* Config fetch failed - uses defaults */ }
  };

  const handleSave = async () => {
    setSaving(true);
    try {
      await configAPI.save({ building_id: selectedBuilding, ...formData });
      toast.success('Configuration saved successfully');
      fetchConfig();
    } catch (error) { toast.error(error.response?.data?.detail || 'Failed to save configuration'); }
    finally { setSaving(false); }
  };

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64">
        <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-[#08263e]"></div>
      </div>
    );
  }

  return (
    <div className="space-y-6" data-testid="parking-config-page">
      <div>
        <h1 className="text-2xl font-bold text-gray-800">Parking Configuration</h1>
        <p className="text-gray-500">Configure parking release times, booking windows, and no-show policies</p>
      </div>

      {/* Building Selector */}
      <Card>
        <CardHeader>
          <CardTitle className="text-lg flex items-center gap-2">
            <Building2 className="w-5 h-5 text-[#08263e]" />
            Select Building
          </CardTitle>
          <CardDescription>Choose a building to configure its parking settings</CardDescription>
        </CardHeader>
        <CardContent>
          <Select value={selectedBuilding} onValueChange={setSelectedBuilding}>
            <SelectTrigger className="w-full md:w-80" data-testid="config-building-select">
              <SelectValue placeholder="Select building" />
            </SelectTrigger>
            <SelectContent>
              {buildings.map((building) => (
                <SelectItem key={building.id} value={building.id}>{building.name}</SelectItem>
              ))}
            </SelectContent>
          </Select>
        </CardContent>
      </Card>

      {selectedBuilding && (
        <div className="grid gap-6 md:grid-cols-2">
          {/* Release Time Configuration */}
          <Card>
            <CardHeader>
              <CardTitle className="text-lg flex items-center gap-2">
                <Clock className="w-5 h-5 text-[#08263e]" />
                Parking Release Time
              </CardTitle>
              <CardDescription>Time when parking slots are released for booking each day</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="space-y-2">
                <Label>Release Time</Label>
                <Input type="time" value={formData.release_time}
                  onChange={(e) => setFormData({ ...formData, release_time: e.target.value })}
                  data-testid="release-time-input" />
                <p className="text-xs text-gray-500">Parking slots will be available for booking after this time</p>
              </div>
            </CardContent>
          </Card>

          {/* Default Hours Configuration */}
          <Card>
            <CardHeader>
              <CardTitle className="text-lg flex items-center gap-2">
                <Settings className="w-5 h-5 text-[#08263e]" />
                Default Parking Hours
              </CardTitle>
              <CardDescription>Default start and end times for reservations</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="grid grid-cols-2 gap-4">
                <div className="space-y-2">
                  <Label>Start Time</Label>
                  <Input type="time" value={formData.default_start_time}
                    onChange={(e) => setFormData({ ...formData, default_start_time: e.target.value })}
                    data-testid="start-time-input" />
                </div>
                <div className="space-y-2">
                  <Label>End Time</Label>
                  <Input type="time" value={formData.default_end_time}
                    onChange={(e) => setFormData({ ...formData, default_end_time: e.target.value })}
                    data-testid="end-time-input" />
                </div>
              </div>
              <div className="bg-[#08263e]/5 rounded-lg p-3 text-sm">
                <p className="text-[#08263e] font-medium">
                  Duration: {calculateHours(formData.default_start_time, formData.default_end_time)} hours
                </p>
              </div>
            </CardContent>
          </Card>

          {/* Booking Window */}
          <Card>
            <CardHeader>
              <CardTitle className="text-lg flex items-center gap-2">
                <Calendar className="w-5 h-5 text-[#08263e]" />
                Booking Window
              </CardTitle>
              <CardDescription>How far in advance users can book parking</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="space-y-2">
                <Label>Advance Booking Days</Label>
                <Input type="number" min="1" max="30" value={formData.booking_window_days}
                  onChange={(e) => setFormData({ ...formData, booking_window_days: parseInt(e.target.value) || 7 })}
                  data-testid="booking-window-input" />
                <p className="text-xs text-gray-500">
                  Users can book parking up to {formData.booking_window_days} days in advance
                </p>
              </div>
            </CardContent>
          </Card>

          {/* No-Show Auto-Release Configuration */}
          <Card className="border-red-100">
            <CardHeader>
              <CardTitle className="text-lg flex items-center gap-2">
                <AlertOctagon className="w-5 h-5 text-[#ec474e]" />
                No-Show Slot Release
                <HelpTip text="When enabled, parking slots from no-show reservations will be automatically released and made available for other users to book." />
              </CardTitle>
              <CardDescription>Configure automatic release of parking slots after a no-show</CardDescription>
            </CardHeader>
            <CardContent className="space-y-4">
              <div className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
                <div>
                  <p className="font-medium text-sm">Enable Auto-Release</p>
                  <p className="text-xs text-gray-500">Automatically free up slots after a no-show</p>
                </div>
                <Switch
                  checked={formData.no_show_release_enabled}
                  onCheckedChange={(checked) => setFormData({ ...formData, no_show_release_enabled: checked })}
                  data-testid="no-show-release-toggle"
                />
              </div>
              {formData.no_show_release_enabled && (
                <div className="space-y-2 animate-in fade-in slide-in-from-top-2">
                  <Label>Release After (minutes)</Label>
                  <Input type="number" min="5" max="240" value={formData.no_show_release_minutes}
                    onChange={(e) => setFormData({ ...formData, no_show_release_minutes: parseInt(e.target.value) || 30 })}
                    data-testid="no-show-release-minutes-input" />
                  <p className="text-xs text-gray-500">
                    Slot will be released <strong>{formData.no_show_release_minutes} minutes</strong> after the reservation is tagged as no-show
                  </p>
                  <div className="bg-red-50 border border-red-100 rounded-lg p-3 text-xs text-red-700">
                    <p>Example: If a reservation is marked as no-show at 10:30, the slot will become available at {
                      (() => {
                        const total = 10 * 60 + 30 + formData.no_show_release_minutes;
                        const rh = Math.floor(total / 60) % 24;
                        const rm = total % 60;
                        return `${String(rh).padStart(2, '0')}:${String(rm).padStart(2, '0')}`;
                      })()
                    }.</p>
                  </div>
                </div>
              )}
            </CardContent>
          </Card>
        </div>
      )}

      {/* Waitlist Configuration */}
      {selectedBuilding && (
        <Card className="border-blue-100">
          <CardHeader>
            <CardTitle className="text-lg flex items-center gap-2">
              <ListOrdered className="w-5 h-5 text-blue-600" />
              Waitlist Configuration
              <HelpTip text="When enabled, users can join a waitlist when all slots are fully booked. They'll receive an in-app notification when a slot becomes available." />
            </CardTitle>
            <CardDescription>Allow users to queue for parking when a building is fully booked</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
              <div>
                <p className="font-medium text-sm">Enable Waitlist</p>
                <p className="text-xs text-gray-500">Users can join a waitlist for fully-booked buildings</p>
              </div>
              <Switch
                checked={formData.waitlist_enabled}
                onCheckedChange={(checked) => setFormData({ ...formData, waitlist_enabled: checked })}
                data-testid="waitlist-enabled-toggle"
              />
            </div>
            {formData.waitlist_enabled && (
              <div className="space-y-2 animate-in fade-in slide-in-from-top-2">
                <Label>Notification Window (minutes)</Label>
                <Input type="number" min="5" max="120" value={formData.waitlist_notification_window_minutes}
                  onChange={(e) => setFormData({ ...formData, waitlist_notification_window_minutes: parseInt(e.target.value) || 15 })}
                  data-testid="waitlist-window-input" />
                <p className="text-xs text-gray-500">
                  When a slot opens, the first waitlisted user has <strong>{formData.waitlist_notification_window_minutes} minutes</strong> to book before it's offered to the next person.
                </p>
                <div className="bg-blue-50 border border-blue-100 rounded-lg p-3 text-xs text-blue-700">
                  <p>Users are notified in order. If a user doesn't book within the window, the slot is automatically offered to the next person in line.</p>
                </div>
              </div>
            )}
          </CardContent>
        </Card>
      )}

      {/* Main Building Exclusivity */}
      {selectedBuilding && (
        <Card className="border-green-100">
          <CardHeader>
            <CardTitle className="text-lg flex items-center gap-2">
              <Building2 className="w-5 h-5 text-green-600" />
              Main Building Exclusivity
              <HelpTip text="When enabled, only employees whose main building is set to this building can make parking reservations here. Users from other buildings will be blocked." />
            </CardTitle>
            <CardDescription>Restrict reservations to employees assigned to this building</CardDescription>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex items-center justify-between p-3 bg-gray-50 rounded-lg">
              <div>
                <p className="font-medium text-sm">Enable Main Building Restriction</p>
                <p className="text-xs text-gray-500">Only users whose main building is this location can reserve here</p>
              </div>
              <Switch
                checked={formData.main_building_exclusive}
                onCheckedChange={(checked) => setFormData({ ...formData, main_building_exclusive: checked })}
                data-testid="main-building-exclusive-toggle"
              />
            </div>
            {formData.main_building_exclusive && (
              <div className="bg-green-50 border border-green-100 rounded-lg p-3 text-xs text-green-700">
                <p>Users from other buildings will see an error when trying to reserve parking here. This does not affect admin users.</p>
              </div>
            )}
          </CardContent>
        </Card>
      )}

      {/* Save Button */}
      {selectedBuilding && (
        <div className="flex justify-end">
          <Button onClick={handleSave} disabled={saving}
            className="bg-[#08263e] hover:bg-[#051a2d] text-white" data-testid="save-config-btn">
            <Save className="w-4 h-4 mr-2" />
            {saving ? 'Saving...' : 'Save Configuration'}
          </Button>
        </div>
      )}
    </div>
  );
};

const calculateHours = (start, end) => {
  const [startH, startM] = start.split(':').map(Number);
  const [endH, endM] = end.split(':').map(Number);
  const diff = (endH * 60 + endM) - (startH * 60 + startM);
  return Math.round(diff / 60 * 10) / 10;
};

export default ParkingConfig;
