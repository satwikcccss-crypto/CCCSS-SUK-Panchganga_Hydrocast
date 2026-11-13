-- ===========================================================================
-- HydroCast Panchganga - Bootstrap administrator account template
-- ---------------------------------------------------------------------------
-- This file is a TEMPLATE for first-time production bootstrapping on a server.
-- It MUST NOT contain a real password hash, because committed hashes can be
-- attacked offline and a shared bootstrap password would be a backdoor.
--
-- Preferred (recommended): create administrators via the CLI, which prompts
-- for a password and writes a fresh bcrypt hash directly to the database:
--
--   python -m backend.scripts.manage_users add --username <admin> --password <password> --role admin --email <email> --name "<Full Name>"
--
-- If you must seed via SQL (offline bootstrap), generate a bcrypt hash on the
-- server (e.g. `python -c "import bcrypt;print(bcrypt.hashpw(b'YOUR_PASSWORD', bcrypt.gensalt(12)).decode())"`),
-- paste it below, run this file once, then remove the password material from the
-- shell history. Do NOT commit a file that contains a real hash.
-- ===========================================================================
/*
INSERT INTO admin_users (username, password_hash, role, display_name, email, is_active, must_change_password)
VALUES
  ('<admin_username>', '<bcrypt_hash>', 'admin', '<Display Name>', '<email>', TRUE, TRUE)
ON CONFLICT (username) DO UPDATE SET
  password_hash = EXCLUDED.password_hash,
  role = EXCLUDED.role,
  display_name = EXCLUDED.display_name,
  email = EXCLUDED.email,
  is_active = EXCLUDED.is_active,
  must_change_password = EXCLUDED.must_change_password;
*/
