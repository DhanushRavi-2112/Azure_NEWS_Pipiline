import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config.database import engine, Base
from database.models import Article, ProcessedArticle

def init_database():
    """Initialize database tables"""
    Base.metadata.create_all(bind=engine)
    print("Database tables created successfully!")

if __name__ == "__main__":
    init_database()