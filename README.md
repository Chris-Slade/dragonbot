# Overview
A chatbot written in Python 3.x for [Discord](discordapp.com).

The `3.1` in the repository name is not the actual bot version, but is a
reference to my previous "DragonBots," the first of which was a HexChat plugin
for use in IRC and the second of which was a bot for Hitbox.tv that ended up
going nowhere. The `.1` is because this is the second remote repository for
this iteration of DragonBot; the first repository no longer exists.

# Dependencies
This bot uses the
[discord.py](http://discordpy.readthedocs.io/en/latest/index.html) framework,
specifically version 0.16.0, though I plan to update the bot to work with later
versions as long as I continue to use it. This naturally means that this bot's
dependencies include all of discord.py's dependencies.

This bot also uses [pyahocorasick](https://pypi.python.org/pypi/pyahocorasick)
to do efficient matching of keywords in messages. As I continue to work on
improving the code quality and making the bot more modular, this dependency may
become optional.

All other dependencies are part of Python's core library.
