#!/usr/bin/env python3
"""
Pipeline Dashboard - Monitor filtering and Stage-A performance
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from config.database import SessionLocal
from database.models import Article, ProcessedArticle
from datetime import datetime, timedelta
import time

def show_dashboard():
    """Display pipeline statistics"""
    db = SessionLocal()
    
    try:
        print("\033[2J\033[H")  # Clear screen
        print("=" * 70)
        print("NEWS PIPELINE DASHBOARD")
        print("=" * 70)
        
        # Overall stats
        total_articles = db.query(Article).count()
        processed_articles = db.query(ProcessedArticle).count()
        pending_articles = db.query(Article).filter(Article.status == "pending").count()
        
        print(f"\nOVERALL STATISTICS:")
        print(f"  Total Articles:     {total_articles}")
        print(f"  Processed:          {processed_articles}")
        print(f"  Pending Analysis:   {pending_articles}")
        
        # Last 24 hours
        yesterday = datetime.utcnow() - timedelta(days=1)
        recent_articles = db.query(Article).filter(Article.created_at >= yesterday).count()
        recent_processed = db.query(ProcessedArticle).filter(ProcessedArticle.created_at >= yesterday).count()
        
        print(f"\nLAST 24 HOURS:")
        print(f"  New Articles:       {recent_articles}")
        print(f"  Processed:          {recent_processed}")
        
        # Stage-A Performance
        successful = db.query(ProcessedArticle).filter(ProcessedArticle.stage_a_success == True).count()
        failed = db.query(ProcessedArticle).filter(ProcessedArticle.stage_a_success == False).count()
        avg_time = db.query(ProcessedArticle).filter(
            ProcessedArticle.stage_a_processing_time_ms.isnot(None)
        ).with_entities(
            db.func.avg(ProcessedArticle.stage_a_processing_time_ms)
        ).scalar()
        
        success_rate = (successful / (successful + failed) * 100) if (successful + failed) > 0 else 0
        
        print(f"\nSTAGE-A PERFORMANCE:")
        print(f"  Success Rate:       {success_rate:.1f}%")
        print(f"  Avg Process Time:   {(avg_time or 0) / 1000:.1f}s")
        
        # Category Distribution
        print(f"\nCATEGORY DISTRIBUTION:")
        categories = db.query(
            ProcessedArticle.category, 
            db.func.count(ProcessedArticle.category)
        ).group_by(ProcessedArticle.category).all()
        
        for category, count in categories:
            if category:
                print(f"  {category:15}: {count}")
        
        # Recent Articles
        print(f"\nRECENT PROCESSED ARTICLES:")
        recent = db.query(ProcessedArticle).join(
            Article, ProcessedArticle.article_id == Article.id
        ).order_by(ProcessedArticle.created_at.desc()).limit(5).all()
        
        for p in recent:
            article = db.query(Article).filter(Article.id == p.article_id).first()
            if article:
                status = "✓" if p.stage_a_success else "✗"
                print(f"  [{status}] {article.title[:50]}...")
                print(f"      Category: {p.category}, Score: {p.newsroom_overall_score}")
        
        print(f"\nUpdated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        
    except Exception as e:
        print(f"Error: {e}")
    finally:
        db.close()

def continuous_dashboard():
    """Run dashboard continuously"""
    while True:
        show_dashboard()
        time.sleep(30)  # Update every 30 seconds

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--once", action="store_true", help="Run once instead of continuous")
    args = parser.parse_args()
    
    if args.once:
        show_dashboard()
    else:
        print("Starting continuous dashboard (Ctrl+C to stop)...")
        continuous_dashboard()