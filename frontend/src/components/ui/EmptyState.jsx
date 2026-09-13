import Button from './Button';

export default function EmptyState({ title, description, icon: Icon, action, onAction }) {
  return (
    <div className="flex flex-col items-center justify-center p-6 text-center text-muted">
      {Icon && <Icon className="mb-4" size={48} strokeWidth={1} />}
      <h3 className="text-lg font-semibold text-text mb-2">{title}</h3>
      {description && <p className="text-sm max-w-sm mb-4">{description}</p>}
      {action && (
        <Button variant="primary" onClick={onAction}>
          {action}
        </Button>
      )}
    </div>
  );
}
