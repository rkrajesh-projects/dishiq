import React from 'react';
import { Utensils, Heart } from 'lucide-react';

export const Footer: React.FC = () => {
  return (
    <footer className="bg-white border-t border-orange-100/60 mt-16 py-8">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 flex flex-col md:flex-row items-center justify-between gap-4">
        <div className="flex items-center gap-2">
          <div className="p-1.5 bg-emerald-600 text-white rounded-lg">
            <Utensils className="w-4 h-4" />
          </div>
          <span className="font-bold text-sm text-gray-900">
            Dish<span className="text-emerald-600">IQ</span>
          </span>
          <span className="text-xs text-gray-500">— Intelligent Meal Planning & Kitchen Memory</span>
        </div>

        <p className="text-xs text-gray-500 flex items-center gap-1">
          Built with <Heart className="w-3.5 h-3.5 text-orange-500 fill-orange-500" /> for smart home cooking.
        </p>

        <p className="text-xs text-gray-400">
          Demo Mode • Prices represent demonstration retail datasets.
        </p>
      </div>
    </footer>
  );
};
