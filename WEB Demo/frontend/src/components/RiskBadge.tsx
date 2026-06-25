interface RiskBadgeProps {
  category: string | null;
}

export function RiskBadge({ category }: RiskBadgeProps) {
  const normalized = (category ?? 'Unknown').toLowerCase();
  const tone = normalized.includes('high') ? 'high' : normalized.includes('medium') ? 'medium' : normalized.includes('low') ? 'low' : 'unknown';

  return <span className={`risk-badge risk-badge--${tone}`}>{category ?? 'Unknown'}</span>;
}
