export default function StatCard({ icon, value, label, variant = 'primary' }) {
  return (
    <div className={`stat-card ${variant}`}>
      <div className="stat-card-icon">{icon}</div>
      <div className="stat-card-value">{typeof value === 'number' ? value.toLocaleString('tr-TR') : value}</div>
      <div className="stat-card-label">{label}</div>
    </div>
  );
}
