import asyncio
import cloudscraper
import json
import random
import requests

from urllib.parse import urlparse
from fake_useragent import UserAgent
from utils.settings import DOMAIN_API, logger, Fore


# Create a Cloudscraper instance
scraper = cloudscraper.create_scraper(
    browser={
        'browser': 'chrome',
        'platform': 'windows',
        'desktop': True
    }
)

# Generates a random User-Agent string
def get_random_user_agent():
    """
    Return a random User-Agent string.
    """
    ua = UserAgent()
    return ua.random

# Function to dynamically build HTTP headers based on URL, account, and method
async def build_headers(url, account, method="POST", data=None):
    """
    Build headers for API requests dynamically.
    """
    # Start with base headers
    headers = {
        "Authorization": f"Bearer {account.token}",
        "Content-Type": "application/json",
        "User-Agent": get_random_user_agent(),
    }

    # Add endpoint-specific headers
    endpoint_specific_headers = get_endpoint_headers(url)
    headers.update(endpoint_specific_headers)

    # Add Content-Length for POST/PUT requests with data
    if method in ["POST", "PUT"] and data:
        try:
            json_data = json.dumps(data)
            headers["Content-Length"] = str(len(json_data))
        except (TypeError, ValueError) as e:
            logger.error(f"{Fore.RED}Failed to calculate Content-Length:{Fore.RESET} {e}")
            raise ValueError("Invalid data format for calculating Content-Length.")

    logger.debug(f"{Fore.CYAN}{account.index:02d}{Fore.RESET} - {Fore.CYAN}Using User-Agent:{Fore.RESET} {headers['User-Agent']}")

    return headers

# Function to return endpoint-specific headers based on the API
def get_endpoint_headers(url):
    """
    Return endpoint-specific headers based on the API.
    """
    EARN_MISSION_SET = {DOMAIN_API["EARN_INFO"], DOMAIN_API["MISSION"], DOMAIN_API["COMPLETE_MISSION"]}
    PING_LIST = DOMAIN_API["PING"]
    ACTIVATE_URL = DOMAIN_API["ACTIVATE"]

    if url in EARN_MISSION_SET:
        return {
            "Accept-Encoding": "gzip, deflate, br, zstd",
            "Host": "api.nodepay.ai"
        }

    elif url in PING_LIST or url == ACTIVATE_URL:
        return {
            "Accept": "application/json, text/plain, */*",
            "Accept-Language": "en-US,en;q=0.9",
            "Referer": "https://app.nodepay.ai/",
            "Origin": "chrome-extension://lgmpfmgeabnnlemejacfljbmonaomfmm",
            "Sec-CH-UA": '"Not/A)Brand";v="8", "Chromium";v="126", "Herond";v="126"'
        }

    return {}

# Function to send HTTP requests with error handling and custom headers
async def send_request(url, data, account, method="POST", timeout=120):
    """
    Perform HTTP requests with proper headers and error handling.
    """
    headers = await build_headers(url, account, method, data)
    proxies = {"http": account.proxy, "https": account.proxy} if account.proxy else None

    parsed_url = urlparse(url)
    path = parsed_url.path

    try:
        if method == "GET":
            response = scraper.get(url, headers=headers, proxies=proxies, timeout=timeout)
        else:
            response = scraper.post(url, json=data, headers=headers, proxies=proxies, timeout=timeout)

        response.raise_for_status()
        return response.json()

    except requests.exceptions.ProxyError as e:
        error_message = "Unable to connect to proxy" if "Unable to connect to proxy" in str(e) else str(e).split(":")[0]
        logger.error(
            f"{Fore.CYAN}{account.index:02d}{Fore.RESET} - {Fore.RED}Proxy connection failed:{Fore.RESET} {error_message}"
        )
        raise

    except requests.exceptions.RequestException as e:
        logger.debug(
            f"{Fore.CYAN}{account.index:02d}{Fore.RESET} - {Fore.RED}HTTP error on{Fore.RESET} "
            f"{Fore.CYAN}{path}:{Fore.RESET} {e}"
        )
        raise

    except Exception as e:
        logger.error(
            f"{Fore.CYAN}{account.index:02d}{Fore.RESET} - {Fore.RED}Unexpected error on{Fore.RESET} "
            f"{Fore.CYAN}{path}:{Fore.RESET} {e}"
        )
        raise

# Function to send HTTP requests with retry logic using exponential backoff
async def retry_request(url, data, account, method="POST", max_retries=3):
    """
    Retry requests using exponential backoff.
    """
    retry_count = 0
    parsed_url = urlparse(url)
    path = parsed_url.path

    while retry_count < max_retries:
        try:
            return await send_request(url, data, account, method)

        except requests.exceptions.HTTPError as e:
            if e.response.status_code == 403:
                logger.error(f"{Fore.CYAN}{account.index:02d}{Fore.RESET} - {Fore.RED}403 Forbidden: Check token or permissions for{Fore.RESET} {Fore.CYAN}{path}{Fore.RESET}")
                break

            logger.error(f"{Fore.RED}HTTP error encountered:{Fore.RESET} {e}")
        
        except ValueError as e:
            error_message = str(e)
            logger.error(
                f"{Fore.CYAN}{account.index:02d}{Fore.RESET} - {Fore.YELLOW}Retrying after invalid value:{Fore.RESET} {error_message}"
            )

        except requests.exceptions.Timeout:
            logger.warning(
                f"{Fore.CYAN}{account.index:02d}{Fore.RESET} - {Fore.YELLOW}Timeout encountered. Retrying...{Fore.RESET}"
            )

        except Exception as e:
            logger.debug(
                f"{Fore.CYAN}{account.index:02d}{Fore.RESET} - {Fore.RED}Unexpected error during retry:{Fore.RESET} {e}"
            )

        await exponential_backoff(retry_count)
        retry_count += 1

    raise Exception(f"{Fore.RED}Max retries reached for{Fore.RESET} {Fore.CYAN}{path}{Fore.RESET}")

# Function to implement exponential backoff delay during retries
async def exponential_backoff(retry_count, base_delay=1):
    """
    Perform exponential backoff for retries.
    """
    delay = base_delay * (2 ** retry_count) + random.uniform(0, 1)
    logger.info(f"{Fore.CYAN}00{Fore.RESET} - Retrying after {delay:.2f} seconds...")
    await asyncio.sleep(delay)
