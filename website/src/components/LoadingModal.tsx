// LoadingModal.tsx
import React from 'react';

interface LoadingModalProps {
  text: string;
  threatDetected: boolean;
  onClose: () => void;
}

const LoadingModal: React.FC<LoadingModalProps> = ({ text, threatDetected, onClose }) => {
  return (
    <div className="modal-overlay">
      <div className="modal-content">
        {!threatDetected ? (
          <p>{text}</p>
        ) : (
          <>
            <p>Угроза традиционным ценностям обнаружена</p>
            <button onClick={onClose} className="destroy-button">
              Приступить к уничтожению
            </button>
          </>
        )}
      </div>
    </div>
  );
};

export default LoadingModal;