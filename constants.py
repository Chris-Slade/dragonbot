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

DEFAULT_CONFIG = 'config.json'
DEFAULT_ENV_CONFIG = 'DRAGONBOT_CONFIG'
DEFAULT_LOG_LEVEL = 'WARNING'
DEFAULT_BOT_LOG_LEVEL = 'INFO'

# TODO Make this configurable
INSULTS_ENV_VAR = 'DRAGONBOT_INSULTS'

LOG_FORMAT = ' | '.join([
    '%(asctime)s',
    '%(levelname)s',
    '%(module)s:%(funcName)s:%(lineno)d',
    '%(message)s'
])

DATE_FORMAT = '%Y-%m-%d %H:%M:%S'
