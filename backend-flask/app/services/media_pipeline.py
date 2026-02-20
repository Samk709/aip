from importlib.util import find_spec


def analyze_face_image(image_path: str) -> dict:
    if find_spec("cv2") is None:
        return {"provider": "unavailable", "emotion": "neutral", "note": "opencv not installed"}

    import cv2

    img = cv2.imread(image_path)
    if img is None:
        return {"provider": "opencv", "emotion": "neutral", "note": "image not found"}

    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    brightness = float(gray.mean()) / 255.0
    # Simplistic proxy; replace with real FER model.
    if brightness > 0.6:
        emotion = "happy"
    elif brightness < 0.35:
        emotion = "sad"
    else:
        emotion = "neutral"

    return {"provider": "opencv", "emotion": emotion, "brightness": round(brightness, 3)}


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
