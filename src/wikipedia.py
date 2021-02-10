from util import command_method
import constants
import discord
import logging
import urllib.parse
import util

WIKI_LONG = 'wikipedia'
WIKI_SHORT = 'wiki'
WIKT_LONG = 'wiktionary'
WIKT_SHORT = 'wikt'

class Wikipedia():

    def __init__(self):
        self.logger = logging.getLogger('dragonbot.' + __name__)

    def register_commands(self, cd):
        """Register this modules's commands with a CommandDispatcher.

        Arguments:
            cd -- The CommandDispatcher to register with.
        """
        cd.register(WIKI_LONG, self.wiki)
        cd.register(WIKI_SHORT, self.wiki)
        cd.register(WIKT_LONG, self.wiki)
        cd.register(WIKT_SHORT, self.wiki)
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
        command, arg = util.split_command(message)
        try:
            async with message.channel.typing():
                if command in (WIKI_LONG, WIKI_SHORT):
                    url = self.make_wikipedia_request(arg)
                elif command in (WIKT_LONG, WIKT_SHORT):
                    url = self.make_wiktionary_request(arg)
                else:
                    await message.channel.send('An error occurred: unknown command')
                    return

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
                            extract = page['extract']
                            if command in (WIKI_LONG, WIKI_SHORT):
                                extract = extract.replace('\n', '\n\n')
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

    def make_wikipedia_request(self, query):
        return util.format_url(
            constants.WIKIPEDIA_API_URL,
            {
                'format': 'json',
                'action': 'query',
                'prop': 'extracts|info',
                'inprop': 'url',
                'exintro': '',
                'explaintext': '',
                'redirects': 1,
                'titles': query,
            }
        )

    def make_wiktionary_request(self, query):
        return util.format_url(
            constants.WIKTIONARY_API_URL,
            {
                'format': 'json',
                'action': 'query',
                'prop': 'extracts|info',
                'explaintext': '',
                'exsectionformat': 'plain',
                'inprop': 'url',
                'redirects': 1,
                'titles': query,
            }
        )
