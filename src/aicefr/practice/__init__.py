"""Practice mode, "assessment for learning" (D023).

The task bank (`bank`), the rule-based mission checker (`missions`), the next
task rule (`recommend`), the daily goal and streak (`streak`) and the advice
after each attempt (`feedback`). Nothing here calls the scoring model: a
practice attempt has no band.
"""

from __future__ import annotations

from aicefr.practice.bank import PRACTICE_MISSIONS, get_mission, list_missions
from aicefr.practice.contracts import (
    MissionGoal,
    MissionKind,
    PracticeMission,
    PracticePurpose,
    PracticeResult,
    PracticeStatus,
)
