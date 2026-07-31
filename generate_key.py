from cryptography.fernet import Fernet

# Generate a new encryption key
key = Fernet.generate_key()

# Save the key to secret.key
with open("secret.key", "wb") as key_file:
    key_file.write(key)

print("✅ secret.key has been generated successfully.")