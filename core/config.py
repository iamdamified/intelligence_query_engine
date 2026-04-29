from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    ENV: str = "development"

    # DB
    DATABASE_URL: str

    # Security
    SECRET_KEY: str
    ALGORITHM: str = "HS256"

    # Tokens
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 3
    REFRESH_TOKEN_EXPIRE_MINUTES: int = 5  # Per spec: 5 minutes

    # 🔐 REQUIRED FOR GITHUB OAUTH (MISSING BEFORE)
    GITHUB_CLIENT_ID: str
    GITHUB_CLIENT_SECRET: str
    GITHUB_REDIRECT_URI: str

    class Config:
        env_file = ".env"
        extra = "ignore"


settings = Settings()