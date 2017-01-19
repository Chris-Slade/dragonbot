from collections import namedtuple

class CommandDispatcher(object):
    """Dispatches bot commands, which can be registered by other
    modules. Handles permissions.
    """

    Command = namedtuple('Command', ['name', 'func', 'may_use'])

    def __init__(self, client, read_only=False):
        """Construct a new CommandDispatcher bound to the given client.

        Arguments:
            client -- A discord.Client.
            read_only -- Whether r/w commands can be executed. Defaults to
                False.
        """
        self.commands = {}
        self.client = client

    def register_command(self, command_name, command_func, may_use):
        """Register a command to make it known to the dispatcher.

        Arguments:
            command_name -- The name of the command, which is the
                that is dispatched on.
            command_func -- The function to call. It should take a
                discord.Client client and a discord.Message as
                positional parameters.
            may_use -- An object containing the IDs of users who are
                permitted to use this function. The collection must
                implement the __contains__ method.
        """
        if command_name in commands:
            raise RuntimeError('Command already registered')
        self.commands[command_name] = Command(
            name=command_name,
            func=command_func,
            may_use=may_use
        )

    def dispatch(self, command_name, message):
        if command_name in commands:

