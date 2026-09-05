import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import { SearchBar } from '../components/common/SearchBar';

describe('SearchBar Component', () => {
  it('renders search input and button', () => {
    render(<SearchBar placeholder="Test search..." />);
    const input = screen.getByPlaceholderText('Test search...');
    expect(input).toBeInTheDocument();
    expect(screen.getByRole('button', { name: /Find Recipe/i })).toBeInTheDocument();
  });

  it('triggers onSearch callback when form is submitted', () => {
    const handleSearch = vi.fn();
    render(<SearchBar onSearch={handleSearch} />);
    const input = screen.getByRole('textbox', { name: /Search recipes/i });

    fireEvent.change(input, { target: { value: 'Paneer' } });
    const button = screen.getByRole('button', { name: /Find Recipe/i });
    fireEvent.click(button);

    expect(handleSearch).toHaveBeenCalledWith('Paneer');
  });
});
