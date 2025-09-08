"""
Volume Reduction Pipeline: Smart Filtering & Deduplication
Focus: 20-30% volume reduction before Stage-A processing
"""

import hashlib
import re
import logging
from typing import List, Dict, Set, Optional, Tuple
from datetime import datetime, timedelta
import pytz
from difflib import SequenceMatcher
from sqlalchemy.orm import Session
from database.models import Article

logger = logging.getLogger(__name__)

class VolumeReducer:
    """Advanced content filtering and deduplication system"""
    
    def __init__(self):
        # Content similarity threshold (0.8 = 80% similar)
        self.similarity_threshold = 0.8
        self.min_content_length = 150  # Minimum viable content length
        
        # Wire service patterns
        self.wire_service_patterns = [
            r'\(Reuters\)',
            r'\(AP\)',
            r'\(AFP\)',
            r'\(Bloomberg\)',
            r'Press Trust of India',
            r'PTI\s*-',
            r'ANI\s*-',
            r'IANS\s*-',
            r'UNI\s*-',
            r'\(IANS\)',
            r'\(PTI\)',
            r'News agencies',
            r'Wire services',
            r'Courtesy:.*Reuters',
            r'Source:.*AP\s',
        ]
        
        # PR/Promotional content patterns
        self.pr_patterns = [
            r'press release',
            r'FOR IMMEDIATE RELEASE',
            r'Business Wire',
            r'PR Newswire',
            r'PRWeb',
            r'Contact:.*@.*\.',
            r'About [A-Z][a-zA-Z\s]*:',
            r'For more information.*visit',
            r'Media Contact:',
            r'Disclaimer:.*investment',
            r'This is a sponsored',
            r'Paid advertisement',
        ]
        
        # Low-value content patterns
        self.low_value_patterns = [
            r'^Live updates:',
            r'^Breaking:.*\.$',  # Single line breaking news
            r'More details to follow',
            r'This is a developing story',
            r'Story will be updated',
            r'^\w+\s+\w+\s*-\s*$',  # Just location-source
            r'No additional details',
            r'Developing\.\.\.',
        ]
        
        # Cache for recent content hashes (last 24 hours)
        self.recent_hashes: Set[str] = set()
        self.hash_cache_expiry = timedelta(hours=24)
        self.last_cache_cleanup = datetime.now()
        
    def create_content_signature(self, title: str, content: str) -> str:
        """Create content signature for deduplication"""
        # Normalize text for comparison
        normalized_title = self._normalize_text(title)
        normalized_content = self._normalize_text(content[:1000])  # First 1000 chars
        
        combined = f"{normalized_title}|{normalized_content}"
        return hashlib.md5(combined.encode()).hexdigest()
    
    def create_fuzzy_signature(self, title: str, content: str) -> str:
        """Create fuzzy signature for near-duplicate detection"""
        # Extract key phrases and entities
        title_words = set(re.findall(r'\b[A-Za-z]{4,}\b', title.lower()))
        content_words = set(re.findall(r'\b[A-Za-z]{4,}\b', content[:500].lower()))
        
        # Get top words by frequency
        key_words = sorted(title_words.union(content_words))[:10]
        
        signature = "|".join(sorted(key_words))
        return hashlib.md5(signature.encode()).hexdigest()
    
    def _normalize_text(self, text: str) -> str:
        """Normalize text for comparison"""
        if not text:
            return ""
        
        # Remove common variations
        text = re.sub(r'\s+', ' ', text)  # Normalize whitespace
        text = re.sub(r'[^\w\s]', '', text)  # Remove punctuation
        text = re.sub(r'\b(the|a|an|and|or|but|in|on|at|to|for|of|with|by)\b', '', text.lower())
        
        return text.strip()
    
    def is_wire_service_content(self, title: str, content: str) -> bool:
        """Detect wire service or syndicated content"""
        full_text = f"{title} {content}"
        
        for pattern in self.wire_service_patterns:
            if re.search(pattern, full_text, re.IGNORECASE):
                logger.debug(f"Wire service detected: {pattern}")
                return True
                
        # Check for multiple bylines (syndicated content)
        byline_count = len(re.findall(r'\b(By|Reporter|Correspondent):', full_text))
        if byline_count > 2:
            logger.debug("Multiple bylines detected (syndicated)")
            return True
            
        return False
    
    def is_pr_content(self, title: str, content: str) -> bool:
        """Detect PR/promotional content"""
        full_text = f"{title} {content}"
        
        for pattern in self.pr_patterns:
            if re.search(pattern, full_text, re.IGNORECASE):
                logger.debug(f"PR content detected: {pattern}")
                return True
                
        # Check for excessive company mentions
        company_mentions = len(re.findall(r'\b[A-Z][a-zA-Z]*\s+(?:Inc|Corp|Ltd|LLC|Co)\b', content))
        if company_mentions > 5:
            logger.debug("Excessive company mentions (promotional)")
            return True
            
        return False
    
    def is_low_value_content(self, title: str, content: str) -> bool:
        """Detect low-value content"""
        # Check content length
        if len(content.strip()) < self.min_content_length:
            logger.debug("Content too short")
            return True
        
        # Check for low-value patterns
        full_text = f"{title} {content}"
        for pattern in self.low_value_patterns:
            if re.search(pattern, full_text, re.IGNORECASE):
                logger.debug(f"Low-value pattern detected: {pattern}")
                return True
        
        # Check for excessive repetition
        words = content.split()
        if len(set(words)) < len(words) * 0.3:  # Less than 30% unique words
            logger.debug("Excessive repetition detected")
            return True
            
        return False
    
    def calculate_similarity(self, text1: str, text2: str) -> float:
        """Calculate text similarity using sequence matching"""
        return SequenceMatcher(None, text1, text2).ratio()
    
    def is_duplicate(self, title: str, content: str, existing_articles: List[Article]) -> Tuple[bool, Optional[str]]:
        """Check if content is duplicate or near-duplicate"""
        
        # Exact hash check
        content_hash = self.create_content_signature(title, content)
        if content_hash in self.recent_hashes:
            return True, "exact_duplicate"
        
        # Fuzzy duplicate check
        fuzzy_hash = self.create_fuzzy_signature(title, content)
        current_normalized = self._normalize_text(f"{title} {content[:500]}")
        
        for article in existing_articles:
            # Skip if too old (older than 7 days)
            if article.created_at:
                # Make both datetimes timezone-aware for comparison
                article_time = article.created_at
                if article_time.tzinfo is None:
                    article_time = pytz.UTC.localize(article_time)
                
                current_time = datetime.now(pytz.UTC)
                if (current_time - article_time).days > 7:
                    continue
            
            # Check fuzzy similarity
            existing_fuzzy = self.create_fuzzy_signature(article.title, article.content or "")
            if fuzzy_hash == existing_fuzzy:
                return True, "fuzzy_duplicate"
            
            # Check content similarity
            existing_normalized = self._normalize_text(f"{article.title} {(article.content or '')[:500]}")
            similarity = self.calculate_similarity(current_normalized, existing_normalized)
            
            if similarity >= self.similarity_threshold:
                logger.debug(f"High similarity ({similarity:.2f}) with article {article.id}")
                return True, "similar_content"
        
        # Add to recent hashes
        self.recent_hashes.add(content_hash)
        return False, None
    
    def should_process_article(
        self, 
        title: str, 
        content: str, 
        url: str,
        existing_articles: List[Article] = None
    ) -> Tuple[bool, List[str]]:
        """
        Main filtering logic - decide if article should be processed
        Returns: (should_process, reasons_for_rejection)
        """
        rejection_reasons = []
        
        # 1. Content quality checks
        if self.is_low_value_content(title, content):
            rejection_reasons.append("low_value_content")
        
        # 2. Wire service filtering
        if self.is_wire_service_content(title, content):
            rejection_reasons.append("wire_service")
        
        # 3. PR content filtering
        if self.is_pr_content(title, content):
            rejection_reasons.append("pr_content")
        
        # 4. Duplicate detection
        if existing_articles:
            is_dup, dup_type = self.is_duplicate(title, content, existing_articles)
            if is_dup:
                rejection_reasons.append(f"duplicate_{dup_type}")
        
        # 5. URL-based filtering
        if self._is_filtered_url(url):
            rejection_reasons.append("filtered_url")
        
        should_process = len(rejection_reasons) == 0
        return should_process, rejection_reasons
    
    def _is_filtered_url(self, url: str) -> bool:
        """Filter based on URL patterns"""
        filtered_patterns = [
            r'/press-release/',
            r'/pr/',
            r'/advertisement/',
            r'/sponsored/',
            r'/jobs/',
            r'/careers/',
            r'/obituary/',
            r'/weather/',
            r'/sports-scores/',
            r'/stock-prices/',
        ]
        
        for pattern in filtered_patterns:
            if re.search(pattern, url, re.IGNORECASE):
                return True
        return False
    
    def cleanup_cache(self):
        """Clean up expired cache entries"""
        current_time = datetime.now()
        if current_time - self.last_cache_cleanup > self.hash_cache_expiry:
            self.recent_hashes.clear()
            self.last_cache_cleanup = current_time
            logger.info("Cleaned up deduplication cache")
    
    def get_filtering_stats(self) -> Dict[str, int]:
        """Get filtering statistics"""
        return {
            "cache_size": len(self.recent_hashes),
            "similarity_threshold": self.similarity_threshold,
            "min_content_length": self.min_content_length,
            "wire_patterns": len(self.wire_service_patterns),
            "pr_patterns": len(self.pr_patterns),
            "low_value_patterns": len(self.low_value_patterns)
        }

# Global instance
volume_reducer = VolumeReducer()

def get_volume_reducer() -> VolumeReducer:
    """Get volume reducer instance"""
    return volume_reducer

def filter_articles_batch(
    articles: List[Dict], 
    db: Session, 
    max_lookback_days: int = 7
) -> Tuple[List[Dict], Dict[str, int]]:
    """
    Filter a batch of articles for processing
    Returns: (filtered_articles, rejection_stats)
    """
    reducer = get_volume_reducer()
    reducer.cleanup_cache()
    
    # Get recent articles for duplicate detection
    cutoff_date = datetime.now(pytz.UTC) - timedelta(days=max_lookback_days)
    # Convert to naive datetime for database query
    cutoff_date = cutoff_date.replace(tzinfo=None)
    recent_articles = (
        db.query(Article)
        .filter(Article.created_at >= cutoff_date)
        .all()
    )
    
    filtered_articles = []
    rejection_stats = {
        "total_input": len(articles),
        "total_filtered": 0,
        "low_value_content": 0,
        "wire_service": 0,
        "pr_content": 0,
        "duplicate_exact_duplicate": 0,
        "duplicate_fuzzy_duplicate": 0,
        "duplicate_similar_content": 0,
        "filtered_url": 0,
        "processed": 0
    }
    
    for article_data in articles:
        title = article_data.get('title', '')
        content = article_data.get('content', '')
        url = article_data.get('url', '')
        
        should_process, reasons = reducer.should_process_article(
            title, content, url, recent_articles
        )
        
        if should_process:
            filtered_articles.append(article_data)
            rejection_stats["processed"] += 1
        else:
            rejection_stats["total_filtered"] += 1
            for reason in reasons:
                rejection_stats[reason] = rejection_stats.get(reason, 0) + 1
            
            logger.info(f"Filtered out: {title[:60]}... Reasons: {', '.join(reasons)}")
    
    # Calculate reduction percentage
    reduction_pct = (rejection_stats["total_filtered"] / rejection_stats["total_input"]) * 100 if rejection_stats["total_input"] > 0 else 0
    
    logger.info(
        f"Volume reduction: {rejection_stats['total_filtered']}/{rejection_stats['total_input']} "
        f"({reduction_pct:.1f}%) filtered out"
    )
    
    return filtered_articles, rejection_stats