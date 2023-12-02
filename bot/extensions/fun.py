from io import BytesIO
from os import getenv

import boto3
import hikari
import lightbulb
import string

from bot import Bot
from bot.pic import render
from data import *

plugin = lightbulb.Plugin("Functions")

## TODO Move nsfw and version commands to a separate utility/admin functions .py file
@plugin.command
@lightbulb.command(name="nsfw", description="check if channel is nsfw")
@lightbulb.implements(lightbulb.PrefixCommand)
async def command_version(ctx: lightbulb.Context) -> None:

    ch_id = ctx.channel_id

    ch_obj = await plugin.app.rest.fetch_channel(ch_id)

    await ctx.respond(ch_obj.is_nsfw)


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
@lightbulb.command(name = "tags", description = "Get list of all available tags")
@lightbulb.implements(lightbulb.SlashCommand, lightbulb.PrefixCommand)
async def command_stats(ctx: lightbulb.Context) -> None:

    f = hikari.File("data/tags.txt")
    await ctx.respond(f)


@plugin.command
@lightbulb.option(
    name = "caption", 
    description = "Caption to add to the picture (125 chars or less)", 
    type = str, default = "", 
    modifier = lightbulb.commands.OptionModifier.CONSUME_REST)
@lightbulb.option(
    name = "tags", 
    description = "Tags to search for (up to 10 words)", 
    type = str, required = True)
@lightbulb.command(
    name = "meme", 
    description = "Put a picture tag and caption in the toaster")
@lightbulb.implements(lightbulb.SlashCommand, lightbulb.PrefixCommand)
async def command_meme(ctx: lightbulb.Context) -> None:
    caption = ctx.options.caption.strip()[:125]
    
    tags_requested = ctx.options.tags.lower().translate(
        str.maketrans('', '', string.punctuation + string.digits)
        ).split()[:10]

    pm2 = getenv("PM2_HOME")

    if pm2:
        conn = sql_connect()
    else:
        server = ssh_connect()
        server.start()

        conn = sql_connect(server)


    tags_filtered = filter_stopwords(tags_requested)

    # Get age-restricted status
    ch_obj = await plugin.app.rest.fetch_channel(ctx.channel_id)
    agerestrict = ch_obj.is_nsfw

    imageChoice, success = query_by_tags(tags_filtered, agerestrict, conn)

    await ctx.respond("Toasting meme...")

    imageChoice_tags = query_tag_by_filename(imageChoice, conn)

    tagsHashed = ["#" + t for t in imageChoice_tags]
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

    log_request(tags=tags_requested, caption=caption,
                success=success, conn=conn)

    conn.close()
    if not pm2:
        server.stop()


@plugin.command
@lightbulb.option(name = "caption", description = "Caption to add to the picture (125 chars or less)", type = str, default = "",
                    modifier = lightbulb.commands.OptionModifier.CONSUME_REST)
@lightbulb.option(name = "emoji", description = "Emoji to search a matching picture for", type = str, required = True)
@lightbulb.command(name = "emoji", description="[BETA] Create meme with an emoji and caption")
@lightbulb.implements(lightbulb.SlashCommand, lightbulb.PrefixCommand)
async def command_emoji(ctx: lightbulb.Context) -> None:

    caption = ctx.options.caption.strip()[:125]

    emoji_list = [i for i in ctx.options.emoji]

    # Drop blanks
    if ' ' in emoji_list:
        emoji_list.remove(' ')
    
    if chr(65039) in emoji_list:
        emoji_list.remove(chr(65039))

    emoji_dict = {}
    remove_list = []

    # If there are more than one emoji or at least one compound emoji, group together icons with \u200d between them
    for i in range(len(emoji_list)):
        if emoji_list[i] == "\u200d":
            emoji_dict["group" + str(i)] = [emoji_list[i-1], emoji_list[i+1]]

            remove_list += [i+1, i, i-1]
        else:
            pass

    # drop all from remove list (if anything is there)
    if len(remove_list) > 0:
        for index in sorted(remove_list, reverse=True):
            del emoji_list[index]

    # Add non-composite emojis to dictionary (If there are any)
    if len(emoji_list) > 0:
        for i, emoji in enumerate(emoji_list):
            emoji_dict["single" + str(i)] = emoji

    # Retrieve unicode from dictionary
    unicode_list = []
    for emoji in emoji_dict.keys():
        unicode_pre_list = []
        for e in emoji_dict[emoji]:

            unicode = hex(ord(e))[2:]

            unicode_pre_list.append(unicode)

        unicode_list.append(
            "-".join(unicode_pre_list)
        )

    # Remove duplicates from unicode list
    unicode_list = [*set(unicode_list)]

    emoji_error_string = f"{ctx.author.mention} I'm sorry, I don't know what to do with flags, numbers or letters. Try a smiley face or a person!"

    # Get env
    pm2 = getenv("PM2_HOME")

    # Depending on env, connect to db with or without ssh tunnel
    if pm2:
        conn = sql_connect()
    else:
        server = ssh_connect()
        server.start()

        conn = sql_connect(server)

    if len(unicode_list) == 0:
        await ctx.respond(f"""
{ctx.author.mention} sorry, I didn't recognize the emojis in your request""")

        log_error(2, "N Emojis == 0", conn)

    elif any([(i > "1f1e5") & (i < "1f1g") for i in unicode_list]):
        await ctx.respond(emoji_error_string)

        log_error(3, "Invalid Emoji: Letter", conn)

    elif any([i in ("20e3", "1f51f", "1f522") for i in unicode_list]):
        await ctx.respond(emoji_error_string)

        log_error(3, "Invalid Emoji: Number, Hash or Asterisk", conn)

    elif any([i in ['2a', '2733'] for i in unicode_list]):
        await ctx.respond(emoji_error_string)

        log_error(3, "Invalid Emoji: asterisk", conn)

    elif any([i == 'e0067' for i in unicode_list]):
        await ctx.respond(emoji_error_string)

        log_error(3, "Invalid Emoji: UK Flag", conn)

    else:
        tags_requested = get_tags_from_unicode(unicode_list, conn)

        # Get age-restricted status
        ch_obj = await plugin.app.rest.fetch_channel(ctx.channel_id)
        agerestrict = ch_obj.is_nsfw

        imageChoice, success = query_by_tags(tags_requested, agerestrict, conn)

        await ctx.respond("Toasting meme...")

        imageChoice_tags = query_tag_by_filename(imageChoice, conn)

        tagsHashed = ["#" + t for t in imageChoice_tags]
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

        log_request(tags=tags_requested, caption=caption,
                    success=success, conn=conn)

        conn.close()
        if not pm2:
            server.stop()
    

##
def load(bot: Bot):
    bot.add_plugin(plugin)

def unload(bot: Bot):
    bot.remove_plugin(plugin)
