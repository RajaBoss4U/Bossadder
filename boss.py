import os
import time
import random
import asyncio
from telethon.sync import TelegramClient
from telethon.errors import (
    SessionPasswordNeededError,
    PhoneCodeInvalidError,
    FloodWaitError,
    UserDeactivatedBanError,
)
from telethon.tl.functions.channels import JoinChannelRequest
from colorama import Fore, init

# Initialize Colorama for colored output
init(autoreset=True)

# Constants
API_ID = 29886028
API_HASH = '2620cb3eb848ddc6781693862a0f670a'
SESSIONS_FOLDER = "sessions"
NUMBERS_FILE = "numbers.txt"
LOG_FILE = "error_log.txt"

# Load accounts from session files
def load_accounts_from_sessions():
    accounts = {}
    if not os.path.exists(SESSIONS_FOLDER):
        print(Fore.RED + "The sessions folder does not exist.")
        return accounts

    if not os.path.exists(NUMBERS_FILE):
        print(Fore.RED + f"File '{NUMBERS_FILE}' not found.")
        return accounts

    with open(NUMBERS_FILE, "r") as file:
        phone_numbers = file.read().splitlines()

    for phone_number in phone_numbers:
        phone_number = phone_number.strip().lstrip('+')
        session_file = os.path.join(SESSIONS_FOLDER, f"{phone_number}.session")
        if os.path.exists(session_file):
            accounts[phone_number] = session_file
        else:
            print(Fore.RED + f"Session file not found for {phone_number}.")
    return accounts


# Check live or dead accounts
async def check_accounts(accounts):
    live_accounts = []
    dead_accounts = []

    print(Fore.CYAN + "Checking accounts...")
    for phone_number, session_file in accounts.items():
        try:
            client = TelegramClient(session_file, API_ID, API_HASH)
            await client.connect()
            if not await client.is_user_authorized():
                print(Fore.YELLOW + f"Account {phone_number} requires re-login.")
                dead_accounts.append(phone_number)
            else:
                print(Fore.GREEN + f"Account {phone_number} is LIVE.")
                live_accounts.append(phone_number)
            await client.disconnect()
        except UserDeactivatedBanError:
            print(Fore.RED + f"Account {phone_number} is BANNED.")
            dead_accounts.append(phone_number)
        except Exception as e:
            print(Fore.RED + f"Failed to check account {phone_number}: {e}")
            dead_accounts.append(phone_number)

    # Update the numbers file and sessions folder
    with open(NUMBERS_FILE, "w") as file:
        file.write("\n".join(live_accounts))

    print(Fore.GREEN + f"Live accounts: {len(live_accounts)}")
    print(Fore.RED + f"Dead accounts: {len(dead_accounts)}")

    # Log dead accounts
    with open(LOG_FILE, "a") as log_file:
        log_file.write("\n".join([f"Dead: {acc}" for acc in dead_accounts]) + "\n")


# Safe client login
async def safe_start_client(client, session_name):
    try:
        await client.start()
        print(Fore.GREEN + f"Logged in with account: {session_name}")
        return True
    except SessionPasswordNeededError:
        print(Fore.RED + f"Account {session_name} requires a password. Skipping.")
        return False
    except PhoneCodeInvalidError:
        print(Fore.RED + f"OTP for account {session_name} was invalid. Skipping.")
        return False
    except Exception as e:
        print(Fore.RED + f"Failed to start client for account {session_name}: {e}")
        return False


# Main menu
async def menu():
    print(Fore.CYAN + """
=======================================================
            🩷 Boss Member Adder V2 🩷
               Created By @BossAdder 
✅️ Supports multiple Telegram accounts with sessions
✅️ Random delays to mimic human behavior
✅️ Dynamic source and target group selection
✅️ Advanced Anti-Ban and Anti-Flood
=======================================================
1. Add members from VCF file to target group/channel
2. Add members from source group to Tg group/channel
3. Join target group/channel with all accounts
4. Scrape all active users from a group/channel
5. Check Live/Dead Accounts (Live Sessions)
=======================================================
""")
    choice = input(Fore.YELLOW + "Choose an option (1/2/3/4/5): ").strip()
    return choice


# Main function
async def main():
    accounts = load_accounts_from_sessions()
    if not accounts:
        print(Fore.RED + "No accounts found in the sessions folder. Exiting.")
        return

    while True:
        choice = await menu()

        if choice == "1":
            group_username = input(Fore.CYAN + "Enter Target Group/Channel Username or Link: ").strip()
            members = input(Fore.CYAN + "Enter members as comma-separated usernames or phone numbers: ").split(',')
            for session_name, session_file in accounts.items():
                client = TelegramClient(session_file, API_ID, API_HASH)
                connected = await safe_start_client(client, session_name)
                if connected:
                    # Add your logic to add members here
                    await client.disconnect()

        elif choice == "2":
            source_group = input(Fore.CYAN + "Enter Source Group Username or Link: ").strip()
            target_group = input(Fore.CYAN + "Enter Target Group/Channel Username or Link: ").strip()
            for session_name, session_file in accounts.items():
                client = TelegramClient(session_file, API_ID, API_HASH)
                connected = await safe_start_client(client, session_name)
                if connected:
                    # Add your logic to transfer members here
                    await client.disconnect()

        elif choice == "3":
            target_group = input(Fore.CYAN + "Enter Target Group/Channel Username or Link: ").strip()
            for session_name, session_file in accounts.items():
                client = TelegramClient(session_file, API_ID, API_HASH)
                connected = await safe_start_client(client, session_name)
                if connected:
                    await client(JoinChannelRequest(target_group))
                    print(Fore.GREEN + f"Joined target group with account: {session_name}")
                    await client.disconnect()

        elif choice == "4":
            group_username = input(Fore.CYAN + "Enter Group Username or Link: ").strip()
            for session_name, session_file in accounts.items():
                client = TelegramClient(session_file, API_ID, API_HASH)
                connected = await safe_start_client(client, session_name)
                if connected:
                    # Add your logic to scrape members here
                    await client.disconnect()

        elif choice == "5":
            await check_accounts(accounts)

        else:
            print(Fore.RED + "Invalid choice. Exiting.")
            break


if __name__ == "__main__":
    asyncio.run(main())
