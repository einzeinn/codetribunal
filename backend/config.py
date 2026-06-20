"""
CodeTribunal - Configuration Module
Configuration settings and environment variables
"""

import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

class Settings:
    """Application settings loaded from environment variables"""
    
    # Application settings
    APP_NAME: str = "CodeTribunal"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = os.getenv("DEBUG", "False").lower() == "true"
    
    # API settings
    API_V1_STR: str = "/api/v1"
    PROJECT_NAME: str = os.getenv("PROJECT_NAME", "CodeTribunal API")
    HOST: str = os.getenv("HOST", "0.0.0.0")
    PORT: int = int(os.getenv("PORT", "8000"))
    
    # Database settings (Neon PostgreSQL)
    DATABASE_URL: str = os.getenv("DATABASE_URL", "postgresql://user:password@localhost:5432/codetribunal")
    
    # Qwen API settings
    QWEN_API_KEY: str = os.getenv("QWEN_API_KEY", "")
    QWEN_BASE_URL: str = os.getenv("QWEN_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1")
    
    # Model settings - specific to each agent
    QWEN_MAX_MODEL: str = os.getenv("QWEN_MAX_MODEL", "qwen-max")
    QWEN_PLUS_MODEL: str = os.getenv("QWEN_PLUS_MODEL", "qwen-plus")
    QWEN_TURBO_MODEL: str = os.getenv("QWEN_TURBO_MODEL", "qwen-turbo")
    
    # Agent-specific model assignments based on documentation
    AEGIS_MODEL: str = os.getenv("AEGIS_MODEL", QWEN_MAX_MODEL)      # qwen-max for adversarial reasoning
    ARBITER_MODEL: str = os.getenv("ARBITER_MODEL", QWEN_MAX_MODEL)  # qwen-max for complex orchestration
    AXIOM_MODEL: str = os.getenv("AXIOM_MODEL", QWEN_PLUS_MODEL)    # qwen-plus for counter-arguments
    METRIC_MODEL: str = os.getenv("METRIC_MODEL", QWEN_PLUS_MODEL)  # qwen-plus for data analysis
    LEDGER_MODEL: str = os.getenv("LEDGER_MODEL", QWEN_TURBO_MODEL) # qwen-turbo for parsing/recording
    
    # Security settings
    SECRET_KEY: str = os.getenv("SECRET_KEY", "dev-secret-key-change-in-production")
    ALGORITHM: str = os.getenv("ALGORITHM", "HS256")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))
    
    # CORS settings
    BACKEND_CORS_ORIGINS: str = os.getenv("BACKEND_CORS_ORIGINS", "*")
    
    # Logging settings
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    LOG_FILE: str = os.getenv("LOG_FILE", "codetribunal.log")
    
    # Token usage tracking
    TRACK_TOKEN_USAGE: bool = os.getenv("TRACK_TOKEN_USAGE", "False").lower() == "true"
    
    # Maximum debate rounds
    MAX_DEBATE_ROUNDS: int = int(os.getenv("MAX_DEBATE_ROUNDS", "3"))
    
    # Confidence threshold for early verdict
    CONFIDENCE_THRESHOLD: float = float(os.getenv("CONFIDENCE_THRESHOLD", "0.7"))


# Create settings instance
settings = Settings()