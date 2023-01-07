from os import environ
import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler
import hikari
import lightbulb

from data import boto_ssm

__VERSION__ = environ['VERSION']
if __VERSION__ == "EC2":
    PREFIX = "toast."
elif __VERSION__ == "LOCAL":
    PREFIX = "test."

DISCORD_TOKEN = boto_ssm("DISCORD_TOKEN")
HOME_GUILD_ID = boto_ssm("HOME_GUILD_ID")
STDOUT_CHANNEL_ID = boto_ssm("STDOUT_CHANNEL_ID")

class Bot(lightbulb.BotApp):
    def __init__(self) -> None:
        self.scheduler = AsyncIOScheduler()
        self.scheduler.configure(timezone="utc")

        intents = (
            hikari.Intents.GUILD_MESSAGES | 
            hikari.Intents.MESSAGE_CONTENT
        )

        super().__init__(
            prefix = PREFIX,
            token = DISCORD_TOKEN,
            intents = intents,
        )

    def run(self) -> None:

        self.event_manager.subscribe(hikari.StartingEvent, self.on_starting)
        self.event_manager.subscribe(hikari.StartedEvent, self.on_started)
        self.event_manager.subscribe(hikari.StoppingEvent, self.on_stopping)
        
        super().run(
            activity = hikari.Activity(
                name = f"toast.help | /meme",
                type = hikari.ActivityType.WATCHING)
        )

    async def on_starting(self, event: hikari.StartedEvent) -> None:
        self.load_extensions_from("./bot/extensions/")

    async def on_started(self, event: hikari.StartedEvent) -> None:
        self.scheduler.start()
        self.stdout_channel = await self.rest.fetch_channel(STDOUT_CHANNEL_ID)
        await self.stdout_channel.send("Test Bot now online")
        logging.info("BOT READY")

    async def on_stopping(self, event: hikari.StoppingEvent) -> None:
        await self.stdout_channel.send("Test Bot shutting down")
        self.scheduler.shutdown()

