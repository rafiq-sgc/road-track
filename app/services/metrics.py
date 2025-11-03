"""Performance metrics tracking."""
import time
from collections import deque
from typing import Dict
from threading import Lock


class MetricsCollector:
    """Collects and reports performance metrics."""
    
    def __init__(self):
        self.lock = Lock()
        self.frame_times = deque(maxlen=60)
        self.detection_counts = deque(maxlen=100)
        self.violation_counts: Dict[str, int] = {}
        self.start_time = time.time()
        
    def record_frame(self, process_time: float, detections: int):
        """Record a frame processing time and detection count."""
        with self.lock:
            self.frame_times.append(process_time)
            self.detection_counts.append(detections)
    
    def record_violation(self, kind: str):
        """Record a violation occurrence."""
        with self.lock:
            self.violation_counts[kind] = self.violation_counts.get(kind, 0) + 1
    
    def get_metrics(self) -> Dict:
        """Get current metrics snapshot."""
        with self.lock:
            if not self.frame_times:
                return {
                    "fps": 0.0,
                    "avg_detections": 0.0,
                    "violations": dict(self.violation_counts),
                    "uptime_seconds": int(time.time() - self.start_time)
                }
            
            avg_time = sum(self.frame_times) / len(self.frame_times)
            fps = 1.0 / avg_time if avg_time > 0 else 0.0
            avg_det = sum(self.detection_counts) / len(self.detection_counts) if self.detection_counts else 0
            
            return {
                "fps": round(fps, 2),
                "avg_process_time_ms": round(avg_time * 1000, 1),
                "avg_detections": round(avg_det, 1),
                "violations": dict(self.violation_counts),
                "uptime_seconds": int(time.time() - self.start_time)
            }
    
    def reset_violations(self):
        """Reset violation counters."""
        with self.lock:
            self.violation_counts.clear()

