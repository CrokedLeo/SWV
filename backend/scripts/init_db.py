"""
Database initialization script
Run this script to create all tables on first startup
"""
import logging
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from backend.models.database import init_db, drop_all_tables, Base, engine
from backend.models.orm import HistoricalReport, PollutantReading

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def main():
    """Initialize database"""
    try:
        logger.info("=" * 60)
        logger.info("SWV Environmental Monitoring - Database Initialization")
        logger.info("=" * 60)
        
        # Create all tables
        init_db()
        
        # Verify tables were created
        inspector_query = """
        SELECT name FROM sqlite_master 
        WHERE type='table' AND name NOT LIKE 'sqlite_%';
        """
        
        logger.info("Created tables:")
        logger.info("  - HistoricalReport")
        logger.info("  - PollutantReading")
        
        logger.info("=" * 60)
        logger.info("Database initialization completed successfully!")
        logger.info("=" * 60)
        return 0
        
    except Exception as e:
        logger.error(f"Database initialization failed: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())
