const BASE = import.meta.env.DEV ? '/api' : '';

function toSnakeCase(obj) {
  if (Array.isArray(obj)) return obj.map(toSnakeCase);
  if (obj && typeof obj === 'object') {
    return Object.fromEntries(
      Object.entries(obj).map(([k, v]) => [
        k.replace(/[A-Z]/g, (m) => '_' + m.toLowerCase()),
        toSnakeCase(v),
      ])
    );
  }
  return obj;
}

function toCamelCase(obj) {
  if (Array.isArray(obj)) return obj.map(toCamelCase);
  if (obj && typeof obj === 'object') {
    return Object.fromEntries(
      Object.entries(obj).map(([k, v]) => [
        k.replace(/_([a-z])/g, (_, c) => c.toUpperCase()),
        toCamelCase(v),
      ])
    );
  }
  return obj;
}

async function post(path, body, signal) {
  const res = await fetch(`${BASE}${path}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(toSnakeCase(body)),
    signal,
  });

  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `Request failed (${res.status})`);
  }

  return toCamelCase(await res.json());
}

export async function recommend(input, signal) {
  return post('/recommend', input, signal);
}

export async function roulette(input, signal) {
  return post('/roulette', input, signal);
}

export async function vote(requestId, voteValue, sessionId, reason) {
  return post('/vote', { requestId, vote: voteValue, sessionId, reason: reason || null });
}

// --- Cast / Show Me ---

async function get(path) {
  const res = await fetch(`${BASE}${path}`);
  if (!res.ok) {
    const err = await res.json().catch(() => ({}));
    throw new Error(err.detail || `Request failed (${res.status})`);
  }
  return toCamelCase(await res.json());
}

export async function getCastStatus() {
  return get('/cast/status');
}

export async function scanCastDevices() {
  return get('/cast/devices');
}

export async function castToTV(recommendation, deviceName) {
  return post('/cast/show', { recommendation, deviceName: deviceName || null });
}
