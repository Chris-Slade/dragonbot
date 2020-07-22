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
# Magic 8-Ball answers
EIGHT_BALL_ANSWERS = [
    'It is certain.',
    'It is decidedly so.',
    'Without a doubt.',
    'Yes – definitely.',
    'You may rely on it.',
    'As I see it, yes.',
    'Most likely.',
    'Outlook good.',
    'Yes.',
    'Signs point to yes.',
    'Reply hazy, try again.',
    'Ask again later.',
    'Better not tell you now.',
    'Cannot predict now.',
    'Concentrate and ask again.',
    "Don't count on it.",
    'My reply is no.',
    'My sources say no.',
    'Outlook not so good.',
    'Very doubtful.',
]
# Maximum size for an embed description
MAX_EMBED_DESC_SIZE = 2048
# Maximum number of dice rolls
MAX_DICE_ROLLS = 100
# Maximum number of sides a die can have
MAX_DIE_SIDES = 1000000
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
WIKIPEDIA_API_URL = 'https://en.wikipedia.org/w/api.php'
INSULT_API_URL = 'https://insult.mattbas.org/api/insult'
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
