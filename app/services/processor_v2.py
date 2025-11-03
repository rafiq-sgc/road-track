"""Enhanced video processor with debouncing, evidence saving, metrics, and robust auto-learning."""
import cv2
import numpy as np
import threading
import time
import logging
from collections import deque
from typing import Deque, Dict, List, Optional, Tuple, Union
from datetime import datetime

from ultralytics import YOLO
import supervision as sv

from app.utils.roi import ROIConfig, load_roi_config, denormalize_points
from app.services.evidence import EvidenceManager
from app.services.metrics import MetricsCollector

logger = logging.getLogger(__name__)

ALLOWED_CLASS_NAMES = {"person", "car", "motorcycle", "bus", "truck", "bicycle"}
VEHICLE_CLASS_NAMES = {"car", "bus", "truck", "motorcycle", "bicycle"}


class VideoProcessorV2:
    """Enhanced video processor with production-ready features."""
    
    def __init__(self):
        self.model: Optional[YOLO] = None
        self.tracker = sv.ByteTrack()
        self.box_annotator = sv.BoxAnnotator()
        self.label_annotator = sv.LabelAnnotator()
        
        self.signal_state: str = "green"
        self.alerts: Deque[Dict] = deque(maxlen=200)
        
        # Alert debouncing (match with violation highlight duration)
        self.alert_cooldown: Dict[Tuple[int, str], float] = {}
        self.cooldown_seconds = 5.0
        self.violation_highlight_seconds = 5.0  # How long red circle shows
        
        # Evidence and metrics
        self.evidence_manager = EvidenceManager()
        self.metrics = MetricsCollector()
        
        # Video capture
        self.cap: Optional[cv2.VideoCapture] = None
        self.frame_lock = threading.Lock()
        self.running = False
        self.thread: Optional[threading.Thread] = None
        self.last_frame: Optional[np.ndarray] = None
        
        # ROI and calibration
        self.roi: ROIConfig = load_roi_config()
        self.m_per_px: Optional[float] = None
        self.track_last: Dict[int, Tuple[float, Tuple[float, float]]] = {}
        
        # Wrong-way detection
        self.track_history: Dict[int, Deque[Tuple[float, Tuple[float, float]]]] = {}
        self.wrong_way_counter: Dict[int, int] = {}
        self.lane_dirs_unit: List[Tuple[float, float]] = []
        self.lane_dir_samples: List[Deque] = []
        self.auto_learning_complete = False
        
        # Violation marking
        self.violation_until: Dict[int, float] = {}
        self.focus_track_id: Optional[int] = None
        self.focus_until: float = 0.0
        
        # Optional models
        self.helmet_model: Optional[YOLO] = None
        if self.roi.helmet_model_path:
            try:
                self.helmet_model = YOLO(self.roi.helmet_model_path)
                logger.info(f"Loaded helmet model from {self.roi.helmet_model_path}")
            except Exception as e:
                logger.warning(f"Failed to load helmet model: {e}")
        
        self.plate_model: Optional[YOLO] = None
        if self.roi.plate_model_path:
            try:
                self.plate_model = YOLO(self.roi.plate_model_path)
                logger.info(f"Loaded plate model from {self.roi.plate_model_path}")
            except Exception as e:
                logger.warning(f"Failed to load plate model: {e}")
        
        self.ocr_reader = None
    
    def start(self, source: Union[int, str]) -> bool:
        """Start processing video from source."""
        try:
            self.stop()
            self.cap = cv2.VideoCapture(source)
            if not self.cap.isOpened():
                logger.error(f"Failed to open video source: {source}")
                self.cap = None
                return False
            
            if self.model is None:
                logger.info("Loading YOLOv8n model...")
                self.model = YOLO("yolov8n.pt")
                logger.info("Model loaded successfully")
            
            self.running = True
            self.thread = threading.Thread(target=self._run_loop, daemon=True)
            self.thread.start()
            logger.info(f"Started processing from {source}")
            return True
            
        except Exception as e:
            logger.error(f"Error starting processor: {e}")
            return False
    
    def stop(self):
        """Stop processing."""
        self.running = False
        if self.thread:
            self.thread.join(timeout=2.0)
            self.thread = None
        if self.cap:
            try:
                self.cap.release()
            except Exception:
                pass
            self.cap = None
        
        # Clear state
        self.track_last.clear()
        self.track_history.clear()
        self.wrong_way_counter.clear()
        self.violation_until.clear()
        self.alert_cooldown.clear()
        self.focus_track_id = None
        self.focus_until = 0.0
        self.auto_learning_complete = False
        logger.info("Stopped processing")
    
    def set_signal_state(self, state: str):
        """Set traffic signal state."""
        state = state.lower().strip()
        if state not in {"red", "green"}:
            return
        self.signal_state = state
        logger.info(f"Signal state changed to {state}")
    
    def get_signal_state(self) -> str:
        return self.signal_state
    
    def get_recent_alerts(self) -> Dict:
        return {"signal": self.signal_state, "alerts": list(self.alerts)}
    
    def get_metrics(self) -> Dict:
        """Get performance metrics."""
        return self.metrics.get_metrics()
    
    def _should_emit_alert(self, track_id: int, kind: str) -> bool:
        """Check if alert should be emitted (debouncing)."""
        now = time.time()
        key = (track_id, kind)
        last_time = self.alert_cooldown.get(key, 0)
        
        if now - last_time < self.cooldown_seconds:
            return False
        
        self.alert_cooldown[key] = now
        return True
    
    def _emit_alert(self, kind: str, track_id: int, info: Dict, frame: Optional[np.ndarray] = None, bbox: Optional[Tuple] = None, vehicle_class: str = "obj"):
        """Emit alert with debouncing and evidence saving."""
        if not self._should_emit_alert(track_id, kind):
            return
        
        now = time.time()
        alert = {
            "ts": now,
            "type": kind,
            "track_id": track_id,
            "info": info,
            "vehicle_class": vehicle_class,
        }
        
        # Save evidence for violations (not plate_read)
        if kind != "plate_read" and frame is not None and bbox is not None:
            evidence_id = self.evidence_manager.save_violation(
                kind, track_id, frame, bbox, info
            )
            if evidence_id:
                alert["evidence_id"] = evidence_id
        
        self.alerts.appendleft(alert)
        self.metrics.record_violation(kind)
        
        # Set highlight (match with panel display time)
        if kind != "plate_read" and track_id >= 0:
            self.violation_until[track_id] = now + self.violation_highlight_seconds
        
        # Focus on wrong-way
        if kind == "wrong_way" and track_id >= 0:
            self.focus_track_id = track_id
            self.focus_until = now + 5.0
        
        logger.info(f"Alert: {kind} by track {track_id} ({vehicle_class})")
    
    def _ensure_ocr(self):
        """Lazy load OCR reader."""
        if self.ocr_reader is None:
            try:
                import easyocr
                self.ocr_reader = easyocr.Reader(['en'], gpu=False)
                logger.info("OCR reader initialized")
            except Exception as e:
                logger.warning(f"Failed to initialize OCR: {e}")
    
    def _try_read_plate(self, frame: np.ndarray, bbox: Tuple[int, int, int, int]) -> Optional[str]:
        """Attempt to read license plate from vehicle crop."""
        if not self.plate_model:
            return None
        
        try:
            x1, y1, x2, y2 = bbox
            h, w = frame.shape[:2]
            veh_crop = frame[max(0, y1):min(h, y2), max(0, x1):min(w, x2)]
            
            if veh_crop.size == 0:
                return None
            
            # Detect plate
            pres = self.plate_model(veh_crop, verbose=False)[0]
            if not pres.boxes or len(pres.boxes) == 0:
                return None
            
            # Get best plate
            idx = int(np.argmax(pres.boxes.conf.cpu().numpy()))
            px1, py1, px2, py2 = map(int, pres.boxes.xyxy.cpu().numpy()[idx])
            plate_crop = veh_crop[max(0, py1):min(veh_crop.shape[0], py2), 
                                  max(0, px1):min(veh_crop.shape[1], px2)]
            
            if plate_crop.size == 0:
                return None
            
            # OCR
            self._ensure_ocr()
            if not self.ocr_reader:
                return None
            
            ocr = self.ocr_reader.readtext(plate_crop)
            if ocr:
                text = sorted(ocr, key=lambda r: -r[2])[0][1]
                return text.strip() if text else None
        except Exception as e:
            logger.debug(f"Plate read failed: {e}")
        
        return None
    
    def _run_loop(self):
        """Main processing loop."""
        assert self.cap is not None
        
        stop_line_px = None
        lane_polys_px: List[List[Tuple[int, int]]] = []
        lane_contours: List[np.ndarray] = []
        fps = self.cap.get(cv2.CAP_PROP_FPS) or 30
        frame_idx = 0
        
        logger.info("Processing loop started")
        
        while self.running and self.cap and self.cap.isOpened():
            frame_start = time.time()
            
            ret, frame = self.cap.read()
            if not ret:
                logger.warning("Failed to read frame, stopping")
                break
            
            frame_idx += 1
            h, w = frame.shape[:2]
            
            # Initialize ROIs once
            if stop_line_px is None:
                stop_line_px = denormalize_points(self.roi.stop_line, w, h) if self.roi.stop_line else None
                lane_polys_px = [denormalize_points(poly, w, h) for poly in self.roi.lanes]
                lane_contours = [np.array(poly, dtype=np.int32).reshape((-1, 1, 2)) for poly in lane_polys_px]
                
                # Speed calibration
                if self.roi.speed_calib_points and self.roi.speed_calib_distance_m:
                    (ax, ay), (bx, by) = self.roi.speed_calib_points
                    p1 = (ax * w, ay * h)
                    p2 = (bx * w, by * h)
                    px_dist = ((p1[0]-p2[0])**2 + (p1[1]-p2[1])**2) ** 0.5
                    if px_dist > 1e-3:
                        self.m_per_px = float(self.roi.speed_calib_distance_m) / px_dist
                        logger.info(f"Speed calibration: {self.m_per_px:.4f} m/px")
                
                # Lane directions setup
                if self.roi.lane_directions:
                    # Static directions
                    for d in self.roi.lane_directions:
                        (x1, y1), (x2, y2) = (int(d[0][0] * w), int(d[0][1] * h)), (int(d[1][0] * w), int(d[1][1] * h))
                        vx, vy = (x2 - x1), (y2 - y1)
                        norm = (vx*vx + vy*vy) ** 0.5
                        if norm > 1e-6:
                            self.lane_dirs_unit.append((vx / norm, vy / norm))
                        else:
                            self.lane_dirs_unit.append((0.0, 0.0))
                    logger.info(f"Using {len(self.lane_dirs_unit)} static lane directions")
                elif self.roi.auto_lane_direction:
                    # Auto learning
                    self.lane_dir_samples = [deque(maxlen=600) for _ in lane_contours]
                    self.lane_dirs_unit = [(0.0, 0.0) for _ in lane_contours]
                    logger.info(f"Auto lane direction learning enabled for {len(lane_contours)} lanes")
            
            # Inference
            results = self.model(frame, verbose=False)[0]
            boxes = results.boxes.xyxy.cpu().numpy() if results.boxes is not None else np.zeros((0, 4))
            conf = results.boxes.conf.cpu().numpy() if results.boxes is not None else np.zeros((0,))
            cls = results.boxes.cls.cpu().numpy().astype(int) if results.boxes is not None else np.zeros((0,), dtype=int)
            class_names = [results.names[int(c)] for c in cls]
            
            mask = np.array([name in ALLOWED_CLASS_NAMES for name in class_names], dtype=bool)
            if mask.size == 0:
                boxes = np.zeros((0, 4))
                conf = np.zeros((0,))
                cls = np.zeros((0,), dtype=int)
            else:
                boxes = boxes[mask]
                conf = conf[mask]
                cls = cls[mask]
            
            detections = sv.Detections(xyxy=boxes, confidence=conf, class_id=cls)
            detections.tracker_id = None
            tracked = self.tracker.update_with_detections(detections)
            
            # Draw ROIs
            if stop_line_px is not None:
                pt1, pt2 = stop_line_px
                cv2.line(frame, pt1, pt2, (0, 0, 255), 3)
            for cnt in lane_contours:
                cv2.polylines(frame, [cnt], isClosed=True, color=(0, 255, 0), thickness=2)
            
            # Auto learning indicator
            if self.roi.auto_lane_direction and not self.auto_learning_complete:
                warmup_progress = min(100, int(100 * frame_idx / self.roi.auto_lane_warmup_frames))
                cv2.putText(frame, f"Learning: {warmup_progress}%", (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 0), 2)
            
            now = time.time()
            
            # Process each tracked object
            for i in range(len(tracked)):
                xyxy = tracked.xyxy[i]
                track_id = int(tracked.tracker_id[i]) if tracked.tracker_id is not None else -1
                cid = int(tracked.class_id[i]) if tracked.class_id is not None else -1
                name = results.names.get(cid, "obj")
                
                cx = float((xyxy[0] + xyxy[2]) / 2)
                cy = float((xyxy[1] + xyxy[3]) / 2)
                bbox_tuple = tuple(map(int, xyxy))
                
                # Try to read plate for vehicles (on first detection)
                plate_number = None
                if name in VEHICLE_CLASS_NAMES and track_id not in self.track_last:
                    plate_number = self._try_read_plate(frame, bbox_tuple)
                    if plate_number:
                        logger.info(f"Plate read for track {track_id}: {plate_number}")
                
                # Red-light violation
                if self.signal_state == "red" and stop_line_px is not None:
                    p = np.array([int(cx), int(cy)], dtype=np.int32)
                    if _point_crossed_line(p, stop_line_px):
                        info = {"cx": int(cx), "cy": int(cy)}
                        if plate_number:
                            info["plate"] = plate_number
                        self._emit_alert("red_light_violation", track_id, info, frame, bbox_tuple, name)
                        cv2.putText(frame, "RED LIGHT", (int(cx), max(0, int(cy) - 12)), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)
                
                # Lane containment + wrong-way
                lane_index = -1
                for idx, cnt in enumerate(lane_contours):
                    if cv2.pointPolygonTest(cnt, (cx, cy), False) >= 0:
                        lane_index = idx
                        break
                
                if lane_index == -1:
                    self.wrong_way_counter[track_id] = 0
                else:
                    # Maintain track history
                    hist = self.track_history.get(track_id)
                    if hist is None:
                        hist = deque(maxlen=12)
                        self.track_history[track_id] = hist
                    hist.append((now, (cx, cy)))
                    
                    # Compute velocity
                    if len(hist) >= 4:
                        t0, (x0, y0) = hist[0]
                        tn, (xn, yn) = hist[-1]
                        dt = tn - t0
                        if dt > 0.1:
                            vx = (xn - x0) / dt
                            vy = (yn - y0) / dt
                            speed_pxps = (vx*vx + vy*vy) ** 0.5
                            
                            # Auto lane direction sampling (vehicles only for robustness)
                            if (self.roi.auto_lane_direction and 
                                len(self.roi.lane_directions) == 0 and
                                name in VEHICLE_CLASS_NAMES and
                                speed_pxps >= 30.0 and
                                lane_index < len(self.lane_dir_samples)):
                                mag = (vx*vx + vy*vy) ** 0.5
                                if mag > 1e-6:
                                    self.lane_dir_samples[lane_index].append((vx/mag, vy/mag))
                            
                            # Wrong-way check
                            if lane_index < len(self.lane_dirs_unit):
                                dx, dy = self.lane_dirs_unit[lane_index]
                                dot = vx * dx + vy * dy
                                speed_min = 30.0
                                
                                if speed_pxps >= speed_min and dot < -0.5 * speed_pxps:
                                    self.wrong_way_counter[track_id] = self.wrong_way_counter.get(track_id, 0) + 1
                                else:
                                    self.wrong_way_counter[track_id] = 0
                                
                                if self.wrong_way_counter.get(track_id, 0) >= 10:
                                    info = {"lane": lane_index, "speed_pxps": round(speed_pxps, 1)}
                                    if plate_number:
                                        info["plate"] = plate_number
                                    self._emit_alert("wrong_way", track_id, info, frame, bbox_tuple, name)
                                    cv2.putText(frame, "WRONG WAY", (int(cx), max(0, int(cy) - 44)), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
                                    x_prev = int(xn - vx * 0.2)
                                    y_prev = int(yn - vy * 0.2)
                                    cv2.arrowedLine(frame, (x_prev, y_prev), (int(xn), int(yn)), (0, 0, 255), 2, tipLength=0.4)
                
                # Lane violation (outside all lanes)
                if lane_contours and lane_index == -1:
                    inside_any = any(cv2.pointPolygonTest(cnt, (cx, cy), False) >= 0 for cnt in lane_contours)
                    if not inside_any:
                        info = {"cx": int(cx), "cy": int(cy)}
                        if plate_number:
                            info["plate"] = plate_number
                        self._emit_alert("lane_violation", track_id, info, frame, bbox_tuple, name)
                        cv2.putText(frame, "LANE VIOLATION", (int(cx), min(h - 4, int(cy) + 16)), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 165, 255), 2)
                
                # Speed check
                if self.m_per_px and self.roi.speed_limit_kmh:
                    prev = self.track_last.get(track_id)
                    if prev:
                        prev_t, (px, py) = prev
                        dt = now - prev_t
                        if dt > 0.05:
                            dp = ((cx - px)**2 + (cy - py)**2) ** 0.5
                            kmh = (dp * self.m_per_px / dt) * 3.6
                            if kmh > self.roi.speed_limit_kmh:
                                info = {"speed_kmh": round(kmh, 1)}
                                if plate_number:
                                    info["plate"] = plate_number
                                self._emit_alert("speeding", track_id, info, frame, bbox_tuple, name)
                                cv2.putText(frame, f"SPEED {kmh:.0f}", (int(cx), max(0, int(cy) - 28)), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 0, 0), 2)
                    self.track_last[track_id] = (now, (cx, cy))
                
                # Helmet check (optional)
                if self.helmet_model and name in {"motorcycle", "bicycle"} and (frame_idx % 5 == 0):
                    x1, y1, x2, y2 = map(int, xyxy)
                    head_crop = frame[max(0, y1):int(y1 + (y2-y1)*0.4), max(0, x1):min(w, x2)]
                    if head_crop.size > 0:
                        try:
                            hres = self.helmet_model(head_crop, verbose=False)[0]
                            names_dict = hres.names
                            labels = [names_dict[int(c)] for c in (hres.boxes.cls.cpu().numpy().astype(int) if hres.boxes else [])]
                            if any("no-helmet" in l.lower() or "no_helmet" in l.lower() for l in labels):
                                info = {}
                                if plate_number:
                                    info["plate"] = plate_number
                                self._emit_alert("no_helmet", track_id, info, frame, bbox_tuple, name)
                                cv2.putText(frame, "NO HELMET", (x1, max(0, y1 - 8)), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)
                        except Exception:
                            pass
                
                # Plate OCR (optional)
                if self.plate_model and name in VEHICLE_CLASS_NAMES and (frame_idx % 7 == 0):
                    x1, y1, x2, y2 = map(int, xyxy)
                    veh_crop = frame[max(0, y1):min(h, y2), max(0, x1):min(w, x2)]
                    if veh_crop.size > 0:
                        try:
                            pres = self.plate_model(veh_crop, verbose=False)[0]
                            if pres.boxes and len(pres.boxes) > 0:
                                idx = int(np.argmax(pres.boxes.conf.cpu().numpy()))
                                px1, py1, px2, py2 = map(int, pres.boxes.xyxy.cpu().numpy()[idx])
                                plate_crop = veh_crop[max(0, py1):min(veh_crop.shape[0], py2), max(0, px1):min(veh_crop.shape[1], px2)]
                                if plate_crop.size > 0:
                                    self._ensure_ocr()
                                    if self.ocr_reader:
                                        try:
                                            ocr = self.ocr_reader.readtext(plate_crop)
                                            if ocr:
                                                text = sorted(ocr, key=lambda r: -r[2])[0][1]
                                                if text:
                                                    self._emit_alert("plate_read", track_id, {"text": text})
                                                    cv2.putText(frame, text, (x1, min(h - 4, y2 + 18)), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (50, 200, 50), 2)
                                        except Exception:
                                            pass
                        except Exception:
                            pass
            
            # Auto lane direction update (median-based for robustness)
            if (self.roi.auto_lane_direction and 
                len(self.roi.lane_directions) == 0 and 
                frame_idx % 60 == 0 and 
                frame_idx >= self.roi.auto_lane_warmup_frames):
                
                for idx in range(len(lane_contours)):
                    if idx < len(self.lane_dir_samples) and len(self.lane_dir_samples[idx]) >= 20:
                        samples = np.array(self.lane_dir_samples[idx], dtype=np.float32)
                        # Use median for robustness
                        median_dir = np.median(samples, axis=0)
                        norm = np.linalg.norm(median_dir) + 1e-6
                        self.lane_dirs_unit[idx] = (float(median_dir[0]/norm), float(median_dir[1]/norm))
                
                if not self.auto_learning_complete:
                    self.auto_learning_complete = True
                    logger.info("Auto lane direction learning complete")
            
            # Annotate boxes
            labels = []
            for i in range(len(tracked)):
                cid = int(tracked.class_id[i]) if tracked.class_id is not None else -1
                conf_i = float(conf[i]) if i < len(conf) else 0.0
                labels.append(f"{results.names.get(cid, 'obj')} {conf_i:.2f}")
            
            frame = self.box_annotator.annotate(scene=frame, detections=tracked)
            frame = self.label_annotator.annotate(scene=frame, detections=tracked, labels=labels)
            
            # Overlay VIOLATED on recent violators with red circle
            now2 = time.time()
            for i in range(len(tracked)):
                if tracked.tracker_id is None:
                    continue
                tid = int(tracked.tracker_id[i])
                if self.violation_until.get(tid, 0) > now2:
                    x1, y1, x2, y2 = map(int, tracked.xyxy[i])
                    # Draw red circle around violator
                    center_x = (x1 + x2) // 2
                    center_y = (y1 + y2) // 2
                    radius = max(abs(x2 - x1), abs(y2 - y1)) // 2 + 20
                    cv2.circle(frame, (center_x, center_y), radius, (0, 0, 255), 4)
                    # Red rectangle
                    cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 0, 255), 3)
                    # "VIOLATED" label
                    cv2.putText(frame, "VIOLATED", (x1, max(0, y1 - 6)), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2)
            
            # Enhanced zoom + focus for violated objects (Picture-in-Picture)
            if self.focus_track_id and self.focus_until > now2 and tracked.tracker_id is not None:
                focus_bbox = None
                focus_class = "obj"
                for i in range(len(tracked)):
                    if int(tracked.tracker_id[i]) == self.focus_track_id:
                        focus_bbox = tracked.xyxy[i]
                        cid = int(tracked.class_id[i]) if tracked.class_id is not None else -1
                        focus_class = results.names.get(cid, "obj")
                        break
                
                if focus_bbox is not None:
                    x1, y1, x2, y2 = map(int, focus_bbox)
                    x1, y1 = max(0, x1), max(0, y1)
                    x2, y2 = min(w-1, x2), min(h-1, y2)
                    
                    # Dim background
                    overlay = np.zeros_like(frame)
                    overlay[:] = (30, 30, 30)
                    mask = np.ones((h, w), dtype=np.float32) * 0.6
                    mask[y1:y2, x1:x2] = 1.0
                    mask = cv2.GaussianBlur(mask, (21, 21), 0)
                    
                    for c in range(3):
                        frame[:, :, c] = (frame[:, :, c] * mask + overlay[:, :, c] * (1 - mask)).astype(np.uint8)
                    
                    # Extract violator crop and create zoomed PIP
                    crop = frame[y1:y2, x1:x2].copy()
                    if crop.size > 0:
                        # Zoom 3x
                        crop_h, crop_w = crop.shape[:2]
                        zoom_scale = 3.0
                        zoomed_w = min(int(crop_w * zoom_scale), w // 2)
                        zoomed_h = min(int(crop_h * zoom_scale), h // 2)
                        
                        if zoomed_w > 0 and zoomed_h > 0:
                            zoomed = cv2.resize(crop, (zoomed_w, zoomed_h), interpolation=cv2.INTER_LINEAR)
                            
                            # Add thick red border to zoomed crop
                            border_thickness = 8
                            zoomed_bordered = cv2.copyMakeBorder(
                                zoomed,
                                border_thickness, border_thickness, border_thickness, border_thickness,
                                cv2.BORDER_CONSTANT,
                                value=(0, 0, 255)
                            )
                            
                            # Position PIP in top-right corner
                            pip_h, pip_w = zoomed_bordered.shape[:2]
                            pip_x = w - pip_w - 20
                            pip_y = 60
                            
                            # Ensure PIP fits in frame
                            if pip_x > 0 and pip_y + pip_h < h:
                                # Add semi-transparent background for PIP
                                pip_bg = frame[pip_y:pip_y+pip_h, pip_x:pip_x+pip_w].copy()
                                alpha = 0.95
                                frame[pip_y:pip_y+pip_h, pip_x:pip_x+pip_w] = cv2.addWeighted(
                                    zoomed_bordered, alpha, pip_bg, 1-alpha, 0
                                )
                                
                                # Add text banner above PIP
                                banner_text = f"VIOLATOR #{self.focus_track_id} - {focus_class.upper()}"
                                text_size = cv2.getTextSize(banner_text, cv2.FONT_HERSHEY_SIMPLEX, 0.7, 2)[0]
                                text_x = pip_x + (pip_w - text_size[0]) // 2
                                text_y = pip_y - 10
                                
                                # Text background
                                cv2.rectangle(frame, 
                                            (text_x - 8, text_y - text_size[1] - 6),
                                            (text_x + text_size[0] + 8, text_y + 6),
                                            (0, 0, 255), -1)
                                cv2.putText(frame, banner_text, (text_x, text_y), 
                                          cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
                    
                    # Red border on original location
                    cv2.rectangle(frame, (x1, y1), (x2, y2), (0, 0, 255), 5)
                    cv2.putText(frame, "FOCUS", (x1, max(0, y1 - 24)), cv2.FONT_HERSHEY_SIMPLEX, 0.8, (0, 0, 255), 2)
            
            # Metrics
            frame_time = time.time() - frame_start
            self.metrics.record_frame(frame_time, len(tracked))
            
            # FPS overlay
            metrics = self.metrics.get_metrics()
            cv2.putText(frame, f"FPS: {metrics['fps']:.1f}", (w - 150, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
            
            with self.frame_lock:
                self.last_frame = frame.copy()
            
            time.sleep(max(0.0, 1.0 / fps / 4))
        
        self.running = False
        logger.info("Processing loop ended")
    
    def mjpeg_generator(self):
        """Generate MJPEG stream."""
        boundary = b"--frame"
        while True:
            if not self.running and self.last_frame is None:
                time.sleep(0.1)
                continue
            
            with self.frame_lock:
                frame = None if self.last_frame is None else self.last_frame.copy()
            
            if frame is None:
                time.sleep(0.03)
                continue
            
            ret, buf = cv2.imencode('.jpg', frame, [cv2.IMWRITE_JPEG_QUALITY, 80])
            if not ret:
                continue
            
            jpg = buf.tobytes()
            yield boundary + b"\r\n" + b"Content-Type: image/jpeg\r\n\r\n" + jpg + b"\r\n"


def _point_crossed_line(p: np.ndarray, line: Tuple[Tuple[int, int], Tuple[int, int]]) -> bool:
    """Check if point is near line segment."""
    (x1, y1), (x2, y2) = line
    px, py = p
    vx, vy = x2 - x1, y2 - y1
    wx, wy = px - x1, py - y1
    c1 = vx * wx + vy * vy
    if c1 <= 0:
        return (px - x1)**2 + (py - y1)**2 < 25
    c2 = vx * vx + vy * vy
    if c2 <= c1:
        return (px - x2)**2 + (py - y2)**2 < 25
    b = c1 / c2
    xp, yp = x1 + b * vx, y1 + b * vy
    return (px - xp)**2 + (py - yp)**2 < 25

