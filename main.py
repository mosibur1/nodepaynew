import asyncio
from utils.core import process


async def main():
    try:
        await process()
    except KeyboardInterrupt:
        print("Program interrupted. Exiting gracefully...")
    finally:
        print("Cleaning up resources before exiting.")


if __name__ == '__main__':
    try:
        asyncio.run(main())
    except (KeyboardInterrupt, SystemExit):
        pass
