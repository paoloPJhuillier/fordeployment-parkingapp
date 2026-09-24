import React, { useEffect, useState } from 'react';
import { Database, Cloud, CheckCircle2, AlertCircle } from 'lucide-react';
import { systemAPI } from '../services/api';

/**
 * Compact badge showing the active database backend (MongoDB / Couchbase).
 * Admin-only. Polls once on mount and when the route changes.
 */
const DbStatusBadge = () => {
  const [info, setInfo] = useState(null);
  const [error, setError] = useState(false);

  useEffect(() => {
    let cancelled = false;
    systemAPI
      .getDbInfo()
      .then((r) => {
        if (!cancelled) setInfo(r.data);
      })
      .catch(() => {
        if (!cancelled) setError(true);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  if (error || !info) {
    return null; // silent fail — badge is non-critical
  }

  const isCouchbase = info.db_type === 'couchbase';
  const Icon = isCouchbase ? Cloud : Database;
  const bgClass = isCouchbase
    ? 'bg-red-500/20 text-red-100 border-red-400/40'
    : 'bg-emerald-500/20 text-emerald-100 border-emerald-400/40';

  return (
    <div
      data-testid="db-status-badge"
      title={`${info.label} — ${info.host || ''}${info.database_name ? ' / ' + info.database_name : ''}`}
      className={`flex items-center gap-1.5 text-[10px] font-medium rounded-full border px-2 py-0.5 ${bgClass}`}
    >
      <Icon className="w-3 h-3" />
      <span className="uppercase tracking-wide">{info.label}</span>
      {info.connected ? (
        <CheckCircle2 className="w-3 h-3 opacity-80" />
      ) : (
        <AlertCircle className="w-3 h-3 opacity-80" />
      )}
    </div>
  );
};

export default DbStatusBadge;
