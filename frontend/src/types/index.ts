export type SeverityLevel = 'low' | 'moderate' | 'high' | 'critical';

export type DecisionStatus =
  | 'MATCHED'
  | 'NO_POLICY'
  | 'LOCATION_REQUIRED'
  | 'LOCATION_ERROR'
  | 'WEATHER_ERROR';

export interface Location {
  query: string;
  name: string;
  latitude: number;
  longitude: number;
  country?: string;
  admin1?: string;
  timezone?: string;
}

export interface WeatherSnapshot {
  timestamp: string;
  temperature_c: number;
  apparent_temperature_c?: number;
  wind_speed_kmh: number;
  precipitation_mm: number;
  precipitation_probability?: number;
  uv_index?: number;
  weather_code?: number;
  relative_humidity_2m?: number;
}

export interface Intent {
  activity: string;
  category: string;
  location?: string | null;
  time_scope: string;
  user_group: string;
  confidence: number;
  raw_query?: string;
}

export interface Decision {
  status: DecisionStatus;
  selected_policy?: PolicyItem | null;
  selected_policy_id?: string | null;
  severity?: SeverityLevel | null;
  matched_policies?: PolicyMatch[];
  matched_policy_ids: string[];
  reasons: string[];
  selection_reason?: string | null;
}

export interface PolicyGuidance {
  title: string;
  recommendation: string;
  advisory_notes?: string;
}

export interface PolicyCondition {
  field: string;
  operator: string;
  value: any;
  secondary_value?: any;
  description?: string;
}

export interface PolicyItem {
  id: string;
  version: string;
  name: string;
  category: string;
  severity: SeverityLevel;
  priority: number;
  applies_to: {
    activities: string[];
    categories: string[];
    user_groups: string[];
  };
  conditions: PolicyConditions;
  guidance: PolicyGuidance;
  recommendation?: string;
}

export interface PolicyConditions {
  all?: PolicyCondition[];
  any?: PolicyCondition[];
  composite_profile?: { min_violations_to_trigger: number; rules: PolicyCondition[] };
}

export interface EvidencePack {
  intent: Intent;
  location?: Location | null;
  weather?: WeatherSnapshot | null;
  matched_policies: PolicyMatch[];
  selected_policy?: PolicyItem | null;
  severity?: SeverityLevel | null;
  matched_conditions: string[];
  evidence_fields: string[];
  selection_reason?: string | null;
  timestamp: string;
}

export interface PolicyMatch {
  policy_id: string;
  policy_name: string;
  severity: SeverityLevel;
  priority: number;
  matched: boolean;
  evaluated_reasons: string[];
  policy_obj: PolicyItem;
}

export interface ChatMessage {
  id: string;
  sender: 'user' | 'assistant';
  content: string;
  decision?: Decision;
  evidence?: EvidencePack | null;
  validation_passed?: boolean;
  timestamp: string;
}

export interface HealthStatus {
  status: string;
  service: string;
  llm_provider: string;
  policies_loaded: number;
  version: string;
}

export type LocationResolved = Location;
export type UserIntent = Intent;
