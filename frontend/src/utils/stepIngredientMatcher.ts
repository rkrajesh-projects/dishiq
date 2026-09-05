export function escapeRegex(string: string): string {
  return string.replace(/[/\-\\^$*+?.()|[\]{}]/g, '\\$&');
}

/**
 * Generates singular/plural regex pattern for a single word.
 */
function getIngredientPattern(word: string): string {
  const clean = word.toLowerCase().trim();

  // Custom plural maps for common kitchen ingredients
  const pluralMaps: Record<string, string[]> = {
    onion: ['onion', 'onions'],
    tomato: ['tomato', 'tomatoes'],
    chili: ['chili', 'chilies', 'chillies'],
    chilli: ['chilli', 'chilies', 'chillies'],
    capsicum: ['capsicum', 'capsicums'],
    potato: ['potato', 'potatoes'],
    lemon: ['lemon', 'lemons'],
    garlic: ['garlic', 'garlics'],
    ginger: ['ginger', 'gingers'],
    spice: ['spice', 'spices'],
    cube: ['cube', 'cubes'],
    clove: ['clove', 'cloves'],
    sprig: ['sprig', 'sprigs'],
    leaf: ['leaf', 'leaves'],
  };

  if (pluralMaps[clean]) {
    return `(?:${pluralMaps[clean].join('|')})`;
  }

  for (const plurals of Object.values(pluralMaps)) {
    if (plurals.includes(clean)) {
      return `(?:${plurals.join('|')})`;
    }
  }

  // Default singular/plural handling
  if (clean.endsWith('s') && clean.length > 2) {
    const singular = clean.slice(0, -1);
    return `(?:${escapeRegex(clean)}|${escapeRegex(singular)})`;
  } else {
    return `(?:${escapeRegex(clean)}s?|${escapeRegex(clean)}es?)`;
  }
}

/**
 * Generates singular/plural expanded regex pattern for compound (multi-word) ingredients.
 */
function getCompoundPattern(canonicalName: string): string {
  const words = canonicalName.toLowerCase().trim().split(/\s+/);
  const wordPatterns = words.map(w => getIngredientPattern(w));
  return wordPatterns.join('\\s+');
}

/**
 * Deterministically filters ingredients relevant to the current cooking instruction.
 * Follows word boundary rules, handles plural forms/synonyms, and resolves compound name conflicts.
 */
export function matchStepIngredients(
  instruction: string,
  ingredients: any[]
): any[] {
  if (!instruction || !ingredients || ingredients.length === 0) {
    return [];
  }

  const cleanInstruction = instruction.toLowerCase().trim();
  const matchedEntries: { ri: any; cleanName: string }[] = [];

  for (const ri of ingredients) {
    const canonicalName = ri.ingredient?.canonical_name;
    if (!canonicalName) continue;

    // Guard: ignore raw numeric titles to prevent false positive index matching
    if (/^\d+$/.test(canonicalName)) {
      continue;
    }

    const pattern = getCompoundPattern(canonicalName);
    // Use word boundaries \b to prevent partial matches like "oil" in "boiling"
    const regex = new RegExp(`\\b${pattern}\\b`, 'i');

    if (regex.test(cleanInstruction)) {
      matchedEntries.push({ ri, cleanName: canonicalName.toLowerCase().trim() });
    }
  }

  // Prefer more specific compound matches (e.g. keep "olive oil", filter out duplicate "oil")
  // Sort matched entries by length of their clean names in descending order
  matchedEntries.sort((a, b) => b.cleanName.length - a.cleanName.length);

  const filteredEntries: any[] = [];
  for (const entry of matchedEntries) {
    // Skip if this cleanName is a substring of an already selected compound ingredient
    const isSub = filteredEntries.some(selected =>
      selected.ingredient?.canonical_name.toLowerCase().includes(entry.cleanName)
    );
    if (!isSub) {
      filteredEntries.push(entry.ri);
    }
  }

  // Preserve the original order of ingredients as they appear in the recipe list
  return ingredients.filter(ri => filteredEntries.includes(ri));
}
