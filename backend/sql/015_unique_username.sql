-- Migration: Ensure unique usernames
-- Purpose: Enforce uniqueness on the username column in profiles table

-- First, ensure the column is unique
-- We might need to handle duplicates first if they exist, but for now we assume they don't or we'll let it fail
ALTER TABLE profiles ADD CONSTRAINT profiles_username_key UNIQUE (username);

-- Add index for faster username lookups (UNIQUE constraint creates an index, but explicit is fine too if needed, though redundant)
-- CREATE INDEX IF NOT EXISTS idx_profiles_username ON profiles(username);
