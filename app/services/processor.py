import cv2
import numpy as np
import threading
import time
from collections import deque
from typing import Deque, Dict, List, Optional, Tuple, Union

from ultralytics import YOLO
import supervision as sv

from app.utils.roi import ROIConfig, load_roi_config, denormalize_points


ALLOWED_CLASS_NAMES = {"person", "car", "motorcycle", "bus", "truck", "bicycle"}
VEHICLE_CLASS_NAMES = {"car", "bus", "truck", "motorcycle", "bicycle"}


class VideoProcessor:
    def __init__(self) -> None:
        self.model: Optional[YOLO] = None
        self.tracker = sv.ByteTrack()
        self.box_annotator = sv.BoxAnnotator()
        self.label_annotator = sv.LabelAnnotator()
        
        self.signal_state: str = "green"
        self.alerts: Deque[Dict] = deque(maxlen=200)

        self.cap: Optional[cv2.VideoCapture] = None
        self.frame_lock = threading.Lock()
        self.running = False
        self.thread: Optional[threading.Thread] = None
        self.last_frame: Optional[np.ndarray] = None

        self.roi: ROIConfig = load_roi_config()
        self.m_per_px: Optional[float] = None
        self.track_last: Dict[int, Tuple[float, Tuple[float, float]]] = {}

        # Wrong-way state
        self.track_history: Dict[int, Deque[Tuple[float, Tuple[float, float]]]] = {}
        self.wrong_way_counter: Dict[int, int] = {}
        self.lane_dirs_unit: List[Tuple[float, float]] = []

        # Per-track violation highlight window
        self.violation_until: Dict[int, float] = {}

        # Optional models
        self.helmet_model: Optional[YOLO] = None
        if self.roi.helmet_model_path:
            try:
                self.helmet_model = YOLO(self.roi.helmet_model_path)
            except Exception:
                self.helmet_model = None
        self.plate_model: Optional[YOLO] = None
        if self.roi.plate_model_path:
            try:
                self.plate_model = YOLO(self.roi.plate_model_path)
            except Exception:
                self.plate_model = None
        self.ocr_reader = None

    def start(self, source: Union[int, str]) -> bool:
        self.stop()
        self.cap = cv2.VideoCapture(source)
        if not self.cap.isOpened():
            self.cap = None
            return False

        if self.model is None:
            # Use small free model for CPU in dev
            self.model = YOLO("yolov8n.pt")

        self.running = True
        self.thread = threading.Thread(target=self._run_loop, daemon=True)
        self.thread.start()
        return True

    def stop(self) -> None:
        self.running = False
        if self.thread:
            self.thread.join(timeout=1.0)
            self.thread = None
        if self.cap:
            try:
                self.cap.release()
            except Exception:
                pass
            self.cap = None
        self.track_last.clear()
        self.track_history.clear()
        self.wrong_way_counter.clear()
        self.violation_until.clear()

    def set_signal_state(self, state: str) -> None:
        state = state.lower().strip()
        if state not in {"red", "green"}:
            return
        self.signal_state = state

    def get_signal_state(self) -> str:
        return self.signal_state

    def get_recent_alerts(self) -> Dict:
        return {"signal": self.signal_state, "alerts": list(self.alerts)}

    def _emit_alert(self, kind: str, track_id: int, info: Dict) -> None:
        now = time.time()
        self.alerts.appendleft({
            "ts": now,
            "type": kind,
            "track_id": track_id,
            "info": info,
        })
        # Set highlight for violations (exclude informational alerts like plate_read)
        if kind != "plate_read" and track_id is not None and track_id >= 0:
            self.violation_until[track_id] = now + 3.0  # highlight for 3 seconds

    def _ensure_ocr(self):
        if self.ocr_reader is None:
            try:
                import easyocr  # type: ignore
                self.ocr_reader = easyocr.Reader(['en'], gpu=False)
            except Exception:
                self.ocr_reader = None

    def _run_loop(self) -> None:
        assert self.cap is not None
        stop_line_px = None
        lane_polys_px: List[List[Tuple[int, int]]]= []
        lane_contours: List[np.ndarray] = []
        fps = self.cap.get(cv2.CAP_PROP_FPS) or 30
        frame_idx = 0

        while self.running and self.cap and self.cap.isOpened():
            ret, frame = self.cap.read()
            if not ret:
                break
            frame_idx += 1

            h, w = frame.shape[:2]
            # Precompute pixel ROIs once
            if stop_line_px is None:
                stop_line_px = denormalize_points(self.roi.stop_line, w, h) if self.roi.stop_line else None
                lane_polys_px = [denormalize_points(poly, w, h) for poly in self.roi.lanes]
                lane_contours = [np.array(poly, dtype=np.int32).reshape((-1, 1, 2)) for poly in lane_polys_px]
                # calibration
                if self.roi.speed_calib_points and self.roi.speed_calib_distance_m:
                    (ax, ay), (bx, by) = self.roi.speed_calib_points
                    p1 = (ax * w, ay * h)
                    p2 = (bx * w, by * h)
                    px_dist = ((p1[0]-p2[0])**2 + (p1[1]-p2[1])**2) ** 0.5
                    if px_dist > 1e-3:
                        self.m_per_px = float(self.roi.speed_calib_distance_m) / px_dist
                    else:
                        self.m_per_px = None
                else:
                    self.m_per_px = None
                # lane directions unit vectors
                self.lane_dirs_unit = []
                for d in self.roi.lane_directions:
                    (x1, y1), (x2, y2) = (int(d[0][0] * w), int(d[0][1] * h)), (int(d[1][0] * w), int(d[1][1] * h))
                    vx, vy = (x2 - x1), (y2 - y1)
                    norm = (vx*vx + vy*vy) ** 0.5
                    if norm > 1e-6:
                        self.lane_dirs_unit.append((vx / norm, vy / norm))
                    else:
                        self.lane_dirs_unit.append((0.0, 0.0))

            # Inference
            results = self.model(frame, verbose=False)[0]  # type: ignore
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

            now = time.time()
            # Evaluate rules + optional analyses
            for i in range(len(tracked)):
                xyxy = tracked.xyxy[i]
                track_id = int(tracked.tracker_id[i]) if tracked.tracker_id is not None else -1
                cid = int(tracked.class_id[i]) if tracked.class_id is not None else -1
                name = results.names.get(cid, "obj")

                cx = float((xyxy[0] + xyxy[2]) / 2)
                cy = float((xyxy[1] + xyxy[3]) / 2)

                # Red-light violation
                if self.signal_state == "red" and stop_line_px is not None:
                    p = np.array([int(cx), int(cy)], dtype=np.int32)
                    if _point_crossed_line(p, stop_line_px):
                        self._emit_alert("red_light_violation", track_id, {"cx": int(cx), "cy": int(cy)})
                        cv2.putText(frame, "RED LIGHT VIOLATION", (int(cx), max(0, int(cy) - 12)), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2, cv2.LINE_AA)

                # Determine containing lane and wrong-way detection
                lane_index = -1
                for idx, cnt in enumerate(lane_contours):
                    if cv2.pointPolygonTest(cnt, (cx, cy), False) >= 0:
                        lane_index = idx
                        break
                if lane_index == -1:
                    self.wrong_way_counter[track_id] = 0
                else:
                    # maintain history
                    hist = self.track_history.get(track_id)
                    if hist is None:
                        hist = deque(maxlen=12)
                        self.track_history[track_id] = hist
                    hist.append((now, (cx, cy)))
                    # compute velocity over window
                    if len(hist) >= 4:
                        t0, (x0, y0) = hist[0]
                        tn, (xn, yn) = hist[-1]
                        dt = tn - t0
                        if dt > 0.1:
                            vx = (xn - x0) / dt
                            vy = (yn - y0) / dt
                            speed_pxps = (vx*vx + vy*vy) ** 0.5
                            if lane_index < len(self.lane_dirs_unit):
                                dx, dy = self.lane_dirs_unit[lane_index]
                                dot = vx * dx + vy * dy
                                speed_min = 30.0
                                if speed_pxps >= speed_min and dot < -0.5 * speed_pxps:
                                    self.wrong_way_counter[track_id] = self.wrong_way_counter.get(track_id, 0) + 1
                                else:
                                    self.wrong_way_counter[track_id] = 0
                                if self.wrong_way_counter.get(track_id, 0) >= 10:
                                    self._emit_alert("wrong_way", track_id, {"lane": lane_index, "speed_pxps": round(speed_pxps, 1)})
                                    cv2.putText(frame, "WRONG WAY", (int(cx), max(0, int(cy) - 44)), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 0, 255), 2, cv2.LINE_AA)
                                    x_prev = int(xn - vx * 0.2)
                                    y_prev = int(yn - vy * 0.2)
                                    cv2.arrowedLine(frame, (x_prev, y_prev), (int(xn), int(yn)), (0, 0, 255), 2, tipLength=0.4)

                # Lane zone check
                if lane_contours:
                    inside_any = any(cv2.pointPolygonTest(cnt, (cx, cy), False) >= 0 for cnt in lane_contours)
                    if not inside_any:
                        self._emit_alert("lane_violation", track_id, {"cx": int(cx), "cy": int(cy)})
                        cv2.putText(frame, "LANE VIOLATION", (int(cx), min(h - 4, int(cy) + 16)), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 165, 255), 2, cv2.LINE_AA)

                # Speed estimation
                if self.m_per_px is not None and self.roi.speed_limit_kmh is not None:
                    prev = self.track_last.get(track_id)
                    if prev is not None:
                        prev_t, (px, py) = prev
                        dt = now - prev_t
                        if dt > 0.05:
                            dp = ((cx - px)**2 + (cy - py)**2) ** 0.5
                            mps = (dp * self.m_per_px) / dt
                            kmh = mps * 3.6
                            if kmh > self.roi.speed_limit_kmh:
                                self._emit_alert("speeding", track_id, {"speed_kmh": round(kmh, 1)})
                                cv2.putText(frame, f"SPEED {kmh:.1f} km/h", (int(cx), max(0, int(cy) - 28)), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 0, 0), 2, cv2.LINE_AA)
                    self.track_last[track_id] = (now, (cx, cy))

                # Optional: helmet check
                if self.helmet_model is not None and name in {"motorcycle", "bicycle"} and (frame_idx % 5 == 0):
                    x1, y1, x2, y2 = map(int, xyxy)
                    head_y2 = int(y1 + (y2 - y1) * 0.4)
                    head_crop = frame[max(0, y1):max(0, head_y2), max(0, x1):max(0, x2)]
                    if head_crop.size > 0:
                        try:
                            hres = self.helmet_model(head_crop, verbose=False)[0]
                            names = hres.names
                            labels = [names[int(c)] for c in (hres.boxes.cls.cpu().numpy().astype(int) if hres.boxes is not None else [])]
                            has_helmet = any("helmet" in lbl.lower() for lbl in labels)
                            no_helmet = any("no-helmet" in lbl.lower() or "no_helmet" in lbl.lower() for lbl in labels)
                            if no_helmet or (not has_helmet and labels):
                                self._emit_alert("no_helmet", track_id, {})
                                cv2.putText(frame, "NO HELMET", (x1, max(0, y1 - 8)), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2, cv2.LINE_AA)
                        except Exception:
                            pass

                # Optional: plate detection + OCR
                if self.plate_model is not None and name in VEHICLE_CLASS_NAMES and (frame_idx % 7 == 0):
                    x1, y1, x2, y2 = map(int, xyxy)
                    veh_crop = frame[max(0, y1):max(0, y2), max(0, x1):max(0, x2)]
                    if veh_crop.size > 0:
                        try:
                            pres = self.plate_model(veh_crop, verbose=False)[0]
                            if pres.boxes is not None and len(pres.boxes) > 0:
                                b = pres.boxes
                                idx = int(np.argmax(b.conf.cpu().numpy()))
                                pxyxy = b.xyxy.cpu().numpy()[idx]
                                px1, py1, px2, py2 = map(int, pxyxy)
                                plate_crop = veh_crop[max(0, py1):max(0, py2), max(0, px1):max(0, px2)]
                                if plate_crop.size > 0:
                                    self._ensure_ocr()
                                    if self.ocr_reader is not None:
                                        try:
                                            ocr = self.ocr_reader.readtext(plate_crop)
                                            if ocr:
                                                text = sorted(ocr, key=lambda r: -r[2])[0][1]
                                                if text:
                                                    self._emit_alert("plate_read", track_id, {"text": text})
                                                    cv2.putText(frame, text, (x1, min(h - 4, y2 + 18)), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (50, 200, 50), 2, cv2.LINE_AA)
                                        except Exception:
                                            pass
                        except Exception:
                            pass

            # Annotate boxes
            labels = []
            for i in range(len(tracked)):
                cid = int(tracked.class_id[i]) if tracked.class_id is not None else -1
                conf_i = float(conf[i]) if i < len(conf) else 0.0
                labels.append(f"{results.names.get(cid, 'obj')} {conf_i:.2f}")
            frame = self.box_annotator.annotate(scene=frame, detections=tracked)
            frame = self.label_annotator.annotate(scene=frame, detections=tracked, labels=labels)

            # Overlay VIOLATED banner on tracks recently alerted
            now2 = time.time()
            for i in range(len(tracked)):
                if tracked.tracker_id is None:
                    continue
                tid = int(tracked.tracker_id[i])
                if self.violation_until.get(tid, 0) > now2:
                    x1, y1, x2, y2 = map(int, tracked.xyxy[i])
                    cv2.putText(frame, "VIOLATED", (x1, max(0, y1 - 6)), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0,0,255), 2, cv2.LINE_AA)

            with self.frame_lock:
                self.last_frame = frame.copy()

            time.sleep(max(0.0, 1.0 / fps / 4))

        self.running = False

    def mjpeg_generator(self):
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
            ret, buf = cv2.imencode('.jpg', frame, [int(cv2.IMWRITE_JPEG_QUALITY), 80])
            if not ret:
                continue
            jpg = buf.tobytes()
            yield boundary + b"\r\n" + b"Content-Type: image/jpeg\r\n\r\n" + jpg + b"\r\n"


# --- Helpers ---

def _point_crossed_line(p: np.ndarray, line: Tuple[Tuple[int, int], Tuple[int, int]]) -> bool:
    (x1, y1), (x2, y2) = line
    px, py = p
    vx, vy = x2 - x1, y2 - y1
    wx, wy = px - x1, py - y1
    c1 = vx * wx + vy * wy
    if c1 <= 0:
        dx, dy = px - x1, py - y1
        d2 = dx * dx + dy * dy
        return d2 < 25
    c2 = vx * vx + vy * vy
    if c2 <= c1:
        dx, dy = px - x2, py - y2
        d2 = dx * dx + dy * dy
        return d2 < 25
    b = c1 / c2
    xp, yp = x1 + b * vx, y1 + b * vy
    dx, dy = px - xp, py - yp
    return (dx * dx + dy * dy) < 25
