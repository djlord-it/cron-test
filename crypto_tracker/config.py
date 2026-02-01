import os
from dataclasses import dataclass


@dataclass
class Config:
    database_url: str
    easycron_url: str
    webhook_url: str
    webhook_port: int
    webhook_secret: str
    cron_expression: str

    @classmethod
    def from_env(cls) -> "Config":
        webhook_host = os.environ.get("WEBHOOK_HOST", "http://localhost")
        webhook_port = int(os.environ.get("PORT", os.environ.get("WEBHOOK_PORT", "9090")))

        if os.environ.get("WEBHOOK_URL"):
            webhook_url = os.environ.get("WEBHOOK_URL")
        elif "localhost" in webhook_host:
            webhook_url = f"{webhook_host}:{webhook_port}/webhook"
        else:
            webhook_url = f"{webhook_host}/webhook"

        return cls(
            database_url=os.environ.get(
                "DATABASE_URL", "postgres://localhost/crypto_tracker?sslmode=disable"
            ),
            easycron_url=os.environ.get("EASYCRON_URL", "http://localhost:8080"),
            webhook_url=webhook_url,
            webhook_port=webhook_port,
            webhook_secret=os.environ.get("WEBHOOK_SECRET", "my-secret-key"),
            cron_expression=os.environ.get("CRON_EXPRESSION", "* * * * *"),
        )
