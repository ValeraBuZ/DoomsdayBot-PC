import unittest

from buzzbot_app import should_autostart_routines


class CommandLineTests(unittest.TestCase):
    def test_autostart_flag_is_case_insensitive(self):
        self.assertTrue(should_autostart_routines(["--AUTOSTART"]))

    def test_other_arguments_do_not_enable_autostart(self):
        self.assertFalse(should_autostart_routines(["--portable"]))


if __name__ == "__main__":
    unittest.main()
