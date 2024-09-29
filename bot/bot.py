import itertools
import os
import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler
import boto3
import hikari
import lightbulb

from data import boto_ssm, ssh_connect, sql_connect, create_tag_list


ssm = boto3.client("ssm",region_name="us-west-1")
pm2 = os.getenv("PM2_HOME")


if pm2:
    base_prefix = "toast."
    server = None
    VERSION = "Public"
    DISCORD_TOKEN = boto_ssm("DISCORD_TOKEN_PRD",ssm)
else:
    base_prefix = "test."
    server = ssh_connect()
    server.start()
    VERSION = "Test"
    DISCORD_TOKEN = boto_ssm("DISCORD_TOKEN_DEV",ssm)

# Use itertools to create a list of all upper/lower combinations
# (Making the prefix command case insensitive)
prefix_products = itertools.product(
    *zip(base_prefix.lower(), base_prefix.upper())
    )

PREFIXES = ["".join(letters) for letters in prefix_products]

HOME_GUILD_ID = boto_ssm("HOME_GUILD_ID", ssm)
STDOUT_CHANNEL_ID = boto_ssm("STDOUT_CHANNEL_ID", ssm)

class Bot(lightbulb.BotApp):
    def __init__(self) -> None:
        self.scheduler = AsyncIOScheduler()
        self.scheduler.configure(timezone="utc")

        intents = (
            hikari.Intents.GUILD_MESSAGES | 
            hikari.Intents.MESSAGE_CONTENT
        )

        super().__init__(
            prefix = lightbulb.when_mentioned_or(PREFIXES),
            token = DISCORD_TOKEN,
            intents = intents,
        )

    def run(self) -> None:

        self.event_manager.subscribe(hikari.StartingEvent, self.on_starting)
        self.event_manager.subscribe(hikari.StartedEvent, self.on_started)
        self.event_manager.subscribe(hikari.StoppingEvent, self.on_stopping)
        
        super().run(
            activity = hikari.Activity(
                name = f"{base_prefix}help | /meme",
                type = hikari.ActivityType.WATCHING)
        )

        # Refresh tags list
        # Note: This does not "save" until the bot is restarted again.
        conn = sql_connect(server=server)
        create_tag_list(conn=conn)
        conn.close()
        if server:
            server.stop()

    async def on_starting(self, event: hikari.StartedEvent) -> None:
        self.load_extensions_from("./bot/extensions/")

    async def on_started(self, event: hikari.StartedEvent) -> None:
        self.scheduler.start()
        self.stdout_channel = await self.rest.fetch_channel(STDOUT_CHANNEL_ID)
        await self.stdout_channel.send(f"{VERSION} bot now online")
        logging.info("BOT READY")

    async def on_stopping(self, event: hikari.StoppingEvent) -> None:
        await self.stdout_channel.send(f"{VERSION} bot shutting down")
        self.scheduler.shutdown()

