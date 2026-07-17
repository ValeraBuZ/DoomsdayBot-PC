import random
import unittest

from tools.run_random_program import MARCH_TASKS, _random_program, _task_failures_from_log


class RandomProgramTests(unittest.TestCase):
    def test_program_is_reproducible_and_has_one_march_task(self):
        first = _random_program(random.Random(12345), 4)
        second = _random_program(random.Random(12345), 4)

        self.assertEqual(first, second)
        self.assertEqual(len(first), 4)
        self.assertEqual(sum(task in MARCH_TASKS for task in first), 1)

    def test_report_detects_incomplete_tasks(self):
        log_text = "\n".join(
            (
                "Routine food timed out without actions; retrying",
                "Routine oil reached the squad screen without an available squad; retrying",
            )
        )

        self.assertEqual(_task_failures_from_log(log_text), ["food", "oil"])


if __name__ == "__main__":
    unittest.main()
