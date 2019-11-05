from util import command_method
import aiohttp
import constants
import discord
import logging
import urllib.parse
import util

class Wikipedia():

    def __init__(self):
        self.logger = logging.getLogger('dragonbot.' + __name__)

    def register_commands(self, cd):
        """Register this modules's commands with a CommandDispatcher.

        Arguments:
            cd -- The CommandDispatcher to register with.
        """
        cd.register('wiki', self.wiki)
        cd.register('wikipedia', self.wiki)
        self.logger.info('Registered commands')

    @staticmethod
    def help():
        return util.create_help_embed(
            title='Wikipedia',
            description='This module allows you to look up article extracts'
                ' on Wikipedia',
            help_msgs=[ [
                '{prefix}wikipedia or {prefix}wiki <article title>',
                'Look up an article on Wikipedia'
            ] ]
        )

    @command_method
    async def wiki(self, _client, message):
        _command, arg = util.split_command(message)
        try:
            async with message.channel.typing():
                url = await self.make_request(arg, constants.WIKIPEDIA_API_URL)
                client = await util.get_http_client()
                rsp = await client.get(url)
                if 400 <= rsp.status <= 599:
                    util.log_http_error(self.logger, rsp)
                    await message.channel.send('An error occurred.')
                else:
                    json = await rsp.json()
                    if (
                        'query' not in json
                        or 'pages' not in json['query']
                        or len(json['query']['pages']) == 0
                        or '-1' in json['query']['pages']
                    ):
                        await message.channel.send(
                            'No pages with that title found.'
                        )
                    else:
                        for page in json['query']['pages'].values():
                            title = page['title']
                            extract = page['extract'].replace('\n', '\n\n')
                            url = page['fullurl']
                            await message.channel.send(
                                embed=discord.Embed(
                                    title=title,
                                    url=url,
                                    description=util.truncate(
                                        extract,
                                        constants.MAX_EMBED_DESC_SIZE
                                    ),
                                    color=constants.EMBED_COLOR,
                                )
                            )

        except Exception:
            self.logger.exception('Unknown error')
            await message.channel.send('Unknown error.')

    async def make_request(self, query, api):
        query_params = urllib.parse.urlencode({
            'format': 'json',
            'action': 'query',
            'prop': 'extracts|info',
            'inprop': 'url',
            'exintro': '',
            'explaintext': '',
            'redirects': 1,
            'titles': query,
        })
        return '{}?{}'.format(constants.WIKIPEDIA_API_URL, query_params)
