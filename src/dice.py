from random import randrange
from util import command_method
import constants
import logging
import re
import util

class Dice():

    def __init__(self):
        self.logger = logging.getLogger('dragonbot.' + __name__)

    def register_commands(self, cd):
        """Register this modules's commands with a CommandDispatcher.

        Arguments:
            cd -- The CommandDispatcher to register with.
        """
        cd.register('roll', self.roll)
        cd.register('r', self.roll)
        self.logger.info('Registered commands')

    @staticmethod
    def help():
        return util.create_help_embed(
            title='Dice',
            description='This module allows you to roll dice',
            help_msgs=[ [
                '{prefix}roll or {prefix}r <dice expression>',
                'Roll dice specified by <dice expression>. A dice expression'
                ' consists of a number of dice rolls or constant modifiers'
                ' separated by plus signs. A dice roll consists of the number'
                ' of times a die is rolled and the number of sides on the die,'
                ' separated by the letter "d". A constant modifier is simply'
                ' any integer value. For example, the expression'
                ' "1d6 + 2d4 + 3" will roll 1 6-sided die, 2 4-sided dice, and'
                ' add 3 to the result.'
            ] ]
        )

    @command_method
    async def roll(self, _client, message):
        _command, expr = util.split_command(message)
        try:
            results = parse_cmd(expr)
            (formatted_expr, total) = format_results(results)
            if (
                formatted_expr == str(total)
                or len(formatted_expr) > constants.MAX_CHARACTERS
            ):
                await message.channel.send(f'**{total}**')
            else:
                await message.channel.send(f'{formatted_expr} = **{total}**')
        except ValueError as e:
            await message.channel.send(str(e))
        except:
            await message.channel.send('Unknown error.')

PATTERN = re.compile(r'^(?P<die>[0-9]+d[0-9]+)|(?P<constant>[0-9]+)$')
SPLIT_PATTERN = re.compile(r'\s*\+\s*')

def format_results(rolls):
    results = []
    for roll in rolls:
        if len(roll) == 0:
            continue
        elif len(roll) == 1:
            results.append(str(roll[0]))
        else:
            results.append(f"[{' + '.join(str(r) for r in roll)}]")
    expression = ' + '.join(results)
    total = sum(roll for l in rolls for roll in l)
    return (expression, total)

def parse_cmd(cmd):
    rolls = SPLIT_PATTERN.split(cmd)
    return [parse_roll(roll) for roll in rolls]

def parse_roll(roll):
    match = PATTERN.match(roll)
    if match is None:
        raise ValueError('Invalid expression')
    if match.group('die'):
        die = match.group('die')
        num, sides = die.split('d')
        num = int(num)
        sides = int(sides)
        if num > constants.MAX_DICE_ROLLS:
            raise ValueError(f'Too many rolls: {die}')
        if sides > constants.MAX_DIE_SIDES:
            raise ValueError(f'Too many sides: {die}')
        results = []
        for i in range(0, num):
            if sides == 0:
                results.append(0)
            else:
                results.append(randrange(1, sides + 1))
        return results
    else:
        return [int(match.group('constant'))]
