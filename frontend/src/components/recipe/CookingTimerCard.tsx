import React, { useState, useEffect } from 'react';
import { Timer, Play, Pause, RotateCcw, Plus, Trash2, X, Bell, BellOff } from 'lucide-react';
import { Button } from '../common/Button';
import { useCookingTimer, CookingTimer } from '../../hooks/useCookingTimer';

export interface CookingTimerCardProps {
  /** The parsed step instructions duration in seconds. 0 if none found. */
  stepDuration: number;
  /** Label describing the active step */
  stepLabel: string;
  /** Callback fired exactly once when the timer reaches 0 */
  onTimerComplete?: () => void;
  /** Access to the parent page warning handlers if needed */
  onTimerRunningChange?: (running: boolean) => void;
}

export function formatTime(seconds: number): string {
  if (seconds < 0) return '00:00';
  const hrs = Math.floor(seconds / 3600);
  const mins = Math.floor((seconds % 3600) / 60);
  const secs = seconds % 60;

  const pad = (num: number) => String(num).padStart(2, '0');

  if (hrs > 0) {
    return `${pad(hrs)}:${pad(mins)}:${pad(secs)}`;
  }
  return `${pad(mins)}:${pad(secs)}`;
}

export function getAccessibleTimeText(seconds: number, status?: string): string {
  if (status === 'completed') return 'Timer complete';
  const hrs = Math.floor(seconds / 3600);
  const mins = Math.floor((seconds % 3600) / 60);
  const secs = seconds % 60;

  let text = '';
  if (hrs > 0) text += `${hrs} hour${hrs > 1 ? 's' : ''} `;
  if (mins > 0) text += `${mins} minute${mins > 1 ? 's' : ''} `;
  if (secs > 0 || text === '') text += `${secs} second${secs > 1 ? 's' : ''}`;

  if (status) {
    return `Timer ${status} - ${text.trim()} remaining`;
  }
  return text.trim();
}

export const CookingTimerCard: React.FC<CookingTimerCardProps> = ({
  stepDuration,
  stepLabel,
  onTimerComplete,
  onTimerRunningChange,
}) => {
  const timer = useCookingTimer(stepDuration, onTimerComplete);

  // Manual timer inputs
  const [showManualForm, setShowManualForm] = useState(false);
  const [minsInput, setMinsInput] = useState('05');
  const [secsInput, setSecsInput] = useState('00');
  const [validationError, setValidationError] = useState<string | null>(null);
  const [announcement, setAnnouncement] = useState('');

  // Let parent page know when timer changes run status (for warning validation checks)
  const isRunning = timer.status === 'running';
  useEffect(() => {
    if (onTimerRunningChange) {
      onTimerRunningChange(isRunning);
    }
  }, [isRunning, onTimerRunningChange]);

  // Determine if timer is configured (either from step instructions or manual addition)
  const isTimerConfigured = timer.durationSeconds > 0;

  // Announce major timer state changes (Phase 9.9)
  useEffect(() => {
    if (!isTimerConfigured) return;
    if (timer.status === 'running') {
      setAnnouncement(`Timer started for ${getAccessibleTimeText(timer.durationSeconds)}`);
    } else if (timer.status === 'paused') {
      setAnnouncement(`Timer paused at ${getAccessibleTimeText(timer.remainingSeconds)}`);
    } else if (timer.status === 'completed') {
      setAnnouncement('Timer complete!');
    } else if (timer.status === 'idle') {
      setAnnouncement('Timer reset.');
    }
  }, [timer.status, isTimerConfigured]);

  const handleStartManual = (e: React.FormEvent) => {
    e.preventDefault();
    const minutes = parseInt(minsInput, 10);
    const seconds = parseInt(secsInput, 10);

    if (isNaN(minutes) || minutes < 0) {
      setValidationError('Minutes must be a positive integer.');
      return;
    }
    if (isNaN(seconds) || seconds < 0 || seconds > 59) {
      setValidationError('Seconds must be between 0 and 59.');
      return;
    }

    const totalSecs = minutes * 60 + seconds;
    if (totalSecs <= 0) {
      setValidationError('Duration must be greater than 00:00.');
      return;
    }

    setValidationError(null);
    setShowManualForm(false);
    timer.setDuration(totalSecs);
    timer.start(totalSecs);
  };

  const handleRemoveTimer = () => {
    timer.setDuration(0);
    timer.reset();
    setShowManualForm(false);
  };

  return (
    <div
      className="bg-white rounded-2xl border border-gray-100 p-5 shadow-sm space-y-4"
      aria-label="Cooking step timer"
    >
      {/* Off-screen screen reader announcements (Phase 9.9) */}
      <div className="sr-only" aria-live="polite" role="status">
        {announcement}
      </div>

      <div className="flex items-center justify-between border-b border-gray-50 pb-3">
        <h3 className="text-sm font-bold text-gray-900 flex items-center gap-2">
          <Timer className="w-4 h-4 text-emerald-600 animate-pulse" />
          <span>Cooking Timer</span>
        </h3>
        {isTimerConfigured && timer.status === 'idle' && (
          <button
            onClick={handleRemoveTimer}
            className="text-gray-400 hover:text-red-600 transition-colors"
            title="Remove Timer"
            aria-label="Remove timer"
          >
            <Trash2 className="w-4 h-4" />
          </button>
        )}
      </div>

      {/* No timer configured state */}
      {!isTimerConfigured && !showManualForm && (
        <div className="text-center py-4 space-y-3">
          <p className="text-xs text-gray-500">No timer set for this step.</p>
          <Button
            variant="outline"
            size="sm"
            icon={<Plus className="w-3.5 h-3.5" />}
            onClick={() => {
              setValidationError(null);
              setShowManualForm(true);
            }}
          >
            Add Timer
          </Button>
        </div>
      )}

      {/* Manual Setup form */}
      {showManualForm && (
        <form onSubmit={handleStartManual} className="space-y-3 pt-2">
          <div className="flex items-center justify-center gap-3">
            <div className="flex flex-col items-center">
              <label htmlFor="manual-timer-mins" className="text-[10px] text-gray-400 uppercase font-bold mb-1">
                Mins
              </label>
              <input
                id="manual-timer-mins"
                type="number"
                min="0"
                value={minsInput}
                onChange={(e) => setMinsInput(e.target.value)}
                className="w-16 p-2 text-center text-sm border border-gray-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-emerald-500 font-mono"
              />
            </div>
            <span className="text-xl font-bold text-gray-400 mt-4">:</span>
            <div className="flex flex-col items-center">
              <label htmlFor="manual-timer-secs" className="text-[10px] text-gray-400 uppercase font-bold mb-1">
                Secs
              </label>
              <input
                id="manual-timer-secs"
                type="number"
                min="0"
                max="59"
                value={secsInput}
                onChange={(e) => setSecsInput(e.target.value)}
                className="w-16 p-2 text-center text-sm border border-gray-200 rounded-xl focus:outline-none focus:ring-2 focus:ring-emerald-500 font-mono"
              />
            </div>
          </div>

          {validationError && (
            <p className="text-[10px] text-red-600 text-center font-semibold" role="alert">
              {validationError}
            </p>
          )}

          <div className="flex items-center gap-2 pt-2">
            <Button
              variant="secondary"
              size="sm"
              className="flex-1"
              type="button"
              onClick={() => setShowManualForm(false)}
            >
              Cancel
            </Button>
            <Button variant="primary" size="sm" className="flex-1" type="submit">
              Start Timer
            </Button>
          </div>
        </form>
      )}

      {/* Main Timer Display */}
      {isTimerConfigured && (
        <div className="text-center py-2 space-y-4">
          <div>
            <p className="text-[10px] text-gray-400 font-bold uppercase tracking-wider mb-1">
              {stepLabel || 'Active Step'}
            </p>
            <div
              className={`text-4xl font-extrabold font-mono transition-colors duration-200 ${
                timer.status === 'completed'
                  ? 'text-red-600 animate-bounce'
                  : timer.status === 'paused'
                  ? 'text-gray-400'
                  : timer.status === 'cancelled'
                  ? 'text-gray-300'
                  : 'text-gray-900'
              }`}
              aria-live="off"
            >
              {formatTime(timer.remainingSeconds)}
            </div>
            {timer.status === 'completed' && (
              <span className="text-xs text-red-600 font-extrabold mt-1 block" role="alert">
                ✓ Timer Complete
              </span>
            )}
            {timer.status === 'cancelled' && (
              <span className="text-xs text-gray-500 font-semibold mt-1 block">
                Timer Cancelled
              </span>
            )}
          </div>

          {/* Desktop Alert Permission Prompt */}
          {timer.notificationPermission === 'default' && (
            <div className="flex justify-center pt-1">
              <button
                type="button"
                onClick={timer.requestNotificationPermission}
                className="text-[11px] text-emerald-800 hover:text-emerald-900 bg-emerald-50 hover:bg-emerald-100 border border-emerald-200/60 px-3 py-1 rounded-full flex items-center gap-1.5 transition-colors"
                title="Enable sound and browser notifications when timers complete"
              >
                <Bell className="w-3 h-3 text-emerald-600" />
                <span>Enable Alerts</span>
              </button>
            </div>
          )}

          {/* Controls based on status state machine */}
          <div className="flex items-center justify-center gap-3 pt-2">
            {timer.status === 'idle' && (
              <Button
                variant="primary"
                size="sm"
                icon={<Play className="w-3.5 h-3.5 fill-current" />}
                onClick={() => timer.start()}
              >
                Start
              </Button>
            )}

            {timer.status === 'running' && (
              <>
                <Button
                  variant="secondary"
                  size="sm"
                  icon={<Pause className="w-3.5 h-3.5 fill-current" />}
                  onClick={() => timer.pause()}
                >
                  Pause
                </Button>
                <Button
                  variant="outline"
                  size="sm"
                  icon={<RotateCcw className="w-3.5 h-3.5" />}
                  onClick={() => timer.reset()}
                >
                  Reset
                </Button>
                <Button
                  variant="outline"
                  size="sm"
                  icon={<X className="w-3.5 h-3.5 text-red-500" />}
                  onClick={() => timer.cancel()}
                  title="Cancel timer"
                >
                  Cancel
                </Button>
              </>
            )}

            {timer.status === 'paused' && (
              <>
                <Button
                  variant="primary"
                  size="sm"
                  icon={<Play className="w-3.5 h-3.5 fill-current" />}
                  onClick={() => timer.resume()}
                >
                  Resume
                </Button>
                <Button
                  variant="outline"
                  size="sm"
                  icon={<RotateCcw className="w-3.5 h-3.5" />}
                  onClick={() => timer.reset()}
                >
                  Reset
                </Button>
                <Button
                  variant="outline"
                  size="sm"
                  icon={<X className="w-3.5 h-3.5 text-red-500" />}
                  onClick={() => timer.cancel()}
                  title="Cancel timer"
                >
                  Cancel
                </Button>
              </>
            )}

            {timer.status === 'completed' && (
              <>
                <Button
                  variant="primary"
                  size="sm"
                  icon={<Play className="w-3.5 h-3.5 fill-current" />}
                  onClick={() => timer.start(timer.durationSeconds)}
                >
                  Start Again
                </Button>
                <Button
                  variant="secondary"
                  size="sm"
                  icon={<X className="w-3.5 h-3.5" />}
                  onClick={() => timer.reset()}
                  title="Dismiss alert"
                >
                  Dismiss
                </Button>
              </>
            )}

            {timer.status === 'cancelled' && (
              <>
                <Button
                  variant="primary"
                  size="sm"
                  icon={<Play className="w-3.5 h-3.5 fill-current" />}
                  onClick={() => timer.start(timer.durationSeconds)}
                >
                  Restart
                </Button>
                <Button
                  variant="outline"
                  size="sm"
                  icon={<RotateCcw className="w-3.5 h-3.5" />}
                  onClick={() => timer.reset()}
                >
                  Reset
                </Button>
              </>
            )}
          </div>
        </div>
      )}
    </div>
  );
};
