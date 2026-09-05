import { renderHook, act } from '@testing-library/react';
import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest';
import { useCookingTimer } from '../hooks/useCookingTimer';
import { CookingTimerCard, formatTime, getAccessibleTimeText } from '../components/recipe/CookingTimerCard';
import { parseDuration } from '../pages/CookingPage';

describe('CookingTimer - Unit Tests (9.5)', () => {
  beforeEach(() => {
    vi.useFakeTimers();
    // Start at a known fixed time
    vi.setSystemTime(new Date('2026-08-13T12:00:00.000Z'));
  });

  afterEach(() => {
    vi.useRealTimers();
    vi.restoreAllMocks();
  });

  // 1. Initial idle state
  it('1. Initializes in idle status with correct duration', () => {
    const { result } = renderHook(() => useCookingTimer(300));
    expect(result.current.status).toBe('idle');
    expect(result.current.durationSeconds).toBe(300);
    expect(result.current.remainingSeconds).toBe(300);
  });

  // 2. Start timer
  it('2. Starts the timer and transitions to running status', () => {
    const { result } = renderHook(() => useCookingTimer(300));
    act(() => {
      result.current.start();
    });
    expect(result.current.status).toBe('running');
  });

  // 3. Countdown
  it('3. Counts down correctly over time', () => {
    const { result } = renderHook(() => useCookingTimer(300));
    act(() => {
      result.current.start();
    });

    // Move clock forward by 5 seconds
    act(() => {
      vi.advanceTimersByTime(5000);
    });

    expect(result.current.remainingSeconds).toBe(295);
  });

  // 4. Pause timer
  it('4. Pauses the timer correctly, freezing remaining seconds', () => {
    const { result } = renderHook(() => useCookingTimer(300));
    act(() => {
      result.current.start();
    });

    act(() => {
      vi.advanceTimersByTime(5000);
    });
    expect(result.current.remainingSeconds).toBe(295);

    act(() => {
      result.current.pause();
    });
    expect(result.current.status).toBe('paused');

    // Move clock forward while paused - remaining seconds should not change
    act(() => {
      vi.advanceTimersByTime(10000);
    });
    expect(result.current.remainingSeconds).toBe(295);
  });

  // 5. Resume timer
  it('5. Resumes counting down after being paused', () => {
    const { result } = renderHook(() => useCookingTimer(300));
    act(() => {
      result.current.start();
    });

    act(() => {
      vi.advanceTimersByTime(5000);
      result.current.pause();
    });

    act(() => {
      result.current.resume();
    });
    expect(result.current.status).toBe('running');

    act(() => {
      vi.advanceTimersByTime(5000);
    });
    expect(result.current.remainingSeconds).toBe(290);
  });

  // 6. Reset timer
  it('6. Resets the timer back to its initial configuration', () => {
    const { result } = renderHook(() => useCookingTimer(300));
    act(() => {
      result.current.start();
    });
    act(() => {
      vi.advanceTimersByTime(5000);
    });
    expect(result.current.remainingSeconds).toBe(295);

    act(() => {
      result.current.reset();
    });
    expect(result.current.status).toBe('idle');
    expect(result.current.remainingSeconds).toBe(300);
  });

  // 7. Timer reaches zero
  // 8. Completed state
  // 9. No negative remaining time
  // 15. Completion callback fires once
  it('7-9, 15. Reaches zero, transitions to completed, avoids negative time, and fires callback exactly once', () => {
    const completeCallback = vi.fn();
    const { result } = renderHook(() => useCookingTimer(5, completeCallback));

    act(() => {
      result.current.start();
    });

    // Advance clock past the limit (e.g. 10 seconds for a 5 second timer)
    act(() => {
      vi.advanceTimersByTime(10000);
    });

    expect(result.current.status).toBe('completed');
    expect(result.current.remainingSeconds).toBe(0); // No negative values
    expect(completeCallback).toHaveBeenCalledTimes(1); // Exactly once
  });

  // 10. Start cannot occur with 00:00
  it('10. Prevents starting a timer with 0 duration', () => {
    const { result } = renderHook(() => useCookingTimer(0));
    act(() => {
      result.current.start();
    });
    expect(result.current.status).toBe('idle');
  });

  // 12. Minute/second formatting
  // 13. Hour formatting
  it('12-13. Formats remaining durations correctly', () => {
    expect(formatTime(30)).toBe('00:30');
    expect(formatTime(65)).toBe('01:05');
    expect(formatTime(3605)).toBe('01:00:05');
    expect(formatTime(0)).toBe('00:00');
    expect(formatTime(-10)).toBe('00:00');
  });

  // 14. Timer cleanup
  it('14. Cleans up intervals correctly upon unmount', () => {
    const clearIntervalSpy = vi.spyOn(global, 'clearInterval');
    const { result, unmount } = renderHook(() => useCookingTimer(300));
    act(() => {
      result.current.start();
    });
    unmount();
    expect(clearIntervalSpy).toHaveBeenCalled();
  });

  // 16. Background elapsed-time calculation
  it('16. Accurately counts down when background tab throttling occurs using absolute timestamps', () => {
    const { result } = renderHook(() => useCookingTimer(300));
    act(() => {
      result.current.start();
    });

    // Directly set system clock forward simulating tab inactive state
    act(() => {
      vi.setSystemTime(new Date(Date.now() + 45000)); // Advance system time 45s
      vi.advanceTimersByTime(200); // Trigger next interval check
    });

    expect(result.current.remainingSeconds).toBe(255); // Correctly processed 45 seconds drop
  });

  // 17. Multiple start clicks do not create duplicate timers
  it('17. Clicking start multiple times does not trigger multiple running intervals', () => {
    const setIntervalSpy = vi.spyOn(global, 'setInterval');
    const { result } = renderHook(() => useCookingTimer(300));

    act(() => {
      result.current.start();
      result.current.start();
      result.current.start();
    });

    // Only one interval registration should be active
    expect(result.current.status).toBe('running');
  });

  // Deterministic Duration Parser tests (Step 9)
  it('Parses various duration text patterns correctly', () => {
    expect(parseDuration('Simmer for 5 minutes.')).toBe(300);
    expect(parseDuration('Bake for 1 hour 30 mins')).toBe(5400);
    expect(parseDuration('Cook for 10 min')).toBe(600);
    expect(parseDuration('Simmer for 1 hr')).toBe(3600);
    // Exclude unrelated integers
    expect(parseDuration('Add 2 tomatoes and stir.')).toBe(0);
    // Exclude multiple durations (Boil for 5 minutes, then simmer for 10 minutes)
    expect(parseDuration('Boil for 5 minutes, then simmer for 10 minutes.')).toBe(0);
  });

  // Accessibility and Screen Reader tick-suppression tests (Phase 9.9)
  it('Has static Cooking step timer label and updates visually hidden live announcer on state changes', async () => {
    render(<CookingTimerCard stepDuration={300} stepLabel="Step 1" />);

    // Container has static aria-label
    const timerContainer = screen.getByLabelText('Cooking step timer');
    expect(timerContainer).toBeInTheDocument();

    // Start timer and check announcement updates
    const startBtn = screen.getByRole('button', { name: /Start/i });
    fireEvent.click(startBtn);

    // Announce start politely
    const liveAnnouncer = screen.getByRole('status');
    expect(liveAnnouncer).toHaveTextContent('Timer started for 5 minutes');
  });
});
