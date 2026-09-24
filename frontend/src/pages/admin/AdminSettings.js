import React, { useState, useEffect } from 'react';
import { templatesAPI, siteContentAPI } from '../../services/api';
import { Button } from '../../components/ui/button';
import { Card, CardContent, CardHeader, CardTitle } from '../../components/ui/card';
import { Input } from '../../components/ui/input';
import { Label } from '../../components/ui/label';
import { Textarea } from '../../components/ui/textarea';
import { toast } from 'sonner';
import { Download, FileSpreadsheet, Globe, Save, Eye } from 'lucide-react';
import { HelpTip } from '../../components/ui/help-tip';

const AdminSettings = () => {
  const [content, setContent] = useState({
    heading_line1: '', heading_highlight: '', heading_line3: '',
    description: '', badge1_text: '', badge2_text: '', announcement: ''
  });
  const [saving, setSaving] = useState(false);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    siteContentAPI.get()
      .then(res => setContent(res.data))
      .catch(() => toast.error('Failed to load site content'))
      .finally(() => setLoading(false));
  }, []);

  const handleDownload = async (type) => {
    try {
      let response, filename;
      if (type === 'users') { response = await templatesAPI.downloadUsers(); filename = 'users_template.csv'; }
      else if (type === 'buildings') { response = await templatesAPI.downloadBuildings(); filename = 'buildings_template.csv'; }
      else { response = await templatesAPI.downloadZones(); filename = 'zones_template.csv'; }
      const url = window.URL.createObjectURL(new Blob([response.data]));
      const a = document.createElement('a'); a.href = url; a.download = filename; a.click();
      window.URL.revokeObjectURL(url);
    } catch { toast.error('Failed to download template'); }
  };

  const handleSaveContent = async () => {
    setSaving(true);
    try {
      await siteContentAPI.update(content);
      toast.success('Login page content updated');
    } catch (error) { toast.error(error.response?.data?.detail || 'Failed to save'); }
    finally { setSaving(false); }
  };

  return (
    <div className="space-y-8" data-testid="admin-settings-page">
      <div>
        <h1 className="text-2xl font-bold text-gray-800">Settings</h1>
        <p className="text-gray-500">Manage templates, content, and application configuration</p>
      </div>

      {/* CSV Templates Section */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-lg">
            <FileSpreadsheet className="w-5 h-5 text-[#08263e]" />
            Bulk Upload Templates
            <HelpTip text="Download CSV templates for bulk uploading users, buildings, and zones. Fill in the template and upload via the respective management pages." />
          </CardTitle>
        </CardHeader>
        <CardContent>
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            <div className="border rounded-lg p-4 space-y-3">
              <div>
                <p className="font-medium text-sm">Users Template</p>
                <p className="text-xs text-gray-500">Columns: email, first_name, last_name, company, role</p>
              </div>
              <Button variant="outline" className="w-full" onClick={() => handleDownload('users')} data-testid="download-users-template">
                <Download className="w-4 h-4 mr-2" /> Download CSV
              </Button>
            </div>
            <div className="border rounded-lg p-4 space-y-3">
              <div>
                <p className="font-medium text-sm">Buildings Template</p>
                <p className="text-xs text-gray-500">Columns: building_name, floor_label, slot_labels</p>
              </div>
              <Button variant="outline" className="w-full" onClick={() => handleDownload('buildings')} data-testid="download-buildings-template">
                <Download className="w-4 h-4 mr-2" /> Download CSV
              </Button>
            </div>
            <div className="border rounded-lg p-4 space-y-3">
              <div>
                <p className="font-medium text-sm">Zones Template</p>
                <p className="text-xs text-gray-500">Columns: zone_name, building_names</p>
              </div>
              <Button variant="outline" className="w-full" onClick={() => handleDownload('zones')} data-testid="download-zones-template">
                <Download className="w-4 h-4 mr-2" /> Download CSV
              </Button>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* Login Page Content Management */}
      <Card>
        <CardHeader>
          <CardTitle className="flex items-center gap-2 text-lg">
            <Globe className="w-5 h-5 text-[#08263e]" />
            Login Page Content
            <HelpTip text="Customize the text displayed on the public login page. Changes are reflected immediately." />
          </CardTitle>
        </CardHeader>
        <CardContent>
          {loading ? (
            <div className="flex items-center justify-center py-8">
              <div className="animate-spin rounded-full h-8 w-8 border-t-2 border-b-2 border-[#08263e]"></div>
            </div>
          ) : (
            <div className="space-y-6">
              {/* Heading */}
              <div className="space-y-4">
                <Label className="text-sm font-semibold text-gray-700">Heading</Label>
                <div className="grid grid-cols-1 md:grid-cols-3 gap-3">
                  <div className="space-y-1">
                    <Label className="text-xs text-gray-500">Line 1</Label>
                    <Input value={content.heading_line1} onChange={(e) => setContent({ ...content, heading_line1: e.target.value })}
                      placeholder="Reserve Your" data-testid="content-heading-line1" />
                  </div>
                  <div className="space-y-1">
                    <Label className="text-xs text-gray-500">Highlight (colored)</Label>
                    <Input value={content.heading_highlight} onChange={(e) => setContent({ ...content, heading_highlight: e.target.value })}
                      placeholder="Parking Spot" data-testid="content-heading-highlight" />
                  </div>
                  <div className="space-y-1">
                    <Label className="text-xs text-gray-500">Line 3</Label>
                    <Input value={content.heading_line3} onChange={(e) => setContent({ ...content, heading_line3: e.target.value })}
                      placeholder="with Ease" data-testid="content-heading-line3" />
                  </div>
                </div>
              </div>

              {/* Description */}
              <div className="space-y-1">
                <Label className="text-xs text-gray-500">Description</Label>
                <Textarea value={content.description} onChange={(e) => setContent({ ...content, description: e.target.value })}
                  placeholder="Seamlessly book, manage, and track your parking reservations..."
                  className="min-h-[80px]" data-testid="content-description" />
              </div>

              {/* Badges */}
              <div className="grid grid-cols-2 gap-3">
                <div className="space-y-1">
                  <Label className="text-xs text-gray-500">Badge 1 Text</Label>
                  <Input value={content.badge1_text} onChange={(e) => setContent({ ...content, badge1_text: e.target.value })}
                    placeholder="Multiple Buildings" data-testid="content-badge1" />
                </div>
                <div className="space-y-1">
                  <Label className="text-xs text-gray-500">Badge 2 Text</Label>
                  <Input value={content.badge2_text} onChange={(e) => setContent({ ...content, badge2_text: e.target.value })}
                    placeholder="Secure Access" data-testid="content-badge2" />
                </div>
              </div>

              {/* Announcement */}
              <div className="space-y-1">
                <Label className="text-xs text-gray-500">Announcement Banner (optional - leave empty to hide)</Label>
                <Input value={content.announcement} onChange={(e) => setContent({ ...content, announcement: e.target.value })}
                  placeholder="e.g., System maintenance on Feb 25..." data-testid="content-announcement" />
              </div>

              {/* Preview */}
              <div className="border rounded-lg p-4 bg-[#08263e] text-white space-y-3">
                <div className="flex items-center gap-2 text-xs text-white/60 mb-2"><Eye className="w-3 h-3" /> Preview</div>
                {content.announcement && (
                  <div className="bg-[#ec474e]/20 border border-[#ec474e]/30 rounded-lg px-3 py-2 text-sm">{content.announcement}</div>
                )}
                <h2 className="text-2xl font-extrabold leading-tight">
                  {content.heading_line1 || 'Reserve Your'}<br />
                  <span className="text-[#ec474e]">{content.heading_highlight || 'Parking Spot'}</span><br />
                  {content.heading_line3 || 'with Ease'}
                </h2>
                <p className="text-white/80 text-sm">{content.description || 'Seamlessly book, manage, and track...'}</p>
                <div className="flex gap-3">
                  {content.badge1_text && <span className="bg-white/10 rounded-full px-3 py-1 text-xs">{content.badge1_text}</span>}
                  {content.badge2_text && <span className="bg-white/10 rounded-full px-3 py-1 text-xs">{content.badge2_text}</span>}
                </div>
              </div>

              <Button className="bg-[#08263e] hover:bg-[#051a2d] text-white" onClick={handleSaveContent} disabled={saving} data-testid="save-content-btn">
                <Save className="w-4 h-4 mr-2" />
                {saving ? 'Saving...' : 'Save Changes'}
              </Button>
            </div>
          )}
        </CardContent>
      </Card>
    </div>
  );
};

export default AdminSettings;
