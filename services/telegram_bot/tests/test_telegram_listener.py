import sys
import os
import unittest
from unittest.mock import patch, MagicMock

# Add parent directory to path so we can import the listener
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

if 'requests' not in sys.modules:
    try:
        import requests
    except ImportError:
        sys.modules['requests'] = MagicMock()

import telegram_listener

class TestTelegramListener(unittest.TestCase):
    
    @patch('telegram_listener.subprocess.run')
    @patch('telegram_listener.os.path.exists')
    @patch('telegram_listener.os.walk')
    @patch('telegram_listener.os.path.getsize')
    @patch('telegram_listener.requests.post')
    @patch('telegram_listener.requests.get')
    def test_status_parsing(self, mock_get, mock_post, mock_getsize, mock_walk, mock_exists, mock_run):
        # Mock environment variables
        os.environ['TELEGRAM_BOT_TOKEN'] = 'test_token'
        os.environ['TELEGRAM_CHAT_ID'] = '12345'
        
        # Mock the updates response to send a /status command
        mock_get.return_value.json.side_effect = [
            {
                "ok": True,
                "result": [
                    {
                        "update_id": 1,
                        "message": {
                            "chat": {"id": 12345},
                            "text": "/status"
                        }
                    }
                ]
            },
            # Return no more updates to let it loop and we'll break it
            KeyboardInterrupt()
        ]
        
        # Mock subprocess.run for ps aux (is_running) and ps -eo (downloads)
        def mock_subprocess_run(args, **kwargs):
            mock_proc = MagicMock()
            if 'aux' in args:
                mock_proc.stdout = "root 123 0.0 0.0 bash monitor_and_capture.sh\n"
            elif '-eo' in args:
                # Provide a non-truncated cmd with -o pointing to session dirs
                mock_proc.stdout = (
                    "05:00 yt-dlp --wait-for-video 60 -f best -o /opt/StreamVault/staging/session_1/chunk.mp4 https://youtube.com/watch?v=123\n"
                    "10:00 yt-dlp --wait-for-video 60 -f best -o /opt/StreamVault/staging/session_2/chunk.mp4 https://youtube.com/watch?v=456\n"
                )
            return mock_proc
            
        mock_run.side_effect = mock_subprocess_run
        
        # Mock file sizes
        mock_exists.return_value = True
        
        # When os.walk is called for session_1, return files summing to 100MB
        # When os.walk is called for session_2, return files summing to 50MB
        def mock_walk_impl(path):
            if 'session_1' in path:
                yield (path, [], ['chunk.mp4'])
            elif 'session_2' in path:
                yield (path, [], ['chunk.mp4', 'chunk2.part'])
            else:
                yield (path, [], [])
                
        mock_walk.side_effect = mock_walk_impl
        
        def mock_getsize_impl(path):
            if 'session_1' in path:
                return 100 * 1024 * 1024 # 100 MB
            elif 'session_2' in path:
                return 25 * 1024 * 1024 # 50 MB total for 2 files
            return 0
            
        mock_getsize.side_effect = mock_getsize_impl
        
        try:
            telegram_listener.main()
        except KeyboardInterrupt:
            pass
                
        # Verify the message sent to Telegram
        mock_post.assert_called_once()
        sent_args = mock_post.call_args[1]['data']
        text = sent_args['text']
        
        self.assertIn("Monitor is ACTIVE", text)
        
        # Verify sizes are calculated correctly per session
        self.assertIn("100.0 MB", text)
        self.assertIn("50.0 MB", text)
        
        # Verify targets
        self.assertIn("https://youtube.com/watch?v=123", text)
        self.assertIn("https://youtube.com/watch?v=456", text)

    @patch('telegram_listener.subprocess.Popen')
    @patch('telegram_listener.subprocess.run')
    @patch('telegram_listener.requests.post')
    @patch('telegram_listener.requests.get')
    def test_update_command(self, mock_get, mock_post, mock_run, mock_popen):
        os.environ['TELEGRAM_BOT_TOKEN'] = 'test_token'
        os.environ['TELEGRAM_CHAT_ID'] = '12345'
        
        mock_get.return_value.json.side_effect = [
            {
                "ok": True,
                "result": [
                    {
                        "update_id": 1,
                        "message": {
                            "chat": {"id": 12345},
                            "text": "/update"
                        }
                    }
                ]
            },
            KeyboardInterrupt()
        ]
        
        try:
            telegram_listener.main()
        except KeyboardInterrupt:
            pass
                
        # Verify it sent the update message
        mock_post.assert_called_once()
        self.assertIn("Initiating Update", mock_post.call_args[1]['data']['text'])
        
        # Verify it ran git pull and systemctl restart
        mock_run.assert_called_once_with(["git", "pull"], cwd=str(telegram_listener.BASE_DIR), check=True, capture_output=True, text=True)
        mock_popen.assert_called_once_with(["bash", "-c", "sleep 2 && systemctl restart streamvault streamvault-bot"])

    @patch('telegram_listener.trigger_download')
    @patch('telegram_listener.requests.post')
    @patch('telegram_listener.requests.get')
    def test_brief_command(self, mock_get, mock_post, mock_trigger):
        os.environ['TELEGRAM_BOT_TOKEN'] = 'test_token'
        os.environ['TELEGRAM_CHAT_ID'] = '12345'
        
        mock_get.return_value.json.side_effect = [
            {
                "ok": True,
                "result": [
                    {
                        "update_id": 1,
                        "message": {
                            "chat": {"id": 12345},
                            "text": "/brief https://youtube.com/watch?v=abc123xyz"
                        }
                    }
                ]
            },
            KeyboardInterrupt()
        ]
        
        try:
            telegram_listener.main()
        except KeyboardInterrupt:
            pass
            
        mock_post.assert_called_once()
        self.assertIn("AI Brief Only", mock_post.call_args[1]['data']['text'])
        mock_trigger.assert_called_once_with("https://youtube.com/watch?v=abc123xyz", True)

if __name__ == '__main__':
    unittest.main()
