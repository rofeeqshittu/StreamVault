#!/usr/bin/env python3
import unittest
import sys
import os
from pathlib import Path
from unittest.mock import patch, MagicMock

# Add scripts directory to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import smart_monitor

class TestSmartMonitor(unittest.TestCase):
    @patch('smart_monitor.subprocess.run')
    def test_is_live_stream_true(self, mock_run):
        mock_proc = MagicMock()
        mock_proc.stdout = "true\n"
        mock_run.return_value = mock_proc
        self.assertTrue(smart_monitor.is_live_stream("https://youtube.com/live/123"))

    @patch('smart_monitor.subprocess.run')
    def test_is_live_stream_false(self, mock_run):
        mock_proc = MagicMock()
        mock_proc.stdout = "false\n"
        mock_run.return_value = mock_proc
        self.assertFalse(smart_monitor.is_live_stream("https://youtube.com/live/123"))

    @patch('smart_monitor.subprocess.run')
    def test_is_live_stream_exception(self, mock_run):
        mock_run.side_effect = Exception("Network timeout")
        self.assertFalse(smart_monitor.is_live_stream("https://youtube.com/live/123"))

    @patch('smart_monitor.shutil.move')
    @patch('smart_monitor.subprocess.run')
    def test_process_batch_single_chunk(self, mock_run, mock_move):
        mock_proc = MagicMock()
        mock_proc.returncode = 0
        mock_proc.stdout = "test_uploader_test_id"
        mock_run.return_value = mock_proc

        chunk = MagicMock(spec=Path)
        chunk.name = "chunk_001.mp4"
        chunk.exists.return_value = True

        session_dir = MagicMock(spec=Path)
        concat_file = MagicMock()
        session_dir.__truediv__.return_value = concat_file

        staging_dir = MagicMock(spec=Path)
        merged_file = MagicMock(spec=Path)
        staging_dir.__truediv__.return_value = merged_file

        smart_monitor.process_batch(
            chunks=[chunk],
            url="https://youtube.com/live/123",
            session_dir=session_dir,
            base_dir=Path("/opt/StreamVault"),
            staging_dir=staging_dir,
            skip_upload=True,
            part_num=1,
            session_id="123"
        )
        mock_move.assert_called_once()

if __name__ == '__main__':
    unittest.main()
