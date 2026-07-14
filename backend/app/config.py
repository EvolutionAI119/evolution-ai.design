"""应用配置：基于pydantic-settings，从.env读取"""
from pathlib import Path
from pydantic_settings import BaseSettings, SettingsConfigDict


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

    DEFAULT_LANGUAGE: str = "zh"
    SUPPORTED_LANGUAGES: str = "zh,en"

    @property
    def allowed_extensions_list(self):
        return [e.strip() for e in self.ALLOWED_EXTENSIONS.split(",")]

    @property
    def supported_languages_list(self):
        return [l.strip() for l in self.SUPPORTED_LANGUAGES.split(",")]

    @property
    def data_path(self): return Path(self.DATA_DIR).resolve()

    @property
    def models_path(self): return Path(self.MODELS_DIR).resolve()

    @property
    def reports_path(self): return Path(self.REPORTS_DIR).resolve()

    @property
    def exports_path(self): return Path(self.EXPORTS_DIR).resolve()

    model_config = SettingsConfigDict(env_file=".env", extra="ignore")


settings = Settings()
