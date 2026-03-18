"""
One-time local setup: log in to Twitter via twscrape so the session
cookies are saved in twscrape.db.  Upload that file to your GitHub
Actions cache or commit it to the repo's data branch.

Usage:
    python scripts/setup_accounts.py <username> <password> <email> [email_password]

If email_password is omitted, it defaults to the Twitter password.
"""

import asyncio
import sys
import twscrape


async def main():
    if len(sys.argv) < 4:
        print("Usage: python scripts/setup_accounts.py <username> <password> <email> [email_password]")
        sys.exit(1)

    username = sys.argv[1]
    password = sys.argv[2]
    email = sys.argv[3]
    email_password = sys.argv[4] if len(sys.argv) > 4 else password

    api = twscrape.API("twscrape.db")

    print(f"Adding account @{username}...")
    await api.pool.add_account(username, password, email, email_password)

    print("Logging in (this may take a moment)...")
    await api.pool.login_all()

    info = await api.pool.accounts_info()
    print(f"Account pool: {info}")
    print()
    print("Done! The session is saved in twscrape.db.")
    print("Upload this file alongside your code when deploying.")


if __name__ == "__main__":
    asyncio.run(main())
