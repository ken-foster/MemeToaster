from io import BytesIO
from os import environ
import string

import boto3
import hikari
import lightbulb

from bot import Bot
from bot.pic import render
from data import *

plugin = lightbulb.Plugin("Functions")

@plugin.command
@lightbulb.command(name="version")
@lightbulb.implements(lightbulb.PrefixCommand)
async def command_version(ctx: lightbulb.Context) -> None:
    
    await ctx.respond(environ["VERSION"])


@plugin.command
@lightbulb.command(name = "tags", description = "Get a link to a list of all available tags")
@lightbulb.implements(lightbulb.SlashCommand, lightbulb.PrefixCommand)
async def command_stats(ctx: lightbulb.Context) -> None:

    f = hikari.File("data/tags.txt")
    await ctx.respond(f)


@plugin.command
@lightbulb.option(name = "caption", description = "caption to attach", type = str, default = "",
                    modifier = lightbulb.commands.OptionModifier.CONSUME_REST)
@lightbulb.option(name = "tag", description = "picture tag", type = str, required = True)
@lightbulb.command(name = "meme", description = "Put a picture tag and caption in the toaster")
@lightbulb.implements(lightbulb.SlashCommand, lightbulb.PrefixCommand)
async def command_meme(ctx: lightbulb.Context) -> None:
    caption = ctx.options.caption.strip()

    if len(caption) > 125:
                await ctx.respond(f"""
{ctx.author.mention} it's a meme, not your master's thesis. Your caption has to be 125 characters or less.""")

    else:
        tag = ctx.options.tag.translate(
            str.maketrans('', '', string.punctuation + string.digits)
            ).split()[0].lower()

        conn = sql_connect()

        imageChoice = query_filename_by_tag(tag, conn)

        if imageChoice is None:
            await ctx.respond(f"""
Sorry {ctx.author.mention}, I don't have any pictures for '{tag}'...yet!
Use toast.help or toast.tags for a list of tags
""")

            log_request(tag=tag, caption=caption,
                        success="0", conn=conn)

        else:
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

                    embed = hikari.Embed()
                    embed.set_footer(tagsSend)
                    embed.set_image(imageBinarySend)
                    await ctx.respond(embed)

            log_request(tag=tag, caption=caption,
                        success="1", conn=conn)

            conn.close()

    

##
def load(bot: Bot):
    bot.add_plugin(plugin)

def unload(bot: Bot):
    bot.remove_plugin(plugin)