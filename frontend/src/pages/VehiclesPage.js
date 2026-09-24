import React, { useState, useEffect } from 'react';
import { useNavigate, Link, useLocation } from 'react-router-dom';
import { useAuth } from '../context/AuthContext';
import { vehiclesAPI } from '../services/api';
import { Button } from '../components/ui/button';
import { Card, CardContent } from '../components/ui/card';
import { Input } from '../components/ui/input';
import { Label } from '../components/ui/label';
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogTrigger } from '../components/ui/dialog';
import { toast } from 'sonner';
import { ArrowLeft, Car, Plus, Trash2, Home, Calendar, User } from 'lucide-react';

const VehiclesPage = () => {
  const { user } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [vehicles, setVehicles] = useState([]);
  const [loading, setLoading] = useState(true);
  const [dialogOpen, setDialogOpen] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [newVehicle, setNewVehicle] = useState({ plate_number: '', make: '', model: '', color: '' });

  useEffect(() => { fetchData(); }, []);

  const fetchData = async () => {
    try {
      const vehiclesRes = await vehiclesAPI.getAll();
      setVehicles(vehiclesRes.data);
    } catch (error) { toast.error('Failed to load vehicles'); }
    finally { setLoading(false); }
  };

  const handleAddVehicle = async (e) => {
    e.preventDefault();
    if (!newVehicle.plate_number) { toast.error('Plate number is required'); return; }
    setSubmitting(true);
    try {
      await vehiclesAPI.create(newVehicle);
      toast.success('Vehicle added successfully');
      setDialogOpen(false);
      setNewVehicle({ plate_number: '', make: '', model: '', color: '' });
      fetchData();
    } catch (error) { toast.error(error.response?.data?.detail || 'Failed to add vehicle'); }
    finally { setSubmitting(false); }
  };

  const handleDeleteVehicle = async (vehicleId) => {
    if (!window.confirm('Are you sure you want to delete this vehicle?')) return;
    try { await vehiclesAPI.delete(vehicleId); toast.success('Vehicle deleted'); fetchData(); }
    catch (error) { toast.error('Failed to delete vehicle'); }
  };

  if (loading) return <div className="min-h-screen flex items-center justify-center bg-gray-50"><div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-[#08263e]"></div></div>;

  return (
    <div className="min-h-screen bg-gray-50 pb-20 md:pb-8" data-testid="vehicles-page">
      <header className="bg-[#08263e] text-white px-4 py-3 md:px-8">
        <div className="max-w-6xl mx-auto flex items-center justify-between">
          <div className="flex items-center gap-4">
            <Button variant="ghost" className="text-white hover:bg-white/20 p-2" onClick={() => navigate('/dashboard')}><ArrowLeft className="w-5 h-5" /></Button>
            <Link to="/dashboard"><img src="/cl-logo.png" alt="Cebuana Lhuillier" className="h-8 w-auto brightness-0 invert cursor-pointer" /></Link>
            <div className="hidden md:block"><p className="text-xs text-white/70">My Vehicles</p></div>
          </div>
          <Dialog open={dialogOpen} onOpenChange={setDialogOpen}>
            <DialogTrigger asChild><Button className="bg-[#ec474e] text-white hover:bg-[#d63a41] rounded-full" data-testid="add-vehicle-btn"><Plus className="w-4 h-4 mr-2" />Add Vehicle</Button></DialogTrigger>
            <DialogContent>
              <DialogHeader><DialogTitle>Add New Vehicle</DialogTitle></DialogHeader>
              <form onSubmit={handleAddVehicle} className="space-y-4 mt-4">
                <div className="space-y-2">
                  <Label htmlFor="plate_number">Plate Number * <span className="text-xs text-gray-400">(1-16 chars)</span></Label>
                  <Input id="plate_number" placeholder="ABC 1234" value={newVehicle.plate_number} onChange={(e) => setNewVehicle({ ...newVehicle, plate_number: e.target.value.toUpperCase().slice(0, 16) })} required maxLength={16} className="font-mono uppercase" data-testid="vehicle-plate-input" />
                </div>
                <div className="grid grid-cols-2 gap-4">
                  <div className="space-y-2"><Label htmlFor="make">Make</Label><Input id="make" placeholder="Toyota" value={newVehicle.make} onChange={(e) => setNewVehicle({ ...newVehicle, make: e.target.value })} data-testid="vehicle-make-input" /></div>
                  <div className="space-y-2"><Label htmlFor="model">Model</Label><Input id="model" placeholder="Vios" value={newVehicle.model} onChange={(e) => setNewVehicle({ ...newVehicle, model: e.target.value })} data-testid="vehicle-model-input" /></div>
                </div>
                <div className="space-y-2"><Label htmlFor="color">Color</Label><Input id="color" placeholder="White" value={newVehicle.color} onChange={(e) => setNewVehicle({ ...newVehicle, color: e.target.value })} data-testid="vehicle-color-input" /></div>
                <div className="flex gap-3 pt-4">
                  <Button type="button" variant="outline" className="flex-1" onClick={() => setDialogOpen(false)}>Cancel</Button>
                  <Button type="submit" className="flex-1 bg-[#08263e] hover:bg-[#051a2d] text-white" disabled={submitting} data-testid="save-vehicle-btn">{submitting ? 'Saving...' : 'Save Vehicle'}</Button>
                </div>
              </form>
            </DialogContent>
          </Dialog>
        </div>
      </header>
      <main className="max-w-6xl mx-auto px-4 py-6 md:px-8">
        {vehicles.length === 0 ? (
          <Card className="border-dashed border-2 border-gray-200"><CardContent className="p-12 text-center"><Car className="w-16 h-16 mx-auto text-gray-300 mb-4" /><h3 className="text-lg font-semibold text-gray-600 mb-2">No Vehicles Registered</h3><p className="text-gray-500 mb-4">Add your first vehicle to start booking</p><Button className="bg-[#ec474e] hover:bg-[#d63a41] text-white rounded-full" onClick={() => setDialogOpen(true)}><Plus className="w-4 h-4 mr-2" />Add Vehicle</Button></CardContent></Card>
        ) : (
          <div className="grid gap-4 md:grid-cols-2 lg:grid-cols-3">
            {vehicles.map((vehicle) => (
              <Card key={vehicle.id} className="overflow-hidden" data-testid={`vehicle-card-${vehicle.id}`}>
                <CardContent className="p-0">
                  <div className="bg-gradient-to-br from-[#08263e] to-[#051a2d] p-4 text-white">
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-3">
                        <div className="w-12 h-12 bg-white/20 rounded-lg flex items-center justify-center"><Car className="w-7 h-7" /></div>
                        <div><p className="font-mono font-bold text-xl">{vehicle.plate_number}</p><p className="text-white/70 text-sm">{[vehicle.color, vehicle.make, vehicle.model].filter(Boolean).join(' ') || 'Vehicle'}</p></div>
                      </div>
                      <Button variant="ghost" size="sm" className="text-white/70 hover:text-white hover:bg-white/20" onClick={() => handleDeleteVehicle(vehicle.id)} data-testid={`delete-vehicle-${vehicle.id}`}><Trash2 className="w-4 h-4" /></Button>
                    </div>
                  </div>
                </CardContent>
              </Card>
            ))}
          </div>
        )}
      </main>
      <nav className="mobile-nav">
        <Link to="/dashboard" className={`mobile-nav-item ${location.pathname === '/dashboard' ? 'active' : ''}`}><Home className="w-5 h-5" /><span className="text-xs">Home</span></Link>
        <Link to="/book" className={`mobile-nav-item ${location.pathname === '/book' ? 'active' : ''}`}><Plus className="w-5 h-5" /><span className="text-xs">Book</span></Link>
        <Link to="/reservations" className={`mobile-nav-item ${location.pathname === '/reservations' ? 'active' : ''}`}><Calendar className="w-5 h-5" /><span className="text-xs">Bookings</span></Link>
        <Link to="/vehicles" className={`mobile-nav-item ${location.pathname === '/vehicles' ? 'active' : ''}`}><Car className="w-5 h-5" /><span className="text-xs">Vehicles</span></Link>
        <Link to="/profile" className={`mobile-nav-item ${location.pathname === '/profile' ? 'active' : ''}`}><User className="w-5 h-5" /><span className="text-xs">Profile</span></Link>
      </nav>
    </div>
  );
};

export default VehiclesPage;
