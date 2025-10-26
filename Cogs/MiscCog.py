import re
import asyncio
import requests
import discord
from discord import app_commands
from discord.ext import commands

MAX_MESSAGE_LENGTH = 2000

IMAGE_REGEX = r'(.*)\n\n(!\[.+?\]\(.+?\))(\s*.*)'

def split_message(message):
    out = ['']
    lines = message.split('\n')

    for line in lines:
        to_add = f'\n{line}'
        curr_length = len(out[-1])

        new_length = curr_length + len(to_add)
        if new_length > MAX_MESSAGE_LENGTH:
            out.append(to_add)
        else:
            out[-1] += to_add

    if out[0] and out[0].startswith('\n'):
        out[0] = out[0][1:]

    return out

def gh_markdown_to_discord(messages):
    i = 0
    while i < len(messages):
        message = messages[i]
        match = re.search(IMAGE_REGEX, message, re.S)
        if match:
            before = match.group(1)
            image = re.sub(r'\[.+\]', '[⠀]', match.group(2).replace('!', ''))
            rest = match.group(3).strip()

            messages[i] = before + image
            if rest:
                messages.insert(i + 1, rest)
                i += 2
            else:
                i += 1
        else:
            i += 1

    return messages

def convert_and_split(content):
    messages = gh_markdown_to_discord([content])

    i = 0
    while i < len(messages):
        message = messages[i]
        split_messages = split_message(message)
        if len(split_messages) > 1:
            messages[i] = split_messages[0]
            y = 1
            while y < len(split_messages):
                messages.insert(i + y, split_messages[y])
                y += 1
        i += 1

    return messages

class MiscCog(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot
        self.base_url = 'https://raw.githubusercontent.com/bliind/snap-wiki/refs/heads/main/'

    async def fetch_article(self, filename):
        if not filename.endswith('.md'):
            filename += '.md'

        resp = requests.get(self.base_url + filename)
        return resp.text

    @app_commands.command(name='fetch_article', description='Fetch a specific article')
    async def fetch_article_command(self, interaction: discord.Interaction, filename: str):
        await interaction.response.defer(ephemeral=True)

        try:
            content = await self.fetch_article(filename)
            messages = convert_and_split(content)
            for message in messages:
                await interaction.channel.send(message)

            await interaction.delete_original_response()
        except Exception as e:
            await interaction.edit_original_response(content='Something went wrong, sorry!')
            print(f'Failed to fetch article at {filename}:')
            print(e)

    @app_commands.command(name='replace_article', description='Delete the current article and fetch a specific one')
    async def replace_article_command(self, interaction: discord.Interaction, filename: str):
        if not isinstance(interaction.channel, discord.Thread):
            return

        await interaction.response.defer(ephemeral=True)
        messages = [m async for m in interaction.channel.history(limit=None, oldest_first=True)]
        # delete all but first message (the opener)
        i = 1
        while i < len(messages):
            await messages[i].delete()
            await asyncio.sleep(0.5)
            i += 1

        # pull article content
        try:
            content = await self.fetch_article(filename)
            messages = convert_and_split(content)
            for message in messages:
                await interaction.channel.send(message)

            await interaction.delete_original_response()
        except Exception as e:
            await interaction.edit_original_response(content='Something went wrong, sorry!')
            print(f'Failed to fetch article at {filename}:')
            print(e)
