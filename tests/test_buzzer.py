import pytest
import asyncio
from backend.buzzer import BuzzerManager

@pytest.mark.asyncio
async def test_simultaneous_buzzer_concurrency():
    buzzer = BuzzerManager()
    quiz_id = "QA-TEST-BUZZ"
    question_id = 101

    # Simulate 10 players buzzing concurrently
    player_names = [f"Player_{i}" for i in range(1, 11)]

    async def buzz_task(p_name):
        return await buzzer.register_buzz(
            quiz_id=quiz_id,
            question_id=question_id,
            participant_id=f"id_{p_name}",
            participant_name=p_name
        )

    # Launch all 10 tasks at the exact same moment
    results = await asyncio.gather(*[buzz_task(name) for name in player_names])

    winners = [r for r in results if r["is_winner"] is True]
    assert len(winners) == 1, f"Expected exactly 1 winner, got {len(winners)}"
    
    first_winner = winners[0]
    assert first_winner["position"] == 1
    assert first_winner["winner_name"] in player_names

    # Check positions are sequential 1 to 10
    positions = sorted([r["position"] for r in results])
    assert positions == list(range(1, 11))
