import React, { useEffect, useState } from 'react';
import { useParams, Link } from 'react-router-dom';
import { reservationsAPI } from '../services/api';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Badge } from '../components/ui/badge';
import { Calendar, Clock, MapPin, Car, User, ArrowLeft } from 'lucide-react';
import { Button } from '../components/ui/button';

const statusColors = {
  pending: 'bg-yellow-100 text-yellow-800',  confirmed: 'bg-green-100 text-green-800',
  cancelled: 'bg-red-100 text-red-800',
  completed: 'bg-blue-100 text-blue-800',
  no_show: 'bg-gray-100 text-gray-800',
};

export default function ScanPage() {
  const { qrToken } = useParams();
  const [data, setData] = useState(null);
  const [error, setError] = useState(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const fetchData = async () => {
      try {
        const response = await reservationsAPI.scanQR(qrToken);
        setData(response.data);
      } catch (err) {
        if (err.response?.status === 401 || err.response?.status === 403) {
          setError('Authentication required. Only parking attendants and admins can scan QR codes.');
        } else {
          setError('Reservation not found or invalid QR code.');
        }
      } finally {
        setLoading(false);
      }
    };
    fetchData();
  }, [qrToken]);

  if (loading) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50" data-testid="scan-loading">
        <div className="animate-spin rounded-full h-12 w-12 border-t-2 border-b-2 border-[#08263e]"></div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen flex items-center justify-center bg-gray-50 p-4" data-testid="scan-error">
        <Card className="max-w-md w-full">
          <CardContent className="pt-6 text-center">
            <p className="text-red-600 font-medium mb-4">{error}</p>
            <Link to="/login">
              <Button variant="outline" data-testid="scan-error-back-btn">
                <ArrowLeft className="w-4 h-4 mr-2" /> Go to Login
              </Button>
            </Link>
          </CardContent>
        </Card>
      </div>
    );
  }

  return (
    <div className="min-h-screen bg-gray-50 p-4 flex items-center justify-center" data-testid="scan-result-page">
      <Card className="max-w-md w-full shadow-lg">
        <CardHeader className="bg-[#08263e] text-white rounded-t-lg">
          <CardTitle className="text-lg" data-testid="scan-result-title">Parking Reservation</CardTitle>
        </CardHeader>
        <CardContent className="pt-6 space-y-4">
          <div className="flex justify-between items-center">
            <span className="text-sm text-gray-500">Status</span>
            <Badge className={statusColors[data.status]} data-testid="scan-result-status">{data.status?.toUpperCase()}</Badge>
          </div>
          <div className="flex items-center gap-3">
            <User className="w-4 h-4 text-gray-400" />
            <span data-testid="scan-result-user">{data.user_name}</span>
          </div>
          <div className="flex items-center gap-3">
            <Calendar className="w-4 h-4 text-gray-400" />
            <span data-testid="scan-result-date">{data.date}</span>
          </div>
          <div className="flex items-center gap-3">
            <Clock className="w-4 h-4 text-gray-400" />
            <span data-testid="scan-result-time">{data.start_time} - {data.end_time}</span>
          </div>
          <div className="flex items-center gap-3">
            <MapPin className="w-4 h-4 text-gray-400" />
            <span data-testid="scan-result-location">{data.building_name} / {data.floor_label} / {data.slot_label}</span>
          </div>
          <div className="flex items-center gap-3">
            <Car className="w-4 h-4 text-gray-400" />
            <span data-testid="scan-result-vehicle">{data.vehicle_plate}</span>
          </div>
          {data.no_show_reported && (
            <Badge variant="destructive" data-testid="scan-result-no-show">No-Show Reported</Badge>
          )}
        </CardContent>
      </Card>
    </div>
  );
}
