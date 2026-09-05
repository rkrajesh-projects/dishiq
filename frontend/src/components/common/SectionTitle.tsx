import React from 'react';

export interface SectionTitleProps {
  title: string;
  subtitle?: string;
  action?: React.ReactNode;
}

export const SectionTitle: React.FC<SectionTitleProps> = ({ title, subtitle, action }) => {
  return (
    <div className="flex flex-col sm:flex-row sm:items-end justify-between mb-6 gap-2">
      <div>
        <h2 className="text-xl sm:text-2xl font-bold text-gray-900 tracking-tight">{title}</h2>
        {subtitle && <p className="text-sm text-gray-600 mt-1">{subtitle}</p>}
      </div>
      {action && <div>{action}</div>}
    </div>
  );
};
