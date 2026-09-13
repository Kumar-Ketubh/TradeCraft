import Badge from './Badge';

export default function StatusBadge({ status, isConnected = false, isRunning = false, className = '' }) {
  let variant = 'neutral';
  
  if (isConnected || isRunning) {
    variant = 'success';
  } else if (status?.toLowerCase() === 'error') {
    variant = 'danger';
  }

  return (
    <Badge variant={variant} className={className}>
      <span className="badge-dot"></span>
      {status || (isConnected ? 'Connected' : 'Not Connected')}
    </Badge>
  );
}
