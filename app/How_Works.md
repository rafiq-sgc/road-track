How violations are detected
Red light violation:
We draw a stop line from roi_config.json.
For each tracked object, we use its center point and test if it crosses the line while signal=red using a distance-to-segment check.
If crossed, we raise red_light_violation.

Lane violation:
Lanes are polygons in roi_config.json.
If an object’s center is not inside any lane polygon (cv2.pointPolygonTest), we raise lane_violation.

Wrong-way (opposite direction):
Each lane has a direction vector (lane_directions start→end).
We keep a short history of each track’s centers and compute its motion vector (px/s).
If the motion’s dot product with the lane vector is sufficiently negative (moving opposite) and persists for several frames, we raise wrong_way.

Speeding:
If you provide calibration (speed_calib_points with speed_calib_distance_m), we compute meters-per-pixel.
Using consecutive positions over time, we estimate speed in km/h and compare to speed_limit_kmh.
If exceeded, we raise speeding.

Helmet/no-helmet (optional):
If helmet_model_path is set, we crop the head region of motorcycles/bicycles periodically and run the model.
If it indicates no helmet (or no helmet detected while a relevant label is present), we raise no_helmet.

Plate read (optional, informational):
If plate_model_path is set, we detect the plate inside the vehicle crop and OCR it with EasyOCR.
We emit plate_read (does not mark as violation).

Tracking and stability:
YOLOv8 detects objects; ByteTrack assigns stable IDs.
We use thresholds and persistence windows (e.g., required frames) to avoid flicker/noise.
When a violation triggers, we show a red “VIOLATED” label over that track for a few seconds to make it obvious.
You can tune ROIs and directions in app/config/roi_config.json, and thresholds can be exposed to config if you want finer control.