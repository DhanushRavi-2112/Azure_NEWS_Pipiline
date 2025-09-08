#!/usr/bin/env python3
"""
Recreate the processed_articles table with the new Stage-A schema
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from sqlalchemy import text
from config.database import engine
from database.models import Base, ProcessedArticle

def recreate_processed_articles_table():
    """Recreate the processed_articles table with new schema"""
    
    print("🔄 Recreating processed_articles table for Stage-A integration...")
    
    try:
        with engine.begin() as connection:  # Use transaction
            
            # First, backup existing data if any
            print("💾 Backing up existing data...")
            try:
                result = connection.execute(text("SELECT COUNT(*) FROM processed_articles"))
                count = result.scalar()
                print(f"📊 Found {count} existing records")
                
                if count > 0:
                    # Create backup table
                    connection.execute(text("""
                        CREATE TABLE processed_articles_backup AS 
                        SELECT * FROM processed_articles
                    """))
                    print("✅ Backup created: processed_articles_backup")
                    
            except Exception as e:
                print(f"⚠️  Backup warning: {e}")
            
            # Drop existing table
            print("🗑️  Dropping old table...")
            connection.execute(text("DROP TABLE IF EXISTS processed_articles"))
            print("✅ Old table dropped")
            
        # Create new table with updated schema
        print("📋 Creating new table with Stage-A schema...")
        Base.metadata.tables['processed_articles'].create(engine)
        print("✅ New table created!")
        
        # Verify the new table structure
        print("🔍 Verifying new table structure...")
        with engine.connect() as connection:
            result = connection.execute(text("""
                SELECT column_name, data_type 
                FROM information_schema.columns 
                WHERE table_name = 'processed_articles'
                ORDER BY ordinal_position
            """))
            
            columns = result.fetchall()
            stage_a_columns = [col for col in columns if 'stage_a' in col[0] or 'newsroom' in col[0]]
            
            print(f"📋 Table created with {len(columns)} total columns")
            print(f"🎯 Stage-A specific columns: {len(stage_a_columns)}")
            
            # Show some key Stage-A columns
            print("Key Stage-A columns:")
            key_columns = ['stage_a_success', 'category', 'sentiment', 'summary_bullets', 
                          'entities_people', 'newsroom_overall_score', 'newsroom_recommendation']
            
            for col_name in key_columns:
                col_info = next((col for col in columns if col[0] == col_name), None)
                if col_info:
                    print(f"  ✅ {col_info[0]} ({col_info[1]})")
                else:
                    print(f"  ❌ {col_name} - missing!")
        
        print("\n✅ Table recreation completed successfully!")
        return True
        
    except Exception as e:
        print(f"❌ Table recreation failed: {e}")
        return False

def test_new_table():
    """Test the new table structure"""
    print("\n🧪 Testing new table...")
    
    try:
        with engine.connect() as connection:
            # Test that we can query Stage-A columns
            connection.execute(text("""
                SELECT stage_a_success, category, sentiment, newsroom_overall_score 
                FROM processed_articles 
                WHERE 1=0
            """))
            print("✅ Stage-A columns are queryable!")
            
            # Show table is empty and ready
            result = connection.execute(text("SELECT COUNT(*) FROM processed_articles"))
            count = result.scalar()
            print(f"📊 Table is ready with {count} records (should be 0)")
            
            return True
            
    except Exception as e:
        print(f"❌ Table test failed: {e}")
        return False

if __name__ == "__main__":
    print("⚠️  WARNING: This will recreate the processed_articles table!")
    print("   Existing data will be backed up to processed_articles_backup")
    
    # Add a simple confirmation
    try:
        confirm = input("\nContinue? (y/N): ").strip().lower()
        if confirm != 'y':
            print("❌ Operation cancelled")
            exit(1)
    except:
        # If input fails (like in automated environments), proceed
        print("🤖 Running in automated mode, proceeding...")
    
    success = recreate_processed_articles_table()
    if success:
        test_success = test_new_table()
        if test_success:
            print("\n🎉 Table recreation completed successfully!")
            print("🚀 Ready to store Stage-A responses!")
            print("\n💡 Next steps:")
            print("   1. Run: python test_store_stage_a.py")
            print("   2. Check your data with: python show_stage_a_mapping.py")
        else:
            print("\n⚠️  Table created but testing failed")
    else:
        print("\n💡 Fix errors above and try again")