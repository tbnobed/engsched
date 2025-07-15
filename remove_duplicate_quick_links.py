#!/usr/bin/env python3
"""
Remove duplicate Quick Links entries from the database.
This script keeps the oldest entry for each unique title+URL combination
and removes any newer duplicates.

Usage: python remove_duplicate_quick_links.py
"""

import os
import sys
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

def remove_duplicate_quick_links():
    """Remove duplicate quick links, keeping the oldest entry for each unique title+URL combination."""
    
    # Get database URL from environment
    database_url = os.environ.get('DATABASE_URL')
    if not database_url:
        print("ERROR: DATABASE_URL environment variable not set")
        return False
    
    try:
        # Create database connection
        engine = create_engine(database_url)
        Session = sessionmaker(bind=engine)
        session = Session()
        
        print("Checking for duplicate Quick Links...")
        
        # Find duplicates
        duplicate_query = text("""
            SELECT title, url, COUNT(*) as duplicate_count,
                   ARRAY_AGG(id ORDER BY created_at) as all_ids,
                   MIN(created_at) as earliest_created
            FROM quick_link 
            GROUP BY title, url 
            HAVING COUNT(*) > 1
            ORDER BY title
        """)
        
        duplicates = session.execute(duplicate_query).fetchall()
        
        if not duplicates:
            print("No duplicate Quick Links found.")
            return True
        
        print(f"Found {len(duplicates)} sets of duplicate Quick Links:")
        
        total_removed = 0
        for duplicate in duplicates:
            title, url, count, all_ids, earliest = duplicate
            print(f"\n'{title}' ({url})")
            print(f"  Found {count} duplicates (IDs: {all_ids})")
            
            # Keep the first (oldest) ID, remove the rest
            ids_to_remove = all_ids[1:]  # All except the first
            keep_id = all_ids[0]  # The first (oldest)
            
            print(f"  Keeping ID {keep_id}, removing IDs: {ids_to_remove}")
            
            # Remove duplicate entries
            for id_to_remove in ids_to_remove:
                delete_query = text("DELETE FROM quick_link WHERE id = :id")
                session.execute(delete_query, {"id": id_to_remove})
                total_removed += 1
        
        # Commit changes
        session.commit()
        print(f"\nSuccessfully removed {total_removed} duplicate Quick Links entries.")
        
        session.close()
        return True
        
    except Exception as e:
        print(f"ERROR: Failed to remove duplicate Quick Links: {e}")
        try:
            if 'session' in locals() and session:
                session.rollback()
                session.close()
        except:
            pass
        return False

if __name__ == "__main__":
    print("Quick Links Duplicate Removal Script")
    print("====================================")
    
    success = remove_duplicate_quick_links()
    
    if success:
        print("\nQuick Links cleanup completed successfully!")
        sys.exit(0)
    else:
        print("\nQuick Links cleanup failed!")
        sys.exit(1)