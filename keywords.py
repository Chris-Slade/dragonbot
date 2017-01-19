class Keywords(object):
    """A keywords module for DragonBot."""

    def __init__(self, keywords_file):
        self.logger = logging.getLogger('dragonbot.' + __name__)
        self.keywords =

    async def do_keyword_reactions(message=None, update_automaton=False):
        try:
            getattr(do_keyword_reactions, '_automaton')
        except AttributeError:
            update_automaton = True

        if update_automaton:
            # Make a new Aho-Corasick automaton
            do_keyword_reactions._automaton = ahocorasick.Automaton(str)
            # Add each keyword
            for keyword in keywords:
                do_keyword_reactions._automaton.add_word(keyword, keyword)
            # Finalize the automaton for searching
            do_keyword_reactions._automaton.make_automaton()

        # In case we were called just to update the automaton
        if message is None:
            return

        content = message.clean_content.casefold()
        for index, keyword in do_keyword_reactions._automaton.iter(content):
            reactions = keywords[keyword]
            logging.debug(
                'Got reactions [%s] for keyword "%s"',
                ", ".join(reactions) if reactions is not None else "None",
                keyword
            )
            for reaction in reactions:
                logger.info('Reacting with "%s"', reaction)
                try:
                    await client.add_reaction(message, reaction)
                except discord.HTTPException as e:
                    logger.exception(
                        'Error reacting to keyword "%s" with "%s"',
                        keyword,
                        reaction
                    )
            stats['keywords seen'] += 1

    async def add_keyword(client, message):
        command, argstr = split_command(message)
        try:
            name, emote = argstr.split(maxsplit=1)
        except:
            await client.send_message(
                message.channel,
                'Need a keyword and emote.'
            )

        # Try to extract a custom emoji's name and ID
        match = re.match(r'<:([^:]+:\d+)>', emote)
        if match:
            emote = match.group(1)

        # Assume an emoji is correct and just store it
        if name in keywords:
            keywords[name].append(emote)
        else:
            keywords[name] = [emote]
        keywords.save()
        await do_keyword_reactions(message=None, update_automaton=True)
        await client.send_message(
            message.channel,
            'Added keyword reaction!'
        )
        logger.info(
            '%s added keyword "%s" -> "%s"',
            message.author.name,
            name,
            emote
        )

    async def remove_keyword(client, message):
        command, name = split_command(message)
        try:
            del keywords[name]
            keywords.save()
            await do_keyword_reactions(message=None, update_automaton=True)
            await client.send_message(
                message.channel,
                'Removed keyword reaction!'
            )
            logger.info(
                '%s removed keyword "%s"',
                message.author.name,
                name
            )
        except KeyError:
            await client.send_message(
                message.channel,
                "That keyword doesn't exist!"
            )
