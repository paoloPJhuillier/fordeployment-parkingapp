import React, { useState, useEffect, useCallback } from 'react';
import { useNavigate } from 'react-router-dom';
import { notificationsAPI } from '../services/api';
import { Popover, PopoverContent, PopoverTrigger } from '../components/ui/popover';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '../components/ui/dialog';
import { Button } from '../components/ui/button';
import { Bell, Check, AlertOctagon, Info, CheckCircle2, Clock, X } from 'lucide-react';
import { formatDistanceToNow, parseISO } from 'date-fns';

const NotificationBell = () => {
  const navigate = useNavigate();
  const [notifications, setNotifications] = useState([]);
  const [unreadCount, setUnreadCount] = useState(0);
  const [open, setOpen] = useState(false);
  const [selectedNotification, setSelectedNotification] = useState(null);

  const fetchUnread = useCallback(async () => {
    try {
      const res = await notificationsAPI.getUnreadCount();
      setUnreadCount(res.data.count);
    } catch {}
  }, []);

  useEffect(() => {
    fetchUnread();
    const interval = setInterval(fetchUnread, 30000); // Check every 30s for waitlist urgency
    return () => clearInterval(interval);
  }, [fetchUnread]);

  const handleOpen = async (isOpen) => {
    setOpen(isOpen);
    if (isOpen) {
      try {
        const res = await notificationsAPI.getAll();
        setNotifications(res.data);
      } catch {}
    }
  };

  const handleMarkAllRead = async () => {
    try {
      await notificationsAPI.markAllRead();
      setUnreadCount(0);
      setNotifications(prev => prev.map(n => ({ ...n, read: true })));
    } catch {}
  };

  const handleNotificationClick = async (n) => {
    // Mark as read
    if (!n.read) {
      try {
        await notificationsAPI.markRead(n.id);
        setNotifications(prev => prev.map(notif => 
          notif.id === n.id ? { ...notif, read: true } : notif
        ));
        setUnreadCount(prev => Math.max(0, prev - 1));
      } catch {}
    }
    
    // Show full content in dialog
    setSelectedNotification(n);
    setOpen(false);
  };

  const handleNotificationAction = (n) => {
    if (n.type === 'waitlist_available') {
      setSelectedNotification(null);
      navigate('/book');
    }
  };

  const getIcon = (type) => {
    switch (type) {
      case 'no_show': return <AlertOctagon className="w-4 h-4 text-red-500 shrink-0" />;
      case 'success': return <CheckCircle2 className="w-4 h-4 text-green-500 shrink-0" />;
      case 'waitlist_available': return <Clock className="w-4 h-4 text-blue-600 shrink-0 animate-pulse" />;
      default: return <Info className="w-4 h-4 text-blue-500 shrink-0" />;
    }
  };

  return (
  <>
    <Popover open={open} onOpenChange={handleOpen}>
      <PopoverTrigger asChild>
        <Button variant="ghost" className="relative text-white hover:bg-white/20 w-10 h-10 p-0" data-testid="notification-bell">
          <Bell className="w-5 h-5" />
          {unreadCount > 0 && (
            <span className="absolute -top-0.5 -right-0.5 w-5 h-5 bg-[#ec474e] text-white text-[10px] font-bold rounded-full flex items-center justify-center animate-pulse" data-testid="notification-badge">
              {unreadCount > 9 ? '9+' : unreadCount}
            </span>
          )}
        </Button>
      </PopoverTrigger>
      <PopoverContent className="w-80 p-0" align="end">
        <div className="flex items-center justify-between p-3 border-b">
          <h3 className="font-semibold text-sm">Notifications</h3>
          {unreadCount > 0 && (
            <Button variant="ghost" size="sm" className="h-7 text-xs text-[#08263e]" onClick={handleMarkAllRead} data-testid="mark-all-read-btn">
              <Check className="w-3 h-3 mr-1" /> Mark all read
            </Button>
          )}
        </div>
        <div className="max-h-80 overflow-y-auto">
          {notifications.length === 0 ? (
            <div className="p-6 text-center text-gray-400 text-sm">
              <Bell className="w-8 h-8 mx-auto mb-2 opacity-30" />
              No notifications
            </div>
          ) : (
            notifications.map(n => (
              <div 
                key={n.id} 
                className={`flex gap-3 p-3 border-b last:border-0 transition-colors cursor-pointer hover:bg-gray-50 ${n.read ? 'bg-white' : n.type === 'waitlist_available' ? 'bg-blue-50' : 'bg-blue-50/50'}`}
                onClick={() => handleNotificationClick(n)}
                data-testid={`notification-${n.id}`}
              >
                <div className="mt-0.5">{getIcon(n.type)}</div>
                <div className="flex-1 min-w-0">
                  <p className={`text-sm ${n.read ? 'text-gray-700' : 'font-medium text-gray-900'}`}>{n.title}</p>
                  <p className="text-xs text-gray-500 mt-0.5 line-clamp-2">{n.message}</p>
                  {n.type === 'waitlist_available' && !n.read && (
                    <Button size="sm" className="mt-2 h-7 bg-blue-600 hover:bg-blue-700 text-white text-xs" data-testid="book-now-from-notification">
                      Book Now
                    </Button>
                  )}
                  <p className="text-[10px] text-gray-400 mt-1">
                    {(() => { try { return formatDistanceToNow(parseISO(n.created_at), { addSuffix: true }); } catch { return ''; } })()}
                  </p>
                </div>
                {!n.read && <div className="w-2 h-2 bg-[#ec474e] rounded-full mt-1.5 shrink-0" />}
              </div>
            ))
          )}
        </div>
      </PopoverContent>
    </Popover>

    {/* Notification Detail Dialog */}
    <Dialog open={!!selectedNotification} onOpenChange={(open) => !open && setSelectedNotification(null)}>
      <DialogContent className="max-w-md">
        <DialogHeader>
          <DialogTitle className="flex items-center gap-2">
            {selectedNotification && getIcon(selectedNotification.type)}
            {selectedNotification?.title}
          </DialogTitle>
        </DialogHeader>
        <div className="space-y-4" data-testid="notification-detail-dialog">
          <p className="text-sm text-gray-700 whitespace-pre-wrap">{selectedNotification?.message}</p>
          <p className="text-xs text-gray-400">
            {selectedNotification?.created_at && (() => { 
              try { return formatDistanceToNow(parseISO(selectedNotification.created_at), { addSuffix: true }); } 
              catch { return ''; } 
            })()}
          </p>
          {selectedNotification?.type === 'waitlist_available' && (
            <Button 
              className="w-full bg-blue-600 hover:bg-blue-700 text-white" 
              onClick={() => handleNotificationAction(selectedNotification)}
              data-testid="notification-action-btn"
            >
              Book Now
            </Button>
          )}
        </div>
      </DialogContent>
    </Dialog>
  </>
  );
};

export default NotificationBell;
