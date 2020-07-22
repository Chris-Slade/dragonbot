from util import command_method
import constants
import logging
import random
import util

class Magic8Ball():

    def __init__(self):
        self.logger = logging.getLogger('dragonbot.' + __name__)

    def register_commands(self, cd):
        """Register this modules's commands with a CommandDispatcher.

        Arguments:
            cd -- The CommandDispatcher to register with.
        """
        cd.register('8ball', self.eightball)
        self.logger.info('Registered commands')

    @staticmethod
    def help():
        return util.create_help_embed(
            title='Magic 8-Ball',
            description='This module lets you query a Magic 8-Ball',
            help_msgs=[ [
                '{prefix}8ball',
                'Query the Magic 8-Ball'
            ] ]
        )

    @command_method
    async def eightball(self, _client, message):
        await message.channel.send(random.choice(constants.EIGHT_BALL_ANSWERS))
