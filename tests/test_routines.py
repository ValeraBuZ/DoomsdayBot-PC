import unittest
from datetime import datetime, timezone

from doomsdaybot.routines import (
    default_routine_tasks,
    effective_task_group,
    image_is_allowed_for_routine,
    is_task_effectively_enabled,
    next_due_task,
    next_run_after_finish,
    next_fixed_utc_run,
    no_action_retry_delay,
    normalize_routine_tasks,
    pick_due_task_index,
    runtime_step_is_ready,
    upgrade_radar_runtime_metadata,
    upgrade_resource_runtime_metadata,
)


class RoutineTaskTests(unittest.TestCase):
    def test_defaults_cover_requested_routines(self):
        tasks = default_routine_tasks()
        ids = {task["id"] for task in tasks}
        self.assertTrue(
            {
                "vip_rewards",
                "alliance_donations",
                "radar",
                "alliance_help",
                "fence_survivors",
                "processing_factory",
                "processing_contest",
                "mail_rewards",
                "completed_tasks",
                "research",
                "gathering_boost",
                "heal",
                "zombie_hunt",
                "collective_mind",
                "prize_hunt",
                "food",
                "wood",
                "metal",
                "oil",
                "train_infantry",
                "train_riders",
                "train_shooters",
                "train_vehicles",
            }.issubset(ids)
        )
        by_id = {task["id"]: task for task in tasks}
        self.assertEqual(by_id["mail_rewards"]["completion_runtime_step"], "claim_reports")
        self.assertEqual(by_id["completed_tasks"]["completion_runtime_step"], "scroll_top_4")
        self.assertEqual(by_id["fence_survivors"]["interval_minutes"], 15.0)
        self.assertEqual(by_id["processing_factory"]["interval_minutes"], 180.0)
        self.assertTrue(by_id["processing_factory"]["complete_when_idle"])
        self.assertTrue(by_id["processing_contest"]["complete_when_idle"])

    def test_resources_are_individually_selectable(self):
        tasks = default_routine_tasks()
        resources = [task for task in tasks if task.get("category") == "resources"]
        self.assertEqual([task["id"] for task in resources], ["food", "wood", "metal", "oil"])
        self.assertTrue(all(task["enabled"] and task["uses_march"] for task in resources))

    def test_normalization_repairs_values_and_merges_settings(self):
        tasks = normalize_routine_tasks([
            {
                "id": "food",
                "group": "  Ферма еды  ",
                "interval_minutes": -1,
                "timeout_seconds": "bad",
                "settings": {"resource_level": 8},
            },
            {
                "id": "custom_daily",
                "name": "Ежедневная награда",
                "group": "Награды",
                "enabled": True,
            },
        ])
        food = next(task for task in tasks if task["id"] == "food")
        custom = next(task for task in tasks if task["id"] == "custom_daily")
        self.assertEqual(food["group"], "Ферма еды")
        self.assertEqual(food["interval_minutes"], 0.1)
        self.assertEqual(food["timeout_seconds"], 30.0)
        self.assertEqual(food["settings"]["resource_level"], 8)
        self.assertEqual(custom["name"], "Ежедневная награда")

    def test_healing_has_priority_when_selected(self):
        tasks = default_routine_tasks()
        heal = next(task for task in tasks if task["id"] == "heal")
        heal["enabled"] = True
        index = pick_due_task_index(tasks, {}, start_index=0, now=100.0, active_marches=0, max_marches=5)
        self.assertEqual(tasks[index]["id"], "heal")

    def test_resource_rotation_starts_from_requested_position(self):
        tasks = default_routine_tasks()
        for task in tasks:
            task["enabled"] = task["id"] in {"food", "wood", "metal", "oil"}
        wood_index = next(index for index, task in enumerate(tasks) if task["id"] == "wood")
        index = pick_due_task_index(tasks, {}, start_index=wood_index, now=100.0, active_marches=0, max_marches=5)
        self.assertEqual(tasks[index]["id"], "wood")

    def test_enabled_prize_hunt_precedes_regular_resources(self):
        tasks = default_routine_tasks()
        prize = next(task for task in tasks if task["id"] == "prize_hunt")
        prize["enabled"] = True
        index = pick_due_task_index(tasks, {}, start_index=0, now=100.0, active_marches=0, max_marches=5)
        self.assertEqual(tasks[index]["id"], "prize_hunt")

    def test_sixth_march_is_never_scheduled(self):
        tasks = default_routine_tasks()
        for task in tasks:
            if not task.get("uses_march"):
                task["enabled"] = False
        index = pick_due_task_index(tasks, {}, 0, 100.0, active_marches=5, max_marches=5)
        self.assertIsNone(index)
        task, wait = next_due_task(tasks, {}, 100.0, active_marches=5, max_marches=5)
        self.assertIsNone(task)
        self.assertIsNone(wait)

    def test_configured_four_march_limit_is_respected(self):
        tasks = default_routine_tasks()
        for task in tasks:
            if not task.get("uses_march"):
                task["enabled"] = False
        blocked = pick_due_task_index(tasks, {}, 0, 100.0, active_marches=4, max_marches=4)
        allowed = pick_due_task_index(tasks, {}, 0, 100.0, active_marches=4, max_marches=5)
        self.assertIsNone(blocked)
        self.assertIsNotNone(allowed)

    def test_research_off_is_not_scheduled(self):
        task = next(task for task in default_routine_tasks() if task["id"] == "research")
        self.assertFalse(task["enabled"])
        self.assertEqual(task["settings"]["branch"], "off")
        task["enabled"] = True
        self.assertFalse(is_task_effectively_enabled(task))
        task["settings"]["branch"] = "economy"
        self.assertTrue(is_task_effectively_enabled(task))
        self.assertEqual(effective_task_group(task), "Исследования")

    def test_alliance_donations_wait_for_the_game_cooldown(self):
        task = next(task for task in default_routine_tasks() if task["id"] == "alliance_donations")
        self.assertFalse(task["enabled"])
        self.assertTrue(task["settings"]["avoid_gems"])
        self.assertEqual(task["settings"]["max_donations"], 30)
        self.assertEqual(task["settings"]["max_project_checks"], 5)
        self.assertEqual(task["interval_minutes"], 20.0)

    def test_next_run_uses_task_interval(self):
        task = {"interval_minutes": 2.5}
        self.assertEqual(next_run_after_finish(task, 100.0), 250.0)

    def test_next_fixed_utc_run_uses_noon_and_midnight(self):
        before_noon = datetime(2026, 7, 15, 11, 59, tzinfo=timezone.utc).timestamp()
        at_noon = datetime(2026, 7, 15, 12, 0, tzinfo=timezone.utc).timestamp()
        before_midnight = datetime(2026, 7, 15, 23, 59, tzinfo=timezone.utc).timestamp()
        at_midnight = datetime(2026, 7, 16, 0, 0, tzinfo=timezone.utc).timestamp()

        self.assertEqual(next_fixed_utc_run(before_noon, [0, 12]), at_noon)
        self.assertEqual(next_fixed_utc_run(at_noon, [0, 12]), at_midnight)
        self.assertEqual(next_fixed_utc_run(before_midnight, [0, 12]), at_midnight)

    def test_radar_next_run_uses_fixed_game_reset(self):
        task = next(task for task in default_routine_tasks() if task["id"] == "radar")
        now = datetime(2026, 7, 15, 12, 30, tzinfo=timezone.utc).timestamp()
        expected = datetime(2026, 7, 16, 0, 0, tzinfo=timezone.utc).timestamp()
        self.assertEqual(next_run_after_finish(task, now), expected)

    def test_no_action_retry_is_bounded(self):
        self.assertEqual(no_action_retry_delay({"interval_minutes": 0.1}), 30.0)
        self.assertEqual(no_action_retry_delay({"interval_minutes": 2.0}), 120.0)
        self.assertEqual(no_action_retry_delay({"interval_minutes": 60.0}), 300.0)

    def test_system_template_can_be_disabled_for_one_routine(self):
        image = {"disabled_routine_ids": ["radar"]}
        self.assertFalse(image_is_allowed_for_routine(image, "radar"))
        self.assertTrue(image_is_allowed_for_routine(image, "oil"))

    def test_runtime_steps_block_unsafe_action_until_prerequisite(self):
        image = {"requires_runtime_steps": ["boost_category"]}
        self.assertFalse(runtime_step_is_ready(image, {"open_bag"}))
        self.assertTrue(runtime_step_is_ready(image, {"open_bag", "boost_category"}))

    def test_runtime_step_any_mode_accepts_selected_boost(self):
        image = {
            "requires_runtime_steps": ["boost_8h", "boost_24h"],
            "runtime_step_mode": "any",
        }
        self.assertFalse(runtime_step_is_ready(image, {"boost_category"}))
        self.assertTrue(runtime_step_is_ready(image, {"boost_24h"}))

    def test_completed_runtime_step_is_not_scanned_again(self):
        image = {"runtime_step": "world_search"}
        self.assertTrue(runtime_step_is_ready(image, set()))
        self.assertFalse(runtime_step_is_ready(image, {"world_search"}))

    def test_old_resource_profile_is_upgraded_to_strict_sequence(self):
        import uuid

        namespace = uuid.UUID("7d37a3a8-c963-49ef-9bf2-e3daecf85c48")
        region_uid = str(uuid.uuid5(namespace, "wood:region"))
        icon_uid = str(uuid.uuid5(namespace, "wood:resource_icon"))
        images = [{"uid": region_uid}, {"uid": icon_uid}]
        tasks = [{"id": "wood", "timeout_seconds": 10.0}]

        self.assertEqual(upgrade_resource_runtime_metadata(images, tasks), 2)
        self.assertEqual(images[0]["action"], "open_world_search")
        self.assertEqual(images[0]["runtime_step"], "world_search")
        self.assertEqual(images[1]["requires_runtime_steps"], ["world_search"])
        self.assertEqual(tasks[0]["timeout_seconds"], 30.0)

    def test_radar_finishes_on_empty_screen_instead_of_action_limit(self):
        import uuid

        namespace = uuid.UUID("7d37a3a8-c963-49ef-9bf2-e3daecf85c48")
        detail_uid = str(uuid.uuid5(namespace, "radar:open_supply"))
        marker_uid = str(uuid.uuid5(namespace, "radar:task_supply"))
        wait_uid = str(uuid.uuid5(namespace, "radar:wait_in_progress"))
        images = [
            {"uid": marker_uid},
            {"uid": detail_uid, "limit_key": "max_tasks"},
            {"uid": wait_uid},
        ]
        tasks = [{"id": "radar", "timeout_seconds": 15.0}]

        self.assertEqual(upgrade_radar_runtime_metadata(images, tasks), 3)
        self.assertLess(images[2]["routine_priority"], images[1]["routine_priority"])
        self.assertLess(images[1]["routine_priority"], images[0]["routine_priority"])
        self.assertNotIn("limit_key", images[1])
        self.assertTrue(images[0]["prevents_idle_completion"])
        self.assertEqual(tasks[0]["timeout_seconds"], 20.0)
        self.assertTrue(tasks[0]["complete_when_idle"])
        self.assertEqual(tasks[0]["idle_confirmations"], 3)


if __name__ == "__main__":
    unittest.main()
