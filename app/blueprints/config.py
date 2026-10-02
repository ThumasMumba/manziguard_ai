"""Configuration. Values come from environment variables (see .env.example)."""
import os
from pathlib import Path
from dotenv import load_dotenv
load_dotenv()
BASE_DIR = Path(__file__).resolve().parent.parent


def database_url() -> str:
    url = os.environ.get("DATABASE_URL", f"sqlite:///{BASE_DIR / 'dev.db'}")
    # Railway and others expose mysql://, SQLAlchemy needs the driver name.
    if url.startswith("mysql://"):
        url = url.replace("mysql://", "mysql+pymysql://", 1)
    return url


class Config:
    # Flask session signing key - MUST be overridden in production
    SECRET_KEY = os.environ.get("SECRET_KEY")
    
    # ------MySLQ connection ------------------------------------------------#
    DB_USER = os.environ.get("DB_USER", "root")
    DB_PASSWORD = os.environ.get("DB_PASSWORD", "")
    DB_HOST = os.environ.get("DB_HOST", "localhost")
    DB_PORT = os.environ.get("DB_PORT", 3306)
    DB_NAME = os.environ.get("DB_NAME", "manziguard_ai_db")
    
    
    SQLALCHEMY_DATABASE_URI = database_url()
    SQLALCHEMY_ENGINE_OPTIONS = {"pool_pre_ping": True}
    SQLALCHEMY_TRACK_MODIFICATIONS = False

    # ---------------------------------------------------------------------------
    # Tunable constants. Keep them here (not buried in functions) so they can be
    # adjusted after testing with real photos on real phones.
    # ---------------------------------------------------------------------------
    MAX_IMAGE_BYTES = 5 * 1024 * 1024   # reject huge uploads before decoding (server safety)
    MIN_IMAGE_SIDE_PX = 200              # smaller photos cannot resolve the pads
    NORMALISED_HEIGHT_PX = 900           # every photo is resized to this height
    MIN_STRIP_HEIGHT_PX = 360            # strip crop must be at least this tall after resizing
    MIN_STRIP_HEIGHT_FRAC = 0.4          # strip must span >= 40% of the photo height
    MIN_STRIP_ASPECT = 2.0               # height/width of the strip bounding box
    CORE_FRACTION = 0.5                  # central share of each pad that is sampled
    MIN_REF_BRIGHTNESS = 60.0            # reference patch mean (0-255) below this = too dark
    SATURATION_LEVEL = 250.0             # any reference channel above this = clipped
    MAX_REF_SPREAD = 20.0                # reference patch unevenness (shadow / glare)
    MAX_GAIN = 2.5                       # strongest allowed per-channel correction

    # ------ Session / cookie hardening ----- #
    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    # Set SESSION_COOKIE_SECURE = True once the app is served over HTTPS.
    SESSION_COOKIE_SECURE = True
    TRUST_PROXY = os.environ.get("TRUST_PROXY", "0") == "1"  # set to 1 behind Railway/Nginx

    SUPPORTED_LANGUAGES = ("en", "bem", "nya")
    DEFAULT_LANGUAGE = os.environ.get("DEFAULT_LANGUAGE", "en")

    MODEL_PATH = os.environ.get("MODEL_PATH", str(BASE_DIR / "ml/models/strip_classifier.tflite"))
    CHART_PATH = os.environ.get("CHART_PATH", str(BASE_DIR / "data/k5_reference_chart.json"))
    MINING_SITES_PATH = os.environ.get("MINING_SITES_PATH", str(BASE_DIR / "data/mining_sites.json"))
    # Refuse to give results until the colour chart has been calibrated on real K5 strips.
    REQUIRE_CALIBRATED_CHART = True
    MAX_MATCH_DELTA_E = 25.0  # colour distance above which a pad reading is rejected

    # --- Decision thresholds: REVIEW with WASH / Ministry of Health partners ---
    NITRATE_UNSAFE_MGL = 50.0   # mg/L as nitrate (WHO short-term guideline value)
    NITRATE_RISKY_MGL = 25.0    # placeholder early-warning level
    PH_SAFE_RANGE = (6.5, 8.5)  # commonly used acceptable range
    PH_EXTREME_RANGE = (5.5, 9.5)  # placeholder: outside this is treated as unsafe
    RAIN_HEAVY_MM_72H = 50.0    # placeholder
    MINING_RISK_KM = 5.0        # placeholder

    SMS_PROVIDER = os.environ.get("SMS_PROVIDER", "console")  # console | mtn
    MTN_API_KEY = os.environ.get("MTN_API_KEY", "")
    MTN_SENDER_ID = os.environ.get("MTN_SENDER_ID", "ManziGuard")
    RAINFALL_API_KEY = os.environ.get("RAINFALL_API_KEY", "")
    USSD_SHARED_SECRET = os.environ.get("USSD_SHARED_SECRET", "")

    RATELIMIT_DEFAULT = "200 per hour"
    RATELIMIT_STORAGE_URI = os.environ.get("RATELIMIT_STORAGE_URI", "memory://")

   

class DevelopmentConfig(Config):
    DEBUG = True
    RATELIMIT_STORAGE_URI = "memory://"
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-only-not-secret")
    SESSION_COOKIE_SECURE = False
    REQUIRE_CALIBRATED_CHART = False  # lets you exercise the flow with the placeholder chart


class TestingConfig(DevelopmentConfig):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = "sqlite:///:memory:"
    WTF_CSRF_ENABLED = False
    RATELIMIT_ENABLED = False


class ProductionConfig(Config):
    pass
    # Railway Redis add-on exposes a URL, e.g. redis://default:...@host:port
    #RATELIMIT_STORAGE_URI = os.environ["REDIS_URL"]

# The CONFIGS dictionary maps environment names to their corresponding configuration classes. This allows the application to easily switch between different configurations based on the environment it is running in (development, testing, or production).
CONFIGS = {
    "development": DevelopmentConfig,
    "testing": TestingConfig,
    "production": ProductionConfig,
}