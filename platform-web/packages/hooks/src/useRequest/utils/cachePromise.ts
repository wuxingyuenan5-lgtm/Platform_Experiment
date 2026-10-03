type CachedKey = string | number;

const cachePromise = new Map<CachedKey, Promise<any>>();

export const getCachePromise = (cacheKey: CachedKey) => {
  return cachePromise.get(cacheKey);
};

export const setCachePromise = (cacheKey: CachedKey, promise: Promise<any>) => {
  // Keep the original promise in the cache so concurrent callers share its identity.
  cachePromise.set(cacheKey, promise);

  // Attach cleanup handlers without replacing the cached promise with a derived one.
  promise
    .then((res) => {
      cachePromise.delete(cacheKey);
      return res;
    })
    .catch(() => {
      cachePromise.delete(cacheKey);
    });
};
