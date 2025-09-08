#!/usr/bin/env python3
"""
Monitor Stage-A Processing Status
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from config.database import SessionLocal
from database.models import Article, ProcessedArticle
from datetime import datetime, timedelta

def monitor_stage_a_status():
    """Monitor Stage-A processing status"""
    db = SessionLocal()
    
    try:
        print("Stage-A Processing Monitor")
        print("=" * 50)
        
        # Get pending articles (waiting for Stage-A)
        pending = db.query(Article).filter(Article.status == "pending").count()
        
        # Get processed articles (Stage-A completed)
        processed = db.query(ProcessedArticle).count()
        
        # Get recent processing (last 24 hours)
        yesterday = datetime.utcnow() - timedelta(days=1)
        recent_processed = db.query(ProcessedArticle).filter(
            ProcessedArticle.created_at >= yesterday
        ).count()
        
        # Get success rate
        successful = db.query(ProcessedArticle).filter(
            ProcessedArticle.stage_a_success == True
        ).count()
        
        success_rate = (successful / processed * 100) if processed > 0 else 0
        
        print(f"Pending Analysis: {pending} articles")
        print(f"Total Processed: {processed} articles")
        print(f"Recent (24h): {recent_processed} articles")
        print(f"Success Rate: {success_rate:.1f}%")
        
        # Show recent results
        print(f"\nRecent Stage-A Results:")
        recent_results = db.query(ProcessedArticle).join(
            Article, ProcessedArticle.article_id == Article.id
        ).order_by(ProcessedArticle.created_at.desc()).limit(5).all()
        
        for result in recent_results:
            article = db.query(Article).filter(Article.id == result.article_id).first()
            status = "SUCCESS" if result.stage_a_success else "FAILED"
            processing_time = result.stage_a_processing_time_ms or 0
            
            print(f"  [{status}] {article.title[:50]}... ({processing_time}ms)")
            if result.stage_a_success:
                print(f"    Category: {result.category}, Sentiment: {result.sentiment}")
                print(f"    Score: {result.newsroom_overall_score}")
        
    except Exception as e:
        print(f"Error: {e}")
    finally:
        db.close()

if __name__ == "__main__":
    monitor_stage_a_status()