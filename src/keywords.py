import ahocorasick
import discord
import logging
import os
import re

from insult import random_insult
from storage import FileStorage
from util import command_method, server_command_method
import config
import constants
import util

class Keywords():
    """A keywords module for DragonBot."""

    def __init__(self): # , keywords_file):
        self.logger = logging.getLogger('dragonbot.' + __name__)
        self.keywords = {}
        self.automata = {}

    def __len__(self):
        return self.keywords.__len__()

    def add_server(self, server):
        """Track emotes for a server."""
        if config.storage_dir:
            self.keywords[server.id] = FileStorage(
                store_type='keywords',
                store_id=server.id
            )
            self.logger.info(
                '[%s] Loaded %d keyword(s) from disk',
                server,
                len(self.keywords[server.id])
            )
        elif config.mongodb_uri:
            pass
        self.update_automaton(server)

    @staticmethod
    def help():
        return """```
Keywords:
  The bot counts keywords and sends messages when "gets" occur.
  (Technically, it counts messages in which a keyword occurs.) The bot
  can also post reactions to keywords.

  {prefix}addkeyword <keyword> <optional reaction>
    Add a keyword. The bot will count these keywords and send a message
    when a "get" occurs. In addition, reactions may be given, which
    are automatically added to messages containing keywords. A given
    keyword may have zero or more reactions, but they have to be added
    one at a time. The syntax of this command might change to allow for
    keyphrases in addition to just words.

  {prefix}count <keyword>
    Show the current count of a given keyword.

  {prefix}deletekeyword
    Alias for `removekeyword`.

  {prefix}refreshkeywords
    (Owner only.) Reload the keywords for the current server.

  {prefix}removekeyword <keyword>
    Remove a keyword. WARNING: This removes a keyword with its count and
    all associated reactions. There is currently not a way to remove
    just a reaction to reset the counter in isolation.
```""".format(prefix=constants.COMMAND_PREFIX)

    def register_commands(self, cd):
        cd.register("addkeyword",    self.add_keyword,    rw=True)
        cd.register("deletekeyword", self.remove_keyword, rw=True)
        cd.register("removekeyword", self.remove_keyword, rw=True)
        cd.register("keywords",      self.list_keywords)
        cd.register("count",         self.show_count)
        cd.register("refreshkeywords", self.refresh_keywords, may_use={config.owner_id})
        self.logger.info('Registered commands')

    def update_automaton(self, server):
        # Make a new Aho-Corasick automaton
        self.automata[server.id] = ahocorasick.Automaton(str)
        automaton = self.automata[server.id]
        # Add each keyword
        for keyword in self.keywords[server.id]:
            automaton.add_word(keyword, keyword)
        # Finalize the automaton for searching
        automaton.make_automaton()
        self.logger.debug('[%s] Updated automaton', server)

    def count_keywords(self):
        return sum([ len(self.keywords[server]) for server in self.keywords ])

    @command_method
    async def handle_keywords(self, _client, message):
        """Processes a message, checking it for keywords and performing
        actions when they are found.
        """
        assert message is not None
        if message.guild is None:
            return
        assert message.guild.id in self.keywords, \
            'ID {} not in keywords, which has keys {}'.format(
                message.guild.id,
                ', '.join(self.keywords.keys())
            )

        server_keywords = self.keywords[message.guild.id]
        if not server_keywords:
            return
        content = message.clean_content.casefold()
        seen = set()
        for _index, keyword in self.automata[message.guild.id].iter(content):
            # Count keyword
            if keyword in seen:
                continue
            seen.add(keyword)
            server_keywords[keyword]['count'] += 1
            count = server_keywords[keyword]['count']
            self.logger.info(
                '%s incremented count of "%s" to %d',
                message.author,
                keyword,
                count
            )
            if util.is_get(count):
                await message.channel.send('{} #{}'.format(keyword, count))
                server_keywords.save()

            # Show reactions
            reactions = server_keywords[keyword]['reactions']
            self.logger.debug(
                'Got reactions [%s] for keyword "%s"',
                ", ".join(reactions) if reactions is not None else "None",
                keyword
            )
            for reaction in reactions:
                self.logger.info('Reacting with "%s"', reaction)
                try:
                    await message.add_reaction(reaction)
                except discord.errors.Forbidden:
                    self.logger.info('Reached max number of reactions')
                    return
                except discord.HTTPException:
                    self.logger.exception(
                        'Error reacting to keyword "%s" with "%s"',
                        keyword,
                        reaction
                    )

    @server_command_method
    async def add_keyword(self, _client, message):
        server_keywords = self.keywords[message.guild.id]
        _command, argstr = util.split_command(message)
        if argstr is None:
            await message.channel.send(
                "I can't add nothing, {}.".format(random_insult())
            )
            return
        try:
            name, emote = argstr.split(maxsplit=1)
        except:
            # If we just have a name, add it as a keyword with no reaction.
            server_keywords[argstr] = { 'reactions' : [], 'count' : 0 }
            self.update_automaton(message.guild)
            await message.channel.send('Keyword added!')
            self.logger.info('%s added keyword "%s"', message.author, argstr)
            return

        # Try to extract a custom emoji's name and ID
        match = re.match(r'<:([^:]+:\d+)>', emote)
        if match:
            emote = match.group(1)

        # Assume an emoji is correct and just store it
        if name in server_keywords:
            server_keywords[name]['reactions'].append(emote)
        else:
            server_keywords[name] = { 'reactions' : [emote], 'count' : 0 }
        server_keywords.save()
        self.update_automaton(message.guild)
        await message.channel.send('Added keyword reaction!')
        self.logger.info(
            '%s added keyword "%s" -> "%s"',
            message.author,
            name,
            emote
        )

    @server_command_method
    async def remove_keyword(self, _client, message):
        server_keywords = self.keywords[message.guild.id]
        _command, name = util.split_command(message)
        if name is None:
            await message.channel.send(
                "I can't delete nothing, {}.".format(random_insult())
            )
            return
        try:
            del server_keywords[name]
            server_keywords.save()
            self.update_automaton(message.guild)
            await message.channel.send('Removed keyword!')
            self.logger.info('%s removed keyword "%s"', message.author, name)
        except KeyError:
            await message.channel.send("That keyword doesn't exist!")

    @server_command_method
    async def refresh_keywords(self, _client, message):
        if hasattr(message, 'guild'):
            self.keywords[message.channel.guild.id].load()
            await message.channel.send('Keywords refreshed!')
        else:
            await message.channel.send('You must be in a server to do that.')

    @server_command_method
    async def list_keywords(self, _client, message):
        server_keywords = self.keywords[message.guild.id]
        if not server_keywords:
            await message.channel.send(
                "I don't have any keywords for this server yet!"
            )
        for chunk in util.chunker(server_keywords.as_text_list(), 2000):
            await message.channel.send(chunk)

    @server_command_method
    async def show_count(self, _client, message):
        server_keywords = self.keywords[message.guild.id]
        _command, keyword = util.split_command(message)
        if keyword in server_keywords:
            await message.channel.send(server_keywords[keyword]['count'])
        else:
            if constants.IDK_REACTION is not None:
                await message.channel.send(constants.IDK_REACTION)
