from pathlib import Path
from .config import settings


def generate_account_qr(account_number: str) -> Path:
    try:
        import qrcode
    except ImportError as exc:
        raise RuntimeError("Install qrcode[pil] to generate QR codes.") from exc
    settings.output_dir.mkdir(parents=True, exist_ok=True)
    path = settings.output_dir / f"account_{account_number}.png"
    qrcode.make(account_number).save(path)
    return path


def scan_qr_image(path: str) -> str:
    try:
        import cv2
        from pyzbar.pyzbar import decode
    except ImportError as exc:
        raise RuntimeError("Install opencv-python and pyzbar to scan QR images.") from exc
    image = cv2.imread(path)
    if image is None:
        raise ValueError("Could not read that image path.")
    results = decode(image)
    if not results:
        raise ValueError("No QR code was detected.")
    value = results[0].data.decode("utf-8").strip()
    if not value.isdigit() or len(value) != 12:
        raise ValueError("QR code does not contain a valid 12-digit account number.")
    return value


def scan_qr_webcam() -> str | None:
    try:
        import cv2
        from pyzbar.pyzbar import decode
    except ImportError as exc:
        raise RuntimeError("Install opencv-python and pyzbar to use the webcam scanner.") from exc
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        raise RuntimeError("Could not open webcam.")
    found = None
    try:
        print("Show an account QR code to the camera; press q to cancel.")
        while True:
            ok, frame = cap.read()
            if not ok:
                break
            for obj in decode(frame):
                value = obj.data.decode("utf-8").strip()
                if value.isdigit() and len(value) == 12:
                    found = value
                    break
            cv2.imshow("Bank account QR scanner", frame)
            if found or (cv2.waitKey(1) & 0xFF) == ord("q"):
                break
    finally:
        cap.release()
        cv2.destroyAllWindows()
    return found
