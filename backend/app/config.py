"""Configuration module for Flanergide backend."""

from pydantic_settings import BaseSettings
from pydantic import Field


class Settings(BaseSettings):
    """Application settings loaded from environment variables."""

    # Server Configuration
    server_host: str = Field(default="0.0.0.0", description="Server host")
    server_port: int = Field(default=8000, description="Server port")

    # Security - JWT
    jwt_secret: str = Field(..., description="JWT secret key (required)")
    jwt_algorithm: str = Field(default="HS256", description="JWT algorithm")
    token_expiry_hours: int = Field(default=24, description="Token expiry in hours")

    # Cloudflare Tunnel
    cloudflare_tunnel_url: str = Field(..., description="Cloudflare tunnel URL (required)")

    # Blog Configuration
    blog_url: str = Field(..., description="Blog homepage URL (required)")
    enable_blog_scraper: bool = Field(default=True, description="Enable blog scraper")
    blog_scraper_interval_hours: int = Field(default=48, description="Blog scraper interval in hours")

    # AI/Summarization (Ollama)
    ollama_host: str = Field(default="http://localhost:11434", description="Ollama server URL")

    # Storage Paths
    chroma_persist_dir: str = Field(default="./app/storage/chroma_db", description="Chroma persistence directory")
    state_dir: str = Field(default="./app/storage/state", description="State directory")

    # Feature Flags
    enable_rate_limiting: bool = Field(default=True, description="Enable rate limiting")
    rate_limit_requests_per_minute: int = Field(default=100, description="Rate limit requests per minute")

    # Logging
    log_level: str = Field(default="INFO", description="Log level")

    class Config:
        """Pydantic config."""

        env_file = ".env"
        case_sensitive = False


# Load settings on module import
settings = Settings()
