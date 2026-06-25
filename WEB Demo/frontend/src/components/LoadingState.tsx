export function LoadingState() {
  return (
    <div className="state-panel" role="status" aria-live="polite">
      <div className="spinner" aria-hidden="true" />
      <div>
        <h2>Loading patient queue</h2>
        <p>Retrieving today’s discharge patients from the backend.</p>
      </div>
    </div>
  );
}
