interface EmptyStateProps {
  onReset: () => void;
}

export function EmptyState({ onReset }: EmptyStateProps) {
  return (
    <div className="empty-state">
      <h2>No patients match these filters</h2>
      <p>Adjust search, risk category, gender, or diagnosis group to widen the queue.</p>
      <button className="secondary-button" type="button" onClick={onReset}>
        Clear filters
      </button>
    </div>
  );
}
