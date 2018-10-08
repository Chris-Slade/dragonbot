import logging
import re

from insult import random_insult
from storage import FileStorage, MongoStorage, KeyExistsError
from util import server_command_method
import config
import constants
import util

class Emotes():
    """Emotes module for DragonBot."""

    def __init__(self):
        self.logger = logging.getLogger('dragonbot.' + __name__)
        self.emotes = {}

    def __len__(self):
        return self.emotes.__len__()

    def add_server(self, server, storage):
        """Track emotes for a server."""
        self.emotes[server.id] = storage

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

  {prefix}refreshemotes
    (Owner only.) Reload the emotes for the current server.

  {prefix}removeemote <emote name>
    Remove an emote.
```""".format(eprefix=constants.EMOTE_PREFIX, prefix=constants.COMMAND_PREFIX)

    def register_commands(self, cd):
        """Register this module's commands with a CommandDispatcher.

        Arguments:
            cd -- The CommandDispatcher to register with.
        """
        cd.register("emotes",        self.list_emotes)
        cd.register("addemote",      self.add_emote,      rw=True)
        cd.register("deleteemote",   self.remove_emote,   rw=True)
        cd.register("removeemote",   self.remove_emote,   rw=True)
        cd.register("refreshemotes", self.refresh_emotes, may_use={config.owner_id})
        self.logger.info('Registered commands')

    def count_emotes(self):
        return sum([ len(self.emotes[server]) for server in self.emotes ])

    @server_command_method
    async def add_emote(self, _client, message):
        _command, argstr = util.split_command(message)
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
            await message.channel.send(
                'Give me a name and a value, {}.'.format(random_insult())
            )
            return

        try:
            self.emotes[message.guild.id][emote] = body
            self.emotes[message.guild.id].save()
            self.logger.info(
                '[%s] %s added emote "%s"',
                message.guild,
                message.author,
                emote
            )
            await message.channel.send('Added emote!')
        except KeyExistsError:
            await message.channel.send(
                'That emote already exists, {}.'.format(random_insult())
            )
    # End of add_emote

    @server_command_method
    async def remove_emote(self, _client, message):
        _command, argstr = util.split_command(message)
        if argstr is None:
            await message.channel.send(
                "I can't delete nothing, {}.".format(random_insult())
            )
            return

        emote = argstr
        try:
            del self.emotes[message.guild.id][emote]
            self.emotes[message.guild.id].save()
            self.logger.info(
                '[%s] %s deleted emote "%s"',
                message.guild,
                message.author,
                emote
            )
            await message.channel.send('Deleted emote!')
        except KeyError:
            await message.channel.send(
                "That emote isn't stored, {}.".format(random_insult())
            )
    # End of remove_emote

    @server_command_method
    async def refresh_emotes(self, _client, message):
        if hasattr(message, 'guild'):
            self.emotes[message.channel.guild.id].load()
            await message.channel.send('Emotes refreshed!')
        else:
            await message.channel.send('You must be in a server to do that.')

    @server_command_method
    async def list_emotes(self, _client, message):
        if not self.emotes[message.guild.id]:
            await message.channel.send(
                "I don't have any emotes for this server yet!"
            )
        for chunk in util.chunker(
            self.emotes[message.guild.id].as_text_list(),
            constants.MAX_CHARACTERS
        ):
            await message.channel.send(chunk)

    @server_command_method
    async def display_emote(self, _client, message):
        emote = message.clean_content[1:]
        server_emotes = self.emotes[message.guild.id]
        if emote in server_emotes:
            self.logger.debug('Posting emote "%s"', server_emotes[emote])
            await message.channel.send(server_emotes[emote])
        else:
            self.logger.debug('Unknown emote')
            if constants.IDK_REACTION is not None:
                await message.add_reaction(constants.IDK_REACTION)

# End of Emotes
