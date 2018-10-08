import discord
import logging
import urllib

import config
import constants
import util

from util import command_method

class WolframAlpha():

    def __init__(self):
        self.logger = logging.getLogger('dragonbot.' + __name__)

    def register_commands(self, cd):
        """Register this module's commands with a CommandDispatcher.

        Arguments:
            cd -- The CommandDispatcher to register with.
        """
        cd.register('wolfram', self.wolfram_alpha)
        cd.register('ask', self.ask)
        self.logger.info('Registered commands')

    @staticmethod
    def help():
        return util.create_help_embed(
            title='Wolfram Alpha',
            description='This module allows you to make queries using Wolfram'
                ' Alpha.',
            help_msgs=[ [
                '{prefix}wolfram',
                'Make a query using Wolfram Alpha.'
            ], [
                '{prefix}ask',
                'Ask a question, get a simple answer.'
            ] ]
        )

    @command_method
    async def wolfram_alpha(self, _client, message):
        _command, arg = util.split_command(message)
        try:
            url = await self.make_request(arg, constants.WOLFRAM_SIMPLE)
            self.logger.debug('GET %s', url)
            sent = await message.channel.send('Working on it…')
            rsp = urllib.request.urlopen(url)
            image = discord.File(fp=rsp, filename='query.png')
            await message.channel.send(file=image)
            await sent.delete()
        except urllib.error.HTTPError as e:
            if e.code == 501:
                await message.channel.send(
                    'Wolfram Alpha could not understand your query.'
                )
            elif e.code == 400:
                await message.channel.send('Invalid input.')
            self.logger.exception('Error from Wolfram Alpha API')
        except:
            self.logger.exception('Unknown error')
            await message.channel.send('Unknown error.')

    @command_method
    async def ask(self, _client, message):
        _command, arg = util.split_command(message)
        if arg is None:
            await message.channel.send('What is your question?')
        try:
            url = await self.make_request(arg, constants.WOLFRAM_SHORT)
            self.logger.debug('GET %s', url)
            rsp = urllib.request.urlopen(url)
            await message.channel.send(rsp.read().decode('utf8'))
        except urllib.error.HTTPError as e:
            if e.code == 501:
                await message.channel.send("I don't know how to answer that.")
            elif e.code == 400:
                await message.channel.send('Invalid input.')
            self.logger.exception('Error from Wolfram Alpha API')
        except:
            self.logger.exception('Unknown error')
            await message.channel.send('Unknown error.')

    async def make_request(self, query, api):
        if api == constants.WOLFRAM_SHORT:
            query_params = urllib.parse.urlencode({
                'appid' : config.wolfram_app_id,
                'i': query,
            })
            return '{}{}?{}'.format(
                constants.WOLFRAM_API_URL,
                api,
                query_params
            )
        if api == constants.WOLFRAM_SIMPLE:
            query_params = urllib.parse.urlencode({
                'appid' : config.wolfram_app_id,
                'i': query,
                'background' : '36393F',
                'foreground' : 'white',
                'units' : 'imperial',
                'layout' : 'labelbar',
            })
            return '{}{}?{}'.format(
                constants.WOLFRAM_API_URL,
                api,
                query_params
            )
        raise ValueError('Invalid Wolfram API: ' + api)
