"""
Filtered Pipeline: Miniflux → Volume Reduction → Stage-A → Database
Focus: Smart filtering to reduce processing load by 20-30%
"""

from fastapi import FastAPI, HTTPException, Depends, Request, BackgroundTasks
from sqlalchemy.orm import Session
from typing import Optional, List, Dict, Any
from datetime import datetime
from pydantic import BaseModel, HttpUrl
import logging
import sys
import os

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Load environment
from dotenv import load_dotenv
load_dotenv()

from config.database import get_db
from database.models import Article, ProcessedArticle
from services.stage_a_client import get_stage_a_client
from app.volume_reduction_pipeline import filter_articles_batch, get_volume_reducer
import hashlib

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Filtered News Pipeline", 
    version="2.0.0",
    description="Smart Volume Reduction + Stage-A Analysis Pipeline"
)

# Schemas
class MinifluxEntry(BaseModel):
    id: int
    user_id: int
    feed_id: int
    title: str
    url: HttpUrl
    author: Optional[str] = None
    content: Optional[str] = None
    published_at: datetime
    created_at: datetime
    status: str
    starred: bool
    feed: Optional[dict] = None

class WebhookPayload(BaseModel):
    event_type: str
    entries: Optional[List[MinifluxEntry]] = None
    entry: Optional[MinifluxEntry] = None

class FilteringStats(BaseModel):
    total_input: int
    total_filtered: int
    processed: int
    reduction_percentage: float
    filter_breakdown: Dict[str, int]

# Global statistics
filtering_stats = {
    "session_total": 0,
    "session_filtered": 0,
    "session_processed": 0,
    "recent_batches": []
}

@app.get("/")
def read_root():
    return {
        "service": "Filtered News Pipeline",
        "version": "2.0.0",
        "features": [
            "20-30% volume reduction",
            "Wire service filtering", 
            "PR content detection",
            "Advanced deduplication",
            "Stage-A analysis for quality content"
        ],
        "status": "running"
    }

@app.get("/filtering/stats")
def get_filtering_statistics():
    """Get detailed filtering statistics"""
    reducer = get_volume_reducer()
    
    total_input = filtering_stats["session_total"]
    total_filtered = filtering_stats["session_filtered"] 
    reduction_pct = (total_filtered / total_input * 100) if total_input > 0 else 0
    
    return {
        "session_stats": {
            "total_input": total_input,
            "total_filtered": total_filtered,
            "total_processed": filtering_stats["session_processed"],
            "reduction_percentage": round(reduction_pct, 1)
        },
        "filter_config": reducer.get_filtering_stats(),
        "recent_batches": filtering_stats["recent_batches"][-10:]  # Last 10 batches
    }

def store_filtered_article(entry: MinifluxEntry, db: Session) -> Article:
    """Store article that passed filtering"""
    content = entry.content or ""
    content_hash = hashlib.sha256(f"{entry.title}{content}".encode()).hexdigest()
    
    article = Article(
        entry_id=str(entry.id),
        feed_id=str(entry.feed_id),
        feed_title=(entry.feed or {}).get('title', 'Unknown Feed'),
        title=entry.title,
        url=str(entry.url),
        content=content,
        author=entry.author,
        published_at=entry.published_at,
        status="pending",
        language="en",
        content_hash=content_hash,
        created_at=datetime.utcnow()
    )
    
    db.add(article)
    db.commit()
    db.refresh(article)
    
    logger.info(f"📰 Stored filtered article {article.id}: {article.title[:50]}...")
    return article

async def process_with_stage_a(article_id: int) -> Optional[ProcessedArticle]:
    """Process high-quality article with Stage-A"""
    # Create new session for background task
    from config.database import SessionLocal
    db = SessionLocal()
    
    try:
        # Re-fetch article with new session
        article = db.query(Article).filter(Article.id == article_id).first()
        if not article:
            logger.error(f"Article {article_id} not found for Stage-A processing")
            return None
            
        logger.info(f"🔬 Stage-A analysis for: {article.title[:50]}...")
        
        stage_a_client = get_stage_a_client()
        processed_article = await stage_a_client.process_article_pipeline(db, article)
        
        if processed_article and processed_article.stage_a_success:
            logger.info(f"✅ Stage-A completed: {article.title[:50]}...")
            return processed_article
        else:
            logger.warning(f"⚠️ Stage-A failed: {article.title[:50]}...")
            return None
            
    except Exception as e:
        if str(e).strip():  # Only log if error message is not empty
            logger.error(f"❌ Stage-A error for article {article_id}: {e}")
        return None
    finally:
        db.close()

@app.post("/webhook/miniflux/filtered")
async def filtered_webhook_handler(
    request: Request,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db)
):
    """
    Main filtered webhook: Miniflux → Filter → Stage-A → DB
    """
    try:
        # Parse webhook data
        data = await request.json()
        logger.info(f"📨 Received webhook: {data.get('event_type', 'unknown')}")
        
        # Extract entries
        entries = []
        if 'entries' in data and data['entries']:
            entries = [MinifluxEntry(**entry) for entry in data['entries']]
        elif 'entry' in data and data['entry']:
            entries = [MinifluxEntry(**data['entry'])]
        else:
            return {"status": "no_entries", "processed": 0}
        
        # Convert to dict format for filtering
        article_data = []
        for entry in entries:
            article_data.append({
                "id": entry.id,
                "title": entry.title,
                "content": entry.content or "",
                "url": str(entry.url),
                "published_at": entry.published_at,
                "feed_title": (entry.feed or {}).get('title', 'Unknown'),
                "entry": entry  # Keep original for later
            })
        
        # Apply volume reduction filtering
        filtered_articles, filter_stats = filter_articles_batch(article_data, db)
        
        # Update global stats
        filtering_stats["session_total"] += filter_stats["total_input"]
        filtering_stats["session_filtered"] += filter_stats["total_filtered"] 
        filtering_stats["session_processed"] += filter_stats["processed"]
        
        # Store batch stats
        batch_stats = {
            "timestamp": datetime.now().isoformat(),
            "input": filter_stats["total_input"],
            "filtered": filter_stats["total_filtered"],
            "processed": filter_stats["processed"],
            "reduction_pct": round((filter_stats["total_filtered"] / filter_stats["total_input"]) * 100, 1) if filter_stats["total_input"] > 0 else 0
        }
        filtering_stats["recent_batches"].append(batch_stats)
        
        # Keep only last 20 batch records
        if len(filtering_stats["recent_batches"]) > 20:
            filtering_stats["recent_batches"] = filtering_stats["recent_batches"][-20:]
        
        # Process filtered articles
        stored_articles = []
        for article_data in filtered_articles:
            try:
                # Store in database
                article = store_filtered_article(article_data["entry"], db)
                stored_articles.append(article)
                
                # Queue for Stage-A analysis
                background_tasks.add_task(process_with_stage_a, article.id)
                
            except Exception as e:
                logger.error(f"Error storing article {article_data['id']}: {e}")
                continue
        
        reduction_pct = round((filter_stats["total_filtered"] / filter_stats["total_input"]) * 100, 1) if filter_stats["total_input"] > 0 else 0
        
        return {
            "status": "success",
            "filtering_summary": {
                "input_articles": filter_stats["total_input"],
                "filtered_out": filter_stats["total_filtered"],
                "will_process": filter_stats["processed"],
                "reduction_percentage": f"{reduction_pct}%"
            },
            "stored_for_analysis": len(stored_articles),
            "filter_breakdown": {
                k: v for k, v in filter_stats.items() 
                if k not in ["total_input", "total_filtered", "processed"] and v > 0
            },
            "message": f"Filtered {reduction_pct}% of articles, processing {len(stored_articles)} quality articles"
        }
        
    except Exception as e:
        if str(e).strip():  # Only log if error message is not empty
            logger.error(f"Filtered webhook error: {e}")
            raise HTTPException(status_code=500, detail=f"Filtering pipeline failed: {str(e)}")
        else:
            logger.error("Filtered webhook error: Empty exception caught")
            raise HTTPException(status_code=500, detail="Unknown filtering error")

@app.post("/webhook/miniflux/test-filter")
async def test_filter_endpoint(request: Request, db: Session = Depends(get_db)):
    """Test filtering without processing - shows what would be filtered"""
    try:
        data = await request.json()
        
        # Extract entries
        entries = []
        if 'entries' in data and data['entries']:
            entries = [MinifluxEntry(**entry) for entry in data['entries']]
        elif 'entry' in data and data['entry']:
            entries = [MinifluxEntry(**data['entry'])]
        else:
            return {"status": "no_entries"}
        
        # Convert to dict format
        article_data = []
        for entry in entries:
            article_data.append({
                "id": entry.id,
                "title": entry.title,
                "content": entry.content or "",
                "url": str(entry.url)
            })
        
        # Test filtering (without storing)
        filtered_articles, filter_stats = filter_articles_batch(article_data, db)
        
        # Show detailed results
        results = []
        reducer = get_volume_reducer()
        
        for article_data in article_data:
            should_process, reasons = reducer.should_process_article(
                article_data["title"], 
                article_data["content"], 
                article_data["url"]
            )
            
            results.append({
                "id": article_data["id"],
                "title": article_data["title"][:60] + "...",
                "will_process": should_process,
                "filter_reasons": reasons if not should_process else []
            })
        
        reduction_pct = round((filter_stats["total_filtered"] / filter_stats["total_input"]) * 100, 1) if filter_stats["total_input"] > 0 else 0
        
        return {
            "test_results": results,
            "summary": {
                "total_articles": len(article_data),
                "would_filter": filter_stats["total_filtered"],
                "would_process": filter_stats["processed"],
                "reduction_percentage": f"{reduction_pct}%"
            },
            "filter_breakdown": filter_stats
        }
        
    except Exception as e:
        logger.error(f"Filter test error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/articles/analysis-queue")
def get_analysis_queue(db: Session = Depends(get_db)):
    """Get articles pending Stage-A analysis"""
    pending = (
        db.query(Article)
        .filter(Article.status == "pending")
        .order_by(Article.created_at.desc())
        .limit(20)
        .all()
    )
    
    return {
        "pending_analysis": len(pending),
        "articles": [
            {
                "id": article.id,
                "title": article.title[:60] + "...",
                "created_at": article.created_at,
                "feed_title": article.feed_title
            }
            for article in pending
        ]
    }

@app.get("/articles/recent-analysis")
def get_recent_analysis(limit: int = 10, db: Session = Depends(get_db)):
    """Get recent Stage-A analysis results"""
    processed = (
        db.query(ProcessedArticle)
        .join(Article, ProcessedArticle.article_id == Article.id)
        .order_by(ProcessedArticle.created_at.desc())
        .limit(limit)
        .all()
    )
    
    results = []
    for p in processed:
        article = db.query(Article).filter(Article.id == p.article_id).first()
        results.append({
            "article_id": p.article_id,
            "title": article.title if article else "Unknown",
            "category": p.category,
            "sentiment": p.sentiment,
            "newsroom_score": p.newsroom_overall_score,
            "processing_time_ms": p.stage_a_processing_time_ms,
            "created_at": p.created_at
        })
    
    return {"recent_analysis": results}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8002)