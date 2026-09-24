import { useEffect, useState } from 'react';
import { systemAPI } from '../services/api';

// Cache the flags for the lifetime of the SPA tab. The endpoint is public,
// cheap, and the values only change at backend restart — fetching once on
// app load is plenty.
let _cache = null;
let _inflight = null;

/**
 * useFeatures — returns the runtime feature-flag snapshot from
 * GET /api/system/features. While the first fetch is in flight we return
 * an empty object (every flag undefined), so callers that gate UI with
 * `if (flag) {...}` simply hide the surface for a few hundred ms instead
 * of flashing it on. On a network/parse error we fail-OPEN so optional UI
 * doesn't disappear forever if the endpoint is briefly unreachable.
 *
 * Usage:
 *   const { ai_insights_enabled } = useFeatures();
 */
export default function useFeatures() {
  const [flags, setFlags] = useState(_cache || {});
  const [loading, setLoading] = useState(_cache == null);

  useEffect(() => {
    if (_cache) return;
    if (!_inflight) {
      _inflight = systemAPI
        .getFeatures()
        .then((r) => {
          _cache = r.data;
          return r.data;
        })
        .catch(() => {
          // Fail-open on hard error: keep optional UI visible if the
          // endpoint is unreachable. Worse to hide a working feature
          // than to show one that 503s on click.
          _cache = { ai_insights_enabled: true };
          return _cache;
        });
    }
    _inflight.then((data) => {
      setFlags(data);
      setLoading(false);
    });
  }, []);

  return { ...flags, loading };
}
