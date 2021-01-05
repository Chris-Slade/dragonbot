import discord
import logging
import urllib.parse

import config
import constants
import util

from util import command_method

class UrbanDictionary():

    def __init__(self):
        self.logger = logging.getLogger('dragonbot.' + __name__)
        self.strip_brackets = str.maketrans({ "[" : None, "]" : None })

    def register_commands(self, cd):
        """Register this modules's commands with a CommandDispatcher.

        Arguments:
            cd -- The CommandDispatcher to register with.
        """
        cd.register('ud', self.urban_dictionary)
        cd.register('urban', self.urban_dictionary)
        cd.register('urbandictionary', self.urban_dictionary)
        self.logger.info('Registered commands')

    @staticmethod
    def help():
        return util.create_help_embed(
            title='Urban Dictionary',
            description='This module allows you to look up definitions'
                ' on Urban Dictionary',
            help_msgs=[ [
                '{prefix}ud or {prefix}urbandictionary <search term>',
                'Look up a search term on Urban Dictioanry'
            ] ]
        )

    @command_method
    async def urban_dictionary(self, _client, message):
        _command, arg = util.split_command(message)
        try:
            async with message.channel.typing():
                client = await util.get_http_client()
                headers = {
                    'x-rapidapi-key': config.rapidapi_key,
                    'x-rapidapi-host': config.rapidapi_host,
                }
                self.logger.info('headers: %s', headers)
                rsp = await client.get(
                    constants.UD_API_URL,
                    params={ 'term': arg },
                    headers=headers
                )
                if 400 <= rsp.status <= 599:
                    util.log_http_error(self.logger, rsp)
                    await message.channel.send('An error occurred.')
                else:
                    json = await rsp.json()
                    if 'list' not in json :
                        await message.channel.send(
                            'No pages with that title found.'
                        )
                    elif len(json['list']) == 0:
                        await message.channel.send(
                            'No results.'
                        )
                    else:
                        result = max(
                            json['list'],
                            key=lambda item: \
                                item['thumbs_up'] - item['thumbs_down']
                        )
                        description = result['definition'] \
                            .translate(self.strip_brackets)
                        await message.channel.send(
                            embed=discord.Embed(
                                title=result['word'],
                                url=result['permalink'],
                                description=description,
                            )
                        )

        except Exception:
            self.logger.exception('Unknown error')
            await message.channel.send('Unknown error.')
