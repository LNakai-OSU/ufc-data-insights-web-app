export default function Modal({ onClose, children }) {
  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="modal-content" onClick={(e) => e.stopPropagation()}>
        <button className="close-btn modal-close" onClick={onClose}>×</button>
        {children}
      </div>
    </div>
  );
}
