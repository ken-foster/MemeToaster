from io import BytesIO
import string

import boto3
import hikari
import lightbulb

from bot import Bot
from bot.pic import render
from data import *

plugin = lightbulb.Plugin("Functions")

@plugin.command
@lightbulb.option(name = "caption", description = "caption to attach", type = str, default = "",
                    modifier = lightbulb.commands.OptionModifier.CONSUME_REST)
@lightbulb.option(name = "tag", description = "picture tag", type = str, required = True)
@lightbulb.command(name = "meme", description = "Put a picture tag and caption in the toaster")
@lightbulb.implements(lightbulb.SlashCommand, lightbulb.PrefixCommand)
async def command_meme(ctx: lightbulb.Context) -> None:
    caption = ctx.options.caption.strip()
    tag = ctx.options.tag.translate(
        str.maketrans('', '', string.punctuation + string.digits)
        ).split()[0].lower()

    conn = sql_connect()
    tags = sql_tags(conn)
    tagSet = set(
        [i[0] for i in tags]
    )

    print(tagSet)

    imageChoice = query_filename_by_tag(tag, conn)
    print(caption)
    print(imageChoice)

    await ctx.respond("Toasting meme...")

    #channel = ctx.get_channel()

    s3 = boto3.Session().resource("s3")

    with BytesIO() as imageBinaryDload:
        with BytesIO() as imageBinarySend:
            s3.Bucket('memetoaster').download_fileobj('images/db/' + imageChoice, imageBinaryDload)
            render(imageBinaryDload, caption).save(imageBinarySend, 'JPEG')

            imageBinarySend.seek(0)

            embed = hikari.Embed()
            embed.set_image(imageBinarySend)
            await ctx.respond(embed)

    await ctx.edit_last_response("Toasting meme... DING")

    conn.close()

    

##
def load(bot: Bot):
    bot.add_plugin(plugin)

def unload(bot: Bot):
    bot.remove_plugin(plugin)