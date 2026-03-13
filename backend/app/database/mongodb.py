from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase
from app.config import get_settings
import logging

logger = logging.getLogger(__name__)

settings = get_settings()


class MongoDB:
    client: AsyncIOMotorClient | None = None
    db: AsyncIOMotorDatabase | None = None


mongo = MongoDB()


async def connect_db() -> None:
    """Create MongoDB connection pool on startup."""
    try:
        mongo.client = AsyncIOMotorClient(
            settings.MONGODB_URI,
            serverSelectionTimeoutMS=5000,
            maxPoolSize=10,
        )
        mongo.db = mongo.client[settings.DATABASE_NAME]
        # Ping to verify connection
        await mongo.client.admin.command("ping")
        logger.info("✅ Connected to MongoDB Atlas")
    except Exception as e:
        logger.error(f"❌ MongoDB connection failed: {e}")
        raise


async def close_db() -> None:
    """Close MongoDB connection pool on shutdown."""
    if mongo.client:
        mongo.client.close()
        logger.info("🔌 MongoDB connection closed")


def get_db() -> AsyncIOMotorDatabase:
    """Dependency injection — returns active DB."""
    if mongo.db is None:
        raise RuntimeError("Database not initialized. Call connect_db() first.")
    return mongo.db
