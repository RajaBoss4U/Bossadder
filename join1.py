import os
import time
import asyncio
from telethon.sync import TelegramClient
from telethon.errors import SessionPasswordNeededError, PhoneCodeInvalidError
from telethon.tl.functions.channels import InviteToChannelRequest
from colorama import Fore, init

# Initialize Colorama for colored text
init(autoreset=True)

# Constants
API_ID = 29886024
API_HASH = '2620cb3eb848ddc6781693862a0f670a'
SESSIONS_FOLDER = "sessions"
NUMBERS_FILE = "numbers.txt"
USERS_FILE = "users.txt"  # File containing User ID and Username

# Parse users.txt file
def parse_users_file(users_file):
    users = []
    if not os.path.exists(users_file):
        print(Fore.RED + f"Users file '{users_file}' not found.")
        return users

    with open(users_file, "r") as file:
        lines = file.readlines()
        for line in lines:
            parts = line.strip().split()
            if len(parts) == 2:
                user_id, username = parts
                users.append({"id": user_id, "username": username})
    return users

# Load accounts from session folder
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

# Add members to a Telegram group and switch accounts after each batch of 5 users
async def add_members_to_group(client, group_username, members, accounts):
    print(Fore.YELLOW + f"Adding members to group '{group_username}'...")
    successfully_added = 0
    users_to_remove = []  # List of user IDs to remove from the file
    account_switch_count = 0  # Counter to track how many users have been added from the current account

    for i in range(0, len(members), 5):  # Process in batches of 5
        batch = members[i:i + 5]
        user_objects = []
        usernames_added = []  # To track added usernames

        for user in batch:
            try:
                entity = await client.get_entity(user["username"] if user["username"] != "None" else int(user["id"]))
                user_objects.append(entity)
                usernames_added.append(user["username"])  # Track the username added
            except Exception as e:
                print(Fore.RED + f"Failed to fetch user {user['username'] or user['id']}: {e}")

        try:
            await client(InviteToChannelRequest(group_username, user_objects))
            successfully_added += len(user_objects)

            # Add the successfully added user IDs to the removal list
            users_to_remove.extend([user["id"] for user in batch])
            print(Fore.GREEN + f"Successfully added: {', '.join(usernames_added)}.")  # Show added usernames
        except Exception as e:
            print(Fore.RED + f"Failed to add batch: {e}")

        time.sleep(2)  # Delay to avoid Telegram rate limits

        # After each batch, remove the successfully added users from the users file
        if users_to_remove:
            remove_users_from_file(USERS_FILE, users_to_remove)
            users_to_remove = []  # Reset the list after each batch
        print(Fore.YELLOW + "Waiting before processing next batch...")

        # Increment the counter and check if we need to switch accounts
        account_switch_count += len(user_objects)

        if account_switch_count >= 5:
            # Disconnect from the current account and switch to the next one
            await client.disconnect()
            print(Fore.YELLOW + "Switching to the next account...")
            account_switch_count = 0  # Reset the counter for the next account

            # Get the next available account from the sessions folder
            if len(accounts) > 0:
                next_account = next(iter(accounts))
                session_file = accounts.pop(next_account)
                client = TelegramClient(session_file, API_ID, API_HASH)
                await safe_start_client(client, next_account)  # Log in to the next account

    print(Fore.GREEN + f"Total successfully added: {successfully_added}")

# Remove users from users.txt file after adding them
def remove_users_from_file(file_path, users_to_remove):
    if not os.path.exists(file_path):
        return

    with open(file_path, "r") as file:
        lines = file.readlines()

    with open(file_path, "w") as file:
        for line in lines:
            user_id = line.strip().split()[0]
            if user_id not in users_to_remove:
                file.write(line)

# Safe client start
async def safe_start_client(client, session_name):
    try:
        await client.start()
        print(Fore.GREEN + f"Logged in with account: {session_name}")
        return True
    except SessionPasswordNeededError:
        print(Fore.RED + f"Account {session_name} requires a password. Skipping.")
        return False
    except PhoneCodeInvalidError:
        print(Fore.RED + f"Invalid code for account {session_name}. Skipping.")
        return False
    except Exception as e:
        print(Fore.RED + f"Failed to start client {session_name}: {e}")
        return False

# Menu to select operation
async def menu():
    print(Fore.CYAN + """
=======================================================
               Telegram Management Tool
1. Add members from users.txt to target group/channel
=======================================================
""")
    choice = input(Fore.YELLOW + "Choose an option (1): ").strip()
    return choice

# Delete the users.txt file
def delete_users_file():
    if os.path.exists(USERS_FILE):
        os.remove(USERS_FILE)
        print(Fore.GREEN + f"Successfully deleted the '{USERS_FILE}' file.")
    else:
        print(Fore.RED + f"File '{USERS_FILE}' does not exist, nothing to delete.")

# Main function
async def main():
    accounts = load_accounts_from_sessions()
    if not accounts:
        print(Fore.RED + "No accounts found in the sessions folder. Exiting.")
        return

    choice = await menu()
    if choice == "1":  # Add members from users.txt
        group_username = input(Fore.CYAN + "Enter Target Group/Channel Username or Link: ").strip()
        members = parse_users_file(USERS_FILE)
        if not members:
            print(Fore.RED + "No members found in the users file. Exiting.")
            return

        # Create the initial Telegram client using the first available account
        session_name, session_file = next(iter(accounts.items()))
        client = TelegramClient(session_file, API_ID, API_HASH)
        connected = await safe_start_client(client, session_name)
        if not connected:
            return

        # Add members to the group and switch accounts after every 5 users
        await add_members_to_group(client, group_username, members, accounts)

        # After processing all accounts, delete the users.txt file
        delete_users_file()

if __name__ == "__main__":
    asyncio.run(main())