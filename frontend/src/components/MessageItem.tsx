import React from 'react';
import { Thermometer, Wind, CloudRain, Sun, AlertTriangle, CheckCircle, ShieldAlert } from 'lucide-react';
import { ChatMessage, SeverityLevel } from '../types';
import { EvidenceDrawer } from './EvidenceDrawer';

interface MessageItemProps {
  message: ChatMessage;
}

export const MessageItem: React.FC<MessageItemProps> = ({ message }) => {
  if (message.sender === 'user') {
    return (
      <div className="message-wrapper user">
        <div className="user-bubble">{message.content}</div>
      </div>
    );
  }

  const decision = message.decision;
  const evidence = message.evidence;
  const weather = evidence?.weather;
  const severity = (decision?.severity?.toLowerCase() || 'no-policy') as SeverityLevel | 'no-policy';

  const renderSeverityBadge = () => {
    if (decision?.status === 'NO_POLICY') {
      return (
        <span className="severity-pill no-policy">
          <CheckCircle size={12} />
          NO POLICY APPLICABLE
        </span>
      );
    }
    if (decision?.status === 'LOCATION_REQUIRED' || decision?.status === 'LOCATION_ERROR') {
      return (
        <span className="severity-pill moderate">
          <AlertTriangle size={12} />
          LOCATION NOTICE
        </span>
      );
    }
    if (decision?.status === 'WEATHER_ERROR') {
      return (
        <span className="severity-pill critical">
          <AlertTriangle size={12} />
          WEATHER UNAVAILABLE
        </span>
      );
    }

    return (
      <span className={`severity-pill ${severity}`}>
        <ShieldAlert size={12} />
        {severity.toUpperCase()} SEVERITY
      </span>
    );
  };

  return (
    <div className="message-wrapper assistant">
      <div className="assistant-card">
        <div className="card-top-bar">
          <div className="badges-group">
            {renderSeverityBadge()}
            {decision?.selected_policy_id && (
              <span className="policy-badge" title="Matched SOP Identifier">
                {decision.selected_policy_id}
              </span>
            )}
          </div>
          <span className="timestamp">{message.timestamp}</span>
        </div>

        {weather && (
          <div className="weather-strip">
            <div className="weather-chip">
              <Thermometer size={18} className="weather-chip-icon" />
              <div className="weather-chip-data">
                <span className="weather-chip-label">Temperature</span>
                <span className="weather-chip-value">{weather.temperature_c}°C</span>
              </div>
            </div>

            <div className="weather-chip">
              <Wind size={18} className="weather-chip-icon" />
              <div className="weather-chip-data">
                <span className="weather-chip-label">Wind Speed</span>
                <span className="weather-chip-value">{weather.wind_speed_kmh} km/h</span>
              </div>
            </div>

            <div className="weather-chip">
              <CloudRain size={18} className="weather-chip-icon" />
              <div className="weather-chip-data">
                <span className="weather-chip-label">Precipitation</span>
                <span className="weather-chip-value">
                  {weather.precipitation_mm} mm ({weather.precipitation_probability ?? 0}%)
                </span>
              </div>
            </div>

            <div className="weather-chip">
              <Sun size={18} className="weather-chip-icon" />
              <div className="weather-chip-data">
                <span className="weather-chip-label">UV Index</span>
                <span className="weather-chip-value">{weather.uv_index ?? 'N/A'}</span>
              </div>
            </div>
          </div>
        )}

        <div className="response-body">{message.content}</div>

        <EvidenceDrawer
          decision={decision}
          evidence={evidence}
          validationPassed={message.validation_passed}
        />
      </div>
    </div>
  );
};
