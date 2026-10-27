import React, { useState } from 'react';
import { Search, Sparkles } from 'lucide-react';
import { Button } from './Button';

export interface SearchBarProps {
  initialValue?: string;
  onSearch?: (query: string) => void;
  placeholder?: string;
  large?: boolean;
}

export const SearchBar: React.FC<SearchBarProps> = ({
  onSearch,
  placeholder = "Search recipes by dish, ingredient or craving...",
  large = false,
  initialValue = "",
}) => {
  const [query, setQuery] = useState(initialValue);
  React.useEffect(() => { setQuery(initialValue); }, [initialValue]);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (onSearch) {
      onSearch(query);
    }
  };

  return (
    <form onSubmit={handleSubmit} className="w-full">
      <div className={`relative flex items-center bg-white rounded-2xl border border-orange-100 shadow-lg p-1.5 transition-all focus-within:ring-2 focus-within:ring-emerald-500 focus-within:border-emerald-500 ${large ? 'py-2 px-3' : 'py-1 px-2'}`}>
        <Search className={`text-orange-500 shrink-0 ml-3 ${large ? 'w-6 h-6' : 'w-5 h-5'}`} />
        <input
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder={placeholder}
          aria-label="Search recipes"
          className={`w-full bg-transparent text-gray-900 placeholder-gray-400 border-none outline-none focus:outline-none focus:ring-0 px-3 ${large ? 'text-base font-normal' : 'text-sm'}`}
        />
        <Button
          type="submit"
          variant="primary"
          size={large ? 'lg' : 'md'}
          icon={<Sparkles className="w-4 h-4" />}
          className="shrink-0 rounded-xl"
        >
          Find Recipe
        </Button>
      </div>
    </form>
  );
};
