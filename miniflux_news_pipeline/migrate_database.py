#!/usr/bin/env python3
"""
Database migration script to add Stage-A fields to processed_articles table
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy import text
from config.database import engine
from database.models import Base, ProcessedArticle

def migrate_database():
    """Add new Stage-A columns to the processed_articles table"""
    
    print("🔄 Starting database migration for Stage-A integration...")
    
    try:
        # Connect to database
        with engine.connect() as connection:
            
            # Check if table exists
            result = connection.execute(text("""
                SELECT COUNT(*) 
                FROM information_schema.tables 
                WHERE table_name = 'processed_articles'
            """))
            
            table_exists = result.scalar() > 0
            
            if not table_exists:
                print("📋 Creating new processed_articles table...")
                Base.metadata.create_all(bind=engine)
                print("✅ New table created successfully!")
                return True
            
            print("📋 Table exists, checking for Stage-A columns...")
            
            # Check if stage_a_success column exists (indicator of migration)
            try:
                connection.execute(text("SELECT stage_a_success FROM processed_articles LIMIT 1"))
                print("✅ Stage-A columns already exist - no migration needed!")
                return True
            except Exception:
                print("🔧 Adding Stage-A columns...")
                pass
            
            # Add new columns one by one
            stage_a_columns = [
                ("stage_a_success", "BOOLEAN DEFAULT FALSE"),
                ("stage_a_processing_time_ms", "INTEGER"),
                ("stage_a_error", "TEXT"),
                
                # Article Metadata
                ("analyzed_title", "TEXT"),
                ("analyzed_publisher", "VARCHAR(255)"),
                ("analyzed_author", "VARCHAR(255)"),
                ("analyzed_published_at", "TIMESTAMP"),
                ("analyzed_language", "VARCHAR(10)"),
                ("analyzed_word_count", "INTEGER"),
                
                # Classification
                ("category", "VARCHAR(100)"),
                ("subcategory", "VARCHAR(100)"),
                ("beats", "JSON"),
                ("tags", "JSON"),
                
                # Sentiment Analysis  
                ("tone", "JSON"),
                ("bias", "JSON"),
                
                # Summary
                ("summary_abstract", "TEXT"),
                ("summary_tldr", "TEXT"),
                ("summary_bullets", "JSON"),
                ("compression_ratio", "JSON"),
                
                # Entities
                ("entities_people", "JSON"),
                ("entities_organizations", "JSON"),
                ("entities_locations", "JSON"),
                ("entities_other", "JSON"),
                
                # Editorial Analysis
                ("newsworthiness", "JSON"),
                ("fact_check", "JSON"),
                ("angles", "JSON"),
                ("impact", "JSON"),
                ("risks", "JSON"),
                ("pitch", "JSON"),
                
                # Quality Metrics
                ("readability", "JSON"),
                ("hallucination_risk", "JSON"),
                ("overall_confidence", "JSON"),
                
                # SEO Analysis
                ("seo_visibility", "JSON"),
                ("seo_keyword_density", "JSON"),
                ("seo_content_freshness", "JSON"),
                ("seo_readability", "JSON"),
                ("seo_trending_potential", "JSON"),
                ("seo_search_intent", "VARCHAR(100)"),
                ("seo_target_keywords", "JSON"),
                ("seo_content_gaps", "JSON"),
                ("seo_competitor_analysis", "JSON"),
                ("seo_overall_score", "JSON"),
                
                # Newsroom Pitch Score
                ("newsroom_newsworthiness", "JSON"),
                ("newsroom_audience_appeal", "JSON"),
                ("newsroom_exclusivity", "JSON"),
                ("newsroom_social_potential", "JSON"),
                ("newsroom_urgency", "JSON"),
                ("newsroom_resources", "JSON"),
                ("newsroom_brand_alignment", "JSON"),
                ("newsroom_controversy_risk", "JSON"),
                ("newsroom_followup_potential", "JSON"),
                ("newsroom_overall_score", "JSON"),
                ("newsroom_recommendation", "VARCHAR(50)"),
                ("newsroom_pitch_summary", "TEXT"),
                ("newsroom_headline_suggestions", "JSON"),
                ("newsroom_target_audience", "JSON"),
                ("newsroom_timeline", "VARCHAR(100)"),
                ("newsroom_pitch_notes", "JSON"),
                
                # Provenance
                ("pipeline_version", "VARCHAR(50)"),
                ("models_used", "JSON"),
                ("processing_notes", "TEXT"),
                
                # Full Stage-A Response
                ("full_stage_a_response", "JSON"),
                
                # Update existing columns to match new defaults
                ("processing_profile", "VARCHAR(50) DEFAULT 'stage-a-full'"),
                ("updated_at", "TIMESTAMP DEFAULT CURRENT_TIMESTAMP")
            ]
            
            # Add columns that don't already exist
            added_count = 0
            
            for column_name, column_def in stage_a_columns:
                try:
                    # Check if column exists
                    connection.execute(text(f"SELECT {column_name} FROM processed_articles LIMIT 1"))
                    print(f"  ✓ Column {column_name} already exists")
                except Exception:
                    # Column doesn't exist, add it
                    try:
                        if column_name in ["processing_profile", "updated_at"]:
                            # These might exist, try to modify instead
                            continue
                            
                        connection.execute(text(f"ALTER TABLE processed_articles ADD COLUMN {column_name} {column_def}"))
                        connection.commit()
                        print(f"  + Added column: {column_name}")
                        added_count += 1
                    except Exception as e:
                        print(f"  ⚠️  Could not add {column_name}: {e}")
                        continue
            
            # Create indexes
            try:
                connection.execute(text("CREATE INDEX IF NOT EXISTS idx_category_sentiment ON processed_articles(category, sentiment)"))
                connection.execute(text("CREATE INDEX IF NOT EXISTS idx_processing_time ON processed_articles(stage_a_processing_time_ms)"))
                connection.commit()
                print("✅ Created performance indexes")
            except Exception as e:
                print(f"⚠️  Index creation warning: {e}")
            
            print(f"✅ Migration completed! Added {added_count} new columns")
            return True
            
    except Exception as e:
        print(f"❌ Migration failed: {e}")
        return False

def test_migration():
    """Test that the migration worked"""
    print("\n🧪 Testing migration...")
    
    try:
        with engine.connect() as connection:
            # Test querying new columns
            result = connection.execute(text("""
                SELECT stage_a_success, category, sentiment, newsroom_overall_score 
                FROM processed_articles 
                LIMIT 1
            """))
            
            print("✅ New columns are queryable!")
            
            # Show table structure
            result = connection.execute(text("""
                SELECT column_name, data_type 
                FROM information_schema.columns 
                WHERE table_name = 'processed_articles' 
                AND column_name LIKE 'stage_a%' OR column_name LIKE 'newsroom_%'
                ORDER BY column_name
            """))
            
            columns = result.fetchall()
            print(f"\n📋 Found {len(columns)} Stage-A columns in database:")
            for column in columns[:10]:  # Show first 10
                print(f"  • {column[0]} ({column[1]})")
            if len(columns) > 10:
                print(f"  ... and {len(columns) - 10} more")
                
            return True
            
    except Exception as e:
        print(f"❌ Migration test failed: {e}")
        return False

if __name__ == "__main__":
    success = migrate_database()
    if success:
        test_success = test_migration()
        if test_success:
            print("\n🎉 Database migration completed successfully!")
            print("🚀 Ready to store Stage-A responses!")
        else:
            print("\n⚠️  Migration completed but testing failed")
    else:
        print("\n💡 Fix migration errors and try again")