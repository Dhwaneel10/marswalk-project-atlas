"""Project Atlas / MarsWalk 2.0 — Milestone 13T
Unified Mission Event Coordinator & Simulation Clock.

Coordinates discrete events across Mars solar time, Mission Elapsed Time (MET),
and solar longitude (L_s). Enforces causal event ordering, priority dispatching,
and deterministic execution histories.
"""

from __future__ import annotations

import heapq
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Tuple

from .atlas_mission_contracts import EventType

MARS_SOL_SECONDS = 88775.244
MARS_SEC_RATIO = MARS_SOL_SECONDS / 86400.0  # ~1.02749125 SI seconds per martian second
DEG_LS_PER_SOL = 360.0 / 668.6  # ~0.538 degrees L_s per sol


def parse_sol_time_to_seconds(sol_time_str: str) -> float:
    """Parse 'HH:MM:SS' sol time string to total SI seconds elapsed within the sol."""
    parts = sol_time_str.split(":")
    if len(parts) == 3:
        h, m, s = float(parts[0]), float(parts[1]), float(parts[2])
    elif len(parts) == 2:
        h, m, s = float(parts[0]), float(parts[1]), 0.0
    else:
        h, m, s = float(parts[0]), 0.0, 0.0
    martian_seconds = h * 3600.0 + m * 60.0 + s
    return martian_seconds * MARS_SEC_RATIO


def format_seconds_to_sol_time(seconds: float) -> str:
    """Convert SI sol seconds to normalized 'HH:MM:SS' string on a 24-hour Mars sol scale."""
    rem_si = seconds % MARS_SOL_SECONDS
    martian_seconds = rem_si / MARS_SEC_RATIO
    hours = int(martian_seconds // 3600.0) % 24
    rem = martian_seconds % 3600.0
    mins = int(rem // 60.0)
    secs = int(round(rem % 60.0))
    if secs == 60:
        secs = 0
        mins += 1
        if mins == 60:
            mins = 0
            hours = (hours + 1) % 24
    return f"{hours:02d}:{mins:02d}:{secs:02d}"


@dataclass(order=True)
class EventEnvelope:
    sort_key: Tuple[int, float, int, str] = field(init=False)
    event_id: str = field(compare=False)
    event_type: EventType = field(compare=False)
    sol: int = field(compare=False)
    sol_time_str: str = field(compare=False, default="12:00:00")
    sol_seconds: float = field(compare=False, default=44387.622)
    priority: int = field(compare=False, default=5)  # 1 (Highest) to 10 (Lowest)
    parent_event_id: Optional[str] = field(compare=False, default=None)
    payload: Dict[str, Any] = field(compare=False, default_factory=dict)
    executed: bool = field(compare=False, default=False)
    execution_result: Optional[str] = field(compare=False, default=None)

    def __post_init__(self) -> None:
        if not self.sol_seconds:
            self.sol_seconds = parse_sol_time_to_seconds(self.sol_time_str)
        self.sort_key = (self.sol, self.sol_seconds, self.priority, self.event_id)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "event_id": self.event_id,
            "event_type": self.event_type.value if isinstance(self.event_type, EventType) else self.event_type,
            "sol": self.sol,
            "sol_time_str": self.sol_time_str,
            "sol_seconds": round(self.sol_seconds, 2),
            "priority": self.priority,
            "parent_event_id": self.parent_event_id,
            "payload": self.payload,
            "executed": self.executed,
            "execution_result": self.execution_result,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> EventEnvelope:
        d = dict(data)
        if "event_type" in d and isinstance(d["event_type"], str):
            d["event_type"] = EventType(d["event_type"])
        return cls(**d)


class MissionEventCoordinator:
    """Deterministic discrete-event engine coordinating simulation time and causal events."""

    def __init__(self, start_sol: int = 1, start_sol_time: str = "06:00:00", initial_ls: float = 56.4) -> None:
        self.current_sol: int = start_sol
        self.current_sol_seconds: float = parse_sol_time_to_seconds(start_sol_time)
        self.initial_ls: float = initial_ls
        self._event_queue: List[EventEnvelope] = []
        self._history: List[EventEnvelope] = []
        self._handlers: Dict[EventType, List[Callable[[EventEnvelope], None]]] = {}

    @property
    def current_sol_time(self) -> str:
        return format_seconds_to_sol_time(self.current_sol_seconds)

    @property
    def current_met_seconds(self) -> float:
        return (self.current_sol - 1) * MARS_SOL_SECONDS + self.current_sol_seconds

    @property
    def current_solar_longitude_ls(self) -> float:
        total_sols = (self.current_sol - 1) + (self.current_sol_seconds / MARS_SOL_SECONDS)
        return round((self.initial_ls + total_sols * DEG_LS_PER_SOL) % 360.0, 3)

    def register_handler(self, event_type: EventType, handler: Callable[[EventEnvelope], None]) -> None:
        """Register an event consumer callback for a specific event type."""
        if event_type not in self._handlers:
            self._handlers[event_type] = []
        self._handlers[event_type].append(handler)

    def schedule_event(
        self,
        event_id: str,
        event_type: EventType,
        sol: int,
        sol_time_str: str = "12:00:00",
        priority: int = 5,
        parent_event_id: Optional[str] = None,
        payload: Optional[Dict[str, Any]] = None,
    ) -> EventEnvelope:
        """Schedule a causal event in the deterministic priority queue."""
        sol_secs = parse_sol_time_to_seconds(sol_time_str)
        event = EventEnvelope(
            event_id=event_id,
            event_type=event_type,
            sol=sol,
            sol_time_str=sol_time_str,
            sol_seconds=sol_secs,
            priority=priority,
            parent_event_id=parent_event_id,
            payload=payload or {},
        )
        heapq.heappush(self._event_queue, event)
        return event

    def peek_next_event(self) -> Optional[EventEnvelope]:
        """Inspect the earliest scheduled event without popping."""
        return self._event_queue[0] if self._event_queue else None

    def advance_time(self, delta_sols: float) -> List[EventEnvelope]:
        """Advance simulation clock by delta_sols, dispatching all events up to the new timestamp."""
        target_met = self.current_met_seconds + delta_sols * MARS_SOL_SECONDS
        dispatched: List[EventEnvelope] = []

        while self._event_queue:
            next_event = self._event_queue[0]
            event_met = (next_event.sol - 1) * MARS_SOL_SECONDS + next_event.sol_seconds
            if event_met > target_met:
                break

            event = heapq.heappop(self._event_queue)
            # Advance clock directly to event time
            self.current_sol = event.sol
            self.current_sol_seconds = event.sol_seconds

            # Dispatch to handlers
            handlers = self._handlers.get(event.event_type, [])
            for handler in handlers:
                handler(event)

            event.executed = True
            event.execution_result = "SUCCESS"
            self._history.append(event)
            dispatched.append(event)

        # Advance to final target time
        final_total_sols = target_met / MARS_SOL_SECONDS
        self.current_sol = int(final_total_sols) + 1
        self.current_sol_seconds = target_met % MARS_SOL_SECONDS
        return dispatched

    def get_history(self) -> List[Dict[str, Any]]:
        return [e.to_dict() for e in self._history]

    def get_pending_queue(self) -> List[Dict[str, Any]]:
        return [e.to_dict() for e in sorted(self._event_queue)]
