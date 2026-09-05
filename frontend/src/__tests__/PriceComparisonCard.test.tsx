import { render, screen, fireEvent } from '@testing-library/react';
import { describe, it, expect, vi } from 'vitest';
import { PriceComparisonCard } from '../components/grocery/PriceComparisonCard';

const mockStore = {
  id: 'store_1',
  name: 'Demo QuickMart',
  store_type: 'Convenience Supermarket',
  city: 'Demo City',
  is_demo_store: true,
  created_at: '2026-08-04T00:00:00Z',
};

describe('PriceComparisonCard (INR & Safe Calculation)', () => {
  it('renders store name correctly', () => {
    render(
      <PriceComparisonCard store={mockStore} itemCost={95} deliveryFee={0} />
    );
    expect(screen.getByText('Demo QuickMart')).toBeInTheDocument();
  });

  it('displays INR formatted item cost', () => {
    render(
      <PriceComparisonCard store={mockStore} itemCost={95} deliveryFee={0} />
    );
    // When delivery fee is 0, both Items and Total display ₹95
    const elements = screen.getAllByText('₹95');
    expect(elements).toHaveLength(2);
    expect(elements[0]).toBeInTheDocument();
  });

  it('renders ₹0 instead of ₹NaN when itemCost is undefined or null', () => {
    render(
      <PriceComparisonCard store={mockStore} itemCost={undefined} deliveryFee={undefined} />
    );
    const zeroElements = screen.getAllByText('₹0');
    expect(zeroElements.length).toBeGreaterThan(0);
    expect(screen.queryByText(/NaN/)).not.toBeInTheDocument();
  });

  it('shows "Free" when delivery fee is zero', () => {
    render(
      <PriceComparisonCard store={mockStore} itemCost={95} deliveryFee={0} />
    );
    expect(screen.getByText('Free')).toBeInTheDocument();
  });

  it('shows INR delivery fee when non-zero', () => {
    render(
      <PriceComparisonCard store={mockStore} itemCost={95} deliveryFee={30} />
    );
    const deliveryElements = screen.getAllByText('₹30');
    expect(deliveryElements.length).toBeGreaterThanOrEqual(1);
    expect(deliveryElements[0]).toBeInTheDocument();
  });

  it('calculates and displays correct total when delivery fee is included', () => {
    render(
      <PriceComparisonCard store={mockStore} itemCost={95} deliveryFee={30} />
    );
    // Total = 95 + 30 = 125
    const totalElements = screen.getAllByText('₹125');
    expect(totalElements.length).toBeGreaterThanOrEqual(1);
    expect(totalElements[0]).toBeInTheDocument();
  });

  it('supports legacy totalCost prop safely', () => {
    render(
      <PriceComparisonCard store={mockStore} totalCost={115} deliveryFee={20} />
    );
    // itemCost = 115 - 20 = 95
    expect(screen.getAllByText('₹95')[0]).toBeInTheDocument();
    expect(screen.getAllByText('₹20')[0]).toBeInTheDocument();
    expect(screen.getAllByText('₹115')[0]).toBeInTheDocument();
  });

  it('shows Best Cart badge when isLowestPrice is true', () => {
    render(
      <PriceComparisonCard store={mockStore} itemCost={95} deliveryFee={0} isLowestPrice />
    );
    expect(screen.getByText('Best Cart')).toBeInTheDocument();
  });

  it('shows demo pricing disclaimer for demo stores', () => {
    render(
      <PriceComparisonCard store={mockStore} itemCost={95} deliveryFee={0} />
    );
    expect(screen.getByText(/Demonstration grocery pricing data \(INR\)/i)).toBeInTheDocument();
  });

  it('renders with selected styling when isSelected is true', () => {
    const { container } = render(
      <PriceComparisonCard store={mockStore} itemCost={95} deliveryFee={0} isSelected />
    );
    expect(container.firstChild).toHaveClass('border-emerald-500');
  });

  it('triggers onClick handler when clicked', () => {
    const onClickMock = vi.fn();
    render(
      <PriceComparisonCard store={mockStore} itemCost={95} deliveryFee={0} onClick={onClickMock} />
    );
    fireEvent.click(screen.getByText('Demo QuickMart'));
    expect(onClickMock).toHaveBeenCalledTimes(1);
  });
});
