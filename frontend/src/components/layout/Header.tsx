import React from 'react';
import { NavLink } from 'react-router-dom';
import { Utensils, Search, ShoppingBag, ChefHat, Package, User, Wifi, WifiOff } from 'lucide-react';
import { useBackendStatus } from '../../hooks/useBackendStatus';

export const Header: React.FC = () => {
  const { isConnected, isPending } = useBackendStatus();

  const navItems = [
    { label: 'Home', path: '/', icon: Utensils },
    { label: 'Recipes', path: '/recipes', icon: Search },
    { label: 'Grocery', path: '/grocery', icon: ShoppingBag },
    { label: 'Cooking', path: '/cooking', icon: ChefHat },
    { label: 'Pantry', path: '/pantry', icon: Package },
    { label: 'Profile', path: '/profile', icon: User },
  ];

  return (
    <header className="bg-white/80 backdrop-blur-md border-b border-orange-100/60 sticky top-0 z-40">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="flex items-center justify-between h-16">
          
          {/* Logo & Brand Name */}
          <NavLink to="/" className="flex items-center gap-2.5 group">
            <div className="p-2 bg-emerald-600 text-white rounded-xl shadow-md shadow-emerald-600/20 group-hover:scale-105 transition-transform">
              <Utensils className="w-5 h-5" />
            </div>
            <div className="flex flex-col">
              <span className="font-bold text-lg text-gray-900 tracking-tight leading-none">
                Dish<span className="text-emerald-600">IQ</span>
              </span>
              <span className="text-[10px] font-medium text-orange-600 tracking-wider uppercase">
                AI Kitchen Assistant
              </span>
            </div>
          </NavLink>

          {/* Navigation Links */}
          <nav className="hidden md:flex items-center gap-1">
            {navItems.map((item) => {
              const Icon = item.icon;
              return (
                <NavLink
                  key={item.path}
                  to={item.path}
                  className={({ isActive }) =>
                    `flex items-center gap-1.5 px-3 py-2 rounded-xl text-xs font-semibold transition-all ${
                      isActive
                        ? 'bg-emerald-50 text-emerald-700 shadow-sm'
                        : 'text-gray-600 hover:text-gray-900 hover:bg-gray-50'
                    }`
                  }
                >
                  <Icon className="w-4 h-4" />
                  <span>{item.label}</span>
                </NavLink>
              );
            })}
          </nav>

          {/* Backend Connection Status Badge */}
          <div className="flex items-center gap-3">
            <div
              data-testid="backend-status"
              className={`inline-flex items-center gap-1.5 px-3 py-1 rounded-full text-xs font-semibold border transition-all ${
                isPending
                  ? 'bg-gray-50 text-gray-500 border-gray-200'
                  : isConnected
                  ? 'bg-emerald-50 text-emerald-700 border-emerald-200 shadow-sm'
                  : 'bg-amber-50 text-amber-700 border-amber-200'
              }`}
            >
              {isPending ? (
                <>
                  <span className="w-2 h-2 rounded-full bg-gray-400 animate-ping" />
                  <span>Checking status...</span>
                </>
              ) : isConnected ? (
                <>
                  <Wifi className="w-3.5 h-3.5 text-emerald-600" />
                  <span>Backend Connected</span>
                </>
              ) : (
                <>
                  <WifiOff className="w-3.5 h-3.5 text-amber-600" />
                  <span>Backend Offline</span>
                </>
              )}
            </div>
          </div>

        </div>
      </div>

      {/* Mobile Nav Bar */}
      <div className="md:hidden border-t border-gray-100 bg-white px-2 py-1.5 flex items-center justify-around">
        {navItems.map((item) => {
          const Icon = item.icon;
          return (
            <NavLink
              key={item.path}
              to={item.path}
              className={({ isActive }) =>
                `flex flex-col items-center gap-0.5 px-2 py-1 rounded-lg text-[10px] font-medium ${
                  isActive ? 'text-emerald-600 font-bold' : 'text-gray-500'
                }`
              }
            >
              <Icon className="w-4 h-4" />
              <span>{item.label}</span>
            </NavLink>
          );
        })}
      </div>
    </header>
  );
};
