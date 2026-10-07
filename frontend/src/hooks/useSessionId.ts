import { useState, useEffect } from 'react';

const SESSION_KEY = 'sqlens_session_id';

export function useSessionId(): string {
  const [sessionId, setSessionId] = useState<string>(() => {
    const existing = localStorage.getItem(SESSION_KEY);
    if (existing) return existing;
    const newId = 'session_' + Math.random().toString(36).substring(2, 11) + '_' + Date.now();
    localStorage.setItem(SESSION_KEY, newId);
    return newId;
  });

  useEffect(() => {
    if (!localStorage.getItem(SESSION_KEY)) {
      localStorage.setItem(SESSION_KEY, sessionId);
    }
  }, [sessionId]);

  return sessionId;
}
