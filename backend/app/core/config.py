from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # Database
    database_url: str = "postgresql://mybookvault:mybookvault@db:5432/mybookvault"

    # App
    app_name: str = "MyBookVault"
    debug: bool = True

    cors_origins: list[str] = ["*"]

    # External book metadata APIs
    open_library_base_url: str = "https://openlibrary.org"
    google_books_base_url: str = "https://www.googleapis.com/books/v1"

settings = Settings()
