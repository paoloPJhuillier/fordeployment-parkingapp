import React, { useState, useEffect } from 'react';
import { useNavigate, Link, useLocation, Outlet } from 'react-router-dom';
import { useAuth } from '../../context/AuthContext';
import { 
  LayoutDashboard, Users, Building2, MapPinned, Settings, 
  BarChart3, UserCog, LogOut, Menu, X, Car, ChevronRight, Calendar, Wrench, FileText, Shield, ShieldBan
} from 'lucide-react';
import { Button } from '../../components/ui/button';
import { cn } from '../../lib/utils';
import DbStatusBadge from '../../components/DbStatusBadge';

const AdminLayout = ({ children }) => {
  const { user, logout } = useAuth();
  const navigate = useNavigate();
  const location = useLocation();
  const [sidebarOpen, setSidebarOpen] = useState(false);

  const handleLogout = () => {
    logout();
    navigate('/login');
  };

  const menuItems = [
    { path: '/admin', icon: LayoutDashboard, label: 'Dashboard', exact: true },
    { path: '/admin/reservations', icon: Calendar, label: 'Reservations' },
    { path: '/admin/users', icon: Users, label: 'User Management' },
    { path: '/admin/buildings', icon: Building2, label: 'Buildings' },
    { path: '/admin/zones', icon: MapPinned, label: 'Zone Management' },
    { path: '/admin/parking-config', icon: Settings, label: 'Parking Config' },
    { path: '/admin/building-policies', icon: Shield, label: 'Building Policies' },
    { path: '/admin/event-blocking', icon: ShieldBan, label: 'Event Blocking' },
    { path: '/admin/reports', icon: BarChart3, label: 'Reports & Analytics' },
    { path: '/admin/attendants', icon: UserCog, label: 'Attendants' },
    { path: '/admin/settings', icon: Wrench, label: 'Settings' },
    { path: '/admin/docs', icon: FileText, label: 'Documentation' },
  ];

  const isActive = (item) => {
    if (item.exact) {
      return location.pathname === item.path;
    }
    return location.pathname.startsWith(item.path);
  };

  return (
    <div className="min-h-screen bg-gray-50" data-testid="admin-layout">
      {/* Mobile Header */}
      <header className="lg:hidden bg-[#08263e] text-white px-4 py-3 flex items-center justify-between">
        <div className="flex items-center gap-3">
          <Button
            variant="ghost"
            size="sm"
            className="text-white hover:bg-white/20 p-1"
            onClick={() => setSidebarOpen(true)}
            data-testid="mobile-menu-btn"
          >
            <Menu className="w-6 h-6" />
          </Button>
          <div className="flex items-center gap-2">
            <div className="w-8 h-8 bg-[#ec474e] rounded-lg flex items-center justify-center">
              <Car className="w-5 h-5 text-[#08263e]" />
            </div>
            <span className="font-bold">Admin Panel</span>
          </div>
        </div>
      </header>

      {/* Sidebar */}
      <aside className={cn(
        "sidebar",
        sidebarOpen ? "translate-x-0" : "-translate-x-full lg:translate-x-0"
      )}>
        {/* Logo */}
        <div className="p-4 border-b border-white/10">
          <div className="flex items-center justify-between">
            <Link to="/admin">
              <img 
                src="/cl-logo.png" 
                alt="Cebuana Lhuillier" 
                className="h-10 w-auto brightness-0 invert cursor-pointer"
              />
            </Link>
            <Button
              variant="ghost"
              size="sm"
              className="lg:hidden text-white hover:bg-white/20 p-1"
              onClick={() => setSidebarOpen(false)}
            >
              <X className="w-5 h-5" />
            </Button>
          </div>
          <p className="text-xs text-white/60 mt-2">Parking Admin Panel</p>
          <div className="mt-2">
            <DbStatusBadge />
          </div>
        </div>

        {/* User Info */}
        <div className="p-4 border-b border-white/10">
          <div className="flex items-center gap-3">
            <div className="w-10 h-10 bg-white/20 rounded-full flex items-center justify-center">
              <span className="text-lg font-bold">{user?.first_name?.[0]}</span>
            </div>
            <div className="flex-1 min-w-0">
              <p className="font-medium truncate">{user?.first_name} {user?.last_name}</p>
              <p className="text-xs text-white/70 truncate capitalize">{user?.role === 'admin' ? 'Administrator' : user?.role}</p>
            </div>
          </div>
        </div>

        {/* Navigation */}
        <nav className="p-2 flex-1">
          {menuItems.map((item) => (
            <Link
              key={item.path}
              to={item.path}
              className={cn(
                "sidebar-item",
                isActive(item) && "active"
              )}
              onClick={() => setSidebarOpen(false)}
              data-testid={`nav-${item.label.toLowerCase().replace(/\s+/g, '-')}`}
            >
              <item.icon className="w-5 h-5" />
              <span>{item.label}</span>
              {isActive(item) && <ChevronRight className="w-4 h-4 ml-auto" />}
            </Link>
          ))}
        </nav>

        {/* Logout */}
        <div className="p-4 border-t border-white/10">
          <Button
            variant="ghost"
            className="w-full justify-start text-white/70 hover:text-white hover:bg-white/10"
            onClick={handleLogout}
            data-testid="admin-logout-btn"
          >
            <LogOut className="w-5 h-5 mr-3" />
            Sign Out
          </Button>
        </div>
      </aside>

      {/* Overlay for mobile */}
      {sidebarOpen && (
        <div 
          className="fixed inset-0 bg-black/50 z-30 lg:hidden"
          onClick={() => setSidebarOpen(false)}
        />
      )}

      {/* Main Content */}
      <main className="lg:ml-64">
        {/* PPA-31 fix: extra bottom padding so the floating "Made with Emergent"
            platform badge in the bottom-right corner never overlaps Save / submit
            buttons sitting at the end of admin pages. */}
        <div className="p-4 md:p-8 pb-24 md:pb-28">
          {children}
        </div>
      </main>
    </div>
  );
};

export default AdminLayout;
