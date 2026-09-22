import React from 'react';
import { X, Shield, RefreshCw } from 'lucide-react';
import { PolicyItem } from '../types';

interface PoliciesModalProps {
  isOpen: boolean;
  onClose: () => void;
  policies: PolicyItem[];
  onReload: () => void;
  isReloading: boolean;
}

export const PoliciesModal: React.FC<PoliciesModalProps> = ({
  isOpen,
  onClose,
  policies,
  onReload,
  isReloading,
}) => {
  if (!isOpen) return null;

  return (
    <div className="modal-overlay" onClick={onClose}>
      <div className="modal-content" onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <div style={{ display: 'flex', alignItems: 'center', gap: '10px' }}>
            <Shield size={20} color="#38bdf8" />
            <h2 style={{ fontSize: '1.2rem', fontWeight: 600 }}>
              Externalized SOP Policy Registry ({policies.length})
            </h2>
          </div>

          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <button
              type="button"
              className="btn-secondary"
              onClick={onReload}
              disabled={isReloading}
              title="Hot-reload policies from YAML files"
            >
              <RefreshCw size={14} className={isReloading ? 'spin-icon' : ''} />
              <span>{isReloading ? 'Reloading...' : 'Hot-Reload YAML'}</span>
            </button>

            <button
              type="button"
              className="btn-secondary"
              onClick={onClose}
              style={{ padding: '6px' }}
            >
              <X size={18} />
            </button>
          </div>
        </div>

        <div className="modal-body">
          {policies.map((p) => (
            <div key={p.id} className="policy-card">
              <div className="policy-card-header">
                <span className="policy-badge">{p.id}</span>
                <span className={`severity-pill ${p.severity.toLowerCase()}`}>
                  {p.severity.toUpperCase()}
                </span>
              </div>
              <h3 className="policy-title">{p.name}</h3>
              <p className="policy-rec">
                <strong>Recommendation:</strong> {p.recommendation || p.guidance?.recommendation}
              </p>
              <div style={{ fontSize: '0.72rem', color: '#64748b' }}>
                Category: <code>{p.category}</code> | Priority: <code>{p.priority}</code> | Version: <code>{p.version}</code>
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};
