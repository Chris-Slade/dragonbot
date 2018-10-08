import asyncio
import discord

from asyncio import Future
from mockito import mock

# https://stackoverflow.com/a/46324983/2884483
def async_test(coro):
    def wrapper(*args, **kwargs):
        loop = asyncio.new_event_loop()
        return loop.run_until_complete(coro(*args, **kwargs))
    return wrapper

def create_command_mocks():
    client  = mock(discord.Client)
    message = mock(discord.Message)
    message.channel = mock(discord.TextChannel)
    message.guild = message.channel.guild = mock(discord.Guild)
    message.author = mock(discord.User)

    return (client, message)

def f(value):
    f = Future()
    f.set_result(value)
    return f
