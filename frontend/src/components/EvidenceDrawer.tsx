import React, { useState } from 'react';
import { ChevronDown, ChevronUp, Cpu, CheckCircle2 } from 'lucide-react';
import { Decision, EvidencePack } from '../types';

interface EvidenceDrawerProps {
  decision?: Decision;
  evidence?: EvidencePack | null;
  validationPassed?: boolean;
}

export const EvidenceDrawer: React.FC<EvidenceDrawerProps> = ({
  decision,
  evidence,
  validationPassed = true,
}) => {
  const [isOpen, setIsOpen] = useState(false);

  if (!evidence && !decision) return null;

  return (
    <div className="evidence-container">
      <button
        type="button"
        className="evidence-toggle"
        onClick={() => setIsOpen(!isOpen)}
        aria-expanded={isOpen}
      >
        <span style={{ display: 'flex', alignItems: 'center', gap: '6px' }}>
          <Cpu size={14} />
          <span>Decision Evidence & Audit Trail</span>
          {validationPassed && (
            <span style={{ color: '#10b981', display: 'flex', alignItems: 'center', gap: '3px', fontSize: '0.7rem' }}>
              <CheckCircle2 size={12} /> Grounded
            </span>
          )}
        </span>
        {isOpen ? <ChevronUp size={16} /> : <ChevronDown size={16} />}
      </button>

      {isOpen && (
        <div className="evidence-panel">
          {evidence?.intent && (
            <div className="evidence-row">
              <span className="evidence-label">User Intent:</span>
              <span className="evidence-value">
                {evidence.intent.activity} / {evidence.intent.category} / {evidence.intent.user_group} / {evidence.intent.time_scope}
              </span>
            </div>
          )}

          {evidence?.location && (
            <div className="evidence-row">
              <span className="evidence-label">Resolved Location:</span>
              <span className="evidence-value">
                {evidence.location.name} ({evidence.location.latitude.toFixed(4)}, {evidence.location.longitude.toFixed(4)})
                {evidence.location.country ? ` — ${evidence.location.country}` : ''}
              </span>
            </div>
          )}

          {evidence?.weather && (
            <div className="evidence-row">
              <span className="evidence-label">Weather Observation:</span>
              <span className="evidence-value">
                {evidence.weather.timestamp} | {evidence.weather.temperature_c}°C | Wind: {evidence.weather.wind_speed_kmh} km/h | Rain Prob: {evidence.weather.precipitation_probability ?? 0}% | UV: {evidence.weather.uv_index ?? 'N/A'}
              </span>
            </div>
          )}

          {decision && (
            <div className="evidence-row">
              <span className="evidence-label">Decision Status:</span>
              <span className="evidence-value" style={{ fontWeight: 600, color: '#38bdf8' }}>
                {decision.status} {decision.selected_policy_id ? `(${decision.selected_policy_id})` : ''}
              </span>
            </div>
          )}

          {decision?.matched_policy_ids && decision.matched_policy_ids.length > 0 && (
            <div className="evidence-row">
              <span className="evidence-label">Matched Policies:</span>
              <span className="evidence-value">
                {decision.matched_policy_ids.join(', ')}
              </span>
            </div>
          )}

          {evidence?.selected_policy && (
            <div className="evidence-row">
              <span className="evidence-label">Selected Policy:</span>
              <span className="evidence-value">
                {evidence.selected_policy.id} / {evidence.severity?.toUpperCase() || decision?.severity?.toUpperCase()}
              </span>
            </div>
          )}

          {decision?.selection_reason && (
            <div className="evidence-row">
              <span className="evidence-label">Selection Reason:</span>
              <span className="evidence-value">{decision.selection_reason}</span>
            </div>
          )}

          {evidence?.matched_conditions && evidence.matched_conditions.length > 0 && (
            <div style={{ marginTop: '4px' }}>
              <span className="evidence-label">Evaluated Condition Rationale:</span>
              <ul className="conditions-list">
                {evidence.matched_conditions.map((cond, idx) => (
                  <li key={idx}>{cond}</li>
                ))}
              </ul>
            </div>
          )}

          {decision?.reasons && decision.reasons.length > 0 && (!evidence?.matched_conditions || evidence.matched_conditions.length === 0) && (
            <div style={{ marginTop: '4px' }}>
              <span className="evidence-label">Decision Reasons:</span>
              <ul className="conditions-list">
                {decision.reasons.map((r, idx) => (
                  <li key={idx}>{r}</li>
                ))}
              </ul>
            </div>
          )}
        </div>
      )}
    </div>
  );
};
