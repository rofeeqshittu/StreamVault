import unittest
import sys
from pathlib import Path

# Add parent dir to path to import listener
sys.path.append(str(Path(__file__).resolve().parent.parent))
from telegram_listener import extract_url

class TestTelegramListener(unittest.TestCase):
    def test_extract_url_clean(self):
        self.assertEqual(extract_url("https://youtube.com/watch?v=123"), "https://youtube.com/watch?v=123")
        
    def test_extract_url_with_text(self):
        self.assertEqual(extract_url("Hey bot, download this: https://youtu.be/abc please"), "https://youtu.be/abc")
        
    def test_no_url(self):
        self.assertIsNone(extract_url("Hello there"))

if __name__ == '__main__':
    unittest.main()
