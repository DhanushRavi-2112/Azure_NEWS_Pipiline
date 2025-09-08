"""
Stage-A Microservice Integration Client
Handles communication with Stage-A and stores enriched metadata
"""

import requests
import logging
from typing import Dict, Any, Optional
from datetime import datetime
from sqlalchemy.orm import Session
from database.models import Article, ProcessedArticle

logger = logging.getLogger(__name__)

class StageAClient:
    def __init__(self, stage_a_url: str = "http://localhost:3456", api_key: str = "prod-key-2025"):
        self.stage_a_url = stage_a_url
        self.api_key = api_key
        self.headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
    
    async def analyze_article(self, url: str) -> Dict[str, Any]:
        """Send article to Stage-A for comprehensive analysis"""
        endpoint = f"{self.stage_a_url}/api/v1/analyze-comprehensive"
        payload = {"url": url}
        
        try:
            response = requests.post(endpoint, json=payload, headers=self.headers, timeout=300)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            logger.error(f"Stage-A analysis failed for {url}: {e}")
            raise
    
    def store_stage_a_response(self, db: Session, article_id: int, stage_a_response: Dict[str, Any]) -> ProcessedArticle:
        """Store Stage-A response in processed_articles table"""
        
        # Check if already processed
        existing = db.query(ProcessedArticle).filter(ProcessedArticle.article_id == article_id).first()
        if existing:
            logger.info(f"Article {article_id} already processed, updating...")
            processed_article = existing
        else:
            processed_article = ProcessedArticle(article_id=article_id)
        
        try:
            # Extract data from Stage-A response
            success = stage_a_response.get("success", False)
            metadata = stage_a_response.get("metadata", {})
            
            # Processing Results
            processed_article.stage_a_success = success
            processed_article.stage_a_processing_time_ms = stage_a_response.get("processing_time_ms")
            processed_article.stage_a_error = stage_a_response.get("error")
            
            if success and metadata:
                # Article Metadata
                article_meta = metadata.get("article", {})
                processed_article.analyzed_title = article_meta.get("title")
                processed_article.analyzed_publisher = article_meta.get("publisher")
                processed_article.analyzed_author = article_meta.get("author")
                processed_article.analyzed_published_at = self._parse_datetime(article_meta.get("published_at"))
                processed_article.analyzed_language = article_meta.get("language")
                processed_article.analyzed_word_count = article_meta.get("word_count")
                
                # Classification
                classification = metadata.get("classification", {})
                processed_article.category = classification.get("category")
                processed_article.subcategory = classification.get("subcategory")
                processed_article.beats = classification.get("beats")
                processed_article.keywords = classification.get("keywords")
                processed_article.tags = classification.get("tags")
                
                # Sentiment
                sentiment_data = classification.get("sentiment", {})
                processed_article.sentiment = sentiment_data.get("label")
                processed_article.sentiment_score = sentiment_data
                processed_article.tone = classification.get("tone")
                processed_article.bias = classification.get("bias")
                
                # Summary
                summary = metadata.get("summary", {})
                processed_article.summary_abstract = summary.get("abstract")
                processed_article.summary_tldr = summary.get("tldr")
                processed_article.summary_bullets = summary.get("bullets")
                processed_article.compression_ratio = summary.get("compression_ratio")
                
                # Entities
                entities = metadata.get("entities", {})
                processed_article.entities_people = entities.get("people")
                processed_article.entities_organizations = entities.get("organizations")
                processed_article.entities_locations = entities.get("locations")
                processed_article.entities_other = entities.get("other")
                
                # Editorial
                editorial = metadata.get("editorial", {})
                processed_article.newsworthiness = editorial.get("newsworthiness")
                processed_article.fact_check = editorial.get("fact_check")
                processed_article.angles = editorial.get("angles")
                processed_article.impact = editorial.get("impact")
                processed_article.risks = editorial.get("risks")
                processed_article.pitch = editorial.get("pitch")
                
                # Quality
                quality = metadata.get("quality", {})
                processed_article.readability = quality.get("readability")
                processed_article.hallucination_risk = quality.get("hallucination_risk")
                processed_article.overall_confidence = quality.get("overall_confidence")
                
                # SEO Analysis
                seo = metadata.get("seo_analysis", {})
                processed_article.seo_visibility = seo.get("search_engine_visibility")
                processed_article.seo_keyword_density = seo.get("keyword_density")
                processed_article.seo_content_freshness = seo.get("content_freshness")
                processed_article.seo_readability = seo.get("readability_score")
                processed_article.seo_trending_potential = seo.get("trending_potential")
                processed_article.seo_search_intent = seo.get("search_intent_match")
                processed_article.seo_target_keywords = seo.get("target_keywords")
                processed_article.seo_content_gaps = seo.get("content_gaps")
                processed_article.seo_competitor_analysis = seo.get("competitor_seo_analysis")
                processed_article.seo_overall_score = seo.get("overall_seo_score")
                
                # Newsroom Pitch Score
                newsroom = metadata.get("newsroom_pitch_score", {})
                processed_article.newsroom_newsworthiness = newsroom.get("newsworthiness")
                processed_article.newsroom_audience_appeal = newsroom.get("audience_appeal")
                processed_article.newsroom_exclusivity = newsroom.get("exclusivity_factor")
                processed_article.newsroom_social_potential = newsroom.get("social_media_potential")
                processed_article.newsroom_urgency = newsroom.get("editorial_urgency")
                processed_article.newsroom_resources = newsroom.get("resource_requirements")
                processed_article.newsroom_brand_alignment = newsroom.get("brand_alignment")
                processed_article.newsroom_controversy_risk = newsroom.get("controversy_risk")
                processed_article.newsroom_followup_potential = newsroom.get("follow_up_potential")
                processed_article.newsroom_overall_score = newsroom.get("overall_pitch_score")
                processed_article.newsroom_recommendation = newsroom.get("recommendation")
                processed_article.newsroom_pitch_summary = newsroom.get("pitch_summary")
                processed_article.newsroom_headline_suggestions = newsroom.get("headline_suggestions")
                processed_article.newsroom_target_audience = newsroom.get("target_audience")
                processed_article.newsroom_timeline = newsroom.get("publishing_timeline")
                processed_article.newsroom_pitch_notes = newsroom.get("pitch_notes")
                
                # Provenance
                provenance = metadata.get("provenance", {})
                processed_article.pipeline_version = provenance.get("pipeline_version")
                processed_article.models_used = provenance.get("models")
                processed_article.processing_notes = provenance.get("notes")
            
            # Store full response for backup/debugging
            processed_article.full_stage_a_response = stage_a_response
            processed_article.processing_version = "1.0.0"
            
            # Save to database
            if existing:
                # Update existing record
                processed_article.updated_at = datetime.utcnow()
            else:
                # Add new record
                db.add(processed_article)
            
            db.commit()
            db.refresh(processed_article)
            
            logger.info(f"Successfully stored Stage-A analysis for article {article_id}")
            return processed_article
            
        except Exception as e:
            db.rollback()
            logger.error(f"Failed to store Stage-A response for article {article_id}: {e}")
            raise
    
    def _parse_datetime(self, dt_str: Optional[str]) -> Optional[datetime]:
        """Parse datetime string from Stage-A response"""
        if not dt_str:
            return None
        
        try:
            # Handle ISO format with timezone
            if dt_str.endswith('Z'):
                return datetime.fromisoformat(dt_str.replace('Z', '+00:00'))
            elif '+' in dt_str or dt_str.endswith(tuple([f'+{i:02d}:00' for i in range(24)])):
                return datetime.fromisoformat(dt_str)
            else:
                return datetime.fromisoformat(dt_str)
        except (ValueError, AttributeError):
            logger.warning(f"Could not parse datetime: {dt_str}")
            return None

    async def process_article_pipeline(self, db: Session, article: Article) -> Optional[ProcessedArticle]:
        """Complete pipeline: analyze article with Stage-A and store results"""
        try:
            # Mark article as processing
            article.status = "processing"
            article.processing_started_at = datetime.utcnow()
            db.commit()
            
            # Send to Stage-A for analysis
            logger.info(f"Sending article {article.id} to Stage-A: {article.url}")
            stage_a_response = await self.analyze_article(article.url)
            
            # Store the results
            processed_article = self.store_stage_a_response(db, article.id, stage_a_response)
            
            # Update article status
            article.status = "completed"
            article.processing_completed_at = datetime.utcnow()
            db.commit()
            
            logger.info(f"Article {article.id} successfully processed by Stage-A")
            return processed_article
            
        except Exception as e:
            # Update article status on error
            article.status = "failed"
            article.processing_error = str(e)
            article.processing_completed_at = datetime.utcnow()
            db.commit()
            
            logger.error(f"Failed to process article {article.id}: {e}")
            return None

# Global client instance
stage_a_client = StageAClient()

def get_stage_a_client() -> StageAClient:
    """Get Stage-A client instance"""
    return stage_a_client