import asyncio
import time

from colorama import Style

from utils.services import retry_request, mask_token, resolve_ip
from utils.settings import DOMAIN_API, PING_DURATION, PING_INTERVAL, logger, Fore


# This function fetches account information from the server
async def fetch_account_info(account):
    logger.debug(f"{Fore.CYAN}{account.index:02d}{Fore.RESET} - Fetching account info...")
    try:
        response = await retry_request(DOMAIN_API["SESSION"], {}, account, method="POST")

        if response and response.get("success"):
            return response.get("data")
        logger.error(f"{Fore.CYAN}{account.index:02d}{Fore.RESET} - {Fore.RED}Failed to fetch account info:{Fore.RESET} {response}")

    except Exception as e:
        logger.error(f"{Fore.CYAN}{account.index:02d}{Fore.RESET} - {Fore.RED}Error fetching account info:{Fore.RESET} {e}")

    return {}

# Send periodic pings to the server for the given account
async def process_ping_response(response, url, account, data):
    if not response or not isinstance(response, dict):
        logger.error(f"{Fore.CYAN}{account.index:02d}{Fore.RESET} - {Fore.RED}Invalid or empty response.{Fore.RESET} {response}")
        return "failed", None

    logger.debug(
        f"{Fore.CYAN}{account.index:02d}{Fore.RESET} - Response {{"
        f"Success: {response.get('success')}, Code: {response.get('code')}, "
        f"IP Score: {response.get('data', {}).get('ip_score', 'N/A')}, "
        f"Message: {response.get('msg', 'No message')}}}"
    )

    try:
        response_data = response.get("data", {})
        version = response_data.get("version", "2.2.7")
        data["version"] = version

        ping_result = "success" if response.get("code") == 0 else "failed"
        network_quality = response_data.get("ip_score", "N/A")

        # Update the account stats based on the ping result
        account.browser_ids[0]['ping_count'] += 1
        if ping_result == "success":
            account.browser_ids[0]['score'] += 10
            account.browser_ids[0]["successful_pings"] += 1
        else:
            account.browser_ids[0]['score'] -= 5

        logger.debug(
            f"{Fore.CYAN}{account.index:02d}{Fore.RESET} - "
            f"Browser Stats {{Ping Count: {account.browser_ids[0]['ping_count']}, "
            f"Success: {account.browser_ids[0]['successful_pings']}, "
            f"Score: {account.browser_ids[0]['score']}, "
            f"Last Ping: {account.browser_ids[0]['last_ping_time']:.2f}}}"
        )

        return ping_result, network_quality

    except AttributeError as e:
        logger.error(f"{Fore.CYAN}{account.index:02d}{Fore.RESET} - {Fore.RED}AttributeError processing response:{Fore.RESET} {e}")
        return "failed", None

# Function to start the ping process for each account
async def start_ping(account):
    current_time = time.time()

    separator_line = f"{Fore.CYAN + Style.BRIGHT}-" * 75 + f"{Style.RESET_ALL}"

    if account.index == 1:
        logger.debug(separator_line)

    # Ensure account.account_info is not empty
    if not account.account_info or not account.account_info.get("uid"):
        logger.debug(f"{Fore.CYAN}{account.index:02d}{Fore.RESET} - Account info is empty or missing UID. Attempting to fetch...")
        account.account_info = await fetch_account_info(account)

        if not account.account_info or not account.account_info.get("uid"):
            logger.error(f"{Fore.CYAN}{account.index:02d}{Fore.RESET} - {Fore.RED}Failed to fetch valid account info. Skipping this account.{Fore.RESET}")
            return

    try:
        # Validate browser_ids
        if not account.browser_ids or not isinstance(account.browser_ids[0], dict) or 'last_ping_time' not in account.browser_ids[0]:
            logger.error(f"{Fore.CYAN}{account.index:02d}{Fore.RESET} - {Fore.RED}Missing last ping time or browser IDs.{Fore.RESET}")
            return

        account.browser_ids[0].setdefault('ping_count', 0)
        account.browser_ids[0].setdefault('score', 0)

        last_ping_time = account.browser_ids[0]['last_ping_time']
        logger.debug(f"{Fore.CYAN}{account.index:02d}{Fore.RESET} - Current time: {current_time}, Last ping time: {last_ping_time}")

        if last_ping_time and (current_time - last_ping_time) < PING_INTERVAL:
            logger.warning(f"{Fore.CYAN}{account.index:02d}{Fore.RESET} - {Fore.YELLOW}Hold on! Please wait a bit longer before trying again.{Fore.RESET}")
            return

        account.browser_ids[0]['last_ping_time'] = current_time

        # Start ping loop
        for url in DOMAIN_API["PING"]:
            try:
                logger.debug(f"{Fore.CYAN}{account.index:02d}{Fore.RESET} - Account info {{uid: {account.account_info.get('uid')}, name: {account.account_info.get('name')}}}")
                data = {"id": account.account_info.get("uid"), "browser_id": account.browser_ids[0], "timestamp": int(time.time())}

                # Send request with retry handling
                response = await retry_request(url, data, account)
                ping_result, network_quality = await process_ping_response(response, url, account, data)

                logger.debug(separator_line)

                identifier = await resolve_ip(account)
                logger.info(
                    f"{Fore.CYAN}{account.index:02d}{Fore.RESET} - {Fore.GREEN}Ping{Fore.RESET} {Fore.GREEN}{ping_result}{Fore.RESET}, "
                    f"Token: {Fore.CYAN}{mask_token(account.token)}{Fore.RESET}, "
                    f"IP Score: {Fore.CYAN}{network_quality}{Fore.RESET}, "
                    f"{'Proxy' if account.proxy else 'IP Address'}: {Fore.CYAN}{identifier}{Fore.RESET}"
                )

                if ping_result == "success":
                    break

            except KeyError as ke:
                logger.error(f"{Fore.CYAN}{account.index:02d}{Fore.RESET} - {Fore.RED}KeyError during ping:{Fore.RESET} {ke}")

            except Exception as e:
                logger.error(f"{Fore.CYAN}{account.index:02d}{Fore.RESET} - {Fore.RED}Error during ping:{Fore.RESET} {e}")
                await asyncio.sleep(1)

    except Exception as main_exception:
        logger.error(f"{Fore.CYAN}{account.index:02d}{Fore.RESET} - {Fore.RED}Critical error in start ping:{Fore.RESET} {main_exception}")

# Ping all accounts periodically
async def ping_all_accounts(accounts):
    start_time = time.time()

    while time.time() - start_time < PING_DURATION:
        try:
            # Ping all accounts concurrently
            results = await asyncio.gather(
                *(start_ping(account) for account in accounts),
                return_exceptions=True
            )

            # Log errors for failed accounts
            for account, result in zip(accounts, results):
                if isinstance(result, Exception):
                    logger.error(f"{Fore.CYAN}{account.index:02d}{Fore.RESET} - {Fore.RED}Error pinging:{Fore.RESET} {result}")

        except Exception as e:
            logger.error(f"{Fore.CYAN}{account.index:02d}{Fore.RESET} - {Fore.RED}Unexpected error:{Fore.RESET} {e}")

        logger.info(f"{Fore.CYAN}00{Fore.RESET} - Sleeping for {PING_INTERVAL} seconds before the next pings")
        await asyncio.sleep(PING_INTERVAL)
