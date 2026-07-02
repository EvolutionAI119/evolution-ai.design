from pydantic_settings import BaseSettings, SettingsConfigDict
from pathlib import Path


class Settings(BaseSettings):
    ENVIRONMENT: str = "development"
    API_HOST: str = "0.0.0.0"
    API_PORT: int = 8000
    DEBUG: bool = True
    LOG_LEVEL: str = "INFO"

    DATABASE_URL: str = "sqlite:///./evolution_ai.db"

    DATA_DIR: str = "../data"
    MODELS_DIR: str = "../data/models"
    REPORTS_DIR: str = "../data/reports"
    EXPORTS_DIR: str = "../data/exports"

    MAX_FILE_SIZE: int = 52428800
    ALLOWED_EXTENSIONS: str = ".glb,.gltf,.obj,.stl,.fbx,.igs,.iges,.step,.stp"

    TOPOLOGY_TARGET_FACES: int = 30000
    TOPOLOGY_MIN_QUAD_RATIO: float = 0.75

    QUALITY_TOLERANCE_POSITION: float = 0.1
    QUALITY_TOLERANCE_TANGENT: float = 0.01
    QUALITY_TOLERANCE_CURVATURE: float = 0.001

    JWT_SECRET_KEY: str = "evolution_ai_secret_key_2026"
    JWT_ALGORITHM: str = "HS256"
    JWT_ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    DEFAULT_LANGUAGE: str = "zh"
    SUPPORTED_LANGUAGES: str = "zh,en"

    @property
    def allowed_extensions_list(self):
        return [ext.strip() for ext in self.ALLOWED_EXTENSIONS.split(",")]

    @property
    def supported_languages_list(self):
        return [lang.strip() for lang in self.SUPPORTED_LANGUAGES.split(",")]

    @property
    def data_path(self):
        return Path(self.DATA_DIR).resolve()

    @property
    def models_path(self):
        return Path(self.MODELS_DIR).resolve()

    @property
    def reports_path(self):
        return Path(self.REPORTS_DIR).resolve()

    @property
    def exports_path(self):
        return Path(self.EXPORTS_DIR).resolve()

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()