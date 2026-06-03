SET search_path TO insuramind;

ALTER TABLE users
    ADD COLUMN IF NOT EXISTS username VARCHAR(80);

UPDATE users
SET username = LOWER(REGEXP_REPLACE(SPLIT_PART(email, '@', 1), '[^a-z0-9._-]', '', 'g')) || '-' || SUBSTRING(REPLACE(id::text, '-', ''), 1, 8)
WHERE username IS NULL OR username = '';

ALTER TABLE users
    ALTER COLUMN username SET NOT NULL;

CREATE UNIQUE INDEX IF NOT EXISTS uk_users_username ON users(username);