const specialLabels: Record<string, string> = {
  Emergency_Room: 'Emergency Room',
  Nursing_Facility_or_Transfer: 'Nursing Facility or Transfer',
  Transfer_Other: 'Other Transfer',
  Emergency_Urgent: 'Emergency or Urgent',
  Other_Unknown: 'Other or Unknown',
};

const lowercaseWords = new Set(['or', 'and', 'of', 'to', 'with', 'from']);

export function formatDisplayLabel(value: string | null | undefined) {
  if (!value) return value ?? null;
  if (specialLabels[value]) return specialLabels[value];

  return value
    .replace(/_/g, ' ')
    .split(/\s+/)
    .filter(Boolean)
    .map((word) => {
      const lower = word.toLowerCase();
      if (lowercaseWords.has(lower)) return lower;
      if (word.toUpperCase() === word) return word;
      return `${word.slice(0, 1).toUpperCase()}${word.slice(1)}`;
    })
    .join(' ');
}

export function displayAge(value: number | null | undefined, fallbackAgeBand: string | null | undefined) {
  if (typeof value === 'number') return String(value);
  return fallbackAgeBand ?? '—';
}
