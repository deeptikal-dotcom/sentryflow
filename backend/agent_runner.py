"""Agent runner — entry point for the untrusted agent container.

This process runs inside the agent container and communicates with
the gateway via HTTP only. It has no access to the database, signing
keys, or payment systems.
"""
from __future__ import annotations

import asyncio
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("sentryflow.agent")


async def main():
    logger.info("SentryFlow Agent Runner starting")
    logger.info("Waiting for gateway availability...")

    while True:
        await asyncio.sleep(60)
        logger.debug("Agent runner heartbeat")


if __name__ == "__main__":
    asyncio.run(main())
