import React from 'react';
import { Loader2 } from 'lucide-react';

export interface LoadingStateProps {
  message?: string;
}

export const LoadingState: React.FC<LoadingStateProps> = ({
  message = "Loading kitchen data...",
}) => {
  return (
    <div className="flex flex-col items-center justify-center p-12 text-center my-8">
      <div className="p-4 bg-emerald-50 text-emerald-600 rounded-full mb-4 animate-spin">
        <Loader2 className="w-8 h-8" />
      </div>
      <p className="text-sm font-medium text-gray-600 animate-pulse">{message}</p>
    </div>
  );
};
