import re
from random import randint


def dice_roll(rolls, dice_type):
    """
        dice roll function, with support for multiple rolls
        :param rolls: number of rolls to do
        :param dice_type: maximum value possible for the desired dice (es 6 for a d6)
        :return: dictionary containing every roll and a total sum
    """
    rolls_log = []
    for i in range(rolls):
        rolls_log.append(randint(1, dice_type))
    total = sum(rolls_log)

    return {'rolls_log': rolls_log, 'rolls_total': total}


def dice_roll_check(rolls, dice_type, user_roll):
    """
        dice_roll_check function support the dice_roll one be checking the command given be
        the player and preparing the message to return him in both cases of error and success
        :param rolls: number of rolls to do
        :param dice_type: maximum value possible for the desired dice (es 6 for a d6)
        :param user_roll: command given be the player
        :return: message to print to the user and the total sum of the rolls
    """
    if user_roll not in [f"roll {rolls}d{dice_type}", f"/roll {rolls}d{dice_type}"]:
        message = "Error! Please use the correct command to roll the dice."
        return {'message': message, 'rolls_total': 0}

    roll = dice_roll(rolls, dice_type)

    # Format the result for the user
    rolls_log = roll['rolls_log']
    rolls_total = roll['rolls_total']

    # Create the response message
    rolls_message = ', '.join(map(str, rolls_log))
    message = f"Your rolls have been: {rolls_message}\nWhich brings the total to: {rolls_total}"

    return {'message': message, 'rolls_total': rolls_total}


def calculate_roll_expression(expression):
    dice_and_numbers_pattern = re.compile(r"(\d+D\d+|\d+)")
    operator_pattern = re.compile(r"[\+\-]")

    components = dice_and_numbers_pattern.findall(expression)
    operators = operator_pattern.findall(expression)

    total = 0
    if components:
        first_component = components[0]
        if 'D' in first_component:
            rolls, sides = map(int, first_component.split('D'))
            total = dice_roll(rolls, sides)['rolls_total']
        else:
            total = int(first_component)

    for i in range(1, len(components)):
        current_component = components[i]
        if 'D' in current_component:
            rolls, sides = map(int, current_component.split('D'))
            current_result = dice_roll(rolls, sides)['rolls_total']
        else:
            current_result = int(current_component)

        if operators[i - 1] == "+":
            total += current_result
        elif operators[i - 1] == "-":
            total -= current_result

    return total


def calculate_skill_level(character, skill_level):
    stats = character["stats"]

    if skill_level is None:
        return None

    if isinstance(skill_level, int):
        return skill_level

    def get_stat_value(stat_name):
        return stats[stat_name.strip().lower()]["value"]

    def multiply(stat_name, multiplier):
        return get_stat_value(stat_name) * int(multiplier)

    def add(stat_names):
        return sum(get_stat_value(stat_name) for stat_name in stat_names)

    def subtract(stat_names):
        return get_stat_value(stat_names[0]) - get_stat_value(stat_names[1])

    def divide(stat_name, divisor):
        return get_stat_value(stat_name) // int(divisor)

    operations = {
        'x': lambda x: multiply(*x.split('x')),
        '+': lambda x: add(x.split('+')),
        '-': lambda x: subtract(x.split('-')),
        '/': lambda x: divide(*x.split('/'))
    }

    for op, func in operations.items():
        if op in skill_level:
            return func(skill_level)

    # Assuming the level is in the format of a single stat name if it doesn't match the above patterns
    return get_stat_value(skill_level)


def calculate_hit_probability(distance, range_value, base_probability):
    """
        Calculate the probability of the attack based on the distance of the target and weapon's range value

        Parameters:
        - distance (int): Target's distance.
        - range_value (int): Weapon's range value.
        - base_probability (int): Success probability of the weapon's skill.

        Returns:
        - int: Updated success probability.
    """
    if distance <= range_value:
        return base_probability         # La distanza è entro la gittata, nessuna modifica alla probabilità
    elif distance <= 2 * range_value:
        return base_probability // 2         # La distanza è superiore alla gittata ma entro il doppio della gittata
    elif distance <= 3 * range_value:
        return base_probability // 4         # La distanza è superiore al doppio della gittata ma entro il triplo
    else:
        return 0    # La distanza è oltre il triplo della gittata, probabilità nulla
