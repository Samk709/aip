from pathlib import Path
import os
from dotenv import load_dotenv
from app import create_app

load_dotenv()
app = create_app()

if __name__ == "__main__":
    port = int(os.getenv("PORT", "5000"))
    print(f"[MindCare] Running from: {Path(__file__).resolve().parent}")
    print(f"[MindCare] Instance: {app.config['INSTANCE_LABEL']}")
    print(f"[MindCare] Build marker endpoint: http://localhost:{port}/api/build-info")
    app.run(host="0.0.0.0", port=port, debug=True)
