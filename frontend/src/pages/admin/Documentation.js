import { useState, useEffect } from 'react';
import { docsAPI } from '../../services/api';
import { FileText, Download, FileIcon, Loader2, Archive } from 'lucide-react';

const DOC_META = {
  '01_Business_Requirements': { label: 'Business Requirements', section: 'Requirements' },
  '02_System_Requirements_Specification': { label: 'System Requirements Specification', section: 'Requirements' },
  '03_System_Design': { label: 'System Design (HLD/LLD)', section: 'System Design' },
  '03a_Architecture_Diagrams': { label: 'Architecture Diagrams', section: 'System Design' },
  '03b_Entity_Relationship_Diagram': { label: 'Entity Relationship Diagram', section: 'System Design' },
  '03c_Sequence_Diagrams': { label: 'Sequence Diagrams', section: 'System Design' },
  '03d_Compliance_Matrix': { label: 'Compliance & Traceability Matrix', section: 'System Design' },
  '04_Test_Plan': { label: 'Test Plan', section: 'Testing' },
  '04a_Test_Scripts': { label: 'Test Scripts', section: 'Testing' },
  '04b_Test_Execution_Results': { label: 'Test Execution Results', section: 'Testing' },
  '05a_End_User_Guide': { label: 'End User Guide', section: 'User Guides' },
  '05b_Admin_User_Guide': { label: 'Admin User Guide', section: 'User Guides' },
  '05c_Attendant_Guide': { label: 'Attendant Guide', section: 'User Guides' },
  '06_Deployment_Guide': { label: 'Deployment Guide', section: 'Deployment' },
};

const SECTION_COLORS = {
  'Requirements': 'bg-blue-50 border-blue-200 text-blue-700',
  'System Design': 'bg-emerald-50 border-emerald-200 text-emerald-700',
  'Testing': 'bg-amber-50 border-amber-200 text-amber-700',
  'User Guides': 'bg-violet-50 border-violet-200 text-violet-700',
  'Deployment': 'bg-slate-50 border-slate-200 text-slate-700',
};

export default function Documentation() {
  const [files, setFiles] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    docsAPI.list().then(res => {
      setFiles(res.data.files || []);
    }).catch(() => {}).finally(() => setLoading(false));
  }, []);

  // Group by document (strip extension) then by section
  const grouped = {};
  files.forEach(f => {
    const baseName = f.name.replace(/\.(docx|pdf)$/, '');
    const meta = DOC_META[baseName] || { label: baseName, section: 'Other' };
    if (!grouped[meta.section]) grouped[meta.section] = {};
    if (!grouped[meta.section][baseName]) {
      grouped[meta.section][baseName] = { label: meta.label, formats: [] };
    }
    grouped[meta.section][baseName].formats.push(f);
  });

  const handleDownload = (filename) => {
    const url = docsAPI.downloadUrl(filename);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    a.click();
  };

  const handleDownloadZip = (format) => {
    const url = docsAPI.downloadZipUrl(format);
    const a = document.createElement('a');
    a.href = url;
    a.click();
  };

  const totalSize = files.reduce((sum, f) => sum + f.size_kb, 0);
  const pdfSize = files.filter(f => f.format === 'pdf').reduce((sum, f) => sum + f.size_kb, 0);
  const docxSize = files.filter(f => f.format === 'docx').reduce((sum, f) => sum + f.size_kb, 0);

  if (loading) {
    return (
      <div className="flex items-center justify-center h-64" data-testid="docs-loading">
        <Loader2 className="w-6 h-6 animate-spin text-slate-400" />
      </div>
    );
  }

  return (
    <div className="space-y-6" data-testid="documentation-page">
      <div className="flex flex-col sm:flex-row sm:items-end sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold text-slate-800" data-testid="docs-title">Documentation</h1>
          <p className="text-sm text-slate-500 mt-1">Download system documentation in Word or PDF format.</p>
        </div>
        {files.length > 0 && (
          <div className="flex flex-wrap gap-2" data-testid="bulk-download-buttons">
            <button
              onClick={() => handleDownloadZip('pdf')}
              className="flex items-center gap-1.5 px-3 py-2 text-xs font-medium rounded-lg bg-red-600 text-white hover:bg-red-700 transition-colors"
              data-testid="download-all-pdf"
            >
              <Archive className="w-3.5 h-3.5" />
              All PDF
              <span className="opacity-70">({Math.round(pdfSize / 1024 * 10) / 10}MB)</span>
            </button>
            <button
              onClick={() => handleDownloadZip('docx')}
              className="flex items-center gap-1.5 px-3 py-2 text-xs font-medium rounded-lg bg-blue-600 text-white hover:bg-blue-700 transition-colors"
              data-testid="download-all-docx"
            >
              <Archive className="w-3.5 h-3.5" />
              All Word
              <span className="opacity-70">({Math.round(docxSize / 1024 * 10) / 10}MB)</span>
            </button>
            <button
              onClick={() => handleDownloadZip('all')}
              className="flex items-center gap-1.5 px-3 py-2 text-xs font-medium rounded-lg bg-slate-700 text-white hover:bg-slate-800 transition-colors"
              data-testid="download-all"
            >
              <Archive className="w-3.5 h-3.5" />
              Download All
              <span className="opacity-70">({Math.round(totalSize / 1024 * 10) / 10}MB)</span>
            </button>
          </div>
        )}
      </div>

      {Object.entries(grouped).map(([section, docs]) => (
        <div key={section} data-testid={`docs-section-${section.toLowerCase().replace(/\s+/g, '-')}`}>
          <div className="flex items-center gap-2 mb-3">
            <span className={`text-xs font-semibold px-2.5 py-1 rounded border ${SECTION_COLORS[section] || 'bg-gray-50 border-gray-200 text-gray-600'}`}>
              {section}
            </span>
            <span className="text-xs text-slate-400">{Object.keys(docs).length} document{Object.keys(docs).length !== 1 ? 's' : ''}</span>
          </div>
          <div className="grid gap-2">
            {Object.entries(docs).map(([baseName, doc]) => (
              <div
                key={baseName}
                className="flex items-center justify-between p-3 bg-white border border-slate-200 rounded-lg hover:border-slate-300 transition-colors"
                data-testid={`doc-row-${baseName}`}
              >
                <div className="flex items-center gap-3 min-w-0">
                  <FileText className="w-5 h-5 text-slate-400 flex-shrink-0" />
                  <span className="text-sm font-medium text-slate-700 truncate">{doc.label}</span>
                </div>
                <div className="flex items-center gap-2 flex-shrink-0">
                  {doc.formats.map(f => (
                    <button
                      key={f.name}
                      onClick={() => handleDownload(f.name)}
                      className={`flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-md transition-colors ${
                        f.format === 'pdf'
                          ? 'bg-red-50 text-red-700 hover:bg-red-100 border border-red-200'
                          : 'bg-blue-50 text-blue-700 hover:bg-blue-100 border border-blue-200'
                      }`}
                      data-testid={`download-${f.name}`}
                    >
                      <Download className="w-3.5 h-3.5" />
                      {f.format.toUpperCase()}
                      <span className="text-[10px] opacity-60">{f.size_kb}KB</span>
                    </button>
                  ))}
                </div>
              </div>
            ))}
          </div>
        </div>
      ))}

      {files.length === 0 && (
        <div className="text-center py-12 text-slate-400" data-testid="docs-empty">
          <FileIcon className="w-12 h-12 mx-auto mb-3 opacity-50" />
          <p>No documentation files found.</p>
        </div>
      )}
    </div>
  );
}
