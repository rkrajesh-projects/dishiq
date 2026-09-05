import { describe, it, expect } from 'vitest';
import { matchStepIngredients } from '../utils/stepIngredientMatcher';

const mockIngredients = [
  { id: '1', ingredient: { canonical_name: 'onion' } },
  { id: '2', ingredient: { canonical_name: 'tomato' } },
  { id: '3', ingredient: { canonical_name: 'oil' } },
  { id: '4', ingredient: { canonical_name: 'salt' } },
  { id: '5', ingredient: { canonical_name: 'olive oil' } },
  { id: '6', ingredient: { canonical_name: '5' } }, // Numeric name guard test
];

describe('stepIngredientMatcher - Unit Tests (9.6)', () => {
  // 1. Exact match
  it('1. Handles exact ingredient matches correctly', () => {
    const result = matchStepIngredients('onion', mockIngredients);
    expect(result).toHaveLength(1);
    expect(result[0].ingredient.canonical_name).toBe('onion');
  });

  // 2. Case-insensitive match
  it('2. Handles case-insensitive matches', () => {
    const result = matchStepIngredients('ONION', mockIngredients);
    expect(result).toHaveLength(1);
    expect(result[0].ingredient.canonical_name).toBe('onion');
  });

  // 3. Singular/plural match
  it('3. Handles singular and plural inflections', () => {
    const result = matchStepIngredients('sauté onions', mockIngredients);
    expect(result).toHaveLength(1);
    expect(result[0].ingredient.canonical_name).toBe('onion');
  });

  // 4. Multiple ingredients
  it('4. Matches multiple ingredients present in the same instruction', () => {
    const result = matchStepIngredients('Add onions, tomatoes, and salt.', mockIngredients);
    expect(result).toHaveLength(3);
    const names = result.map(ri => ri.ingredient.canonical_name);
    expect(names).toContain('onion');
    expect(names).toContain('tomato');
    expect(names).toContain('salt');
  });

  // 5. No match
  it('5. Returns an empty array when no matches are found', () => {
    const result = matchStepIngredients('Simmer for 10 minutes.', mockIngredients);
    expect(result).toHaveLength(0);
  });

  // 6. Numbers ignored
  it('6. Does not match numeric ingredient names with quantities', () => {
    const result = matchStepIngredients('Add 2 tomatoes.', mockIngredients);
    expect(result).toHaveLength(1);
    expect(result[0].ingredient.canonical_name).toBe('tomato');
    // '5' is also in mockIngredients, make sure "2" does not match anything
    const matchedNames = result.map(ri => ri.ingredient.canonical_name);
    expect(matchedNames).not.toContain('5');
  });

  // 7. Cooking durations ignored
  it('7. Excludes numeric ingredient names matching time values', () => {
    const result = matchStepIngredients('Boil for 5 minutes.', mockIngredients);
    const matchedNames = result.map(ri => ri.ingredient.canonical_name);
    expect(matchedNames).not.toContain('5');
  });

  // 8. Substring false-positive prevention
  it('8. Avoids partial string substring matches', () => {
    const result = matchStepIngredients('Heat boiling water.', mockIngredients);
    const matchedNames = result.map(ri => ri.ingredient.canonical_name);
    // "oil" must not match "boiling"
    expect(matchedNames).not.toContain('oil');
  });

  // 9. Compound ingredients
  it('9. Matches multi-word compound ingredients', () => {
    const result = matchStepIngredients('Pour some olive oil in the pan.', mockIngredients);
    const matchedNames = result.map(ri => ri.ingredient.canonical_name);
    expect(matchedNames).toContain('olive oil');
  });

  // 10. Duplicate prevention
  it('10. Prevents duplicate ingredient listings in output', () => {
    const result = matchStepIngredients('Chop onions and chop more onions.', mockIngredients);
    expect(result).toHaveLength(1);
  });

  // 11. Synonym matching
  it('11. Resolves plural word synonyms correctly', () => {
    const result = matchStepIngredients('Add chillies.', [
      { id: '1', ingredient: { canonical_name: 'chili' } }
    ]);
    expect(result).toHaveLength(1);
  });

  // 12. Empty instruction
  it('12. Gracefully handles empty instructions string', () => {
    const result = matchStepIngredients('', mockIngredients);
    expect(result).toHaveLength(0);
  });

  // 13. Empty ingredient list
  it('13. Gracefully handles empty ingredient list array', () => {
    const result = matchStepIngredients('Heat oil.', []);
    expect(result).toHaveLength(0);
  });

  // 14. Punctuation
  it('14. Ignores punctuation symbols surrounding names', () => {
    const result = matchStepIngredients('Sauté onion; then add tomato!', mockIngredients);
    expect(result).toHaveLength(2);
  });

  // 15. Ingredient order
  it('15. Preserves the original order in the recipe list', () => {
    // onion is index 0, oil is index 2. Even if instruction says "oil first then onion", output should keep original order
    const result = matchStepIngredients('Heat oil, add onion.', mockIngredients);
    expect(result[0].ingredient.canonical_name).toBe('onion');
    expect(result[1].ingredient.canonical_name).toBe('oil');
  });

  // 16. Most-specific compound ingredient matching
  it('16. Selects most specific compound ingredient and filters parent substring duplicates', () => {
    const result = matchStepIngredients('Add olive oil.', mockIngredients);
    const matchedNames = result.map(ri => ri.ingredient.canonical_name);
    // Should contain "olive oil" but NOT the generic "oil"
    expect(matchedNames).toContain('olive oil');
    expect(matchedNames).not.toContain('oil');
  });
});
