import discord
import logging
import os
import re

from insult import random_insult
from storage import Storage, KeyExistsError
from util import command_method, server_command_method
import constants
import util

class Emotes(object):
    """Emotes module for DragonBot."""

    def __init__(self):
        self.logger = logging.getLogger('dragonbot.' + __name__)
        self.emotes = {}

    def __len__(self):
        return self.emotes.__len__()

    def add_server(self, server, storage_dir):
        """Track emotes for a server."""
        self.storage_dir = storage_dir
        server_dir = os.path.join(
            storage_dir,
            '{}-{}'.format(util.normalize_path(server.name), server.id)
        )
        try:
            os.mkdir(server_dir)
        except FileExistsError:
            pass
        self.emotes[server.id] = Storage(os.path.join(server_dir, 'emotes.json'))
        self.logger.info(
            '[%s] Loaded %d emote(s) from disk',
            server,
            len(self.emotes[server.id])
        )

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

    def count_emotes(self):
        return sum([ len(self.emotes[server]) for server in self.emotes ])

    @server_command_method
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
            await message.channel.send(
                'Give me a name and a URL, {}.'.format(random_insult())
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
    async def remove_emote(self, client, message):
        command, argstr = util.split_command(message)
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
    async def refresh_emotes(self, client, message):
        # FIXME
        self.emotes.load(self.emotes_file)
        await message.channel.send('Emotes refreshed!')

    @server_command_method
    async def list_emotes(self, client, message):
        if len(self.emotes[message.guild.id]) == 0:
            await message.channel.send(
                "I don't have any emotes for this server yet!"
            )
        for chunk in util.chunker(
            self.emotes[message.guild.id].as_text_list(),
            constants.MAX_CHARACTERS
        ):
            await message.channel.send(chunk)

    @server_command_method
    async def display_emote(self, client, message):
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
