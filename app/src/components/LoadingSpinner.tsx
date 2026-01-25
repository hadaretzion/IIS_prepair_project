import './LoadingSpinner.css';

interface LoadingSpinnerProps {
  message?: string;
  size?: 'small' | 'medium' | 'large';
}

export function LoadingSpinner({ message, size = 'medium' }: LoadingSpinnerProps) {
  return (
    <div className={`loading-spinner-container loading-${size}`}>
      <div className="loading-spinner">
        <div className="spinner-ring"></div>
        <div className="spinner-ring"></div>
        <div className="spinner-ring"></div>
      </div>
      {message && <p className="loading-message">{message}</p>}
    </div>
  );
}

export function FullPageLoader({ message }: { message?: string }) {
  return (
    <div className="full-page-loader">
      <LoadingSpinner size="large" message={message} />
    </div>
  );
}
