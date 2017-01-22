import discord
import logging
import re

from insult import random_insult
from storage import Storage, KeyExistsError
from util import command_method
import constants
import util

class Emotes(object):
    """Emotes module for DragonBot."""

    def __init__(self, emotes_file):
        self.logger = logging.getLogger('dragonbot.' + __name__)
        self.emotes_file = emotes_file
        self.emotes = Storage(emotes_file)
        self.logger.info('Loaded %d emotes from disk', len(self.emotes))

    @staticmethod
    def help():
        return """```
Emotes:
  Emotes are activated by sending a message beginning with the prefix
  "{eprefix}" followed by the name of the emote.

  {prefix}addemote {{<emote name>}}{{<emote payload>}}
    Adds an emote. For example, `!addemote
    {{example}}{{http://example.com/emote.png}}` will allow you to
    use `@example` to have the corresponding URL posted by the bot.
    Because both emote names and the corresponding strings may contain
    whitespace, both must be surrounded by curly braces, as in the
    example.

  {prefix}deleteemote <emote name>
    Alias for `{prefix}removeemote`.

  {prefix}emotes
    Show a list of known emotes.

  {prefix}removeemote <emote name>
    Remove an emote.
```""".format(eprefix=constants.EMOTE_PREFIX, prefix=constants.COMMAND_PREFIX)

    def register_commands(self, cd, config=None):
        """Register this module's commands with a CommandDispatcher.

        Arguments:
            cd -- The CommandDispatcher to register with.
        """
        cd.register("emotes",        self.list_emotes)
        cd.register("addemote",      self.add_emote,      rw=True)
        cd.register("deleteemote",   self.remove_emote,   rw=True)
        cd.register("removeemote",   self.remove_emote,   rw=True)
        cd.register("refreshemotes", self.refresh_emotes, may_use={config['owner_id']})
        self.logger.info('Registered commands')

    @command_method
    async def add_emote(self, client, message):
        command, argstr = util.split_command(message)
        try:
            if argstr is None:
                raise ValueError('No arguments')
            pattern = re.compile(
                r'^ \s* \{ \s* ([^{}]+) \s* \} \s* \{ \s* ([^{}]+) \s* \}',
                re.X
            )
            match = pattern.search(argstr)
            if match:
                emote, body = match.group(1, 2)
                emote = emote.strip()
                body = body.strip()
            else:
                raise ValueError('Malformed parameters to !addemote')
        except Exception as e:
            self.logger.info('Failed to parse !addcommand', exc_info=e)
            await client.send_message(
                message.channel,
                'Give me a name and a URL, {}.'.format(random_insult())
            )
            return

        try:
            self.emotes[emote] = body
            self.emotes.save()
            self.logger.info(
                'Emote "%s" added by "%s"',
                emote,
                message.author.name
            )
            await client.send_message(
                message.channel,
                'Added emote!'
            )
        except KeyExistsError:
            await client.send_message(
                message.channel,
                'That emote already exists, {}.'.format(random_insult())
            )
    # End of add_emote

    @command_method
    async def remove_emote(self, client, message):
        command, argstr = util.split_command(message)
        if argstr is None:
            await client.send_message(
                message.channel,
                "I can't delete nothing, {}.".format(random_insult())
            )
            return

        emote = argstr
        try:
            del self.emotes[emote]
            self.emotes.save()
            self.logger.info(
                'Emote "%s" deleted by "%s"',
                emote,
                message.author.name
            )
            await client.send_message(message.channel, 'Deleted emote!')
        except KeyError:
            await client.send_message(
                message.channel,
                "That emote isn't stored, {}.".format(random_insult())
            )
    # End of remove_emote

    @command_method
    async def refresh_emotes(self, client, message):
        self.emotes.load(self.emotes_file)
        await client.send_message(message.channel, 'Emotes refreshed!')

    @command_method
    async def list_emotes(self, client, message):
        if len(self.emotes) == 0:
            await client.send_message(
                message.channel,
                "I don't have any emotes yet!"
            )
        for chunk in util.chunker(
            self.emotes.as_text_list(),
            constants.MAX_CHARACTERS
        ):
            await client.send_message(message.channel, chunk)

    @command_method
    async def display_emote(self, client, message):
        emote = message.clean_content[1:]
        if emote in self.emotes:
            self.logger.debug('Posting emote "%s"', self.emotes[emote])
            await client.send_message(message.channel, self.emotes[emote])
        else:
            self.logger.debug('Unknown emote')
            await client.add_reaction(message, constants.IDK_REACTION)

# End of Emotes
