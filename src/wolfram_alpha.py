import aiohttp
import discord
import io
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
                '{prefix}wolfram <query>',
                'Make a query using Wolfram Alpha.'
            ], [
                '{prefix}ask <question>',
                'Ask a question, get a simple answer.'
            ] ]
        )

    @command_method
    async def wolfram_alpha(self, _client, message):
        _command, arg = util.split_command(message)
        try:
            async with message.channel.typing():
                url    = await self.make_request(arg, constants.WOLFRAM_SIMPLE)
                client = await util.get_http_client()
                rsp    = await client.get(url)
                if rsp.status == 501:
                    util.log_http_error(self.logger, rsp)
                    await message.channel.send(
                        'Wolfram Alpha could not understand your query.'
                    )
                elif rsp.status == 400:
                    util.log_http_error(self.logger, rsp)
                    await message.channel.send('Invalid input.')
                else:
                    fp = io.BytesIO(await rsp.read())
                    image = discord.File(fp=fp, filename='query.png')
                    await message.channel.send(file=image)
        except Exception:
            self.logger.exception('Unknown error')
            await message.channel.send('Unknown error.')

    @command_method
    async def ask(self, _client, message):
        _command, arg = util.split_command(message)
        if arg is None:
            await message.channel.send('What is your question?')
        try:
            async with message.channel.typing():
                url    = await self.make_request(arg, constants.WOLFRAM_SHORT)
                client = await util.get_http_client()
                rsp    = await client.get(url)
                text   = await rsp.text()
                if text:
                    text = text.replace('Wolfram|Alpha', 'DragonBot')
                    text = text.replace('Wolfram Alpha', 'DragonBot')
                if rsp.status == 501:
                    util.log_http_error(self.logger, rsp)
                    if text:
                        await message.channel.send(text)
                    else:
                        await message.channel.send(
                            "I don't know how to answer that."
                        )
                elif rsp.status == 400:
                    util.log_http_error(self.logger, rsp)
                    await message.channel.send('Invalid input.')
                else:
                    await message.channel.send(text)
        except aiohttp.ClientResponseError:
            self.logger.exception('Error reading response body')
            await message.channel.send('Error getting response')
        except Exception:
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
