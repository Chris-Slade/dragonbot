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
# Default insult for when no insults file is provided
DEFAULT_INSULT = 'you dummy'
# Default color for embeds created by the bot
EMBED_COLOR = 0xFF00FF
# Allowed schemes for image URLs.
# See https://discordapp.com/developers/docs/resources/channel#embed-object-embed-image-structure
EMBEDDABLE_IMAGE_SCHEMES = ('http', 'https')
# Image extensions recognized by Discord
EMBEDDABLE_IMAGE_EXTS = (
    '.jpg', '.jpeg', '.gif', '.png', '.webp', '.bmp', '.tiff'
)
WOLFRAM_API_URL = 'http://api.wolframalpha.com'
WOLFRAM_SIMPLE = '/v2/simple'
WOLFRAM_SHORT = '/v1/result'
# Config vars that shouldn't be shown
SENSITIVE_CONFIG_VARS = ('token', 'mongodb_uri', 'wolfram_app_id')

LOG_LEVELS = [ 'DEBUG', 'INFO', 'WARNING', 'ERROR', 'CRITICAL' ]

LOG_FORMAT = ' | '.join([
    '%(asctime)s',
    '%(levelname)s',
    '%(module)s:%(funcName)s:%(lineno)d',
    '%(message)s'
])

DATE_FORMAT = '%Y-%m-%d %H:%M:%S'
