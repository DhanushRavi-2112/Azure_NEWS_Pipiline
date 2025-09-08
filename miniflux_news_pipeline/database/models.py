from sqlalchemy import Column, Integer, String, Text, DateTime, Boolean, JSON, Index, UniqueConstraint
from sqlalchemy.sql import func
from config.database import Base
from datetime import datetime

class Article(Base):
    __tablename__ = "articles"
    
    id = Column(Integer, primary_key=True, index=True)
    
    # Miniflux webhook data
    entry_id = Column(String(255), unique=True, nullable=False, index=True)
    feed_id = Column(String(255), nullable=False, index=True)
    feed_title = Column(String(500))
    
    # Article content
    title = Column(Text, nullable=False)
    url = Column(Text, nullable=False)
    content = Column(Text)
    author = Column(String(255))
    published_at = Column(DateTime, nullable=False)
    
    # Processing status
    status = Column(String(50), default="pending", index=True)
    processing_started_at = Column(DateTime)
    processing_completed_at = Column(DateTime)
    processing_error = Column(Text)
    
    # Metadata
    language = Column(String(10))
    categories = Column(JSON)
    tags = Column(JSON)
    
    # Deduplication
    content_hash = Column(String(64), index=True)
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Indexes for performance
    __table_args__ = (
        Index('idx_published_at_desc', published_at.desc()),
        Index('idx_status_created_at', status, created_at),
        Index('idx_feed_id_published_at', feed_id, published_at),
    )

class ProcessedArticle(Base):
    __tablename__ = "processed_articles"
    
    id = Column(Integer, primary_key=True, index=True)
    article_id = Column(Integer, nullable=False, index=True)
    
    # Stage-A Processing Results
    stage_a_success = Column(Boolean, default=False)
    stage_a_processing_time_ms = Column(Integer)
    stage_a_error = Column(Text)
    
    # Article Metadata (from Stage-A)
    analyzed_title = Column(Text)
    analyzed_publisher = Column(String(255))
    analyzed_author = Column(String(255))
    analyzed_published_at = Column(DateTime)
    analyzed_language = Column(String(10))
    analyzed_word_count = Column(Integer)
    
    # Classification
    category = Column(String(100), index=True)
    subcategory = Column(String(100))
    beats = Column(JSON)
    keywords = Column(JSON)
    tags = Column(JSON)
    
    # Sentiment Analysis
    sentiment = Column(String(50), index=True)
    sentiment_score = Column(JSON)
    tone = Column(JSON)
    bias = Column(JSON)
    
    # Summary
    summary_abstract = Column(Text)
    summary_tldr = Column(Text)
    summary_bullets = Column(JSON)
    compression_ratio = Column(JSON)
    
    # Entities (People, Organizations, Locations)
    entities_people = Column(JSON)
    entities_organizations = Column(JSON)
    entities_locations = Column(JSON)
    entities_other = Column(JSON)
    
    # Editorial Analysis
    newsworthiness = Column(JSON)
    fact_check = Column(JSON)
    angles = Column(JSON)
    impact = Column(JSON)
    risks = Column(JSON)
    pitch = Column(JSON)
    
    # Quality Metrics
    readability = Column(JSON)
    hallucination_risk = Column(JSON)
    overall_confidence = Column(JSON)
    
    # SEO Analysis
    seo_visibility = Column(JSON)
    seo_keyword_density = Column(JSON)
    seo_content_freshness = Column(JSON)
    seo_readability = Column(JSON)
    seo_trending_potential = Column(JSON)
    seo_search_intent = Column(String(100))
    seo_target_keywords = Column(JSON)
    seo_content_gaps = Column(JSON)
    seo_competitor_analysis = Column(JSON)
    seo_overall_score = Column(JSON)
    
    # Newsroom Pitch Score
    newsroom_newsworthiness = Column(JSON)
    newsroom_audience_appeal = Column(JSON)
    newsroom_exclusivity = Column(JSON)
    newsroom_social_potential = Column(JSON)
    newsroom_urgency = Column(JSON)
    newsroom_resources = Column(JSON)
    newsroom_brand_alignment = Column(JSON)
    newsroom_controversy_risk = Column(JSON)
    newsroom_followup_potential = Column(JSON)
    newsroom_overall_score = Column(JSON)
    newsroom_recommendation = Column(String(50))
    newsroom_pitch_summary = Column(Text)
    newsroom_headline_suggestions = Column(JSON)
    newsroom_target_audience = Column(JSON)
    newsroom_timeline = Column(String(100))
    newsroom_pitch_notes = Column(JSON)
    
    # Provenance
    pipeline_version = Column(String(50))
    models_used = Column(JSON)
    processing_notes = Column(Text)
    
    # Full Stage-A Response (for backup/debugging)
    full_stage_a_response = Column(JSON)
    
    # Processing metadata
    processing_profile = Column(String(50), default="stage-a-full")  # stage-a-full, stage-a-light
    processing_version = Column(String(20))
    
    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    __table_args__ = (
        UniqueConstraint('article_id', name='uq_article_id'),
        Index('idx_category_sentiment', category, sentiment),
        Index('idx_processing_time', 'stage_a_processing_time_ms'),
        # Note: Removed JSON column indexes as they need special handling in PostgreSQL
    )