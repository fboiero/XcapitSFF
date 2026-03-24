import { useState, useEffect, useCallback } from 'react';

export function useApi(fetcher, deps = [], options = {}) {
  const { immediate = true, fallback = null } = options;
  const [data, setData] = useState(fallback);
  const [loading, setLoading] = useState(immediate);
  const [error, setError] = useState(null);

  const execute = useCallback(async (...args) => {
    setLoading(true);
    setError(null);
    try {
      const result = await fetcher(...args);
      setData(result);
      return result;
    } catch (err) {
      setError(err.message);
      if (fallback !== null) setData(fallback);
      return null;
    } finally {
      setLoading(false);
    }
  }, deps);

  useEffect(() => {
    if (immediate) execute();
  }, [execute, immediate]);

  return { data, loading, error, execute, setData };
}

export function usePolling(fetcher, intervalMs = 10000, deps = []) {
  const api = useApi(fetcher, deps);

  useEffect(() => {
    const id = setInterval(() => api.execute(), intervalMs);
    return () => clearInterval(id);
  }, [api.execute, intervalMs]);

  return api;
}
