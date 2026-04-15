function getStorage() {
  try {
    if (!globalThis.window?.localStorage) {
      return null;
    }

    return globalThis.window.localStorage;
  } catch {
    return null;
  }
}

export function readStoredConsentState(analyticsConfig) {
  const storage = getStorage();
  const decisionStorageKey = analyticsConfig?.consent?.decisionStorageKey;
  const updatedAtStorageKey = analyticsConfig?.consent?.updatedAtStorageKey;
  if (!storage || !decisionStorageKey || !updatedAtStorageKey) {
    return {
      decision: null,
      updatedAt: null,
    };
  }

  try {
    return {
      decision: normalizeDecision(storage.getItem(decisionStorageKey)),
      updatedAt: normalizeUpdatedAt(storage.getItem(updatedAtStorageKey)),
    };
  } catch {
    return {
      decision: null,
      updatedAt: null,
    };
  }
}

export function writeStoredConsentDecision(analyticsConfig, decision, updatedAt = new Date().toISOString()) {
  const storage = getStorage();
  const decisionStorageKey = analyticsConfig?.consent?.decisionStorageKey;
  const updatedAtStorageKey = analyticsConfig?.consent?.updatedAtStorageKey;
  const normalizedDecision = normalizeDecision(decision);
  const normalizedUpdatedAt = normalizeUpdatedAt(updatedAt) || new Date().toISOString();
  if (!storage || !decisionStorageKey || !updatedAtStorageKey || !normalizedDecision) {
    return {
      decision: null,
      updatedAt: null,
    };
  }

  try {
    storage.setItem(decisionStorageKey, normalizedDecision);
    storage.setItem(updatedAtStorageKey, normalizedUpdatedAt);
  } catch {
    return {
      decision: null,
      updatedAt: null,
    };
  }

  return {
    decision: normalizedDecision,
    updatedAt: normalizedUpdatedAt,
  };
}

function normalizeDecision(value) {
  if (value === "accepted" || value === "declined") {
    return value;
  }

  return null;
}

function normalizeUpdatedAt(value) {
  return typeof value === "string" && value.trim().length > 0 ? value.trim() : null;
}
