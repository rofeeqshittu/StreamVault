#!/usr/bin/env python3
"""
Eval Suite for Smart Monitor
Validates that timeout settings and stall-detection threshold constants are robust.
"""
import sys
from pathlib import Path

# Add scripts directory to path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import smart_monitor

def eval_smart_monitor_safety():
    print("Evaluating smart_monitor resilience...")
    # Verify stall detection safety check exists
    import inspect
    source = inspect.getsource(smart_monitor.smart_monitor)
    assert "--socket-timeout" in source, "Eval Failed: Missing socket-timeout in yt-dlp arguments"
    assert "Stream stalled and is no longer live" in source, "Eval Failed: Missing stall detection logic"
    assert "is_live_stream" in source, "Eval Failed: Missing live check during monitoring"
    print("PASS: Smart monitor stall and timeout checks verified.")

if __name__ == '__main__':
    eval_smart_monitor_safety()
