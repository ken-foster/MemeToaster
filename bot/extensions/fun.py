from io import BytesIO
from os import getenv

import boto3
import hikari
import lightbulb

from bot import Bot
from bot.pic import render
from data import *

plugin = lightbulb.Plugin("Functions")

@plugin.command
@lightbulb.command(name="version", description="For testing env vars")
@lightbulb.implements(lightbulb.PrefixCommand)
async def command_version(ctx: lightbulb.Context) -> None:

    pm2 = getenv("PM2_HOME")
    if pm2:
        await ctx.respond(pm2)
    else:
        await ctx.respond("local dev machine")


@plugin.command
@lightbulb.command(name = "tags", description = "Get a link to a list of all available tags")
@lightbulb.implements(lightbulb.SlashCommand, lightbulb.PrefixCommand)
async def command_stats(ctx: lightbulb.Context) -> None:

    f = hikari.File("data/tags.txt")
    await ctx.respond(f)


@plugin.command
@lightbulb.option(name = "caption", description = "Caption to add to the picture", type = str, default = "",
                    modifier = lightbulb.commands.OptionModifier.CONSUME_REST)
@lightbulb.option(name = "tags", description = "Tag to search for", type = str, required = True)
@lightbulb.command(name = "meme", description = "Put a picture tag and caption in the toaster")
@lightbulb.implements(lightbulb.SlashCommand, lightbulb.PrefixCommand)
async def command_meme(ctx: lightbulb.Context) -> None:
    caption = ctx.options.caption.strip()

    if len(caption) > 125:
                await ctx.respond(f"""
{ctx.author.mention} it's a meme, not your master's thesis. Your caption has to be 125 characters or less.""")

    else:
        tags_requested = process_tags_arg(ctx.options.tags)

        pm2 = getenv("PM2_HOME")
        if pm2:
            conn = sql_connect()
        else:
            server = ssh_connect()
            server.start()

            conn = sql_connect(server)        

        imageChoice, success = query_by_tags(tags_requested, conn)

        await ctx.respond("Toasting meme...")

        tags = query_tag_by_filename(imageChoice, conn)

        tagsHashed = ["#" + t for t in tags]
        tagsSend = " ".join(tagsHashed)

        s3 = boto3.Session().resource("s3")

        with BytesIO() as imageBinaryDload:
            with BytesIO() as imageBinarySend:
                s3.Bucket('memetoaster').download_fileobj('images/db/' + imageChoice, imageBinaryDload)
                render(imageBinaryDload, caption).save(imageBinarySend, 'JPEG')

                imageBinarySend.seek(0)

                if success == "1":
                    embed = hikari.Embed()
                else:
                    embed = hikari.Embed(
                        title = f"I couldn't find anything for {tags_requested}, so I just used this picture:"
                    )

                embed.set_footer(tagsSend)
                embed.set_image(imageBinarySend)

                await ctx.edit_last_response(content="Toasting meme...DING", 
                                             embed=embed)

        log_request(tag=tags, caption=caption,
                    success=success, conn=conn)

        conn.close()
        if not pm2:
            server.stop()


    

##
def load(bot: Bot):
    bot.add_plugin(plugin)

def unload(bot: Bot):
    bot.remove_plugin(plugin)