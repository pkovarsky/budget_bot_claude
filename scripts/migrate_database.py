#!/usr/bin/env python3
"""
Database migration script to add emoji columns and subcategories table
"""

import sqlite3
import logging
from database import engine, Base
from sqlalchemy import text

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def migrate_database():
    """Migrate database to add missing columns and tables"""
    
    # Use a transaction
    with engine.begin() as connection:
        try:
            # Check if categories table has emoji column
            try:
                result = connection.execute(text("SELECT emoji FROM categories LIMIT 1"))
                logger.info("✅ Categories table already has emoji column")
            except Exception:
                logger.info("🔄 Adding emoji column to categories table")
                connection.execute(text('ALTER TABLE categories ADD COLUMN emoji VARCHAR DEFAULT "📁"'))
                logger.info("✅ Added emoji column to categories table")
            
            # Check if subcategories table exists
            try:
                result = connection.execute(text("SELECT * FROM subcategories LIMIT 1"))
                logger.info("✅ Subcategories table already exists")
            except Exception:
                logger.info("🔄 Creating subcategories table")
                connection.execute(text('''
                    CREATE TABLE subcategories (
                        id INTEGER PRIMARY KEY,
                        name VARCHAR NOT NULL,
                        emoji VARCHAR DEFAULT "📂",
                        category_id INTEGER NOT NULL,
                        user_id INTEGER NOT NULL,
                        created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                        FOREIGN KEY (category_id) REFERENCES categories(id),
                        FOREIGN KEY (user_id) REFERENCES users(id)
                    )
                '''))
                logger.info("✅ Created subcategories table")
            
            # Check if transactions table has subcategory_id column
            try:
                result = connection.execute(text("SELECT subcategory_id FROM transactions LIMIT 1"))
                logger.info("✅ Transactions table already has subcategory_id column")
            except Exception:
                logger.info("🔄 Adding subcategory_id column to transactions table")
                connection.execute(text('ALTER TABLE transactions ADD COLUMN subcategory_id INTEGER'))
                logger.info("✅ Added subcategory_id column to transactions table")
            
            # Update existing categories to have default emoji if they don't have one
            logger.info("🔄 Updating existing categories with default emoji")
            connection.execute(text('UPDATE categories SET emoji = "📁" WHERE emoji IS NULL OR emoji = ""'))
            logger.info("✅ Updated existing categories with default emoji")
            
            logger.info("🎉 Database migration completed successfully!")
            
        except Exception as e:
            logger.error(f"❌ Migration failed: {e}")
            raise

def recreate_tables():
    """Recreate all tables from scratch (use with caution - will lose data)"""
    logger.warning("🚨 This will recreate all tables and LOSE ALL DATA!")
    response = input("Are you sure you want to continue? (yes/no): ")
    
    if response.lower() != 'yes':
        logger.info("❌ Operation cancelled")
        return
    
    logger.info("🔄 Recreating all tables...")
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    logger.info("✅ All tables recreated")

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "--recreate":
        recreate_tables()
    else:
        migrate_database()