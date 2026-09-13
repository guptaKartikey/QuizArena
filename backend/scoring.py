from typing import List, Dict

def calculate_score(
    is_correct: bool,
    response_time: float,
    total_time: float,
    correct_points: float = 10.0,
    wrong_points: float = -5.0,
    no_answer_points: float = 0.0,
    enable_negative_marking: bool = True,
    enable_speed_bonus: bool = True,
    mode: str = "CLASSIC",
    speed_tiers: List[Dict] = None
) -> tuple[float, float]:
    """
    Calculates final points and speed bonus.
    Supports CLASSIC mode formula and custom Speed Tiers mode.
    """
    if not is_correct:
        pts = wrong_points if enable_negative_marking else 0.0
        return float(pts), 0.0

    base_points = float(correct_points)
    speed_bonus = 0.0

    # Custom Speed Tiers mode
    if mode == "SPEED_QUIZ" and speed_tiers:
        bonus = calculate_speed_tier_points(response_time, speed_tiers)
        return float(base_points + bonus), float(bonus)

    # Standard continuous speed bonus
    if enable_speed_bonus and response_time > 0 and total_time > 0:
        time_ratio = max(0.0, (total_time - response_time) / total_time)
        speed_bonus = round(base_points * 0.5 * time_ratio, 1)

    total_points = round(base_points + speed_bonus, 1)
    return total_points, speed_bonus

def calculate_speed_tier_points(response_time: float, speed_tiers: List[Dict]) -> float:
    """
    Example speed_tiers:
    [
        {"min_s": 0, "max_s": 5, "pts": 10},
        {"min_s": 5, "max_s": 10, "pts": 8},
        {"min_s": 10, "max_s": 15, "pts": 6},
        {"min_s": 15, "max_s": 20, "pts": 4},
        {"min_s": 20, "max_s": 30, "pts": 2}
    ]
    """
    for tier in speed_tiers:
        min_s = float(tier.get("min_s", 0))
        max_s = float(tier.get("max_s", 999))
        pts = float(tier.get("pts", 0))
        if min_s <= response_time < max_s:
            return pts
    return 0.0
