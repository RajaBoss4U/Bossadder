import os
import time
import asyncio
from telethon.sync import TelegramClient
from telethon.errors import SessionPasswordNeededError, PhoneCodeInvalidError
from telethon.tl.functions.channels import JoinChannelRequest, InviteToChannelRequest, GetParticipantsRequest
from telethon.tl.types import User, ChannelParticipantsSearch, InputPeerUser
from datetime import datetime, timedelta
from colorama import Fore, init
from vobject import readOne  # To read .vcf file

# Initialize Colorama for color printing
init(autoreset=True)

# Constants
API_ID = 29886024
API_HASH = '2620cb3eb848ddc6781693862a0f670a'
SESSIONS_FOLDER = "sessions"
NUMBERS_FILE = "numbers.txt"
VCF_FILE = "users.vcf"  # VCF file to get users from

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

# Read phone numbers from VCF file
def read_vcf_file(vcf_file):
    numbers = []
    if not os.path.exists(vcf_file):
        print(Fore.RED + f"VCF file '{vcf_file}' not found.")
        return numbers

    with open(vcf_file, "r") as file:
        vcf_data = file.read()
        vcards = vcf_data.split("BEGIN:VCARD")
        for vcard in vcards:
            if "TEL:" in vcard:
                lines = vcard.splitlines()
                for line in lines:
                    if line.startswith("TEL:"):
                        number = line.replace("TEL:", "").strip()
                        numbers.append(number)
    return numbers

# Add members to the group in batches of 5
async def add_members_to_group(client, group_username, members):
    print(Fore.YELLOW + f"Adding members to group '{group_username}'...")
    successfully_added = []  # List to track added users
    try:
        for i in range(0, len(members), 5):
            batch = members[i:i+5]
            try:
                # Convert usernames to InputPeerUser objects
                user_objects = []
                for member in batch:
                    # Fetch user info by username
                    user = await client.get_entity(member)
                    if user:
                        # Ensure the user is converted to InputPeerUser (used for invites)
                        user_objects.append(InputPeerUser(user.id, user.access_hash))  # Convert to InputPeerUser

                print(Fore.GREEN + f"Adding batch {user_objects} to the group...")
                await client(InviteToChannelRequest(
                    group_username,
                    user_objects  # Adding 5 users at a time
                ))
                print(Fore.GREEN + f"Successfully added members: {user_objects}")
                successfully_added.extend(user_objects)  # Track successful additions
            except Exception as e:
                print(Fore.RED + f"Failed to add batch {batch}: {e}")
            time.sleep(2)  # Sleep for 2 seconds to avoid hitting rate limits
    except Exception as e:
        print(Fore.RED + f"Error while adding members to group '{group_username}': {e}")
    
    # Remove successfully added members from the VCF file
    await remove_users_from_vcf(VCF_FILE, successfully_added)

# Function to remove successfully added users from the VCF file
async def remove_users_from_vcf(vcf_file, added_users):
    with open(vcf_file, "r") as file:
        lines = file.readlines()

    # Filter out the added users from the VCF file
    remaining_lines = []
    for line in lines:
        if not any(user.username in line for user in added_users):
            remaining_lines.append(line)

    with open(vcf_file, "w") as file:
        file.writelines(remaining_lines)

# Safe client start with retries and skip problematic sessions
async def safe_start_client(client, session_name, retries=3):
    try:
        await client.start()
        print(Fore.GREEN + f"Logged in with account: {session_name}")
        return True
    except SessionPasswordNeededError:
        print(Fore.RED + f"Account {session_name} requires a password (OTP). Skipping and removing from numbers.txt.")
        remove_account_from_numbers(session_name)
        return False
    except PhoneCodeInvalidError:
        print(Fore.RED + f"OTP for account {session_name} was invalid. Skipping and removing from numbers.txt.")
        remove_account_from_numbers(session_name)
        return False
    except Exception as e:
        print(Fore.RED + f"Failed to start client for account {session_name}: {e}")
        return False

# Function to remove account from numbers.txt
def remove_account_from_numbers(account):
    with open(NUMBERS_FILE, "r") as file:
        phone_numbers = file.read().splitlines()

    if account in phone_numbers:
        phone_numbers.remove(account)

    with open(NUMBERS_FILE, "w") as file:
        file.write("\n".join(phone_numbers))
    print(Fore.RED + f"Removed account {account} from {NUMBERS_FILE}")

# Menu to select operation
async def menu():
    print(Fore.CYAN + """
=======================================================
               Telegram Management Tool
1. Add members from VCF file to target group/channel
2. Join target group/channel with all accounts
3. Check active accounts and clean numbers.txt
4. Scrape active, non-deleted, non-bot users from group
5. Scrape members who were online in the last day from group
=======================================================
""")
    choice = input(Fore.YELLOW + "Choose an option (1/2/3/4/5): ").strip()
    return choice

# Main function
async def main():
    print(Fore.CYAN + """
=======================================================
               Telegram Management Tool
=======================================================
""")
    accounts = load_accounts_from_sessions()
    if not accounts:
        print(Fore.RED + "No accounts found in the sessions folder. Exiting.")
        return

    choice = await menu()

    if choice == "1":  # Add members from VCF file
        group_username = input(Fore.CYAN + "Enter Target Group/Channel Username or Link: ").strip()
        members = read_vcf_file(VCF_FILE)
        if members:
            for session_name, session_file in accounts.items():
                client = TelegramClient(session_file, API_ID, API_HASH)
                connected = await safe_start_client(client, session_name)
                if not connected:
                    continue
                await add_members_to_group(client, group_username, members)
                await client.disconnect()

    elif choice == "2":  # Join target group
        target_group = input(Fore.CYAN + "Enter Target Group/Channel Username or Link: ").strip()
        for session_name, session_file in accounts.items():
            client = TelegramClient(session_file, API_ID, API_HASH)
            connected = await safe_start_client(client, session_name)
            if not connected:
                continue
            await join_target_group(client, target_group)
            await client.disconnect()

    elif choice == "3":  # Check active accounts and clean numbers.txt
        print(Fore.YELLOW + "This feature is under development.")

    elif choice == "4":  # Scrape active members
        group_username = input(Fore.CYAN + "Enter Group Username or Link: ").strip()
        for session_name, session_file in accounts.items():
            client = TelegramClient(session_file, API_ID, API_HASH)
            connected = await safe_start_client(client, session_name)
            if not connected:
                continue
            active_members = await scrape_active_members(client, group_username)
            print(Fore.GREEN + f"Active members found: {len(active_members)}")
            await client.disconnect()

    elif choice == "5":  # Scrape members online in the last day
        group_username = input(Fore.CYAN + "Enter Group Username or Link: ").strip()
        for session_name, session_file in accounts.items():
            client = TelegramClient(session_file, API_ID, API_HASH)
            connected = await safe_start_client(client, session_name)
            if not connected:
                continue
            online_members = await scrape_online_last_day(client, group_username)
            print(Fore.GREEN + f"Members found who were online in the last day: {len(online_members)}")
            await client.disconnect()

    else:
        print(Fore.RED + "Invalid choice. Exiting.")

if __name__ == "__main__":
    asyncio.run(main())