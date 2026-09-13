export default function Card({ children, className = '', title, bodyClassName = '', ...props }) {
  return (
    <div className={`card flex-col ${className}`} {...props}>
      {title && (
        <div className="p-4 border-b border-[var(--border)]">
          <h3 className="font-semibold text-[var(--text)]">{title}</h3>
        </div>
      )}
      <div className={title ? `p-4 ${bodyClassName}` : `p-6 ${bodyClassName}`}>
        {children}
      </div>
    </div>
  );
}
