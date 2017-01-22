import ahocorasick
import discord
import logging
import re

from storage import Storage
from util import command_method
import constants
import util

class Keywords(object):
    """A keywords module for DragonBot."""

    def __init__(self, keywords_file):
        self.logger = logging.getLogger('dragonbot.' + __name__)
        self.keywords_file = keywords_file
        self.keywords = Storage(keywords_file)
        self.logger.info('Loaded %d keywords from disk', len(self.keywords))
        self.update_automaton()

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

  {prefix}removekeyword <keyword>
    Remove a keyword. WARNING: This removes a keyword with its count and
    all associated reactions. There is currently not a way to remove
    just a reaction to reset the counter in isolation.
```""".format(prefix=constants.COMMAND_PREFIX)

    def register_commands(self, cd, config):
        cd.register("addkeyword",    self.add_keyword,    rw=True)
        cd.register("deletekeyword", self.remove_keyword, rw=True)
        cd.register("removekeyword", self.remove_keyword, rw=True)
        cd.register("keywords",      self.list_keywords)
        cd.register("count",         self.show_count)
        self.logger.info('Registered commands')

    def update_automaton(self):
        # Make a new Aho-Corasick automaton
        self.automaton = ahocorasick.Automaton(str)
        # Add each keyword
        for keyword in self.keywords:
            self.automaton.add_word(keyword, keyword)
        # Finalize the automaton for searching
        self.automaton.make_automaton()
        self.logger.debug('Updated automaton')

    @command_method
    async def handle_keywords(self, client, message):
        """Processes a message, checking it for keywords and performing
        actions when they are found.
        """
        assert message is not None

        content = message.clean_content.casefold()
        seen = set()
        for index, keyword in self.automaton.iter(content):
            # Count keyword
            if keyword in seen:
                continue
            seen.add(keyword)
            self.keywords[keyword]['count'] += 1
            count = self.keywords[keyword]['count']
            self.logger.info('Incremented count of "%s" to %d', keyword, count)
            if util.is_get(count):
                await client.send_message(
                    message.channel,
                    '{} #{}'.format(keyword, count)
                )
                self.keywords.save()

            # Show reactions
            reactions = self.keywords[keyword]['reactions']
            self.logger.debug(
                'Got reactions [%s] for keyword "%s"',
                ", ".join(reactions) if reactions is not None else "None",
                keyword
            )
            for reaction in reactions:
                self.logger.info('Reacting with "%s"', reaction)
                try:
                    await client.add_reaction(message, reaction)
                except discord.errors.Forbidden:
                    self.logger.info('Reached max number of reactions')
                    return
                except discord.HTTPException as e:
                    self.logger.exception(
                        'Error reacting to keyword "%s" with "%s"',
                        keyword,
                        reaction
                    )

    @command_method
    async def add_keyword(self, client, message):
        command, argstr = util.split_command(message)
        try:
            name, emote = argstr.split(maxsplit=1)
        except:
            # If we just have a name, add it as a keyword with no reaction.
            self.keywords[argstr] = { 'reactions' : [], 'count' : 0 }
            self.update_automaton()
            await client.send_message(message.channel, 'Keyword added!')
            self.logger.info(
                '%s added keyword "%s"',
                message.author.name,
                argstr
            )
            return

        # Try to extract a custom emoji's name and ID
        match = re.match(r'<:([^:]+:\d+)>', emote)
        if match:
            emote = match.group(1)

        # Assume an emoji is correct and just store it
        if name in self.keywords:
            self.keywords[name]['reactions'].append(emote)
        else:
            self.keywords[name] = { 'reactions' : [emote], 'count' : 0 }
        self.keywords.save()
        self.update_automaton()
        await client.send_message(
            message.channel,
            'Added keyword reaction!'
        )
        self.logger.info(
            '%s added keyword "%s" -> "%s"',
            message.author.name,
            name,
            emote
        )

    @command_method
    async def remove_keyword(self, client, message):
        command, name = util.split_command(message)
        try:
            del self.keywords[name]
            self.keywords.save()
            self.update_automaton()
            await client.send_message(
                message.channel,
                'Removed keyword!'
            )
            self.logger.info(
                '%s removed keyword "%s"',
                message.author.name,
                name
            )
        except KeyError:
            await client.send_message(
                message.channel,
                "That keyword doesn't exist!"
            )

    @command_method
    async def list_keywords(self, client, message):
        if len(self.keywords) == 0:
            await client.send_message(
                message.channel,
                "I don't have any keywords yet!"
            )
        for chunk in util.chunker(self.keywords.as_text_list(), 2000):
            await client.send_message(message.channel, chunk)

    @command_method
    async def show_count(self, client, message):
        command, keyword = util.split_command(message)
        if keyword in self.keywords:
            await client.send_message(
                message.channel,
                self.keywords[keyword]['count']
            )
        else:
            await client.send_message(message.channel, constants.IDK_REACTION)
