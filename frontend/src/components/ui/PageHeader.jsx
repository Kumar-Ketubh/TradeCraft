export default function PageHeader({ title, description, action }) {
  return (
    <div className="flex justify-between items-center mb-6">
      <div>
        <h2 className="text-xl font-bold mb-1">{title}</h2>
        {description && <p className="text-muted text-sm">{description}</p>}
      </div>
      {action && <div>{action}</div>}
    </div>
  );
}
