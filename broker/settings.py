import os
from typing import Optional

class Settings:
    # Akash configuration
    AKASH_NODE: str = os.getenv("AKASH_NODE", "https://rpc.akash.forbole.com:443")
    AKASH_CHAIN_ID: str = os.getenv("AKASH_CHAIN_ID", "akashnet-2")
    AKASH_KEYRING_BACKEND: str = os.getenv("AKASH_KEYRING_BACKEND", "os")
    AKASH_FROM: str = os.getenv("AKASH_FROM", "")
    
    # Billing configuration
    STRIPE_SECRET_KEY: str = os.getenv("STRIPE_SECRET_KEY", "")
    STRIPE_WEBHOOK_SECRET: str = os.getenv("STRIPE_WEBHOOK_SECRET", "")
    
    # Pricing (uakt per hour)
    LEASE_PRICE_UAKT: int = int(os.getenv("LEASE_PRICE_UAKT", "5000"))
    
    # Gaming configuration
    SUNSHINE_PORT: int = int(os.getenv("SUNSHINE_PORT", "47984"))
    SUNSHINE_UDP_PORT: int = int(os.getenv("SUNSHINE_UDP_PORT", "47989"))
    
    # API configuration
    API_HOST: str = os.getenv("API_HOST", "0.0.0.0")
    API_PORT: int = int(os.getenv("API_PORT", "8000"))
    
    @classmethod
    def validate(cls) -> None:
        """Validate required environment variables"""
        required_vars = ["AKASH_FROM", "STRIPE_SECRET_KEY"]
        missing = [var for var in required_vars if not getattr(cls, var)]
        if missing:
            raise ValueError(f"Missing required environment variables: {', '.join(missing)}")

settings = Settings()