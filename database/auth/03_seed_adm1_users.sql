-- ===========================================================================
-- HydroCast Panchganga - Seed @Adm1 Primary Administrator Accounts
-- All @Adm1 users get "admin" role (full control: user mgmt, forecast trigger, DB, logs)
-- ===========================================================================

-- Deactivate legacy email-based accounts (keep for audit trail, do not delete)
UPDATE admin_users SET is_active = FALSE
WHERE username IN ('satwikcccss@gmail.com', 'panhalkarsachin@gmail.com', 'gonioelect@gmail.com', 'nikhilpawar6297@gmail.com');

-- Seed @Adm1 primary administrators with validated bcrypt hashes (cost=12)
INSERT INTO admin_users (username, password_hash, role, display_name, email, is_active, must_change_password)
VALUES
  ('DEV.Satwikcccss@Adm1',
   '$2b$12$8Wy09LwYuAvPMXZDPNa6Pub3VrELJo.1kIXuNFxq90bDro7R8JoxG',
   'admin',
   'Er. Satwik K. Udupi',
   'Satwikudupi@gmail.com',
   TRUE, FALSE),
  ('PI.Panhalkarsachin@Adm1',
   '$2b$12$pdZsj.AxItgq/yoQJr4hVu0QHbBNotG3mPJLsuNfw/xqeg.m3HpJO',
   'admin',
   'Dr. Sachin S. Panhalkar',
   'panhalkarsachin@gmail.com',
   TRUE, FALSE),
  ('COPI.Nivhekarganesh@Adm1',
   '$2b$12$Zv5GBEoGaAFmb8s4XmbKkerCqkXt/k4fFLdKdw4AJqXgbb8wN9vw6',
   'admin',
   'Dr. Ganesh S. Nhivekar',
   'gonioelect@gmail.com',
   TRUE, FALSE),
  ('JRF.PawarNikhil@Adm1',
   '$2b$12$YwCWUDVa//Xc49h9YayEhOWX7a0ZI8053.rhNrKNs.JXyoPvAtUyq',
   'admin',
   'Nikhil Pawar',
   'nikhilpawar6297@gmail.com',
   TRUE, FALSE),
  ('Dev.Arunbaby@Adm1',
   '$2b$12$.TKocUFIZPmLDtw7bp2Prug8I2ZxV0bygmXgzKc/belnBJB7E2KLa',
   'admin',
   'Arun Baby',
   NULL,
   TRUE, FALSE)
ON CONFLICT (username) DO UPDATE SET
  password_hash = EXCLUDED.password_hash,
  role = EXCLUDED.role,
  display_name = EXCLUDED.display_name,
  email = EXCLUDED.email,
  is_active = EXCLUDED.is_active,
  must_change_password = EXCLUDED.must_change_password;
