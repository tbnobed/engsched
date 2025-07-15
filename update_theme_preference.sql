-- Add theme_preference column to the user table
ALTER TABLE "user" ADD COLUMN theme_preference VARCHAR(20) DEFAULT 'dark';