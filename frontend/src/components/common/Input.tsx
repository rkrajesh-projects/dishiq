import React from 'react';
import { clsx } from 'clsx';

export interface InputProps extends React.InputHTMLAttributes<HTMLInputElement> {
  label?: string;
  error?: string;
  icon?: React.ReactNode;
}

export const Input: React.FC<InputProps> = ({
  label,
  error,
  icon,
  className,
  id,
  ...props
}) => {
  const inputId = id || (label ? label.toLowerCase().replace(/\s+/g, '-') : undefined);

  return (
    <div className="w-full flex flex-col gap-1.5">
      {label && (
        <label htmlFor={inputId} className="text-xs font-semibold uppercase tracking-wider text-gray-700">
          {label}
        </label>
      )}
      <div className="relative flex items-center">
        {icon && (
          <span className="absolute left-3.5 text-gray-400 pointer-events-none">
            {icon}
          </span>
        )}
        <input
          id={inputId}
          className={clsx(
            'w-full bg-white text-gray-900 placeholder-gray-400 border rounded-xl px-4 py-2.5 text-sm transition-all focus:outline-none focus:ring-2 focus:ring-emerald-500 focus:border-emerald-500 shadow-sm',
            icon ? 'pl-10' : 'pl-4',
            error ? 'border-red-500 ring-1 ring-red-500' : 'border-gray-200 hover:border-gray-300',
            className
          )}
          {...props}
        />
      </div>
      {error && <span className="text-xs text-red-600 font-medium">{error}</span>}
    </div>
  );
};
