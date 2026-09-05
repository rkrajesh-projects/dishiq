import { useState, useEffect, useRef } from 'react';

export type TimerStatus = 'idle' | 'running' | 'paused' | 'completed';

export interface CookingTimer {
  status: TimerStatus;
  remainingSeconds: number;
  durationSeconds: number;
  start: (seconds?: number) => void;
  pause: () => void;
  resume: () => void;
  reset: () => void;
  setDuration: (seconds: number) => void;
}

/**
 * Custom React Hook managing a precise, drift-free cooking step timer.
 * Calculates remaining duration from timestamps to support background tab throttling.
 */
export function useCookingTimer(initialDuration = 0, onComplete?: () => void): CookingTimer {
  const [durationSeconds, setDurationSeconds] = useState(initialDuration);
  const [remainingSeconds, setRemainingSeconds] = useState(initialDuration);
  const [status, setStatus] = useState<TimerStatus>('idle');

  // Keep references of status, duration, and time boundaries to handle event loops cleanly
  const stateRef = useRef({
    status: 'idle' as TimerStatus,
    durationSeconds: initialDuration,
    remainingSeconds: initialDuration,
    endTime: null as number | null,
    pausedTimeRemaining: null as number | null,
  });

  const onCompleteRef = useRef(onComplete);
  useEffect(() => {
    onCompleteRef.current = onComplete;
  }, [onComplete]);

  const syncState = (updates: Partial<typeof stateRef.current>) => {
    stateRef.current = { ...stateRef.current, ...updates };
    if (updates.status !== undefined) setStatus(updates.status);
    if (updates.durationSeconds !== undefined) setDurationSeconds(updates.durationSeconds);
    if (updates.remainingSeconds !== undefined) setRemainingSeconds(updates.remainingSeconds);
  };

  // Re-initialize state if base instruction duration changes
  useEffect(() => {
    syncState({
      durationSeconds: initialDuration,
      remainingSeconds: initialDuration,
      status: 'idle',
      endTime: null,
      pausedTimeRemaining: null,
    });
  }, [initialDuration]);

  // Timer countdown hook utilizing absolute System time diffs
  useEffect(() => {
    if (status !== 'running') return;

    const intervalId = setInterval(() => {
      const { endTime } = stateRef.current;
      if (!endTime) return;

      const now = Date.now();
      const diff = Math.max(0, Math.ceil((endTime - now) / 1000));

      syncState({ remainingSeconds: diff });

      if (diff === 0) {
        syncState({ status: 'completed', endTime: null, pausedTimeRemaining: null });
        clearInterval(intervalId);
        if (onCompleteRef.current) {
          onCompleteRef.current();
        }
      }
    }, 200);

    return () => clearInterval(intervalId);
  }, [status]);

  const start = (seconds?: number) => {
    const targetSeconds = seconds !== undefined ? seconds : stateRef.current.durationSeconds;
    if (targetSeconds <= 0) return;

    const now = Date.now();
    syncState({
      status: 'running',
      durationSeconds: targetSeconds,
      remainingSeconds: targetSeconds,
      endTime: now + targetSeconds * 1000,
      pausedTimeRemaining: null,
    });
  };

  const pause = () => {
    if (stateRef.current.status !== 'running') return;

    const now = Date.now();
    const { endTime } = stateRef.current;
    if (!endTime) return;

    const remaining = Math.max(0, (endTime - now) / 1000);
    syncState({
      status: 'paused',
      pausedTimeRemaining: remaining,
      endTime: null,
    });
  };

  const resume = () => {
    if (stateRef.current.status !== 'paused') return;
    const { pausedTimeRemaining } = stateRef.current;
    if (pausedTimeRemaining === null || pausedTimeRemaining <= 0) return;

    const now = Date.now();
    syncState({
      status: 'running',
      endTime: now + pausedTimeRemaining * 1000,
      pausedTimeRemaining: null,
    });
  };

  const reset = () => {
    syncState({
      status: 'idle',
      remainingSeconds: stateRef.current.durationSeconds,
      endTime: null,
      pausedTimeRemaining: null,
    });
  };

  const setDuration = (seconds: number) => {
    if (seconds < 0) return;
    syncState({
      durationSeconds: seconds,
      remainingSeconds: seconds,
      status: 'idle',
      endTime: null,
      pausedTimeRemaining: null,
    });
  };

  return {
    status,
    remainingSeconds,
    durationSeconds,
    start,
    pause,
    resume,
    reset,
    setDuration,
  };
}
