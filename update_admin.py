import sqlite3
import bcrypt

# Set your new admin password here
new_password = "abhishek"

# Hash the password securely using bcrypt
salt = bcrypt.gensalt()
hashed_pw = bcrypt.hashpw(new_password.encode('utf-8'), salt).decode('utf-8')

# Connect to your database and update the admin record
conn = sqlite3.connect('vault_users_v2.db')
c = conn.cursor()

c.execute("UPDATE users SET password = ?, failed_attempts = 0, locked_until = 0 WHERE username = 'admin'", (hashed_pw,))
conn.commit()
conn.close()

print("✅ Admin password successfully updated and encrypted!")
