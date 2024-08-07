from telegram.ext import Application, CallbackQueryHandler
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, ReplyKeyboardRemove, \
    KeyboardButton
from telegram.ext import CommandHandler, MessageHandler, filters, ConversationHandler, ContextTypes
import json
import re
from utils import dice_roll
from utils import dice_roll_check, calculate_skill_level

# Global info
tmp_user_data = {}  # User data temp info
counter = 0  # Service int variable

# character creation stages
GENRE, DOMINANT_HAND, HEIGHT, DESCRIPTION, AGE, STATS, COS, TAG, INT, POT, DES, FAS, MOV, \
    STATS_MODIFIER, STATS_UPDATE, REDUCE_STAT, CONFIRM_REDUCTION, ADD_STAT, CONFIRM_ADD, PROFESSION, \
    SKILLS, CHOOSE_OPTIONAL_SKILLS, MENAGE_SPECIFIED_SKILL, ASSIGN_SKILL_POINTS, \
    DISTINCTIVE_TRAITS, WEAPONS, ARMOR, EQUIPMENT = range(28)

MAX_CHAR_LENGTH = 255


def validate_input_length(input_text: str, max_length: int = MAX_CHAR_LENGTH) -> bool:
    return len(input_text) <= max_length


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    #await update.message.edit_reply_markup(reply_markup=ReplyKeyboardRemove())
    await update.message.reply_text("Hello! Welcome to the Basic Roleplaying bot.")


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Cancels character creation"""
    user_id = update.effective_user.name
    # deleting tmp info
    global tmp_user_data
    try:
        del (tmp_user_data[f"{user_id}"])
    except KeyError:
        pass
    await update.message.reply_text(
        'Character creation cancelled', reply_markup=ReplyKeyboardRemove()
    )

    return ConversationHandler.END


async def new_pc_start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("You want to create a new character! Please tell me his name")
    return GENRE


async def new_pc_genre(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """saves player name info, initializes tmp data structure, builds keyboard for genre selection"""
    user_id = update.effective_user.name
    pc_name = update.message.text

    # check for user file and if character name is already taken
    try:
        with open(f"Json/users/{user_id}.json", "r") as fp:
            user_data = json.load(fp)
        pc_name_key = "_".join(pc_name.lower().split())
        if pc_name_key in user_data.keys():
            await update.message.reply_text("I'm sorry, you already have a character with this name. Try again...")
            return ConversationHandler.END
    except IOError:
        pass

    # creating new pc and saving them into tmp structure
    with open("Json/character_sheet.json", "r") as fp:
        new_character = json.load(fp)
    new_character['name'] = pc_name

    # building tmp data structure
    global tmp_user_data
    tmp_user_data[f"{user_id}"] = {}
    tmp_user_data[f"{user_id}"]["tmp_character"] = new_character

    # Loading the genre options from json file
    with open("Json/genre_choices.json", "r") as fp:
        genre_data = json.load(fp)

    # Acquiring list of available genre
    genre = genre_data["genre_choices"]

    # Creating keyboard for response
    reply_keyboard = [[g] for g in genre]

    await update.message.reply_text(
        'Neat! What genre would you like your character to be?',
        reply_markup=ReplyKeyboardMarkup(
            reply_keyboard, one_time_keyboard=True, input_field_placeholder='Choose your genre'
        ),
    )
    return DOMINANT_HAND


async def new_pc_dominant_hand(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.name
    user_genre = update.message.text

    # Loading the genre options from json file
    with open("Json/genre_choices.json", "r") as fp:
        genre_data = json.load(fp)

    # Acquiring list of available genre
    genre_choices = genre_data["genre_choices"]

    if user_genre in genre_choices:
        tmp_user_data[f"{user_id}"]["tmp_character"]["genre"] = user_genre
        await update.message.reply_text(f"Genre '{user_genre}' selected.")
    else:
        await update.message.reply_text("Genre not valid, please try again.")
        return GENRE

    # Creating keyboard for response
    reply_keyboard = [['Right', 'Left']]

    await update.message.reply_text(
        'Now tell me what his dominant hand is: ',
        reply_markup=ReplyKeyboardMarkup(
            reply_keyboard, one_time_keyboard=True, input_field_placeholder='Choose your dominant hand'
        ),
    )

    return HEIGHT


async def new_pc_height(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.name
    user_dominant_hand = update.message.text.lower()

    if user_dominant_hand not in ["left", "right"]:
        await update.message.reply_text("Dominant hand not valid, please try again.")
        return HEIGHT

    tmp_user_data[f"{user_id}"]["tmp_character"]["dominant_hand"] = user_dominant_hand

    reply_keyboard = [['Tall', 'Medium', 'Short']]

    await update.message.reply_text(
        'Please select the height for your character:',
        reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True)
    )

    return DESCRIPTION


async def new_pc_description(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.name
    user_height = update.message.text.lower()

    if user_height not in ["tall", "medium", "short"]:
        await update.message.reply_text("The height selected id not valid, please try again.")
        return DESCRIPTION

    tmp_user_data[f"{user_id}"]["tmp_character"]["height"] = user_height

    await update.message.reply_text("Perfect! Now write a brief description for your character: ")

    return AGE


async def new_pc_age(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.name
    user_description = update.message.text

    if not validate_input_length(user_description):
        await update.message.reply_text(
            f"Height description too long! Please enter a height up to {MAX_CHAR_LENGTH} characters.")
        return DESCRIPTION

    tmp_user_data[f"{user_id}"]["tmp_character"]["description"] = user_description

    await update.message.reply_text("Done! What will your age be?")

    return STATS


async def new_pc_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.name
    user_age = update.message.text

    # Caricamento delle opzioni di razza dal file json
    with open("Json/races.json", "r") as fp:
        races_data = json.load(fp)

    # Acquisizione delle informazioni per la razza umana
    human_info = races_data["human"]

    if not user_age.isdigit() or not (0 <= int(user_age) <= human_info["max_age"]):
        max_age = human_info["max_age"]
        if update.message:
            await update.message.reply_text(
                f"A valid age for a human must be between 0 and {max_age}. Please try again.")
        return STATS

    tmp_user_data[f"{user_id}"]["tmp_character"]["age"] = int(user_age)

    # Preparing dice roll for stat 'FOR'
    await update.message.reply_text("Now it is time to get your stats! You will have to roll a "
                                    "six-faces dice 3 times for each stat")
    await update.message.reply_text("To roll the correct dice type '/roll 3d6' or click the special "
                                    "button on your keyboard.")

    # Creating the markup keyboard
    reply_keyboard = [['roll 3d6']]
    await update.message.reply_text(
        'This roll will determine the stat FOR',
        reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True)
    )
    return COS


async def new_pc_stat_cos(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.name
    user_roll = update.message.text

    return_message = dice_roll_check(3, 6, user_roll)
    if "error" in return_message['message'].lower():
        return COS

    # Partially saving the stat FOR
    tmp_user_data[f"{user_id}"]["tmp_character"]["stats"]["for"]["value"] = return_message['rolls_total']

    # Send the response back to the user
    await update.message.reply_text(return_message['message'])

    # Creating the markup keyboard
    reply_keyboard = [['roll 3d6']]
    await update.message.reply_text(
        'Now do the same for the stat COS',
        reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True)
    )

    return TAG


async def new_pc_stat_tag(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.name
    user_roll = update.message.text

    return_message = dice_roll_check(3, 6, user_roll)
    if "error" in return_message['message'].lower():
        return TAG

    # Partially saving the stat COS
    tmp_user_data[f"{user_id}"]["tmp_character"]["stats"]["cos"]["value"] = return_message['rolls_total']

    # Send the response back to the user
    await update.message.reply_text(return_message['message'])

    # Creating the markup keyboard
    reply_keyboard = [['roll 3d6']]
    await update.message.reply_text(
        'What will your TAG stat be?',
        reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True)
    )

    return INT


async def new_pc_stat_int(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.name
    user_roll = update.message.text

    return_message = dice_roll_check(3, 6, user_roll)
    if "error" in return_message['message'].lower():
        return INT

    # Partially saving the stat TAG
    tmp_user_data[f"{user_id}"]["tmp_character"]["stats"]["tag"]["value"] = return_message['rolls_total']

    # Send the response back to the user
    await update.message.reply_text(return_message['message'])

    # Creating the markup keyboard
    reply_keyboard = [['roll 3d6']]
    await update.message.reply_text(
        'Roll to get the INT stat!',
        reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True)
    )

    return POT


async def new_pc_stat_pot(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.name
    user_roll = update.message.text

    return_message = dice_roll_check(3, 6, user_roll)
    if "error" in return_message['message'].lower():
        return POT

    # Partially saving the stat INT
    tmp_user_data[f"{user_id}"]["tmp_character"]["stats"]["int"]["value"] = return_message['rolls_total']

    # Send the response back to the user
    await update.message.reply_text(return_message['message'])

    # Creating the markup keyboard
    reply_keyboard = [['roll 3d6']]
    await update.message.reply_text(
        'What will your POT stat be?',
        reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True)
    )

    return DES


async def new_pc_stat_des(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.name
    user_roll = update.message.text

    return_message = dice_roll_check(3, 6, user_roll)
    if "error" in return_message['message'].lower():
        return DES

    # Partially saving the stat POT
    tmp_user_data[f"{user_id}"]["tmp_character"]["stats"]["pot"]["value"] = return_message['rolls_total']

    # Send the response back to the user
    await update.message.reply_text(return_message['message'])

    # Creating the markup keyboard
    reply_keyboard = [['roll 3d6']]
    await update.message.reply_text(
        'It is time for thew DES stat?',
        reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True)
    )

    return FAS


async def new_pc_stat_fas(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.name
    user_roll = update.message.text

    return_message = dice_roll_check(3, 6, user_roll)
    if "error" in return_message['message'].lower():
        return FAS

    # Partially saving the stat DES
    tmp_user_data[f"{user_id}"]["tmp_character"]["stats"]["des"]["value"] = return_message['rolls_total']

    # Send the response back to the user
    await update.message.reply_text(return_message['message'])

    # Creating the markup keyboard
    reply_keyboard = [['roll 3d6']]
    await update.message.reply_text(
        'You are almost there! Roll for FAS!',
        reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True)
    )

    return MOV


async def new_pc_stat_mov(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.name
    user_roll = update.message.text

    return_message = dice_roll_check(3, 6, user_roll)
    if "error" in return_message['message'].lower():
        return MOV

    # Partially saving the stat FAS
    tmp_user_data[f"{user_id}"]["tmp_character"]["stats"]["fas"]["value"] = return_message['rolls_total']

    # Send the response back to the user
    await update.message.reply_text(return_message['message'])

    # Creating the markup keyboard
    reply_keyboard = [['roll 3d6']]
    await update.message.reply_text(
        'Your last roll will decide the stat MOV!',
        reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True)
    )
    return STATS_MODIFIER


async def new_pc_stats_modifier(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.name
    user_roll = update.message.text

    return_message = dice_roll_check(3, 6, user_roll)
    if "error" in return_message['message'].lower():
        return STATS_MODIFIER

    # Partially saving the stat MOV
    tmp_user_data[f"{user_id}"]["tmp_character"]["stats"]["mov"]["value"] = return_message['rolls_total']

    # Send the response back to the user
    await update.message.reply_text(return_message['message'])

    # Asking player if he wants to modify his stats
    stats_message = "Your character stats are:\n"
    for stat, values in tmp_user_data[f"{user_id}"]["tmp_character"]["stats"].items():
        stats_message += f"{stat.upper()}: {values['value']}\n"

    await update.message.reply_text(stats_message)
    await update.message.reply_text("If you want you can now decide to remove a max of 3 "
                                    "points for each stat to add in the stat you prefer")
    await update.message.reply_text("To do so use the keyboard special buttons 'MODIFY' to "
                                    "update a stat or 'OK' to confirm the current stats")

    # Creating the count variable (in context) to manage extra stat points obtained by reducing the stats
    context.user_data['extra_points'] = 0

    # Creating the markup keyboard
    reply_keyboard = [['MODIFY', 'OK']]
    await update.message.reply_text(
        'Please chose one option displayed on keyboard!',
        reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True)
    )

    return PROFESSION


async def new_pc_stats_update(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.name
    user_roll = update.message.text

    reply_keyboard = []

    if user_roll == "RemovePoints":
        context.user_data['tmp_list_of_stats'] = []  # Initialize the list in the context

        for stat, values in tmp_user_data[f"{user_id}"]["tmp_character"]["stats"].items():
            if values["modifier"] > 0:
                reply_keyboard.append([KeyboardButton(stat.upper())])
                context.user_data['tmp_list_of_stats'].append(stat.upper())  # Add item to the list

        await update.message.reply_text(
            'Decide which stat to reduce!',
            reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True)
        )

        return REDUCE_STAT
    elif user_roll == "AddPoints":
        reply_keyboard = [['FOR'], ['COS'], ['TAG'], ['INT'], ['POT'], ['DES'], ['FAS'], ['MOV']]

        await update.message.reply_text(
            'Decide which stat you want to increase!',
            reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True)
        )

        return ADD_STAT


async def reduce_stat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.name
    user_roll = update.message.text

    if user_roll not in context.user_data['tmp_list_of_stats']:
        await update.message.reply_text(f"You are not allowed to choose the {user_roll} stat!")
        return REDUCE_STAT

    context.user_data['tmp_stat_to_decrease'] = user_roll.lower()  # Saving stat's name to reduce

    max_points_reducible = tmp_user_data[f"{user_id}"]["tmp_character"]["stats"][f"{user_roll.lower()}"]["modifier"]
    await update.message.reply_text(f"Please chose form 0 to a max of {max_points_reducible} points to remove!")

    # Preparing the special keyboard
    reply_keyboard = []
    for point in range(max_points_reducible + 1):
        reply_keyboard.append([KeyboardButton(str(point))])
    await update.message.reply_text(
        'Use the special keyboard to decide!',
        reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True)
    )

    return CONFIRM_REDUCTION


async def confirm_reduction(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.name
    user_roll = int(update.message.text)

    stat_to_decrease = context.user_data['tmp_stat_to_decrease']
    if user_roll not in range(
            tmp_user_data[f"{user_id}"]["tmp_character"]["stats"][f"{stat_to_decrease}"]["modifier"] + 1):
        await update.message.reply_text("Please chose a valid number of points to remove from the stat!")
        return CONFIRM_REDUCTION

    tmp_user_data[f"{user_id}"]["tmp_character"]["stats"][f"{stat_to_decrease}"]["modifier"] -= user_roll
    tmp_user_data[f"{user_id}"]["tmp_character"]["stats"][f"{stat_to_decrease}"]["value"] -= user_roll

    # Removing from context the tmp elements saved and updating the extra_points
    context.user_data.pop('tmp_list_of_stats', None)  # Remove the list from context
    context.user_data.pop('tmp_stat_to_decrease', None)
    context.user_data['extra_points'] += user_roll

    # Showing the player all stats updated
    stats_message = "Perfect! Your stat has been correctly reduced: \n"
    for stat, values in tmp_user_data[f"{user_id}"]["tmp_character"]["stats"].items():
        stats_message += f"{stat.upper()}: {values['value']}\n"

    await update.message.reply_text(stats_message)

    # Creating the markup keyboard
    reply_keyboard = [['MODIFY', 'OK']]
    await update.message.reply_text(
        'Please chose one option displayed on keyboard!',
        reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True)
    )

    return PROFESSION


async def add_stat(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.name
    user_roll = update.message.text

    if user_roll.upper() not in ('FOR', 'COS', 'TAG', 'INT', 'POT', 'DES', 'FAS', 'MOV'):
        await update.message.reply_text(f"Unfortunately the {user_roll} stat does not exist!")
        return REDUCE_STAT

    context.user_data['tmp_stat_to_increase'] = user_roll.lower()  # Saving stat's name to increase

    await update.message.reply_text("Please chose the number of points you want to add to the stat!")

    # Preparing the special keyboard
    reply_keyboard = []
    for point in range(context.user_data.get('extra_points') + 1):
        reply_keyboard.append([KeyboardButton(str(point))])
    await update.message.reply_text(
        'Use the special keyboard to decide!',
        reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True)
    )

    return CONFIRM_ADD


async def confirm_add(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.name
    user_roll = int(update.message.text)

    stat_to_increase = context.user_data['tmp_stat_to_increase']
    if user_roll not in range(context.user_data.get('extra_points') + 1):
        await update.message.reply_text("Please chose a valid number of points to add!")
        return CONFIRM_REDUCTION

    tmp_user_data[f"{user_id}"]["tmp_character"]["stats"][f"{stat_to_increase}"]["modifier"] += user_roll
    tmp_user_data[f"{user_id}"]["tmp_character"]["stats"][f"{stat_to_increase}"]["value"] += user_roll

    # Removing from context the tmp elements saved and updating the extra_points
    context.user_data.pop('tmp_stat_to_increase', None)
    context.user_data['extra_points'] -= user_roll

    # Showing the player all stats updated
    stats_message = "Perfect! Your stat has been correctly increased: \n"
    for stat, values in tmp_user_data[f"{user_id}"]["tmp_character"]["stats"].items():
        stats_message += f"{stat.upper()}: {values['value']}\n"

    await update.message.reply_text(stats_message)

    # Creating the markup keyboard
    reply_keyboard = [['MODIFY', 'OK']]
    await update.message.reply_text(
        'Please chose one option displayed on keyboard!',
        reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True)
    )
    return PROFESSION


async def new_pc_profession(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.name
    user_roll = update.message.text
    print(tmp_user_data)

    extra_points = context.user_data['extra_points']
    if user_roll != "OK":
        if extra_points == 0:
            reply_keyboard = [['RemovePoints']]
        else:
            reply_keyboard = [['RemovePoints'], ['AddPoints']]

        await update.message.reply_text(
            'Decide what to do using the special keyboard!',
            reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True)
        )
        return STATS_UPDATE

    if extra_points != 0:
        await update.message.reply_text(f"You still have {extra_points} extra points to assign!")

        # Preparing the special keyboard
        reply_keyboard = [['RemovePoints'], ['AddPoints']]
        await update.message.reply_text(
            'Decide what to do using the special keyboard!',
            reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True)
        )
        return STATS_UPDATE

    # Cleaning the context
    context.user_data.pop('extra_points', None)

    await update.message.reply_text("Ok! Your stats have now been confirmed")

    # Asking the user to choose a profession
    await update.message.reply_text("Now it is time for you to choose a profession!")

    # Loading professions from json file
    with open("Json/professions.json", "r") as fp:
        professions = json.load(fp)

    # Creating keyboard for response
    reply_keyboard = [[key] for key in professions]
    await update.message.reply_text(
        'Use the special keyboard to decide!',
        reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True)
    )

    return SKILLS


async def new_pc_skills(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.name
    user_roll = update.message.text
    print(tmp_user_data)

    # Loading professions from json file
    with open("Json/professions.json", "r") as fp:
        professions = json.load(fp)

    # Loading skills from json file
    with open("Json/skills.json", "r") as fp:
        skills_list = json.load(fp)

    if user_roll not in professions:
        await update.message.reply_text("Please choose a valid profession!")
        return SKILLS

    # Saving profession
    tmp_user_data[f"{user_id}"]["tmp_character"]["profession"] = user_roll

    profession = professions[user_roll]
    fixed_abilities = profession.get('fixed_abilities', [])
    optional_abilities = profession.get('optional_abilities', [])
    optional_abilities_to_select = profession.get('optional_abilities_to_select', 0)

    # Preparing the context
    context.user_data['skills_to_analyze'] = []
    context.user_data['optional_abilities'] = []
    context.user_data['optional_abilities'] = optional_abilities
    context.user_data['number_to_select'] = optional_abilities_to_select

    for skill in fixed_abilities:
        if '(qualsiasi)' in skill:
            skill_without_parentheses = re.sub(r" \(.*\)$", "", skill)
            context.user_data['skills_to_analyze'].append(skill_without_parentheses)
        elif re.match(r".*\(.*\)$", skill) and '(qualsiasi)' not in skill:
            # Extracting info from skill
            content_in_parentheses = re.search(r"\((.*?)\)$", skill).group(1)
            print(content_in_parentheses)
            skill_without_parentheses = re.sub(r" \(.*\)$", "", skill)

            skill_to_add = {content_in_parentheses: skills_list[skill_without_parentheses]['base_lvl']}
            tmp_user_data[f"{user_id}"]["tmp_character"]["skills"].update(skill_to_add)
        else:
            skill_to_add = {skill: skills_list[skill]['base_lvl']}
            tmp_user_data[f"{user_id}"]["tmp_character"]["skills"].update(skill_to_add)

    # In case of no optional skills to select skips a state
    if optional_abilities_to_select == 0:
        print("okkkkk")
        skills = tmp_user_data[f"{user_id}"]["tmp_character"]["skills"]
        for skill in skills:
            tmp_user_data[f"{user_id}"]["tmp_character"]["skills"][skill] = calculate_skill_level(
                tmp_user_data[f"{user_id}"]["tmp_character"], skill)

        context.user_data['all_skills'] = skills
        skills_message = "Here are your skills levels:\n"
        for skill, level in skills.items():
            skill_info = f"{skill}: {level}"
            skills_message += skill_info + "\n"

        print(context.user_data)

        await update.message.reply_text(skills_message)
        await update.message.reply_text("You currently have 300 points to increase your skills' level. Please type the"
                                        "skill you want to improve followed by the number of points to use on it")

        return ASSIGN_SKILL_POINTS
    # Asking the player to select the optional skills
    skills_message = f"Your profession allows you to select {optional_abilities_to_select} of the following skills:\n\n"
    skills_message += "\n".join(f"- {skill}" for skill in optional_abilities)
    await update.message.reply_text(skills_message)

    print(context.user_data.get('skills_to_analyze', []))

    return CHOOSE_OPTIONAL_SKILLS


async def choose_optional_skills(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Gets input from user and does validity check on the skills given."""
    user_id = update.effective_user.name
    user_message = update.message.text
    print("entering choose_optional_skills")
    print(tmp_user_data)

    # Split the user's message into a list of selected skills
    selected_skills = [skill.strip() for skill in user_message.split(',')]

    print(selected_skills)

    # Getting info from context
    optional_abilities = context.user_data.get('optional_abilities', [])
    number_to_select = context.user_data.get('number_to_select', 0)

    if len(selected_skills) != number_to_select:
        await update.message.reply_text("Please choose a valid number of skills!")
        return CHOOSE_OPTIONAL_SKILLS

    for skill in selected_skills:
        if skill not in optional_abilities:
            await update.message.reply_text("Please choose valid skills!")
            return CHOOSE_OPTIONAL_SKILLS

    # Cleaning the context
    context.user_data.pop('optional_abilities', None)
    context.user_data.pop('number_to_select', None)

    # Loading skills from json file
    with open("Json/skills.json", "r") as fp:
        skills_list = json.load(fp)

    for skill in selected_skills:
        print("1")
        print(skill)
        if '(qualsiasi)' in skill:
            print("entered qualsiasi skill")
            skill_without_parentheses = re.sub(r" \(.*\)$", "", skill)
            context.user_data['skills_to_analyze'].append(skill_without_parentheses)
        elif re.match(r".*\(.*\)$", skill) and '(qualsiasi)' not in skill:
            print("2")
            # Extracting info from skill
            content_in_parentheses = re.search(r"\((.*?)\)$", skill).group(1)
            skill_without_parentheses = re.sub(r" \(.*\)$", "", skill)

            print(content_in_parentheses)

            skill_to_add = {content_in_parentheses: skills_list[skill_without_parentheses]['base_lvl']}
            tmp_user_data[f"{user_id}"]["tmp_character"]["skills"].update(skill_to_add)
        else:
            skill_to_add = {skill: skills_list[skill]['base_lvl']}
            tmp_user_data[f"{user_id}"]["tmp_character"]["skills"].update(skill_to_add)

    print(context.user_data.get('skills_to_analyze', []))

    print(context.user_data)

    """
        Getting the skills to analyze saved in the context in order to
        show the list of them to the user. In case there are no more specified 
        skill to analyze returns the 'new_pc_distinctive_traits' state
    """
    print("entering menage_specified_skill")
    print(tmp_user_data)

    # Checking for empty list in context and getting first element
    skills_to_analyze = context.user_data.get('skills_to_analyze', [])
    if not skills_to_analyze:
        print("entered if")
        return ASSIGN_SKILL_POINTS
    skill_to_analyze = skills_to_analyze[0]

    specialized_skills = skills_list[skill_to_analyze]['specializations']

    # Creating keyboard for response
    reply_keyboard = [[skill] for skill in specialized_skills]
    await update.message.reply_text(
        'Use the special keyboard to select a specific skill to add!',
        reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True)
    )

    return MENAGE_SPECIFIED_SKILL


async def menage_specified_skill(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
        Gets specified skill selected by the user and, after a validity check done by
        pop the first element of the list 'skills_to_analyze' in context,
        adds it to 'tmp_user_data', then returns itself until there are no more elements in the context list 'skills_to_analyze'
    """
    user_id = update.effective_user.name
    user_roll = update.message.text
    print(tmp_user_data)

    # Loading skills from json file
    with open("Json/skills.json", "r") as fp:
        skills_list = json.load(fp)

    # Getting first element of the list in the context
    skill_to_analyze = context.user_data['skills_to_analyze'][0]

    if user_roll not in skills_list[skill_to_analyze]['specializations']:
        await update.message.reply_text("Please choose a valid skill!")
        return MENAGE_SPECIFIED_SKILL

    # If no error occurred then pop of the first element of the list
    skill_to_analyze = context.user_data['skills_to_analyze'].pop(0)

    # Saving the skill in 'tmp_user_data'
    skill_to_add = {skill_to_analyze: skills_list[skill_to_analyze]['base_lvl']}
    tmp_user_data[f"{user_id}"]["tmp_character"]["skills"].update(skill_to_add)

    await update.message.reply_text("Your skills set have been correctly updated!")

    # Checking for empty list in context and getting first element
    skills_to_analyze = context.user_data.get('skills_to_analyze', [])
    if not skills_to_analyze:
        """
            Preparing the list of skills for the user 
            to choose how to spend his 300 skill_points
        """
        print("entered if")
        # Updating the context
        context.user_data.pop('skills_to_analyze', None)
        context.user_data['skill_points'] = 300

        skills = tmp_user_data[f"{user_id}"]["tmp_character"]["skills"]
        for skill in skills:
            tmp_user_data[f"{user_id}"]["tmp_character"]["skills"][skill] = calculate_skill_level(tmp_user_data[f"{user_id}"]["tmp_character"], skill)

        context.user_data['all_skills'] = skills
        skills_message = "Here are your skills levels:\n"
        for skill, level in skills.items():
            skill_info = f"{skill}: {level}"
            skills_message += skill_info + "\n"

        print(context.user_data)

        await update.message.reply_text(skills_message)
        await update.message.reply_text("You currently have 300 points to increase your skills' level. Please type the"
                                        "skill you want to improve followed by the number of points to use on it")

        return ASSIGN_SKILL_POINTS
    skill_to_analyze = skills_to_analyze[0]

    specialized_skills = skills_list[skill_to_analyze]['specializations']

    # Creating keyboard for response
    reply_keyboard = [[skill] for skill in specialized_skills]
    await update.message.reply_text(
        'Use the special keyboard to select a specific skill to add!',
        reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True)
    )

    return MENAGE_SPECIFIED_SKILL


async def assign_skill_points(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """
        Gets the input from the user. After validity check updates the point assignable in the
        context to prepare for the next iteration. Returns to 'assign_skill_points' state.
        In case there are no more points to add, directly returns to next 'operative state'
        (new_pc_distinctive_traits). Extract first skill in 'tmp_user_data' and ask the player the number
        of point he wants to add. Then returns 'confirm_skill_points' state
    """
    print("entering assign_skill_points")
    print(tmp_user_data)

    user_id = update.effective_user.name
    user_message = update.message.text

    skills_with_level = context.user_data.get('all_skills', {})

    # Checking the validity of the format
    if ':' in user_message:
        skill_name, skill_level_str = user_message.rsplit(':', 1)
        skill_name = skill_name.strip()
        skill_level_str = skill_level_str.strip()

        # Making sure the given skill is valid
        if skill_name not in skills_with_level.keys():
            await update.message.reply_text("Please choose a valid skill that has not been modified already!")
            return ASSIGN_SKILL_POINTS

        # Making sure that the second part is an integer
        if skill_level_str.isdigit():
            skill_level = int(skill_level_str)
        else:
            await update.message.reply_text("The level must be an integer. Please enter the skill and level correctly.")
            return ASSIGN_SKILL_POINTS
    else:
        await update.message.reply_text("Please enter the skill and level in the format: <skill>: <level>")
        return ASSIGN_SKILL_POINTS

    old_level = context.user_data['all_skills'][skill_name]

    # Checking validity of input level from user
    new_level = old_level + skill_level
    if new_level > 100:
        await update.message.reply_text("Remember that a skill level can not exceed 100!")
        return ASSIGN_SKILL_POINTS

    # Saving the new level
    tmp_user_data[f"{user_id}"]["tmp_character"]["skills"][skill_name] = new_level

    # Updating the context
    context.user_data['skill_points'] -= skill_level
    extra_skill_points = context.user_data['skill_points']
    context.user_data['all_skills'] = tmp_user_data[f"{user_id}"]["tmp_character"]["skills"]

    if extra_skill_points == 0:
        # Cleaning the context
        context.user_data.pop('skill_points', None)
        context.user_data.pop('all_skills', None)

        await update.message.reply_text("Nice! base on your 'FAS' your character will "
                                        "have more or less distinctive traits")

        # For every 3 points of the 'fas' stat you are entitled a distinctive trait
        fas_stat = tmp_user_data[f"{user_id}"]["tmp_character"]["stats"]["fas"]["value"]
        number_of_distinctive_traits = fas_stat // 3

        # Preparing the context
        context.user_data['number_of_distinctive_traits'] = number_of_distinctive_traits

        await update.message.reply_text(f"Your character must have {number_of_distinctive_traits} distinctive traits \n"
                                        f"Please type theme divided by a comma")
        print(context.user_data)

        return DISTINCTIVE_TRAITS

    # Showing user the updated info
    await update.message.reply_text(f"You still have {extra_skill_points} points to add!")
    skills_message = "Here are the skills you can still improve:\n"
    for skill, level in skills_with_level.items():
        skill_info = f"{skill}: {level}"
        skills_message += skill_info + "\n"
    await update.message.reply_text(skills_message)

    return ASSIGN_SKILL_POINTS


async def new_pc_distinctive_traits(update: Update, context: ContextTypes.DEFAULT_TYPE):
    return WEAPONS


async def new_pc_weapons(update: Update, context: ContextTypes.DEFAULT_TYPE):
    return ARMOR


async def new_pc_armor(update: Update, context: ContextTypes.DEFAULT_TYPE):
    return EQUIPMENT


async def new_pc_equipment(update: Update, context: ContextTypes.DEFAULT_TYPE):
    return ConversationHandler.END


def main():
    application = Application.builder().token('7123849260:AAEai7w3pLmZl1RpsYB-mFiLVaxObtaryQE').build()

    # Handler for '/start' command
    start_handler = CommandHandler('start', start)
    application.add_handler(start_handler)

    pc_creation_handler = ConversationHandler(
        entry_points=[CommandHandler('new_pc', new_pc_start)],
        states={
            GENRE: [MessageHandler(filters.TEXT & ~filters.COMMAND, new_pc_genre)],
            DOMINANT_HAND: [MessageHandler(filters.TEXT & ~filters.COMMAND, new_pc_dominant_hand)],
            HEIGHT: [MessageHandler(filters.TEXT & ~filters.COMMAND, new_pc_height)],
            DESCRIPTION: [MessageHandler(filters.TEXT & ~filters.COMMAND, new_pc_description)],
            AGE: [MessageHandler(filters.TEXT & ~filters.COMMAND, new_pc_age)],
            STATS: [MessageHandler(filters.TEXT & ~filters.COMMAND, new_pc_stats)],
            COS: [MessageHandler(filters.TEXT & ~filters.COMMAND, new_pc_stat_cos)],
            TAG: [MessageHandler(filters.TEXT & ~filters.COMMAND, new_pc_stat_tag)],
            INT: [MessageHandler(filters.TEXT & ~filters.COMMAND, new_pc_stat_int)],
            POT: [MessageHandler(filters.TEXT & ~filters.COMMAND, new_pc_stat_pot)],
            DES: [MessageHandler(filters.TEXT & ~filters.COMMAND, new_pc_stat_des)],
            FAS: [MessageHandler(filters.TEXT & ~filters.COMMAND, new_pc_stat_fas)],
            MOV: [MessageHandler(filters.TEXT & ~filters.COMMAND, new_pc_stat_mov)],
            STATS_MODIFIER: [MessageHandler(filters.TEXT & ~filters.COMMAND, new_pc_stats_modifier)],
            REDUCE_STAT: [MessageHandler(filters.TEXT & ~filters.COMMAND, reduce_stat)],
            CONFIRM_REDUCTION: [MessageHandler(filters.TEXT & ~filters.COMMAND, confirm_reduction)],
            ADD_STAT: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_stat)],
            CONFIRM_ADD: [MessageHandler(filters.TEXT & ~filters.COMMAND, confirm_add)],
            STATS_UPDATE: [MessageHandler(filters.TEXT & ~filters.COMMAND, new_pc_stats_update)],
            PROFESSION: [MessageHandler(filters.TEXT & ~filters.COMMAND, new_pc_profession)],
            SKILLS: [MessageHandler(filters.TEXT & ~filters.COMMAND, new_pc_skills)],
            CHOOSE_OPTIONAL_SKILLS: [MessageHandler(filters.TEXT & ~filters.COMMAND, choose_optional_skills)],
            MENAGE_SPECIFIED_SKILL: [MessageHandler(filters.TEXT & ~filters.COMMAND, menage_specified_skill)],
            ASSIGN_SKILL_POINTS: [MessageHandler(filters.TEXT & ~filters.COMMAND, assign_skill_points)],
            DISTINCTIVE_TRAITS: [MessageHandler(filters.TEXT & ~filters.COMMAND, new_pc_distinctive_traits)],
            WEAPONS: [MessageHandler(filters.TEXT & ~filters.COMMAND, new_pc_weapons)],
            ARMOR: [MessageHandler(filters.TEXT & ~filters.COMMAND, new_pc_armor)],
            EQUIPMENT: [MessageHandler(filters.TEXT & ~filters.COMMAND, new_pc_equipment)]
        },
        fallbacks=[CommandHandler('cancel', cancel)]
    )

    application.add_handler(pc_creation_handler)

    application.run_polling()


if __name__ == '__main__':
    main()
