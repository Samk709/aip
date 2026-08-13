from importlib.util import find_spec
from pathlib import Path
from app.services.media_models import predict_face_emotion_cnn, EMOTION_CLASSES

# Smart-crop tuning: FER models are trained on face-centric crops with a small
# margin, not raw detection boxes. This pads the detection box before cropping the ROI.
CROP_PAD_RATIO = 0.15

# MediaPipe BlazeFace detector cache (much more robust than Haar on live webcam)
_MP_FACE_DETECTOR = None
_MP_FACE_DETECTOR_FAILED = False


def _get_mediapipe_face_detector():
    """Lazily creates the MediaPipe Tasks FaceDetector (BlazeFace short-range,
    optimized for faces within ~2m of the camera, i.e. webcam use)."""
    global _MP_FACE_DETECTOR, _MP_FACE_DETECTOR_FAILED
    if _MP_FACE_DETECTOR is not None:
        return _MP_FACE_DETECTOR
    if _MP_FACE_DETECTOR_FAILED:
        return None

    try:
        if find_spec("mediapipe") is None:
            _MP_FACE_DETECTOR_FAILED = True
            return None
        import mediapipe as mp
        from mediapipe.tasks import python as mp_python
        from mediapipe.tasks.python import vision

        candidates = [
            Path(__file__).resolve().parent.parent.parent.parent / "assets" / "blaze_face_short_range.tflite",
            Path("assets/blaze_face_short_range.tflite"),
        ]
        model_path = next((p for p in candidates if p.exists()), None)
        if model_path is None:
            _MP_FACE_DETECTOR_FAILED = True
            return None

        opts = vision.FaceDetectorOptions(
            base_options=mp_python.BaseOptions(model_asset_path=str(model_path)),
            min_detection_confidence=0.5,
        )
        _MP_FACE_DETECTOR = vision.FaceDetector.create_from_options(opts)
        print(f"[OK] Loaded MediaPipe BlazeFace detector from {model_path}")
        return _MP_FACE_DETECTOR
    except Exception as e:
        print(f"[!] MediaPipe detector unavailable ({e}); using Haar cascades")
        _MP_FACE_DETECTOR_FAILED = True
        return None


def _detect_face_mediapipe(img_bgr):
    """Returns (x, y, w, h) of the largest detected face, or None."""
    detector = _get_mediapipe_face_detector()
    if detector is None:
        return None
    try:
        import cv2
        import mediapipe as mp

        rgb = cv2.cvtColor(img_bgr, cv2.COLOR_BGR2RGB)
        mp_img = mp.Image(image_format=mp.ImageFormat.SRGB, data=rgb)
        result = detector.detect(mp_img)
        if not result.detections:
            return None
        # Largest detection wins
        best = max(
            result.detections,
            key=lambda d: d.bounding_box.width * d.bounding_box.height,
        )
        bb = best.bounding_box
        return (int(bb.origin_x), int(bb.origin_y), int(bb.width), int(bb.height))
    except Exception:
        return None


def _crop_face_roi(gray, img_h, img_w, x, y, w, h):
    """Crops the face ROI with a padded, boundary-clamped margin around the
    detection box so forehead/chin context matches training-time crops."""
    pad = int(max(w, h) * CROP_PAD_RATIO)
    x1, y1 = max(0, x - pad), max(0, y - pad)
    x2, y2 = min(img_w, x + w + pad), min(img_h, y + h + pad)
    return gray[y1:y2, x1:x2]


def measure_facial_biomarkers(face_roi_gray):
    """
    Extracts raw facial geometry measurements (smile-region detections, dark mouth
    cavity ratio, upper/lower face luminance ratio) from a cropped grayscale face ROI.

    IMPORTANT: These are supplementary EXPLAINABILITY measurements only. They are
    never used to decide the emotion label, the confidence, or the per-class
    breakdown — that decision comes exclusively from the MiniXception CNN's live
    softmax output for the specific frame.
    """
    import cv2
    import numpy as np

    h, w = face_roi_gray.shape[:2]
    if h < 15 or w < 15:
        return None

    mouth_roi = face_roi_gray[int(h * 0.50):h, :]

    cascade_dir = cv2.data.haarcascades
    smile_cascade = cv2.CascadeClassifier(cascade_dir + "haarcascade_smile.xml")
    smiles = smile_cascade.detectMultiScale(mouth_roi, scaleFactor=1.5, minNeighbors=15)

    dark_mouth_ratio = float(np.mean(mouth_roi < 50))
    lower_mean = float(np.mean(face_roi_gray[int(h * 0.50):h, :]))
    upper_mean = float(np.mean(face_roi_gray[0:int(h * 0.50), :]))
    eye_region_mean = float(np.mean(face_roi_gray[int(h * 0.15):int(h * 0.45), :]))

    return {
        "smile_region_detections": int(len(smiles)),
        "dark_mouth_cavity_ratio": round(dark_mouth_ratio, 3),
        "lower_upper_luminance_ratio": round(lower_mean / (upper_mean + 1e-5), 3),
        "mouth_region_mean_intensity": round(lower_mean, 1),
        "eye_region_mean_intensity": round(eye_region_mean, 1)
    }


def analyze_face_image(image_path: str) -> dict:
    """
    Real-time Facial Expression Recognition (FER) Pipeline:
    1. Detects face ROI using OpenCV Haar Cascades & YCrCb skin color segmentation.
    2. Strictly validates face ROI. Returns face_detected=False if no face is in frame.
    3. Feeds the cropped grayscale face ROI into the PyTorch MiniXception CNN model.
    4. The CNN's live softmax output is the SOLE source of the emotion label,
       confidence, and per-class breakdown.
    5. Geometric facial biomarkers are attached as raw explainability measurements
       only — they play no role in the decision.
    """
    if find_spec("cv2") is None:
        return {
            "face_detected": False,
            "provider": "unavailable",
            "emotion": "neutral",
            "confidence": None,
            "note": "opencv not installed; no prediction made"
        }

    import cv2
    import numpy as np

    img = cv2.imread(image_path)
    if img is None:
        return {
            "face_detected": False,
            "provider": "opencv-haar",
            "emotion": "neutral",
            "confidence": None,
            "note": "image file unreadable or missing; no prediction made"
        }

    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    img_h, img_w = gray.shape[:2]

    # Preprocessing Feature 1: Guard against pitch-black / camera-off / disabled video frames
    mean_brightness = float(np.mean(gray))
    std_brightness = float(np.std(gray))
    if mean_brightness < 15 or std_brightness < 5:
        return {
            "face_detected": False,
            "provider": "pytorch-minixception-cnn",
            "emotion": "no face",
            "confidence": 0.0,
            "emotions_breakdown": {c: 0.0 for c in EMOTION_CLASSES},
            "bounding_box": None,
            "note": "Camera stream is pitch black or disabled. Please enable webcam in browser."
        }

    # CLAHE handles uneven webcam lighting better than global histogram equalization
    clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
    gray_eq = clahe.apply(gray)

    # PRIMARY DETECTOR: MediaPipe BlazeFace (robust on live webcam); Haar cascade
    # chain below remains as the fallback.
    faces = []
    mp_box = _detect_face_mediapipe(img)
    if mp_box is not None:
        faces = [mp_box]

    # OpenCV Haar Cascades: fallback face bounding box detection
    if len(faces) == 0:
        cascade_dir = cv2.data.haarcascades
        face_cascade = cv2.CascadeClassifier(cv2.samples.findFile(cascade_dir + "haarcascade_frontalface_default.xml"))
        face_cascade_alt = cv2.CascadeClassifier(cv2.samples.findFile(cascade_dir + "haarcascade_frontalface_alt.xml"))
        face_cascade_alt2 = cv2.CascadeClassifier(cv2.samples.findFile(cascade_dir + "haarcascade_frontalface_alt2.xml"))
        profile_cascade = cv2.CascadeClassifier(cv2.samples.findFile(cascade_dir + "haarcascade_profileface.xml"))

        # Multi-pass face bounding box detection
        faces = list(face_cascade.detectMultiScale(gray_eq, scaleFactor=1.05, minNeighbors=3, minSize=(30, 30)))
        if len(faces) == 0:
            faces = list(face_cascade_alt.detectMultiScale(gray_eq, scaleFactor=1.05, minNeighbors=3, minSize=(30, 30)))
        if len(faces) == 0:
            faces = list(face_cascade_alt2.detectMultiScale(gray_eq, scaleFactor=1.05, minNeighbors=3, minSize=(30, 30)))
        if len(faces) == 0:
            faces = list(profile_cascade.detectMultiScale(gray_eq, scaleFactor=1.05, minNeighbors=3, minSize=(30, 30)))

    # Fallback: YCrCb Skin Color Space Segmentation if Haar cascades miss fine bounding box
    if len(faces) == 0:
        ycrcb = cv2.cvtColor(img, cv2.COLOR_BGR2YCrCb)
        mask = cv2.inRange(ycrcb, np.array([0, 133, 77], dtype=np.uint8), np.array([255, 173, 127], dtype=np.uint8))
        contours, _ = cv2.findContours(mask, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        valid_contours = [c for c in contours if cv2.contourArea(c) > (img_w * img_h * 0.06)]
        if valid_contours:
            largest_c = max(valid_contours, key=cv2.contourArea)
            fx, fy, fw, fh = cv2.boundingRect(largest_c)
            aspect = float(fw) / float(fh + 1e-5)
            if 0.65 <= aspect <= 1.6:
                faces = [(fx, fy, fw, fh)]

    # STRICT FACE DETECTION GUARD: If no genuine face ROI is detected, return face_detected=False
    if len(faces) == 0:
        return {
            "face_detected": False,
            "provider": "opencv-haar-landmarks",
            "emotion": "No face detected",
            "confidence": 0.0,
            "emotions_breakdown": {c: 0.0 for c in EMOTION_CLASSES},
            "bounding_box": None,
            "note": "No face detected in camera frame. Please position face clearly inside webcam view."
        }

    # Crop genuine detected face region (padded smart crop)
    faces = sorted(faces, key=lambda f: f[2] * f[3], reverse=True)
    (x, y, w, h) = faces[0]
    face_roi = _crop_face_roi(gray, img_h, img_w, x, y, w, h)

    if face_roi.size == 0 or w < 20 or h < 20:
        return {
            "face_detected": False,
            "provider": "opencv-haar-landmarks",
            "emotion": "No face detected",
            "confidence": 0.0,
            "emotions_breakdown": {c: 0.0 for c in EMOTION_CLASSES},
            "bounding_box": None,
            "note": "Face bounding box invalid or too small"
        }

    # FINAL DECISION: the trained model's live softmax output for this exact frame.
    # No rule-based post-processing, no fusion, no fixed confidence values.
    cnn_res = predict_face_emotion_cnn(face_roi)

    if cnn_res.get("provider") == "fallback":
        return {
            "face_detected": False,
            "provider": "fallback",
            "emotion": "uncertain",
            "confidence": 0.0,
            "emotions_breakdown": {c: 0.0 for c in EMOTION_CLASSES},
            "bounding_box": {"x": int(x), "y": int(y), "w": int(w), "h": int(h)},
            "biomarkers": None,
            "note": "No trained model weights available; no emotion prediction was made."
        }

    # Supplementary explainability measurements (raw values only, zero decision role)
    biomarkers = measure_facial_biomarkers(face_roi)

    primary_emotion = cnn_res["emotion"]
    max_conf = cnn_res["confidence"]
    emotions_breakdown = cnn_res["emotions_breakdown"]
    model_provider = cnn_res.get("provider", "unknown")

    print(f"[FER MODEL INFERENCE] Provider: {model_provider} | Primary: {primary_emotion} | Conf: {max_conf} | Breakdown: {emotions_breakdown}")

    return {
        "face_detected": True,
        "provider": model_provider,
        "emotion": primary_emotion,
        "confidence": max_conf,
        "emotions_breakdown": emotions_breakdown,
        "bounding_box": {"x": int(x), "y": int(y), "w": int(w), "h": int(h)},
        "biomarkers": biomarkers,
        "explainability_note": (
            f"Emotion label and confidence come solely from the '{model_provider}' "
            "model's live softmax output for this frame. Biomarker measurements are "
            "raw supplementary context only and do not influence the prediction."
        )
    }


def analyze_voice_audio(audio_path: str) -> dict:
    if find_spec("librosa") is None:
        return {"provider": "unavailable", "stress": 0.5, "note": "librosa not installed"}

    import librosa
    import numpy as np

    y, sr = librosa.load(audio_path, sr=None)
    if y.size == 0:
        return {"provider": "librosa", "stress": 0.5, "note": "empty audio"}

    rms = float(np.sqrt(np.mean(y ** 2)))
    zcr = float(np.mean(librosa.feature.zero_crossing_rate(y)))
    stress = max(0.0, min(1.0, (rms * 2.5 + zcr * 1.5)))
    return {"provider": "librosa", "stress": round(stress, 3), "rms": round(rms, 4), "zcr": round(zcr, 4)}
