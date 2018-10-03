from collections import namedtuple

class CommandDispatcher(object):
    """Dispatches bot commands, which can be registered by other
    modules. Handles permissions.
    """

    class PermissionDenied(Exception):
        pass

    class WriteDenied(Exception):
        pass

    class UnknownCommand(Exception):
        pass

    class DuplicateCommand(Exception):
        pass

    Command = namedtuple('Command', ['name', 'func', 'rw', 'may_use'])

    def __init__(self, read_only=False):
        """Construct a new CommandDispatcher bound to the given client.

        Arguments:
            read_only -- Whether r/w commands can be executed. Defaults to
                False.
        """
        self.commands = {}
        self.read_only = read_only

    def register(
        self,
        command_name,
        command_func,
        rw=False,
        may_use=None
    ):
        """Register a command to make it known to the dispatcher.

        Arguments:
            command_name -- The name of the command, which is the
                that is dispatched on.
            command_func -- The coroutine to call. It should take a
                discord.Client client and a discord.Message as
                positional parameters.
            rw -- Whether the command is read-write or read-only.
                Defaults to False.
            may_use -- An object containing the IDs of users who are
                permitted to use this command. The collection must
                implement the __contains__ method. If anyone may use the
                command, pass None.
        """
        if command_name in self.commands:
            raise CommandDispatcher.DuplicateCommand(
                'Command already registered'
            )
        self.commands[command_name] = CommandDispatcher.Command(
            name=command_name,
            func=command_func,
            rw=rw,
            may_use=may_use
        )

    def is_registered(self, command_name):
        return command_name in self.commands

    async def dispatch(self, client, command_name, message):
        """Dispatch the given command.

        Arguments:
            client -- The discord.Client that received the message which
                triggered the command.
            message -- The discord.Message that triggered the command.

        Returns: The return value of the command function, if any.

        Raises:
            PermissionDenied -- If the caller does not have permission
                to use the command.
            WriteDenied -- If the command is read/write and the
                read-only option was set in the constructor.
            UnknownCommand -- If the command name was not registered.

            As well as any other exception that a command function might
        raise.
        """
        # Command has to be registered
        if command_name not in self.commands:
            raise CommandDispatcher.UnknownCommand(
                'Unknown command: "{}"'.format(command_name)
            )
        command = self.commands[command_name]
        # Caller has to have permission to use the command
        if command.may_use is not None:
            if message.author.id not in command.may_use:
                raise CommandDispatcher.PermissionDenied(
                    '[{}] User "{}#{}" does not have permission'
                    ' to use command "{}"'.format(
                        message.guild,
                        message.author.name,
                        message.author.id,
                        command_name
                    )
                )
        # Must not be in read-only mode for read/write commands
        if command.rw and self.read_only:
            raise CommandDispatcher.WriteDenied(
                'Cannot call read/write command in read-only mode'
            )
        # Call the command
        assert command.func is not None
        return await command.func(client, message)

    def known_command_names(self):
        return self.commands.keys()
