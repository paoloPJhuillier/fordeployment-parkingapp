import axios from 'axios';

const API_URL = process.env.REACT_APP_BACKEND_URL || '';

const api = axios.create({
  baseURL: `${API_URL}/api`,
  headers: {
    'Content-Type': 'application/json'
  },
  withCredentials: true
});

// Bearer-token fallback. The backend accepts EITHER the HttpOnly auth cookie
// OR an Authorization: Bearer token. Relying on the cookie alone is fragile in
// local dev (cross-site/SameSite rules, and a race where dashboard data calls
// fire before the login Set-Cookie is committed -> intermittent 401s /
// "Failed to load data"). Persisting the login token and sending it as a
// header makes auth independent of cookie timing.
const TOKEN_KEY = 'pjli_access_token';

export const setAuthToken = (token) => {
  if (token) {
    localStorage.setItem(TOKEN_KEY, token);
    api.defaults.headers.common['Authorization'] = `Bearer ${token}`;
  } else {
    localStorage.removeItem(TOKEN_KEY);
    delete api.defaults.headers.common['Authorization'];
  }
};

// Restore any previously stored token on module load (page refresh).
const _storedToken = typeof localStorage !== 'undefined' ? localStorage.getItem(TOKEN_KEY) : null;
if (_storedToken) {
  api.defaults.headers.common['Authorization'] = `Bearer ${_storedToken}`;
}

// Handle auth errors - skip redirect for auth check endpoints
api.interceptors.response.use(
  (response) => response,
  (error) => {
    const url = error.config?.url || '';
    if (error.response?.status === 401 && !url.includes('/auth/me') && !url.includes('/auth/login') && !url.includes('/auth/register') && !url.includes('/auth/logout')) {
      window.location.href = '/login';
    }
    return Promise.reject(error);
  }
);

// Auth API
export const authAPI = {
  login: (email, password) => api.post('/auth/login', { email, password }),
  getMe: () => api.get('/auth/me'),
  logout: () => api.post('/auth/logout'),
  changePassword: (currentPassword, newPassword) => api.post('/auth/change-password', { current_password: currentPassword, new_password: newPassword }),
  forceChangePassword: (newPassword) => api.post('/auth/change-password', { new_password: newPassword }),
  forgotPassword: (email) => api.post('/auth/forgot-password', { email }),
  updateBookingPreferences: (startTime, endTime) => api.put(`/auth/booking-preferences?default_start_time=${startTime || ''}&default_end_time=${endTime || ''}`)
};

// Users API
export const usersAPI = {
  getAll: () => api.get('/users'),
  create: (userData) => api.post('/users', userData),
  update: (userId, userData) => api.put(`/users/${userId}`, userData),
  delete: (userId) => api.delete(`/users/${userId}`),
  bulkUpload: (file, defaultPassword) => {
    const formData = new FormData();
    formData.append('file', file);
    formData.append('default_password', defaultPassword);
    return api.post('/users/bulk-upload', formData, {
      headers: { 'Content-Type': 'multipart/form-data' }
    });
  },
  block: (userId) => api.put(`/users/${userId}/block`),
  unblock: (userId) => api.put(`/users/${userId}/unblock`),
  resetPassword: (userId, password) => api.put(`/users/${userId}/reset-password`, { password }),
  assignMainBuilding: (userId, mainBuilding) => api.put(`/users/${userId}/main-building`, { main_building: mainBuilding }),
  updateTags: (userId, tags) => api.put(`/users/${userId}/tags`, { tags }),
  bulkSetBuilding: (userIds, mainBuilding) => api.post('/users/bulk-set-building', { user_ids: userIds, main_building: mainBuilding }),
  bulkAssignZone: (userIds, zoneId) => api.post('/users/bulk-assign-zone', { user_ids: userIds, zone_id: zoneId }),
};

// Vehicles API
export const vehiclesAPI = {
  getAll: () => api.get('/vehicles'),
  create: (vehicleData) => api.post('/vehicles', vehicleData),
  delete: (vehicleId) => api.delete(`/vehicles/${vehicleId}`)
};

// Buildings API
export const buildingsAPI = {
  getAll: () => api.get('/buildings'),
  create: (buildingData) => api.post('/buildings', buildingData),
  delete: (buildingId) => api.delete(`/buildings/${buildingId}`),
  update: (buildingId, data) => api.put(`/buildings/${buildingId}`, data),
  addFloor: (buildingId, floorData) => api.post(`/buildings/${buildingId}/floors`, floorData),
  uploadFloorLayout: (floorId, file) => {
    const formData = new FormData();
    formData.append('file', file);
    return api.post(`/floors/${floorId}/layout`, formData, {
      headers: { 'Content-Type': 'multipart/form-data' }
    });
  },
  deleteFloorLayout: (floorId) => api.delete(`/floors/${floorId}/layout`)
};

// Reservations API
export const reservationsAPI = {
  getAll: (params) => api.get('/reservations', { params }),
  create: (reservationData) => api.post('/reservations', reservationData),
  cancel: (reservationId) => api.put(`/reservations/${reservationId}/cancel`),
  confirm: (reservationId, photo) => api.post(`/reservations/${reservationId}/confirm-with-photo`, { photo }),
  // Parker self-check-in. Only callable when attendant mode is disabled
  // (server returns 403 otherwise). Returns 410 if the window has expired.
  selfCheckin: (reservationId) => api.post(`/reservations/${reservationId}/checkin`),
  getDailyReservations: (date, building_id) => api.get('/attendant/daily-reservations', { params: { date, building_id } }),
  getAttendantBuildings: () => api.get('/attendant/buildings'),
  getQRCode: (reservationId) => api.get(`/reservations/${reservationId}/qr`),
  adminGetAll: (params) => api.get('/admin/reservations', { params }),
  adminCancel: (reservationId) => api.put(`/admin/reservations/${reservationId}/cancel`),
  reportNoShow: (reservationId) => api.post(`/attendant/reservations/${reservationId}/report-no-show`),
  scanQR: (qrToken) => api.get(`/scan/${qrToken}`),
  confirmReservation: (reservationId) => api.put(`/reservations/${reservationId}/confirm`),
  getStats: () => api.get('/reservations/stats')
};

// Slots API
export const slotsAPI = {
  getAvailable: (buildingId, date, floorId) => api.get('/slots/available', {
    params: { building_id: buildingId, date, floor_id: floorId }
  }),
  rename: (slotId, label) => api.put(`/slots/${slotId}`, { label }),
  addToFloor: (floorId, data) => api.post(`/floors/${floorId}/slots`, data),
  delete: (slotId) => api.delete(`/slots/${slotId}`),
  updateStatus: (slotId, status) => api.put(`/slots/${slotId}/status?status=${status}`)
};

// Zones API
export const zonesAPI = {
  getAll: () => api.get('/zones'),
  create: (zoneData) => api.post('/zones', zoneData),
  update: (zoneId, data) => api.put(`/zones/${zoneId}`, data),
  delete: (zoneId) => api.delete(`/zones/${zoneId}`),
  getUserBuildings: () => api.get('/zones/user-buildings')
};

// Parking Config API
export const configAPI = {
  get: (buildingId) => api.get(`/parking-config/${buildingId}`),
  save: (configData) => api.post('/parking-config', configData)
};

// Reports API
export const reportsAPI = {
  getStats: (params) => api.get('/reports/stats', { params }),
  generateAIInsights: (buildingId) => api.post('/reports/ai-insights', null, { params: { building_id: buildingId } }),
  getInsightsHistory: (limit = 10) => api.get('/reports/ai-insights/history', { params: { limit } }),
  deleteInsight: (insightId) => api.delete(`/reports/ai-insights/${insightId}`),
  // Legacy alias
  getAIInsights: (buildingId) => api.post('/reports/ai-insights', null, { params: { building_id: buildingId } })
};

// Templates API
export const templatesAPI = {
  downloadUsers: () => api.get('/templates/users', { responseType: 'blob' }),
  downloadBuildings: () => api.get('/templates/buildings', { responseType: 'blob' }),
  downloadZones: () => api.get('/templates/zones', { responseType: 'blob' })
};

// Documentation API
export const docsAPI = {
  list: () => api.get('/docs/list'),
  downloadUrl: (filename) => `${API_URL}/api/docs/download/${filename}`,
  downloadZipUrl: (format) => `${API_URL}/api/docs/download-zip?format=${format}`,
};

// Building Policy API
export const buildingPolicyAPI = {
  list: () => api.get('/building-policies'),
  get: (buildingId) => api.get(`/building-policies/${buildingId}`),
  create: (data) => api.post('/building-policies', data),
  update: (buildingId, data) => api.put(`/building-policies/${buildingId}`, data),
  delete: (buildingId) => api.delete(`/building-policies/${buildingId}`),
};

// Slot Registration API
export const slotRegistrationAPI = {
  list: (params) => api.get('/slot-registrations', { params }),
  forUser: (userId) => api.get(`/slot-registrations/user/${userId}`),
  create: (data) => api.post('/slot-registrations', data),
  bulkCreate: (data) => api.post('/slot-registrations/bulk', data),
  update: (id, data) => api.put(`/slot-registrations/${id}`, data),
  delete: (id) => api.delete(`/slot-registrations/${id}`),
};

// Site Content API
export const siteContentAPI = {
  get: () => api.get('/site-content'),
  update: (data) => api.put('/admin/site-content', data)
};

// Notifications API
export const notificationsAPI = {
  getAll: () => api.get('/notifications'),
  getUnreadCount: () => api.get('/notifications/unread-count'),
  markAllRead: () => api.put('/notifications/read-all'),
  markRead: (id) => api.put(`/notifications/${id}/read`)
};

// Waitlist API
export const waitlistAPI = {
  join: (data) => api.post('/waitlist/join', data),
  leave: (entryId) => api.delete(`/waitlist/${entryId}`),
  status: (buildingId, date) => api.get('/waitlist/status', { params: { building_id: buildingId, date } }),
  count: (buildingId, date) => api.get('/waitlist/count', { params: { building_id: buildingId, date } }),
  getTimeline: (buildingId, floorId, date) => api.get('/slots/timeline', { params: { building_id: buildingId, floor_id: floorId, date } }),
};

// Event Blocks API
export const eventBlocksAPI = {
  list: (params) => api.get('/event-blocks', { params }),
  create: (data) => api.post('/event-blocks', data),
  delete: (id) => api.delete(`/event-blocks/${id}`),
};

// System API (admin-only system information)
export const systemAPI = {
  getDbInfo: () => api.get('/system/db-info'),
  getCollectionStats: () => api.get('/system/collection-stats'),
  syncMongoToCouchbase: () => api.post('/system/sync-mongo-to-couchbase'),
  // Public — no auth required. Used by the admin UI to hide gated features
  // (e.g. AI Insights) when the deployment has them turned off.
  getFeatures: () => api.get('/system/features'),
};

export default api;
