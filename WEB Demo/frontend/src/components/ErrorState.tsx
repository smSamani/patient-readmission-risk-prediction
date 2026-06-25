interface ErrorStateProps {
  message: string;
  onRetry: () => void;
}

export function ErrorState({ message, onRetry }: ErrorStateProps) {
  return (
    <div className="state-panel state-panel--error" role="alert">
      <div>
        <h2>Unable to load patient queue</h2>
        <p>{message}</p>
        <p className="state-hint">Confirm the FastAPI backend is running on the configured API URL.</p>
      </div>
      <button className="secondary-button" type="button" onClick={onRetry}>
        Retry
      </button>
    </div>
  );
}
