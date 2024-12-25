import asyncio

from utils.settings import logger, Fore


# Track processed tokens globally
processed_tokens = set()
lock = asyncio.Lock()

# Masks sensitive parts of a token
def mask_token(token):
    return f"{token[:5]}--{token[-5:]}"

# Load tokens from a file
async def load_tokens():
    try:
        with open('tokens.txt', 'r') as file:
            tokens = file.read().splitlines()
        return tokens
    except Exception as e:
        logger.error(f"{Fore.CYAN}00{Fore.RESET} - {Fore.RED}Error loading tokens: {e}{Fore.RESET}")
        raise SystemExit("Exiting due to failure in loading tokens")

# Function to add a token to the processed list
async def mark_token(account):
    async with lock:
        # Ensure the token is not already processed
        if account.token in processed_tokens:
            return False
        # Add token to the processed list
        processed_tokens.add(account.token)
        return True
