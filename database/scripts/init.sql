-- Extensions
CREATE EXTENSION IF NOT EXISTS pgcrypto;   -- gen_random_uuid()
CREATE EXTENSION IF NOT EXISTS pg_trgm;    -- fast title searches

-- Optional enum for clarity
DO $$
BEGIN 
  IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'extraction_method') THEN
    CREATE TYPE extraction_method AS ENUM ('structured', 'readability');
  END IF;
END$$;

-- Main table
CREATE TABLE IF NOT EXISTS recipes (
  id               uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  user_id          uuid NOT NULL,                                   -- no FK yet; you can add a users table later
  title            text NOT NULL CHECK (length(btrim(title)) > 0),
  description      text,
  servings         text,                                            -- keep as text: "4", "4–6", etc.
  prep_time_min    integer CHECK (prep_time_min  IS NULL OR prep_time_min  >= 0),
  cook_time_min    integer CHECK (cook_time_min  IS NULL OR cook_time_min  >= 0),
  total_time_min   integer CHECK (total_time_min IS NULL OR total_time_min >= 0),

  ingredients      jsonb NOT NULL CHECK (jsonb_typeof(ingredients) = 'array'),
  steps            jsonb NOT NULL CHECK (jsonb_typeof(steps)       = 'array'),

  source_url       text NOT NULL CHECK (source_url ~* '^https?://'),
  source_host      text,
  extraction       extraction_method NOT NULL,                      -- 'structured' | 'readability'
  legal_note       text NOT NULL DEFAULT 'For personal use/research only. Do not republish; see the original source link.',
  raw_json         jsonb NOT NULL,                                  -- verbatim cleaned scrape

  created_at       timestamptz NOT NULL DEFAULT now(),
  updated_at       timestamptz NOT NULL DEFAULT now(),

  CONSTRAINT uq_user_source UNIQUE (user_id, source_url)
);

-- Useful indexes
CREATE INDEX IF NOT EXISTS idx_recipes_user_created_at ON recipes (user_id, created_at DESC);
CREATE INDEX IF NOT EXISTS idx_recipes_source_host     ON recipes (source_host);
CREATE INDEX IF NOT EXISTS idx_recipes_title_trgm      ON recipes USING GIN (title gin_trgm_ops);
CREATE INDEX IF NOT EXISTS idx_recipes_ingredients_gin ON recipes USING GIN (ingredients);
CREATE INDEX IF NOT EXISTS idx_recipes_steps_gin       ON recipes USING GIN (steps);

-- Auto-update updated_at on UPDATE
CREATE OR REPLACE FUNCTION set_updated_at()
RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
  NEW.updated_at := now();
  RETURN NEW;
END$$;

DROP TRIGGER IF EXISTS trg_recipes_updated_at ON recipes;
CREATE TRIGGER trg_recipes_updated_at
BEFORE UPDATE ON recipes
FOR EACH ROW EXECUTE FUNCTION set_updated_at();