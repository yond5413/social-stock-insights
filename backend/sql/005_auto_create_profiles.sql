-- Migration: Auto-create profiles for new auth users
-- Purpose: Automatically create a profile entry in public.profiles when a new user signs up
-- This ensures consistency between auth.users and public.profiles tables

-- Function: handle_new_user
-- Purpose: Creates a profile entry for newly registered users
CREATE OR REPLACE FUNCTION public.handle_new_user()
RETURNS trigger AS $$
BEGIN
  INSERT INTO public.profiles (id, username, email, created_at)
  VALUES (
    new.id,
    COALESCE(
      new.raw_user_meta_data->>'username',
      split_part(new.email, '@', 1),
      'user_' || substring(new.id::text, 1, 8)
    ),
    new.email,
    now()
  )
  ON CONFLICT (id) DO NOTHING;
  RETURN new;
END;
$$ LANGUAGE plpgsql SECURITY DEFINER;

-- Trigger: on_auth_user_created
-- Purpose: Automatically invoke handle_new_user() when a new user is created
DROP TRIGGER IF EXISTS on_auth_user_created ON auth.users;
CREATE TRIGGER on_auth_user_created
  AFTER INSERT ON auth.users
  FOR EACH ROW EXECUTE FUNCTION public.handle_new_user();

-- Backfill: Create profiles for existing auth users
-- This ensures all existing users have corresponding profile entries
INSERT INTO public.profiles (id, username, email, created_at)
SELECT 
  au.id,
  COALESCE(
    au.raw_user_meta_data->>'username',
    split_part(au.email, '@', 1),
    'user_' || substring(au.id::text, 1, 8)
  ) as username,
  au.email,
  au.created_at
FROM auth.users au
WHERE NOT EXISTS (
  SELECT 1 FROM public.profiles p WHERE p.id = au.id
)
ON CONFLICT (id) DO NOTHING;

-- Comment on function for documentation
COMMENT ON FUNCTION public.handle_new_user() IS 
'Automatically creates a profile entry in public.profiles when a new user signs up via Supabase Auth. This ensures data consistency between auth.users and public.profiles.';






