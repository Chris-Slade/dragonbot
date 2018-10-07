# Maximum number of reactions that can be added to a message.
MAX_REACTIONS = 20
# Maximum number of characters a text message may contain.
MAX_CHARACTERS = 2000
# For when the bot doesn't know how to respond to something.
IDK_REACTION = None # '❔'
# Prefix for command messages
COMMAND_PREFIX = '!'
# Prefix for emote messages
EMOTE_PREFIX = '@'

# TODO Make this configurable
INSULTS_ENV_VAR = 'DRAGONBOT_INSULTS'

LOG_LEVELS = [ 'DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL' ]

LOG_FORMAT = ' | '.join([
    '%(asctime)s',
    '%(levelname)s',
    '%(module)s:%(funcName)s:%(lineno)d',
    '%(message)s'
])

DATE_FORMAT = '%Y-%m-%d %H:%M:%S'
