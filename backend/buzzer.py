import asyncio
import time
from typing import Dict, List, Optional

class BuzzerManager:
    def __init__(self):
        # Maps (quiz_id, question_id) -> Dict of buzz details
        # State: {"locked": bool, "winner_index": int, "queue": List[dict]}
        self._buzz_states: Dict[str, dict] = {}
        self._lock = asyncio.Lock()

    def _get_key(self, quiz_id: str, question_id: int) -> str:
        return f"{quiz_id}:{question_id}"

    async def register_buzz(self, quiz_id: str, question_id: int, participant_id: str, participant_name: str) -> dict:
        key = self._get_key(quiz_id, question_id)
        now_ns = time.time_ns()

        async with self._lock:
            if key not in self._buzz_states:
                self._buzz_states[key] = {
                    "locked": False,
                    "winner_index": 0,
                    "queue": []
                }

            state = self._buzz_states[key]

            # Check if participant already buzzed
            already_buzzed = any(item["participant_id"] == participant_id for item in state["queue"])
            if already_buzzed:
                pos = next(idx + 1 for idx, item in enumerate(state["queue"]) if item["participant_id"] == participant_id)
                current_winner = state["queue"][state["winner_index"]] if state["queue"] else None
                return {
                    "is_winner": (pos - 1 == state["winner_index"]),
                    "position": pos,
                    "winner_name": current_winner["participant_name"] if current_winner else "",
                    "timestamp_ns": now_ns,
                    "already_buzzed": True
                }

            buzz_item = {
                "participant_id": participant_id,
                "participant_name": participant_name,
                "timestamp_ns": now_ns
            }
            state["queue"].append(buzz_item)
            position = len(state["queue"])

            if position == 1:
                state["locked"] = True
                state["winner_index"] = 0
                return {
                    "is_winner": True,
                    "position": 1,
                    "winner_name": participant_name,
                    "timestamp_ns": now_ns,
                    "already_buzzed": False
                }
            else:
                current_winner = state["queue"][state["winner_index"]]
                return {
                    "is_winner": False,
                    "position": position,
                    "winner_name": current_winner["participant_name"],
                    "timestamp_ns": now_ns,
                    "already_buzzed": False
                }

    async def pass_to_next_fastest(self, quiz_id: str, question_id: int) -> Optional[dict]:
        """
        Used for Second Chance in First-to-Buzz mode.
        Passes the lock to the next player in the queue.
        """
        key = self._get_key(quiz_id, question_id)
        async with self._lock:
            state = self._buzz_states.get(key)
            if not state:
                return None

            state["winner_index"] += 1
            if state["winner_index"] < len(state["queue"]):
                next_winner = state["queue"][state["winner_index"]]
                return {
                    "winner_id": next_winner["participant_id"],
                    "winner_name": next_winner["participant_name"],
                    "rank": state["winner_index"] + 1
                }
            return None

    async def reset_buzzer(self, quiz_id: str, question_id: int):
        key = self._get_key(quiz_id, question_id)
        async with self._lock:
            if key in self._buzz_states:
                del self._buzz_states[key]

    async def get_buzz_winner(self, quiz_id: str, question_id: int) -> Optional[dict]:
        key = self._get_key(quiz_id, question_id)
        async with self._lock:
            state = self._buzz_states.get(key)
            if state and state["queue"] and state["winner_index"] < len(state["queue"]):
                return state["queue"][state["winner_index"]]
            return None

buzzer_manager = BuzzerManager()
