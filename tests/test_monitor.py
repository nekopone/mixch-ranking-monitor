from __future__ import annotations

import json
import os
import tempfile
import unittest
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import patch

from src.mixch_monitor import (
    Config,
    StateError,
    Stream,
    build_stream_embed,
    load_state,
    maintain_state,
    mark_notified,
    parse_ranking_page,
    select_eligible_streams,
)


FIXTURE = Path(__file__).parent / "fixtures" / "ranking_sample.html"
NOW = datetime(2026, 8, 8, 1, 30, tzinfo=timezone.utc)


def new_state() -> dict:
    return {"version": 1, "notifications": {}, "metadata": {}}


def stream(user_id: str, momentum: int, name: str = "配信者") -> Stream:
    return Stream(
        user_id=user_id,
        broadcaster_name=name,
        title="配信タイトル",
        url=f"https://mixch.tv/u/{user_id}/live",
        momentum=momentum,
        rank=1,
        elapsed_minutes=75,
        elapsed_text="1時間15分",
    )


class ParserTests(unittest.TestCase):
    def test_parses_user_id_momentum_and_elapsed_time(self) -> None:
        parsed = parse_ranking_page(FIXTURE.read_text(encoding="utf-8"))

        self.assertEqual(2, len(parsed))
        self.assertEqual("111", parsed[0].user_id)
        self.assertEqual("配信者🔥A", parsed[0].broadcaster_name)
        self.assertEqual("ガチイベ最終日", parsed[0].title)
        self.assertEqual(151, parsed[0].momentum)
        self.assertEqual(329, parsed[0].elapsed_minutes)
        self.assertEqual("5時間29分", parsed[0].elapsed_text)
        self.assertEqual("https://mixch.tv/u/111/live", parsed[0].url)

    def test_raises_when_header_has_streams_but_no_liveboxes(self) -> None:
        html = "<html><span id='live_list_header1'>勢い順 MixChannel [20人放送中]</span></html>"
        with self.assertRaisesRegex(Exception, "配信枠を取得できません"):
            parse_ranking_page(html)

    def test_keeps_stream_with_blank_broadcaster_name(self) -> None:
        html = """
        <span id="live_list_header1">勢い順 MixChannel [1人放送中]</span>
        <div id="livebox" data-uid="mixch_9738940">
          <div class="live_rankNum">1</div>
          <div class="live_title"><a href="https://mixch.tv/u/9738940/live">無名配信</a></div>
          <div class="live_name"><a href="https://mixch.tv/u/9738940/live"></a></div>
          <a class="live_timenum" title="74分経過"><span>1時間</span><span>14分</span></a>
          <div class="live_viewer"><span>180</span><span>points</span></div>
        </div>
        """
        parsed = parse_ranking_page(html)
        self.assertEqual(1, len(parsed))
        self.assertEqual("名称未設定（ID: 9738940）", parsed[0].broadcaster_name)
        self.assertEqual(74, parsed[0].elapsed_minutes)


class EligibilityTests(unittest.TestCase):
    def test_threshold_is_strictly_greater_than_150(self) -> None:
        eligible = select_eligible_streams(
            [stream("150", 150), stream("151", 151)],
            new_state(),
            threshold=150,
            cooldown_hours=12,
            now=NOW,
        )
        self.assertEqual(["151"], [item.user_id for item in eligible])

    def test_same_user_is_suppressed_even_after_name_change(self) -> None:
        state = new_state()
        mark_notified(state, [stream("111", 200, "旧名")], NOW - timedelta(hours=3))

        eligible = select_eligible_streams(
            [stream("111", 300, "新名")],
            state,
            threshold=150,
            cooldown_hours=12,
            now=NOW,
        )
        self.assertEqual([], eligible)

    def test_same_user_is_eligible_after_twelve_hours(self) -> None:
        state = new_state()
        mark_notified(
            state, [stream("111", 200)], NOW - timedelta(hours=12, seconds=1)
        )

        eligible = select_eligible_streams(
            [stream("111", 250)],
            state,
            threshold=150,
            cooldown_hours=12,
            now=NOW,
        )
        self.assertEqual(["111"], [item.user_id for item in eligible])


class StateTests(unittest.TestCase):
    def test_rejects_corrupted_timestamp_instead_of_resending(self) -> None:
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "state.json"
            path.write_text(
                json.dumps(
                    {
                        "version": 1,
                        "notifications": {
                            "111": {"last_notified_at": "壊れた時刻"}
                        },
                        "metadata": {},
                    },
                    ensure_ascii=False,
                ),
                encoding="utf-8",
            )
            with self.assertRaises(StateError):
                load_state(path)

    def test_heartbeat_updates_weekly_and_old_records_are_removed(self) -> None:
        state = new_state()
        state["metadata"]["last_heartbeat_at"] = (
            NOW - timedelta(days=8)
        ).isoformat()
        mark_notified(state, [stream("old", 200)], NOW - timedelta(days=31))

        changed = maintain_state(state, NOW, cooldown_hours=12, heartbeat_days=7)

        self.assertTrue(changed)
        self.assertNotIn("old", state["notifications"])
        self.assertEqual("2026-08-08T01:30:00Z", state["metadata"]["last_heartbeat_at"])


class NotificationFormattingTests(unittest.TestCase):
    def test_embed_contains_requested_information(self) -> None:
        item = stream("111", 234, "配信者A")
        embed = build_stream_embed(item, threshold=150, observed_at=NOW)

        rendered = json.dumps(embed, ensure_ascii=False)
        self.assertIn("配信者A", rendered)
        self.assertIn("234 points", rendered)
        self.assertIn("1時間15分", rendered)
        self.assertIn("https://mixch.tv/u/111/live", rendered)


class ConfigTests(unittest.TestCase):
    def test_defaults_match_requested_values(self) -> None:
        with patch.dict(os.environ, {}, clear=True):
            config = Config.from_environment()
        self.assertEqual(150, config.momentum_threshold)
        self.assertEqual(12, config.cooldown_hours)

    def test_repository_variables_override_defaults(self) -> None:
        with patch.dict(
            os.environ,
            {"MOMENTUM_THRESHOLD": "275", "COOLDOWN_HOURS": "8"},
            clear=True,
        ):
            config = Config.from_environment()
        self.assertEqual(275, config.momentum_threshold)
        self.assertEqual(8, config.cooldown_hours)


if __name__ == "__main__":
    unittest.main()
