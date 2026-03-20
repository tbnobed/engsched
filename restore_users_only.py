#!/usr/bin/env python3
"""Restore only users from a JSON backup file, leaving schedules untouched.
Usage: python restore_users_only.py backup_file.json

Upserts users by ID — inserts new users, updates existing ones.
"""
import json
import sys
import os
import psycopg2

def main():
    if len(sys.argv) < 2:
        print("Usage: python restore_users_only.py <backup_file.json>")
        sys.exit(1)

    backup_file = sys.argv[1]
    with open(backup_file, 'r') as f:
        data = json.load(f)

    users = data.get('users', [])
    if not users:
        print("No users found in backup file.")
        sys.exit(1)

    db_url = os.environ.get('DATABASE_URL')
    if not db_url:
        db_url = "postgresql://technician_scheduler_user:technician_scheduler_pass@localhost:5432/technician_scheduler"
        print(f"DATABASE_URL not set, using default: {db_url}")

    conn = psycopg2.connect(db_url)
    conn.autocommit = False
    cur = conn.cursor()

    inserted = 0
    updated = 0
    skipped = 0

    for u in users:
        uid = u['id']
        username = u['username']
        email = u['email']
        password_hash = u.get('password_hash')
        is_admin = u.get('is_admin', False)
        color = u.get('color', '#3498db')
        timezone = u.get('timezone', 'UTC')
        theme_preference = u.get('theme_preference', 'dark')
        profile_picture = u.get('profile_picture')

        try:
            cur.execute("SELECT id FROM \"user\" WHERE id = %s", (uid,))
            existing = cur.fetchone()

            if existing:
                cur.execute("""
                    UPDATE "user" SET
                        username = %s, email = %s, password_hash = %s,
                        is_admin = %s, color = %s, timezone = %s,
                        theme_preference = %s, profile_picture = %s
                    WHERE id = %s
                """, (username, email, password_hash, is_admin, color,
                      timezone, theme_preference, profile_picture, uid))
                updated += 1
                print(f"  Updated: {username} (id={uid})")
            else:
                cur.execute("""
                    INSERT INTO "user" (id, username, email, password_hash,
                        is_admin, color, timezone, theme_preference, profile_picture)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                """, (uid, username, email, password_hash, is_admin, color,
                      timezone, theme_preference, profile_picture))
                inserted += 1
                print(f"  Inserted: {username} (id={uid})")
        except Exception as e:
            print(f"  SKIPPED: {username} (id={uid}) — {e}")
            conn.rollback()
            conn.autocommit = False
            skipped += 1
            continue

    cur.execute("SELECT setval('user_id_seq', (SELECT COALESCE(MAX(id), 1) FROM \"user\"))")

    conn.commit()
    cur.close()
    conn.close()

    print(f"\nDone! Inserted: {inserted}, Updated: {updated}, Skipped: {skipped}")

if __name__ == '__main__':
    main()
