import React from 'react';
import { Shield, RotateCcw, BookOpen } from 'lucide-react';
import { HealthStatus } from '../types';

interface HeaderProps {
  health: HealthStatus | null;
  onNewSession: () => void;
  onOpenPolicies: () => void;
}

export const Header: React.FC<HeaderProps> = ({
  health,
  onNewSession,
  onOpenPolicies,
}) => {
  return (
    <header className="header">
      <div className="brand-wrapper">
        <div className="brand-icon">
          <Shield size={24} />
        </div>
        <div>
          <h1 className="brand-title">WeatherGuard</h1>
          <p className="brand-subtitle">Policy-First Weather Advisory Support Bot</p>
        </div>
      </div>

      <div className="header-actions">
        <div className="status-badge" title="Deterministic Policy Engine Active">
          <span className="status-dot"></span>
          <span>{health ? `${health.policies_loaded} SOPs Active` : 'Connecting...'}</span>
        </div>

        <button
          type="button"
          className="btn-secondary"
          onClick={onOpenPolicies}
          title="View externalized SOP policy registry"
        >
          <BookOpen size={16} />
          <span>SOPs</span>
        </button>

        <button
          type="button"
          className="btn-secondary"
          onClick={onNewSession}
          title="Reset conversation state and session ID"
        >
          <RotateCcw size={16} />
          <span>New Session</span>
        </button>
      </div>
    </header>
  );
};
