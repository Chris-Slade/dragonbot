import discord
import mockito
import unittest
import unittest.mock

from mockito import mock, when, verify, expect, ANY
from unittest.mock import sentinel
from utils import async_test, create_command_mocks, f

import emotes

from emotes import Emotes
from storage import FileStorage

class TestEmotes(unittest.TestCase):

    def setUp(self):
        when(emotes).random_insult().thenReturn('DUMMY')

    def test_add_server(self):
        e = Emotes()
        server = mock(discord.Guild)
        server.id = sentinel.server_id
        storage = mock(FileStorage)
        e.add_server(server, storage)
        self.assertEqual(e._get_server_emotes(sentinel.server_id), storage)

    # pylint: disable=protected-access
    def test_emotes_setter_getter(self):
        e = Emotes()
        e._set_server_emotes(sentinel.server_id, sentinel.emotes)
        self.assertEqual(e._get_server_emotes(sentinel.server_id), sentinel.emotes)

    @async_test
    async def test_add_emote(self):
        e = Emotes()

        client, msg = create_command_mocks()
        msg.guild.id = sentinel.server_id
        msg.id = sentinel.msg_id
        when(msg.channel).send(ANY).thenReturn(f(True))
        msg.content = '!addemote {test}{value}'

        mock_storage = mock(FileStorage)
        when(mock_storage).__setitem__(ANY, ANY).thenReturn()
        when(mock_storage).save().thenReturn()

        e.add_server(msg.guild, mock_storage)
        await e.add_emote(client, msg)

        verify(mock_storage).save()
        verify(mock_storage).__setitem__('test', 'value')
        verify(msg.channel).send('Added emote!')

    @async_test
    async def test_remove_nothing(self):
        MESSAGE = "I can't delete nothing, DUMMY."
        e = emotes.Emotes()
        client, msg = create_command_mocks()
        msg.content = '!removeemote'

        expect(msg.channel).send(MESSAGE).thenReturn(f(True))
        await e.remove_emote(client, msg)

    @async_test
    async def test_remove_nonexistent_emote(self):
        MESSAGE = "That emote isn't stored, DUMMY."
        e = Emotes()
        client, msg = create_command_mocks()
        msg.content = '!removeemote nonexistent'
        msg.id = sentinel.msg_id
        msg.guild.id = sentinel.server_id

        expect(msg.channel, times=1).send(MESSAGE).thenReturn(f(True))
        await e.remove_emote(client, msg)

    @async_test
    async def test_refresh_emotes(self):
        e = Emotes()
        client, msg = create_command_mocks()
        msg.guild.id = sentinel.server_id
        storage = mock(FileStorage)
        e.add_server(msg.guild, storage)

        expect(storage, times=1).load().thenReturn()
        expect(msg.channel).send('Emotes refreshed!').thenReturn(f(True))
        await e.refresh_emotes(client, msg)

    @async_test
    async def test_display_emote(self):
        e = Emotes()
        client, msg = create_command_mocks()
        msg.guild.id = sentinel.server_id

        storage = mock(FileStorage)
        when(storage).__contains__('nonexistent').thenReturn(False)
        when(storage).__contains__('test').thenReturn(True)
        when(storage).__getitem__('test').thenReturn('value')

        e.add_server(msg.guild, storage)

        when(msg.channel).send(ANY).thenReturn(f(True))

        msg.content = msg.clean_content = '@nonexistent'
        await e.display_emote(client, msg)
        verify(msg.channel, times=0).send()

        msg.content = msg.clean_content = '@test'
        await e.display_emote(client, msg)
        verify(msg.channel, times=1).send('value')
