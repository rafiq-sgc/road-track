"""Evidence management for saving violation snapshots and metadata."""
import os
import json
import cv2
import numpy as np
from datetime import datetime
from pathlib import Path
from typing import Dict, Optional, Tuple
import logging

logger = logging.getLogger(__name__)


class EvidenceManager:
    """Manages saving and retrieving violation evidence."""
    
    def __init__(self, base_dir: str = "violations"):
        self.base_dir = Path(base_dir)
        self.base_dir.mkdir(parents=True, exist_ok=True)
        (self.base_dir / "crops").mkdir(exist_ok=True)
        (self.base_dir / "fullframes").mkdir(exist_ok=True)
        (self.base_dir / "metadata").mkdir(exist_ok=True)
        
    def save_violation(
        self,
        kind: str,
        track_id: int,
        frame: np.ndarray,
        bbox: Tuple[int, int, int, int],
        metadata: Dict
    ) -> Optional[str]:
        """Save violation evidence: crop, full frame, and metadata."""
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")[:-3]
            filename = f"{kind}_{track_id}_{timestamp}"
            
            # Save crop
            x1, y1, x2, y2 = bbox
            crop = frame[max(0, y1):min(frame.shape[0], y2), 
                        max(0, x1):min(frame.shape[1], x2)]
            if crop.size > 0:
                crop_path = self.base_dir / "crops" / f"{filename}.jpg"
                cv2.imwrite(str(crop_path), crop, [cv2.IMWRITE_JPEG_QUALITY, 90])
            
            # Save full frame (resized for storage)
            h, w = frame.shape[:2]
            scale = min(1.0, 1280 / w)
            if scale < 1.0:
                frame_resized = cv2.resize(frame, (int(w * scale), int(h * scale)))
            else:
                frame_resized = frame
            frame_path = self.base_dir / "fullframes" / f"{filename}.jpg"
            cv2.imwrite(str(frame_path), frame_resized, [cv2.IMWRITE_JPEG_QUALITY, 85])
            
            # Save metadata
            meta = {
                "timestamp": timestamp,
                "violation_type": kind,
                "track_id": track_id,
                "bbox": [int(x1), int(y1), int(x2), int(y2)],
                "crop_path": str(crop_path.relative_to(self.base_dir)),
                "frame_path": str(frame_path.relative_to(self.base_dir)),
                **metadata
            }
            meta_path = self.base_dir / "metadata" / f"{filename}.json"
            with open(meta_path, 'w') as f:
                json.dump(meta, f, indent=2)
            
            logger.info(f"Saved evidence for {kind} violation by track {track_id}")
            return filename
            
        except Exception as e:
            logger.error(f"Failed to save evidence: {e}")
            return None
    
    def get_recent_violations(self, limit: int = 50):
        """Get recent violations with metadata."""
        meta_dir = self.base_dir / "metadata"
        files = sorted(meta_dir.glob("*.json"), key=os.path.getmtime, reverse=True)
        
        violations = []
        for f in files[:limit]:
            try:
                with open(f, 'r') as fp:
                    violations.append(json.load(fp))
            except Exception as e:
                logger.warning(f"Failed to read {f}: {e}")
        return violations

