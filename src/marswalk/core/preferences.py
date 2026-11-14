"""
MarsWalk Mission Commander AI: Learn from the Commander.
Implements personalized, explainable route preference learning from explicit
pairwise route choices using regularized logistic ranking on physically grounded features.
Operates strictly locally, never mutates planetary rasters, and respects deterministic hard constraints.
"""

from dataclasses import dataclass, field, asdict
import datetime
import enum
import hashlib
import json
import math
import os
from typing import Dict, List, Optional, Tuple, Any

import numpy as np
import scipy.optimize

from marswalk.core.terrain import TerrainGrid
from marswalk.core.planner import RouteResult


# Feature indices and names
FEATURE_NAMES = [
    "norm_distance",
    "norm_cost",
    "norm_science",
    "norm_elevation_gain",
]

# Default reference scales for bounding features to [0.0, 2.0]
DEFAULT_D_SCALE = 10000.0  # meters
DEFAULT_C_SCALE = 20000.0  # equivalent flat meters
DEFAULT_S_SCALE = 250.0    # priority points
DEFAULT_E_SCALE = 500.0    # vertical climb meters

MIN_FEEDBACK_THRESHOLD = 3  # Minimum user choices required for personalized state


class LearningState(str, enum.Enum):
    UNTRAINED = "untrained"
    COLLECTING_INITIAL = "collecting_initial"
    PERSONALIZED = "personalized"
    RESET = "reset"


@dataclass
class RouteFeatures:
    """
    Physical route metrics extracted directly from calculated traverse paths.

    Attributes
    ----------
    distance_m : float
        Physical ground distance traversed in meters.
    cost : float
        Modeled directional terrain effort in equivalent flat meters.
    science_score : float
        Total scientific priority points harvested at visited waypoints.
    elevation_gain_m : float
        Cumulative vertical climb along the path in meters.
    """

    distance_m: float
    cost: float
    science_score: float
    elevation_gain_m: float

    def to_normalized_vector(
        self,
        d_scale: float = DEFAULT_D_SCALE,
        c_scale: float = DEFAULT_C_SCALE,
        s_scale: float = DEFAULT_S_SCALE,
        e_scale: float = DEFAULT_E_SCALE,
    ) -> np.ndarray:
        """
        Convert raw physical features to bounded, normalized floats in [0.0, 2.0].
        Guarantees numerical stability and prevents extreme gradient scaling.
        """
        v_d = min(2.0, max(0.0, float(self.distance_m) / max(1.0, d_scale)))
        v_c = min(2.0, max(0.0, float(self.cost) / max(1.0, c_scale)))
        v_s = min(2.0, max(0.0, float(self.science_score) / max(1.0, s_scale)))
        v_e = min(2.0, max(0.0, float(self.elevation_gain_m) / max(1.0, e_scale)))
        return np.array([v_d, v_c, v_s, v_e], dtype=np.float64)

    def to_dict(self) -> Dict[str, float]:
        return {
            "distance_m": round(self.distance_m, 2),
            "cost": round(self.cost, 2),
            "science_score": round(self.science_score, 2),
            "elevation_gain_m": round(self.elevation_gain_m, 2),
        }

    @classmethod
    def from_dict(cls, d: Dict[str, Any]) -> "RouteFeatures":
        return cls(
            distance_m=float(d.get("distance_m", 0.0)),
            cost=float(d.get("cost", 0.0)),
            science_score=float(d.get("science_score", 0.0)),
            elevation_gain_m=float(d.get("elevation_gain_m", 0.0)),
        )


def extract_route_features(route: RouteResult, terrain: Optional[TerrainGrid] = None) -> RouteFeatures:
    """
    Extract attributable physical features from a RouteResult and terrain elevation matrix.
    """
    dist = float(route.distance_m) if route.is_reachable else 0.0
    cost = float(route.cost) if (route.is_reachable and math.isfinite(route.cost)) else 0.0
    sci = float(route.science_score) if route.is_reachable else 0.0

    # Calculate cumulative positive elevation gain along vertices
    elev_gain = 0.0
    if route.is_reachable and terrain is not None and len(route.path) > 1:
        elev_array = terrain.elevation
        H, W = terrain.shape
        last_z = None
        for r, c in route.path:
            if 0 <= r < H and 0 <= c < W:
                z = float(elev_array[r, c])
                if last_z is not None and z > last_z:
                    elev_gain += (z - last_z)
                last_z = z

    return RouteFeatures(
        distance_m=dist,
        cost=cost,
        science_score=sci,
        elevation_gain_m=elev_gain,
    )


@dataclass
class CandidateOption:
    """A feasible candidate alternative presented to the Commander."""

    profile: str
    features: RouteFeatures
    route: Optional[RouteResult] = None


@dataclass
class PreferenceObservation:
    """
    An explicit user choice event recording a selected route and rejected alternatives.
    """

    choice_id: str
    timestamp: str
    selected_profile: str
    selected_features: RouteFeatures
    rejected_candidates: List[CandidateOption]

    def to_dict(self) -> Dict[str, Any]:
        return {
            "choice_id": self.choice_id,
            "timestamp": self.timestamp,
            "selected_profile": self.selected_profile,
            "selected_features": self.selected_features.to_dict(),
            "rejected_candidates": [
                {
                    "profile": c.profile,
                    "features": c.features.to_dict(),
                }
                for c in self.rejected_candidates
            ],
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "PreferenceObservation":
        sel_feat = RouteFeatures.from_dict(data["selected_features"])
        rejs = [
            CandidateOption(
                profile=c["profile"],
                features=RouteFeatures.from_dict(c["features"]),
            )
            for c in data.get("rejected_candidates", [])
        ]
        return cls(
            choice_id=data["choice_id"],
            timestamp=data["timestamp"],
            selected_profile=data["selected_profile"],
            selected_features=sel_feat,
            rejected_candidates=rejs,
        )


@dataclass
class RankedRoute:
    """Output ranking for a candidate route."""

    profile: str
    route: RouteResult
    features: RouteFeatures
    utility_score: float
    rank: int
    is_recommended: bool
    explanation: str

    @property
    def utility(self) -> float:
        """Alias for utility_score to provide backward-compatible attribute access."""
        return self.utility_score


class PreferenceModel:
    """
    Regularized linear utility ranking model: U(x) = w · x.
    Learns weights w from pairwise preferences (x_sel - x_rej) using convex L2-regularized
    logistic cross-entropy minimization.
    """

    def __init__(self, l2_reg: float = 0.5):
        self.l2_reg = float(l2_reg)
        self.weights: np.ndarray = np.zeros(len(FEATURE_NAMES), dtype=np.float64)
        self.observations: List[PreferenceObservation] = []
        self.state: LearningState = LearningState.UNTRAINED

    def get_state(self) -> LearningState:
        if self.state == LearningState.RESET:
            return LearningState.RESET
        n = len(self.observations)
        if n == 0:
            return LearningState.UNTRAINED
        elif n < MIN_FEEDBACK_THRESHOLD:
            return LearningState.COLLECTING_INITIAL
        else:
            return LearningState.PERSONALIZED

    def reset(self) -> None:
        """Clear all recorded observations and revert weights to zero."""
        self.observations.clear()
        self.weights = np.zeros(len(FEATURE_NAMES), dtype=np.float64)
        self.state = LearningState.RESET

    def add_observation(self, observation: PreferenceObservation) -> bool:
        """
        Add a preference observation if not duplicate, and retrain model.
        Returns True if added, False if duplicate.
        """
        for existing in self.observations:
            if existing.choice_id == observation.choice_id:
                return False

        self.observations.append(observation)
        self.state = self.get_state()
        self._fit()
        return True

    def _fit(self) -> None:
        """
        Fit weights via L-BFGS-B optimization on Bradley-Terry pairwise comparisons.
        """
        pairs: List[np.ndarray] = []
        for obs in self.observations:
            x_sel = obs.selected_features.to_normalized_vector()
            for rej in obs.rejected_candidates:
                x_rej = rej.features.to_normalized_vector()
                # z = x_sel - x_rej
                diff = x_sel - x_rej
                # Ignore degenerate identical vectors
                if np.linalg.norm(diff) > 1e-6:
                    pairs.append(diff)

        if not pairs:
            self.weights = np.zeros(len(FEATURE_NAMES), dtype=np.float64)
            return

        Z = np.vstack(pairs)  # Shape: (K, 4)

        def loss_and_grad(w: np.ndarray) -> Tuple[float, np.ndarray]:
            logits = np.dot(Z, w)  # Shape: (K,)
            # Loss: sum log(1 + exp(-logits)) + (lambda / 2) * ||w||^2
            # Use logaddexp for stable calculation
            loss_data = np.sum(np.logaddexp(0.0, -logits))
            loss_reg = 0.5 * self.l2_reg * np.sum(w**2)
            total_loss = float(loss_data + loss_reg)

            # Gradient: - sum (1 - sigmoid(logits)) * z_i + lambda * w
            # sigmoid(logits)
            sig = 1.0 / (1.0 + np.exp(-np.clip(logits, -30.0, 30.0)))
            grad_data = -np.dot(1.0 - sig, Z)
            grad = grad_data + self.l2_reg * w
            return total_loss, grad

        w_init = np.zeros(len(FEATURE_NAMES), dtype=np.float64)
        res = scipy.optimize.minimize(
            loss_and_grad,
            w_init,
            jac=True,
            method="L-BFGS-B",
            options={"maxiter": 100, "ftol": 1e-7},
        )

        if res.success or res.fun is not None:
            self.weights = res.x
        else:
            self.weights = w_init

    def predict_utility(self, features: RouteFeatures) -> float:
        """
        Compute scalar linear utility U(features) = w · x.
        """
        x = features.to_normalized_vector()
        return float(np.dot(self.weights, x))

    def rank_routes(
        self,
        candidate_routes: Dict[str, RouteResult],
        terrain: Optional[TerrainGrid] = None,
    ) -> List[RankedRoute]:
        """
        Rank candidate routes according to learned preference utility.
        CRITICAL: Hard constraints always take priority. Only routes that are reachable,
        budget-feasible, and non-empty can be ranked.
        """
        feasible_candidates: List[Tuple[str, RouteResult, RouteFeatures, float]] = []

        for prof_name, route in candidate_routes.items():
            if route is None:
                continue
            # Enforce hard constraints
            if not route.is_reachable or not route.is_budget_feasible or len(route.path) < 2:
                continue

            feats = extract_route_features(route, terrain=terrain)
            utility = self.predict_utility(feats)
            feasible_candidates.append((prof_name, route, feats, utility))

        if not feasible_candidates:
            return []

        # Sort descending by utility
        feasible_candidates.sort(key=lambda item: item[3], reverse=True)

        ranked: List[RankedRoute] = []
        for rank_idx, (p_name, r_res, f_res, u_val) in enumerate(feasible_candidates, start=1):
            is_top = (rank_idx == 1)
            expl = self._generate_route_explanation(p_name, f_res, u_val, is_top)
            ranked.append(
                RankedRoute(
                    profile=p_name,
                    route=r_res,
                    features=f_res,
                    utility_score=u_val,
                    rank=rank_idx,
                    is_recommended=is_top,
                    explanation=expl,
                )
            )

        return ranked

    def _generate_route_explanation(
        self, profile: str, features: RouteFeatures, utility: float, is_top: bool
    ) -> str:
        state = self.get_state()
        if state != LearningState.PERSONALIZED:
            return (
                f"{profile.replace('_', ' ').title()} traverse. "
                "Mission Commander AI is still gathering baseline choices."
            )

        w = self.weights
        # Determine dominant positive/negative factor
        # Features: [dist, cost, sci, elev]
        w_d, w_c, w_s, w_e = w[0], w[1], w[2], w[3]

        reasons = []
        if w_s > 0.2 and features.science_score > 0:
            reasons.append(f"captures {features.science_score:.0f} science pts")
        if w_d < -0.2:
            reasons.append(f"walking distance {features.distance_m:.0f} m")
        if w_c < -0.2:
            reasons.append(f"terrain effort {features.cost:.0f}")

        reason_str = ", ".join(reasons) if reasons else f"composite utility score {utility:+.2f}"
        if is_top:
            return f"Top Recommendation: Aligns with learned preference ({reason_str})."
        else:
            return f"Ranked alternative ({reason_str})."

    def get_preference_summary(self, voice_mode: str = "professional") -> Dict[str, Any]:
        """
        Generate user-facing narrative and weight breakdown.
        """
        state = self.get_state()
        is_humour = voice_mode == "dry_humour"

        if state == LearningState.UNTRAINED:
            if is_humour:
                headline = "Commander AI: Awaiting Your Orders"
                detail = "No route choices recorded yet. Make a few choices, and I'll learn whether you prefer rocks or rest."
            else:
                headline = "Mission Commander AI: Untrained Profile"
                detail = "No route preferences recorded yet. Select and save preferred routes to calibrate personalization."
            return {
                "headline": headline,
                "detail": detail,
                "state": state.value,
                "num_choices": 0,
                "weights": {},
            }

        elif state == LearningState.COLLECTING_INITIAL:
            n = len(self.observations)
            rem = MIN_FEEDBACK_THRESHOLD - n
            if is_humour:
                headline = f"Probation Period: {n}/{MIN_FEEDBACK_THRESHOLD} Choices Recorded"
                detail = f"I'm still learning your priorities. Need {rem} more choice(s) before I start giving advice."
            else:
                headline = f"Calibrating Preferences ({n}/{MIN_FEEDBACK_THRESHOLD} choices)"
                detail = f"Gathering baseline exploration priorities. {rem} more recorded choice(s) required to activate personalized ranking."
            return {
                "headline": headline,
                "detail": detail,
                "state": state.value,
                "num_choices": n,
                "weights": {},
            }

        elif state == LearningState.RESET:
            headline = "Profile Reset"
            detail = "Preference history cleared. Exploration recommendations have reverted to standard deterministic profiles."
            return {
                "headline": headline,
                "detail": detail,
                "state": state.value,
                "num_choices": 0,
                "weights": {},
            }

        # Personalized State
        w = self.weights
        w_d, w_c, w_s, w_e = float(w[0]), float(w[1]), float(w[2]), float(w[3])

        weights_dict = {
            "Travel Distance": round(w_d, 3),
            "Terrain Cost": round(w_c, 3),
            "Science Priority": round(w_s, 3),
            "Elevation Gain": round(w_e, 3),
        }

        # Formulate narrative based on weight tendencies
        if w_s > abs(w_d) and w_s > abs(w_c):
            if is_humour:
                headline = "Commander Profile: The Relentless Geologist"
                detail = (
                    "You've consistently voted for more rocks over less walking. "
                    "The science team approves; your fictional knees are negotiating."
                )
            else:
                headline = "Personalized Priority: Science Maximization"
                detail = (
                    f"Learned Commander weights place primary value on scientific yield (weight: {w_s:+.2f}). "
                    f"The model favors routes capturing high-priority outcrops, accepting moderate distance penalties."
                )
        elif abs(w_d) > w_s or abs(w_c) > w_s:
            if is_humour:
                headline = "Commander Profile: Safety First, Scenery Second"
                detail = (
                    "You've consistently favored shorter, flatter paths. "
                    "Flight surgeons are nodding in approval; geologists are quietly weeping."
                )
            else:
                headline = "Personalized Priority: Terrain Conservation"
                detail = (
                    f"Learned Commander weights penalize travel distance ({w_d:+.2f}) and terrain roughness ({w_c:+.2f}). "
                    "The model prioritizes direct, low-slope corridors and life-support margin conservation."
                )
        else:
            if is_humour:
                headline = "Commander Profile: The Diplomat"
                detail = "A delicate balance between gathering dust samples and not dying of exhaustion."
            else:
                headline = "Personalized Priority: Balanced Exploration"
                detail = "Learned Commander weights reflect a balanced compromise between scientific harvesting and traverse endurance."

        return {
            "headline": headline,
            "detail": detail,
            "state": state.value,
            "num_choices": len(self.observations),
            "weights": weights_dict,
        }

    def to_dict(self) -> Dict[str, Any]:
        """Serialize complete preference history and learned weights."""
        return {
            "schema_version": "1.0",
            "updated_at": datetime.datetime.now(datetime.timezone.utc).isoformat(),
            "state": self.state.value,
            "weights": [float(val) for val in self.weights],
            "num_choices": len(self.observations),
            "observations": [obs.to_dict() for obs in self.observations],
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "PreferenceModel":
        """Deserialize and restore model safely."""
        if not isinstance(data, dict) or data.get("schema_version") != "1.0":
            model = cls()
            return model

        model = cls()
        obs_list = []
        for o_data in data.get("observations", []):
            try:
                obs_list.append(PreferenceObservation.from_dict(o_data))
            except Exception:
                continue

        model.observations = obs_list
        if "weights" in data and len(data["weights"]) == len(FEATURE_NAMES):
            model.weights = np.array(data["weights"], dtype=np.float64)
        else:
            model._fit()

        raw_state = data.get("state", LearningState.UNTRAINED.value)
        if raw_state == LearningState.RESET.value and len(model.observations) == 0:
            model.state = LearningState.RESET
        else:
            model.state = model.get_state()

        return model


# ==============================================================================
# Local Persistence Manager
# ==============================================================================
def create_choice_id(selected_profile: str, selected_feats: RouteFeatures, rejected_profiles: List[str]) -> str:
    """Generate a deterministic deduplication hash for a choice event."""
    payload = f"{selected_profile}:{selected_feats.to_dict()}:{sorted(rejected_profiles)}"
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()[:16]


def load_preference_model(filepath: str) -> PreferenceModel:
    """
    Safely load PreferenceModel from local JSON file.
    Handles missing, corrupted, or incompatible files gracefully.
    """
    if not os.path.exists(filepath):
        return PreferenceModel()

    try:
        with open(filepath, "r", encoding="utf-8") as f:
            data = json.load(f)
        return PreferenceModel.from_dict(data)
    except Exception:
        # Graceful fallback on corrupt file
        return PreferenceModel()


def save_preference_model(model: PreferenceModel, filepath: str) -> bool:
    """
    Save PreferenceModel to local JSON file atomically.
    """
    try:
        os.makedirs(os.path.dirname(os.path.abspath(filepath)), exist_ok=True)
        tmp_path = filepath + ".tmp"
        with open(tmp_path, "w", encoding="utf-8") as f:
            json.dump(model.to_dict(), f, indent=2)
        # Atomic rename on Windows/POSIX
        os.replace(tmp_path, filepath)
        return True
    except Exception:
        return False
