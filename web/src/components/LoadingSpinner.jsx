export default function LoadingSpinner({ text = 'Yükleniyor...' }) {
  return (
    <div className="loading-overlay">
      <div className="spinner" />
      <span>{text}</span>
    </div>
  );
}
