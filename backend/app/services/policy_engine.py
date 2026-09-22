import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import yaml

from backend.app.schemas.intent import UserIntent
from backend.app.schemas.policy import (
    Policy,
    PolicyCondition,
    PolicyMatch,
    SeverityLevel,
)
from backend.app.schemas.weather import WeatherSnapshot

logger = logging.getLogger(__name__)

SEVERITY_WEIGHTS = {
    SeverityLevel.CRITICAL: 4,
    SeverityLevel.HIGH: 3,
    SeverityLevel.MODERATE: 2,
    SeverityLevel.LOW: 1,
}

class PolicyEngine:
    """Deterministic, auditable policy engine that evaluates externalized SOP rules.

    The LLM plays NO role in safety policy decisions. The engine matches policies,
    evaluates conditions strictly against trusted WeatherSnapshot numbers,
    and deterministically resolves conflicts.
    """

    def __init__(self, policies_dir: Optional[Path] = None):
        self.policies_dir = policies_dir or (Path(__file__).resolve().parent.parent / "policies")
        self.policies: List[Policy] = []
        self.load_policies()

    def load_policies(self, directory: Optional[Path] = None) -> List[Policy]:
        """Loads and validates all YAML policy files in the policies directory."""
        target_dir = directory or self.policies_dir
        loaded_policies: List[Policy] = []

        if not target_dir.exists():
            logger.warning(f"Policies directory not found: {target_dir}")
            self.policies = []
            return []

        yaml_files = list(target_dir.glob("*.yaml")) + list(target_dir.glob("*.yml"))
        seen_ids = set()
        for file_path in yaml_files:
            try:
                with open(file_path, "r", encoding="utf-8") as f:
                    data = yaml.safe_load(f)
                    if not data:
                        continue
                    if isinstance(data, list):
                        for item in data:
                            policy = Policy.model_validate(item)
                            if policy.id in seen_ids:
                                raise ValueError(f"Duplicate policy id: {policy.id}")
                            seen_ids.add(policy.id)
                            loaded_policies.append(policy)
                    elif isinstance(data, dict):
                        policy = Policy.model_validate(data)
                        if policy.id in seen_ids:
                            raise ValueError(f"Duplicate policy id: {policy.id}")
                        seen_ids.add(policy.id)
                        loaded_policies.append(policy)
            except Exception as e:
                logger.error(f"Failed to load policy file {file_path}: {e}")
                raise ValueError(f"Error parsing policy file {file_path}: {e}") from e

        self.policies = loaded_policies
        logger.info(f"Loaded {len(self.policies)} SOPs from {target_dir}")
        return self.policies

    def reload_policies(self) -> int:
        """Hot-reloads policies from disk without restarting application."""
        self.load_policies()
        return len(self.policies)

    def _is_applicable(self, policy: Policy, intent: UserIntent) -> bool:
        """Determines if a policy applies to the user's requested activity, category, and demographic."""
        applies_to = policy.applies_to

        # Demographic filter: if policy specifies user_groups (e.g. child, elderly),
        # intent user_group must match or overlap
        if applies_to.user_groups:
            # If policy is specifically for 'child' or 'elderly', do not trigger for general adult queries
            req_groups = [g.lower() for g in applies_to.user_groups]
            user_grp = intent.user_group.value.lower()
            if ("general" not in req_groups and "adult" not in req_groups) and user_grp not in req_groups:
                return False

        # Activity matching (exact, synonym, or substring in both directions)
        act_query = intent.activity.lower().replace("-", "_").replace(" ", "_")
        matched_activity = False

        if not applies_to.activities and not applies_to.categories:
            # Broad policy
            matched_activity = True
        else:
            for act in applies_to.activities:
                norm_act = act.lower().replace("-", "_").replace(" ", "_")
                if norm_act == act_query or norm_act in act_query or act_query in norm_act:
                    matched_activity = True
                    break

            # Category fallback is valid only for policies without activity constraints.
            if not matched_activity and not applies_to.activities and applies_to.categories:
                intent_cat = intent.category.value.lower()
                for cat in applies_to.categories:
                    if cat.lower() == intent_cat:
                        matched_activity = True
                        break

        return matched_activity

    def _evaluate_single_condition(
        self,
        cond_dict: Dict[str, Any],
        weather: WeatherSnapshot
    ) -> Tuple[bool, str]:
        """Generic evaluation of a single condition against WeatherSnapshot."""
        field = cond_dict.get("field", "")
        op = cond_dict.get("operator", "")
        target_val = cond_dict.get("value")
        sec_val = cond_dict.get("secondary_value")
        desc = cond_dict.get("description", "")

        actual_val = getattr(weather, field, None)
        if actual_val is None:
            return False, f"{field} is unavailable in weather snapshot"

        passed = False
        try:
            if op == ">=":
                passed = float(actual_val) >= float(target_val)
            elif op == "<=":
                passed = float(actual_val) <= float(target_val)
            elif op == ">":
                passed = float(actual_val) > float(target_val)
            elif op == "<":
                passed = float(actual_val) < float(target_val)
            elif op == "==":
                passed = actual_val == target_val
            elif op == "!=":
                passed = actual_val != target_val
            elif op == "in":
                passed = actual_val in target_val
            elif op == "between" and sec_val is not None:
                passed = float(target_val) <= float(actual_val) <= float(sec_val)
            else:
                return False, f"Unsupported condition operator '{op}'"
        except (ValueError, TypeError) as e:
            return False, f"Type error comparing {field}={actual_val} with {target_val}: {e}"

        status_str = "MET" if passed else "NOT MET"
        reason = f"{field} ({actual_val}) {op} {target_val}: {status_str}"
        if desc:
            reason += f" [{desc}]"
        return passed, reason

    def _evaluate_conditions(
        self,
        policy: Policy,
        weather: WeatherSnapshot
    ) -> Tuple[bool, List[str]]:
        """Evaluates condition blocks (all, any, composite_profile) against WeatherSnapshot."""
        conds = policy.conditions
        reasons: List[str] = []

        # 1. Composite profile (Fuzzy / multi-factor profile)
        if "composite_profile" in conds:
            profile = conds["composite_profile"]
            min_violations = profile.get("min_violations_to_trigger", 2)
            rules = profile.get("rules", [])
            violation_count = 0
            profile_reasons = []

            for rule in rules:
                passed, reason = self._evaluate_single_condition(rule, weather)
                if passed:
                    violation_count += 1
                    profile_reasons.append(f"Discomfort trigger: {reason}")

            if violation_count >= min_violations:
                reasons.append(
                    f"Composite profile matched: {violation_count}/{len(rules)} discomfort factors detected (threshold >= {min_violations})"
                )
                reasons.extend(profile_reasons)
                return True, reasons
            else:
                reasons.append(
                    f"Composite profile not met: {violation_count}/{len(rules)} discomfort factors (requires >= {min_violations})"
                )
                return False, reasons

        # 2. 'all' conditions (Logical AND)
        if "all" in conds:
            all_rules = conds["all"]
            all_met = True
            for rule in all_rules:
                passed, reason = self._evaluate_single_condition(rule, weather)
                reasons.append(reason)
                if not passed:
                    all_met = False
            return all_met, reasons

        # 3. 'any' conditions (Logical OR)
        if "any" in conds:
            any_rules = conds["any"]
            any_met = False
            for rule in any_rules:
                passed, reason = self._evaluate_single_condition(rule, weather)
                reasons.append(reason)
                if passed:
                    any_met = True
            return any_met, reasons

        return False, ["No recognizable condition block found in policy"]

    def match(self, intent: UserIntent, weather: WeatherSnapshot) -> List[PolicyMatch]:
        """Evaluates all loaded policies against the user intent and weather snapshot.

        Returns a list of all matched PolicyMatch objects.
        """
        matches: List[PolicyMatch] = []

        for policy in self.policies:
            if not self._is_applicable(policy, intent):
                continue

            matched, reasons = self._evaluate_conditions(policy, weather)
            if matched:
                matches.append(
                    PolicyMatch(
                        policy_id=policy.id,
                        policy_name=policy.name,
                        severity=policy.severity,
                        priority=policy.priority,
                        matched=True,
                        evaluated_reasons=[
                            f"activity = {intent.activity} matched policy applicability",
                            f"category = {intent.category.value}",
                            f"user_group = {intent.user_group.value}",
                            *reasons,
                        ],
                        policy_obj=policy,
                    )
                )

        return matches

    def resolve_conflicts(self, matches: List[PolicyMatch]) -> Optional[PolicyMatch]:
        """Deterministically selects the winning policy when multiple policies match.

        Resolution Strategy:
        1. Highest severity rank (CRITICAL > HIGH > MODERATE > LOW)
        2. Highest policy priority integer (e.g. 95 > 85)
        3. Most specific policy (highest number of verified evaluated reasons)
        4. Stable tie-breaker: alphabetical policy ID
        """
        if not matches:
            return None

        # Higher scores win; the full policy ID gives a stable deterministic tie-breaker.
        sorted_matches = sorted(
            matches,
            key=lambda m: (
                SEVERITY_WEIGHTS.get(m.severity, 0),
                m.priority,
                len(m.evaluated_reasons),
            ),
            reverse=True
        )
        top = sorted_matches[0]
        winning = min(
            (match for match in sorted_matches if (
                SEVERITY_WEIGHTS.get(match.severity, 0),
                match.priority,
                len(match.evaluated_reasons),
            ) == (
                SEVERITY_WEIGHTS.get(top.severity, 0),
                top.priority,
                len(top.evaluated_reasons),
            )),
            key=lambda match: match.policy_id,
        )
        logger.info(
            f"Conflict resolution selected {winning.policy_id} (Severity: {winning.severity}, "
            f"Priority: {winning.priority}) from {len(matches)} matches"
        )
        return winning
