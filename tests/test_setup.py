import json
import os
import sys
import tempfile
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "scripts"))
import setup_environment as setup  # noqa: E402


class FindToolTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)

    def make_file(self, name):
        path = os.path.join(self.temp.name, name)
        with open(path, "w", encoding="utf-8") as handle:
            handle.write("")
        return path

    def test_argument_wins_over_environment_and_config(self):
        arg = self.make_file("arg-ffmpeg")
        env = self.make_file("env-ffmpeg")
        conf = self.make_file("conf-ffmpeg")
        path, source = setup.find_tool("ffmpeg", arg, {"FFMPEG_BINARY": env}, {"ffmpeg": conf})
        self.assertEqual((path, source), (os.path.abspath(arg), "argument"))

    def test_environment_then_config(self):
        env = self.make_file("env-ffmpeg")
        conf = self.make_file("conf-ffmpeg")
        self.assertEqual(setup.find_tool("ffmpeg", None, {"FFMPEG_BINARY": env}, {"ffmpeg": conf})[1], "environment")
        self.assertEqual(setup.find_tool("ffmpeg", None, {}, {"ffmpeg": conf})[1], "tools.local.json")

    def test_stale_path_is_reported_not_skipped(self):
        missing = os.path.join(self.temp.name, "gone", "ffprobe")
        path, source = setup.find_tool("ffprobe", None, {"FFPROBE_BINARY": missing}, {})
        self.assertIsNone(path)
        self.assertIn("missing file", source)

    def test_load_config_reads_utf8_json(self):
        config = os.path.join(self.temp.name, "tools.local.json")
        with open(config, "w", encoding="utf-8") as handle:
            json.dump({"ffmpeg": "C:/도구/ffmpeg.exe"}, handle, ensure_ascii=False)
        self.assertEqual(setup.load_config(config)["ffmpeg"], "C:/도구/ffmpeg.exe")

    def test_python_version_gate(self):
        self.assertTrue(setup.python_ok((3, 13, 0)))
        self.assertTrue(setup.python_ok((3, 12, 5)))
        self.assertFalse(setup.python_ok((3, 11, 9)))


if __name__ == "__main__":
    unittest.main()
