import React, { useEffect, useState } from 'react';
import { Card, CardContent, CardHeader, CardTitle } from '../components/ui/card';
import { Button } from '../components/ui/button';
import { Database, Cloud, RefreshCw, Check, AlertTriangle } from 'lucide-react';
import { toast } from 'sonner';
import { systemAPI } from '../services/api';

/**
 * Admin-only card that shows per-collection counts on the active DB and
 * provides a one-click "Sync now: Mongo -> Couchbase" button. The sync
 * button only appears when Couchbase is the active backend.
 */
const DatabaseHealthCard = () => {
  const [info, setInfo] = useState(null);
  const [stats, setStats] = useState(null);
  const [loading, setLoading] = useState(true);
  const [syncing, setSyncing] = useState(false);

  const fetchAll = async () => {
    setLoading(true);
    try {
      const [dbInfo, collStats] = await Promise.all([
        systemAPI.getDbInfo(),
        systemAPI.getCollectionStats(),
      ]);
      setInfo(dbInfo.data);
      setStats(collStats.data);
    } catch (e) {
      // Admin-only endpoints; non-admins will silently see nothing
      setInfo(null);
      setStats(null);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchAll();
  }, []);

  const handleSync = async () => {
    if (syncing) return;
    setSyncing(true);
    const tId = toast.loading('Mirroring MongoDB → Couchbase Capella...');
    try {
      const { data } = await systemAPI.syncMongoToCouchbase();
      toast.success(
        `Synced ${data.total_written} docs in ${data.elapsed_seconds}s` +
          (data.errors ? ` (${data.errors} errors)` : ''),
        { id: tId }
      );
      // Refresh counts against current DB
      fetchAll();
    } catch (e) {
      const msg = e?.response?.data?.detail || e?.message || 'Sync failed';
      toast.error(`Sync failed: ${msg}`, { id: tId });
    } finally {
      setSyncing(false);
    }
  };

  if (loading) {
    return null; // keep the dashboard quiet until we know
  }
  if (!info || !stats) {
    return null; // non-admin or endpoint unavailable
  }

  const isCouchbase = info.db_type === 'couchbase';
  const HeaderIcon = isCouchbase ? Cloud : Database;
  const accent = isCouchbase ? 'text-red-600' : 'text-emerald-600';
  const bubble = isCouchbase
    ? 'bg-red-50 border-red-200'
    : 'bg-emerald-50 border-emerald-200';

  const nonEmpty = stats.collections.filter((c) => c.count !== 0);

  return (
    <Card data-testid="db-health-card" className="border-slate-200">
      <CardHeader className="pb-3">
        <div className="flex items-start justify-between gap-3">
          <CardTitle className="text-lg flex items-center gap-2">
            <HeaderIcon className={`w-5 h-5 ${accent}`} />
            Database Health
          </CardTitle>
          <div className={`text-xs rounded-full border px-2 py-0.5 ${bubble} ${accent} flex items-center gap-1`}>
            <Check className="w-3 h-3" />
            {info.label}
          </div>
        </div>
        <p className="text-xs text-gray-500 mt-1 truncate" title={info.host}>
          {info.host}
          {info.database_name ? ` / ${info.database_name}` : ''}
        </p>
      </CardHeader>

      <CardContent className="space-y-4">
        <div className="flex items-baseline gap-2">
          <span className="text-3xl font-bold text-[#08263e]" data-testid="db-health-total">
            {stats.total_documents.toLocaleString()}
          </span>
          <span className="text-xs text-gray-500">total documents across {nonEmpty.length} collections</span>
        </div>

        <div
          className="grid grid-cols-2 md:grid-cols-3 gap-x-4 gap-y-1.5 text-xs max-h-48 overflow-y-auto pr-2"
          data-testid="db-health-collection-grid"
        >
          {stats.collections.map((c) => (
            <div
              key={c.name}
              className="flex items-center justify-between border-b border-slate-100 py-1 last:border-b-0"
              data-testid={`db-health-row-${c.name}`}
            >
              <span className="truncate text-gray-600">{c.name}</span>
              <span
                className={`font-mono tabular-nums ${c.count < 0 ? 'text-amber-600' : 'text-[#08263e]'}`}
                title={c.count < 0 ? 'Unable to count' : undefined}
              >
                {c.count < 0 ? '—' : c.count.toLocaleString()}
              </span>
            </div>
          ))}
        </div>

        {isCouchbase && (
          <div className="flex items-start gap-3 pt-2 border-t border-slate-100">
            <Button
              size="sm"
              onClick={handleSync}
              disabled={syncing}
              data-testid="db-health-sync-btn"
              className="bg-[#08263e] hover:bg-[#051a2d] text-white"
            >
              <RefreshCw className={`w-4 h-4 mr-2 ${syncing ? 'animate-spin' : ''}`} />
              {syncing ? 'Syncing...' : 'Sync now: Mongo → Couchbase'}
            </Button>
            <div className="text-[11px] text-gray-500 leading-snug max-w-sm">
              <AlertTriangle className="w-3 h-3 inline mr-1 text-amber-500" />
              Mirrors the local MongoDB snapshot into Capella with upsert.
              Safe to re-run — existing Couchbase docs are overwritten by Mongo's version.
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
};

export default DatabaseHealthCard;
