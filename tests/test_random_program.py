import random
import unittest

from tools.run_random_program import (
    MARCH_TASKS,
    _busy_tasks_from_log,
    _march_tasks_for_account,
    _random_program,
    _task_failures_from_log,
)


class RandomProgramTests(unittest.TestCase):
    def test_program_is_reproducible_and_has_one_march_task(self):
        first = _random_program(random.Random(12345), 4)
        second = _random_program(random.Random(12345), 4)

        self.assertEqual(first, second)
        self.assertEqual(len(first), 4)
        self.assertEqual(sum(task in MARCH_TASKS for task in first), 1)

    def test_zombie_hunt_is_only_generated_for_main_account(self):
        main_tasks = _march_tasks_for_account("Phoenix675")
        farm_tasks = _march_tasks_for_account("FocusFarm")

        self.assertIn("zombie_hunt", main_tasks)
        self.assertNotIn("zombie_hunt", farm_tasks)
        for seed in range(50):
            program = _random_program(random.Random(seed), 4, farm_tasks)
            self.assertNotIn("zombie_hunt", program)

    def test_report_detects_incomplete_tasks(self):
        log_text = "\n".join(
            (
                "Routine food timed out without actions; retrying",
                "Routine oil reached the squad screen without an available squad; retrying",
                "Routine train_shooters is temporarily unavailable (max_queue_checks); retrying",
                "Routine research is temporarily unavailable (max_lab_checks); retrying",
                "Routine radar is temporarily unavailable (не удалось вернуться из постороннего окна); retrying",
            )
        )

        self.assertEqual(_task_failures_from_log(log_text), ["food", "radar"])
        self.assertEqual(
            _busy_tasks_from_log(log_text),
            ["oil", "research", "train_shooters"],
        )


if __name__ == "__main__":
    unittest.main()
