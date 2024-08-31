import os
from asyncore import dispatcher
from lib2to3.fixes.fix_input import context

from telegram.ext import Application, CallbackQueryHandler, CallbackContext
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, ReplyKeyboardMarkup, ReplyKeyboardRemove, \
    KeyboardButton
from telegram.ext import CommandHandler, MessageHandler, filters, ConversationHandler, ContextTypes
import json
import re
import math
from utils import dice_roll, calculate_hit_probability, calculate_roll_expression
from utils import dice_roll_check, calculate_skill_level

# Global info
tmp_user_data = {}  # User data temp info

# character creation stages
GENRE, DOMINANT_HAND, HEIGHT, DESCRIPTION, AGE, STATS, COS, TAG, INT, POT, DES, FAS, MOV, \
    STATS_MODIFIER, STATS_UPDATE, REDUCE_STAT, CONFIRM_REDUCTION, ADD_STAT, CONFIRM_ADD, PROFESSION, \
    SKILLS, CHOOSE_OPTIONAL_SKILLS, MENAGE_SPECIFIED_SKILL, ASSIGN_SKILL_POINTS, \
    DISTINCTIVE_TRAITS = range(25)

MAX_CHAR_LENGTH = 255


def validate_input_length(input_text: str, max_length: int = MAX_CHAR_LENGTH) -> bool:
    return len(input_text) <= max_length


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
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
    await update.message.reply_text("You want to create a new character! "
                                    "Remember that in each step you can undo the character by typing '/cancel'")
    await update.message.reply_text("Please tell me his name")
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
            skill_without_parentheses = re.sub(r" \(.*\)$", "", skill)

            skill_to_add = {content_in_parentheses: skills_list[skill_without_parentheses]['base_lvl']}
            tmp_user_data[f"{user_id}"]["tmp_character"]["skills"].update(skill_to_add)
        else:
            skill_to_add = {skill: skills_list[skill]['base_lvl']}
            tmp_user_data[f"{user_id}"]["tmp_character"]["skills"].update(skill_to_add)

    # In case of no optional skills to select skips a state
    if optional_abilities_to_select == 0:
        await preparing_assign_skill_points_state(user_id, update, context)

        return ASSIGN_SKILL_POINTS
    # Asking the player to select the optional skills
    skills_message = f"Your profession allows you to select {optional_abilities_to_select} of the following skills:\n\n"
    skills_message += "\n".join(f"- {skill}" for skill in optional_abilities)
    await update.message.reply_text(skills_message)

    return CHOOSE_OPTIONAL_SKILLS


async def choose_optional_skills(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Gets input from user and does validity check on the skills given."""
    user_id = update.effective_user.name
    user_message = update.message.text

    # Split the user's message into a list of selected skills
    selected_skills = [skill.strip() for skill in user_message.split(',')]

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
        if '(qualsiasi)' in skill:
            skill_without_parentheses = re.sub(r" \(.*\)$", "", skill)
            context.user_data['skills_to_analyze'].append(skill_without_parentheses)
        elif re.match(r".*\(.*\)$", skill) and '(qualsiasi)' not in skill:
            # Extracting info from skill
            content_in_parentheses = re.search(r"\((.*?)\)$", skill).group(1)
            skill_without_parentheses = re.sub(r" \(.*\)$", "", skill)

            skill_to_add = {content_in_parentheses: skills_list[skill_without_parentheses]['base_lvl']}
            tmp_user_data[f"{user_id}"]["tmp_character"]["skills"].update(skill_to_add)
        else:
            skill_to_add = {skill: skills_list[skill]['base_lvl']}
            tmp_user_data[f"{user_id}"]["tmp_character"]["skills"].update(skill_to_add)

    """
        Getting the skills to analyze saved in the context in order to
        show the list of them to the user. In case there are no more specified 
        skill to analyze returns the 'new_pc_distinctive_traits' state
    """
    # Checking for empty list in context and getting first element
    skills_to_analyze = context.user_data.get('skills_to_analyze', [])
    if not skills_to_analyze:
        await preparing_assign_skill_points_state(user_id, update, context)

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
    user_message = update.message.text
    print(tmp_user_data)

    # Loading skills from json file
    with open("Json/skills.json", "r") as fp:
        skills_list = json.load(fp)

    # Getting first element of the list in the context
    skill_to_analyze = context.user_data['skills_to_analyze'][0]

    if user_message not in skills_list[skill_to_analyze]['specializations']:
        await update.message.reply_text("Please choose a valid skill!")
        return MENAGE_SPECIFIED_SKILL

    # If no error occurred then pop of the first element of the list
    skill_to_analyze = context.user_data['skills_to_analyze'].pop(0)

    # Saving the skill in 'tmp_user_data'
    skill_to_add = {user_message: skills_list[skill_to_analyze]['base_lvl']}
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
        await preparing_assign_skill_points_state(user_id, update, context)

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
    """
        Gets input from user. After validity check done on the length of distinctive_traits'
        list written by the player saves the new parameters in 'tmp_user_data'.
    """
    user_id = update.effective_user.name
    user_message = update.message.text

    # Extracting info from context
    number_of_distinctive_traits = context.user_data['number_of_distinctive_traits']

    distinctive_traits = [skill.strip() for skill in user_message.split(',')]

    if len(distinctive_traits) != number_of_distinctive_traits:
        await update.message.reply_text("Please enter the correct number of distinctive traits")
        return DISTINCTIVE_TRAITS

    tmp_user_data[f"{user_id}"]["tmp_character"]["distinctive_traits"] = distinctive_traits

    # Cleaning the context
    context.user_data.pop('number_of_distinctive_traits', None)

    print(context.user_data)

    # Completing and saving the new created character
    new_pc_compute(user_id)

    # Character created successfully
    await update.message.reply_text("Character created successfully")

    return ConversationHandler.END


def new_pc_compute(user_id: str):
    """
        Computes the remaining character info.
        After that saves the 'tmp_character' in a json file
    """
    # Computing remaining character info
    tag = tmp_user_data[f"{user_id}"]["tmp_character"]['stats']['tag']['value']

    """
        Function that helps compute the parameter 
        'weight' for the newly created character
    """
    def get_weight_category(weight_level):
        weight_categories = {
            1: "underweight",
            2: "skinny",
            3: "fit",
            4: "fat"
        }
        # Return weight category based on weight_level, or "overweight" in case weight_level > 4
        return weight_categories.get(weight_level, "overweight")

    tmp_user_data[f"{user_id}"]["tmp_character"]["weight"] = get_weight_category(tag // 6)

    # Calculating hit points
    hit_points = math.ceil(calculate_skill_level(tmp_user_data[f"{user_id}"]["tmp_character"], "COS+TAG") / 2)
    tmp_user_data[f"{user_id}"]["tmp_character"]["hit_points"]["current"] = hit_points
    tmp_user_data[f"{user_id}"]["tmp_character"]["hit_points"]["max"] = hit_points

    # Calculating power points
    power_points = tmp_user_data[f"{user_id}"]["tmp_character"]["stats"]["pot"]["value"]
    tmp_user_data[f"{user_id}"]["tmp_character"]["power_points"]["current"] = power_points
    tmp_user_data[f"{user_id}"]["tmp_character"]["power_points"]["max"] = power_points

    # Assigning weapons
    with open("Json/skills.json", "r") as fp:
        all_skills = json.load(fp)

    firearms = all_skills['Arma da Fuoco']["specializations"]
    melee = all_skills['Arma da Mischia']["specializations"]
    ranged = all_skills['Arma a Distanza']["specializations"]
    heavy = all_skills['Arma Pesante']["specializations"]

    for skill in tmp_user_data[f"{user_id}"]["tmp_character"]["skills"]:
        if skill in firearms:
            tmp_user_data[f"{user_id}"]["tmp_character"]["weapons"]["firearm"].append(skill)
        elif skill in melee:
            tmp_user_data[f"{user_id}"]["tmp_character"]["weapons"]["melee"].append(skill)
        elif skill in ranged:
            tmp_user_data[f"{user_id}"]["tmp_character"]["weapons"]["ranged"].append(skill)
        elif skill in heavy:
            tmp_user_data[f"{user_id}"]["tmp_character"]["weapons"]["heavy"].append(skill)

    # Assigning equipment
    with open("Json/professions.json", "r") as fp:
        professions = json.load(fp)

    profession = tmp_user_data[f"{user_id}"]["tmp_character"]["profession"]
    equipment = professions[f"{profession}"]["clothes"]
    tmp_user_data[f"{user_id}"]["tmp_character"]["equipment"] = equipment

    # Calculating cash
    status_level = tmp_user_data[f"{user_id}"]["tmp_character"]["skills"].get('Status', 0)
    tmp_user_data[f"{user_id}"]["tmp_character"]["cash"] = status_level * 5

    print(tmp_user_data[f"{user_id}"]["tmp_character"])

    # saving character in json file
    os.makedirs("Json/users", exist_ok=True)
    try:
        with open(f"Json/users/{user_id}.json", "r") as fp:
            user_info = json.load(fp)
    except FileNotFoundError:
        user_info = {}

    # name conversion into lower case to standardize keys:
    pc_name_key = ("_".join(tmp_user_data[f'{user_id}']['tmp_character']['name'].split())).lower()
    user_info[f"{pc_name_key}"] = tmp_user_data[f"{user_id}"]["tmp_character"]

    with open(f"Json/users/{user_id}.json", "w") as fp:
        json.dump(user_info, fp, indent=4)

    tmp_user_data.pop(f"{user_id}")


async def view_character(update: Update, context: CallbackContext):
    """Display all character info"""
    user_id = update.effective_user.name

    # Pattern per verificare che l'input contenga solo un nome
    pattern = "^[^,]+$"
    input_text = " ".join(context.args)  # Unisce gli argomenti in una singola stringa
    if not re.fullmatch(pattern, input_text):
        await update.message.reply_text("Correct usage:\n\"/view_character <character name>\"")
        return

    # Formatting character's name for json access
    pc_name = " ".join(input_text.split())
    pc = "_".join(input_text.lower().split())

    try:
        # Carica il file JSON del personaggio
        with open(f"Json/users/{user_id}.json", "r") as file:
            all_character = json.load(file)
            character = all_character[f"{pc}"]
    except KeyError:
        await update.message.reply_text(f"You have no character named {pc_name}")
        return
    except FileNotFoundError:
        print("File del personaggio non trovato.")
        return
    except json.JSONDecodeError:
        print("Errore nella decodifica del file JSON.")
        return

    # Extracting character data
    name = character.get("name", "N/A")
    race = character.get("race", "N/A")
    genre = character.get("genre", "N/A")
    dominant_hand = character.get("dominant_hand", "N/A")
    height = character.get("height", "N/A")
    weight = character.get("weight", "N/A")
    description = character.get("description", "N/A")
    age = character.get("age", "N/A")
    distinctive_traits = ", ".join(character.get("distinctive_traits", []))
    profession = character.get("profession", "N/A")
    level = character.get("level", 1)

    stats = character.get("stats", {})
    hit_points = character.get("hit_points", {"current": 0, "max": 0})
    power_points = character.get("power_points", {"current": 0, "max": 0})

    skills = character.get("skills", {})
    weapons = character.get("weapons", {})
    armor = ", ".join(character.get("armor", []))
    shield = ", ".join(character.get("shield", []))
    equipment = ", ".join(character.get("equipment", []))
    cash = character.get("cash", 0)

    # Costruisci la sezione delle skill
    skills_text = ""
    if skills:
        skills_text = "**Skill:**\n" + "\n".join([f"  {skill}: level {level}" for skill, level in skills.items()])
    else:
        skills_text = "**Skills:** None"

    # Costruisci il testo da stampare
    details = (
        f"**Nome:** {name}\n"
        f"**Razza:** {race}\n"
        f"**Genere:** {genre}\n"
        f"**Mano Dominante:** {dominant_hand}\n"
        f"**Altezza:** {height}\n"
        f"**Peso:** {weight}\n"
        f"**Età:** {age}\n"
        f"**Descrizione:** {description}\n"
        f"**Tratti Distintivi:** {distinctive_traits}\n"
        f"**Professione:** {profession}\n"
        f"**Livello:** {level}\n\n"
        f"**Statistiche:**\n"
        f"  Forza: {stats.get('for', {}).get('value', 0)}\n"
        f"  Costituzione: {stats.get('cos', {}).get('value', 0)}\n"
        f"  Taglio: {stats.get('tag', {}).get('value', 0)}\n"
        f"  Intelligenza: {stats.get('int', {}).get('value', 0)}\n"
        f"  Potere: {stats.get('pot', {}).get('value', 0)}\n"
        f"  Destrezza: {stats.get('des', {}).get('value', 0)}\n"
        f"  Flessibilità: {stats.get('fas', {}).get('value', 0)}\n"
        f"  Movimento: {stats.get('mov', {}).get('value', 0)}\n\n"
        f"**Punti Ferita:** Correnti: {hit_points.get('current', 0)} / Massimi: {hit_points.get('max', 0)}\n"
        f"**Punti Potere:** Correnti: {power_points.get('current', 0)} / Massimi: {power_points.get('max', 0)}\n\n"
        f"{skills_text}\n\n"
        f"**Armi:**\n"
        f"  Fuoco: {', '.join(weapons.get('firearm', []))}\n"
        f"  Corpo a Corpo: {', '.join(weapons.get('melee', []))}\n"
        f"  A Distanza: {', '.join(weapons.get('ranged', []))}\n"
        f"  Pesante: {', '.join(weapons.get('heavy', []))}\n\n"
        f"**Armature:** {armor}\n"
        f"**Scudi:** {shield}\n"
        f"**Equipaggiamento:** {equipment}\n"
        f"**Denaro:** {cash} monete\n\n"
    )

    await update.message.reply_text(details)


async def assign_skill(update: Update, context: CallbackContext):
    """Adds skill at level 1 to a character"""
    user_id = update.effective_user.name

    # Checking input format
    pattern = "^[^,]+,[^,]+$"
    if not re.fullmatch(pattern, "".join(context.args)):
        await update.message.reply_text("Correct usage:\n\"/assign_skill <character name>, <skill to add>\"")
        return

    input_text = (" ".join(context.args)).split(", ")
    pc_name = " ".join(input_text[0].split())
    pc = "_".join(input_text[0].lower().split())
    skill_to_add = input_text[1].strip()

    # Making sure the selected character exists
    try:
        with open(f"Json/users/{user_id}.json", "r") as fp:
            user_data = json.load(fp)
            user_data_player = user_data[f"{pc}"]
    except KeyError:
        await update.message.reply_text(f"You have no character named {pc_name}")
        return

    with open(f"Json/skills.json", "r") as fp:
        skills_fp = json.load(fp)

    all_skills = []
    for skill, details in skills_fp.items():
        specializations = details.get("specializations", [])
        if specializations:
            all_skills.extend(specializations)
        else:
            all_skills.append(skill)

    if skill_to_add in all_skills and skill_to_add not in user_data_player["skills"]:
        skill_to_add = {skill_to_add: 1}
        user_data_player["skills"].update(skill_to_add)

        with open(f"Json/users/{user_id}.json", "w") as fp:
            json.dump(user_data, fp, indent=4)

        await update.message.reply_text(f"New skills set: {user_data[f'{pc}']['skills']}")
    else:
        await update.message.reply_text("Aborted: enter a valid skill from the following")
        skills_to_show = [skill for skill in all_skills if skill not in user_data_player["skills"]]
        await update.message.reply_text(skills_to_show)


async def level_up_skill(update: Update, context: CallbackContext):
    """Automatic dice roll of a 100 faces dice to upgrade the given character's skill"""
    user_id = update.effective_user.name

    # Checking input format
    pattern = "^[^,]+,[^,]+$"
    if not re.fullmatch(pattern, "".join(context.args)):
        await update.message.reply_text("Correct usage:\n\"/level_up_skill <character name>, <skill to upgrade>\"")
        return

    input_text = (" ".join(context.args)).split(", ")
    pc_name = " ".join(input_text[0].split())
    pc = "_".join(input_text[0].lower().split())
    skill_to_upgrade = input_text[1].strip()

    # Making sure the selected character exists
    try:
        with open(f"Json/users/{user_id}.json", "r") as fp:
            user_data = json.load(fp)
            user_data_player = user_data[f"{pc}"]
    except KeyError:
        await update.message.reply_text(f"You have no character named {pc_name}")
        return

    # Managing skill's level update
    if skill_to_upgrade in user_data_player["skills"]:      # The character actually has the skill
        current_level = user_data_player["skills"][skill_to_upgrade]
        return_message = dice_roll_check(1, 100, "/roll 1d100")

        await update.message.reply_text(return_message["message"])

        dice_roll_result = return_message["rolls_total"]
        if dice_roll_result > current_level:
            user_data_player["skills"][skill_to_upgrade] = dice_roll_result
            message = f"Your skill has been correctly upgraded at level {dice_roll_result}"
        else:
            message = f"Level up failed: your skill is already at level {dice_roll_result} or above"

        with open(f"Json/users/{user_id}.json", "w") as fp:
            json.dump(user_data, fp, indent=4)

        await update.message.reply_text(message)
    else:
        await update.message.reply_text("Aborted: enter a valid skill your character possesses")


async def add_weapon(update: Update, context: CallbackContext):
    """Adds weapon to a character after checking for weapon existence"""
    user_id = update.effective_user.name

    # Checking input format
    pattern = "^[^,]+,[^,]+$"
    if not re.fullmatch(pattern, "".join(context.args)):
        await update.message.reply_text("Correct usage:\n\"/add_weapon <character name>, <weapon to add>\"")
        return

    input_text = (" ".join(context.args)).split(", ")
    pc_name = " ".join(input_text[0].split())
    pc = "_".join(input_text[0].lower().split())
    weapon_to_add = input_text[1].strip()

    # Making sure the selected character exists
    try:
        with open(f"Json/users/{user_id}.json", "r") as fp:
            user_data = json.load(fp)
            user_data_player = user_data[f"{pc}"]
    except KeyError:
        await update.message.reply_text(f"You have no character named {pc_name}")
        return

    # Getting all possible weapons from json
    with open(f"Json/weapons/firearm.json", "r") as fp:
        firearm = json.load(fp)
    with open(f"Json/weapons/heavy.json", "r") as fp:
        heavy = json.load(fp)
    with open(f"Json/weapons/melee.json", "r") as fp:
        melee = json.load(fp)
    with open(f"Json/weapons/ranged.json", "r") as fp:
        ranged = json.load(fp)

    # Mapping weapon types to their respective JSON data
    weapons = {
        "firearm": firearm,
        "heavy": heavy,
        "melee": melee,
        "ranged": ranged
    }

    def check_string(weapon, weapons_data):
        for weapon_type, weapon_dict in weapons_data.items():
            if weapon in weapon_dict:
                # Ensure the weapon type exists in user_data_player
                if weapon_type not in user_data_player["weapons"]:
                    user_data_player["weapons"][weapon_type] = []

                # Add the weapon name to the appropriate category in user_data_player
                user_data_player["weapons"][weapon_type].append(weapon)
                message = f"Successfully added {weapon} to your {weapon_type} weapons."
                return message

        message = "Abort: select a valid weapon from the following:"
        return message

    return_message = check_string(weapon_to_add, weapons)
    await update.message.reply_text(return_message)

    if "Successfully" in return_message:
        with open(f"Json/users/{user_id}.json", "w") as fp:
            json.dump(user_data, fp, indent=4)
    else:
        list_of_weapons = ""
        for weapon_type, weapon_dict in weapons.items():
            list_of_weapons += f"{weapon_type.capitalize()}:\n"

            for weapon_name in weapon_dict.keys():
                list_of_weapons += f"• {weapon_name}\n"

            list_of_weapons += "\n"

        await update.message.reply_text(list_of_weapons)


async def add_armor(update: Update, context: CallbackContext):
    """Add a type of armor to a given character after checking for armor existence"""
    user_id = update.effective_user.name

    # Checking input format
    pattern = "^[^,]+,[^,]+$"
    if not re.fullmatch(pattern, "".join(context.args)):
        await update.message.reply_text("Correct usage:\n\"/add_armor <character name>, <armor to add>\"")
        return

    input_text = (" ".join(context.args)).split(", ")
    pc_name = " ".join(input_text[0].split())
    pc = "_".join(input_text[0].lower().split())
    armor_to_add = input_text[1].strip()

    # Making sure the selected character exists
    try:
        with open(f"Json/users/{user_id}.json", "r") as fp:
            user_data = json.load(fp)
            user_data_player = user_data[f"{pc}"]
    except KeyError:
        await update.message.reply_text(f"You have no character named {pc_name}")
        return

    with open(f"Json/armors.json", "r") as fp:
        armors = json.load(fp)

    if armor_to_add in armors and armor_to_add not in user_data_player["armor"]:
        user_data_player["armor"].append(armor_to_add)

        with open(f"Json/users/{user_id}.json", "w") as fp:
            json.dump(user_data, fp, indent=4)

        await update.message.reply_text(f"Your armor set has been updated: {user_data[f'{pc}']['armor']}")
    else:
        await update.message.reply_text("Aborted: enter a valid armor from the following")
        armors_to_show = [armor for armor in armors if armor not in user_data_player["armor"]]
        await update.message.reply_text(armors_to_show)


async def add_shield(update: Update, context: CallbackContext):
    """Add a type of shield to a given character after checking for shield existence"""
    user_id = update.effective_user.name

    # Checking input format
    pattern = "^[^,]+,[^,]+$"
    if not re.fullmatch(pattern, "".join(context.args)):
        await update.message.reply_text("Correct usage:\n\"/add_shield <character name>, <shield to add>\"")
        return

    input_text = (" ".join(context.args)).split(", ")
    pc_name = " ".join(input_text[0].split())
    pc = "_".join(input_text[0].lower().split())
    shield_to_add = input_text[1].strip()

    # Making sure the selected character exists
    try:
        with open(f"Json/users/{user_id}.json", "r") as fp:
            user_data = json.load(fp)
            user_data_player = user_data[f"{pc}"]
    except KeyError:
        await update.message.reply_text(f"You have no character named {pc_name}")
        return

    with open(f"Json/shields.json", "r") as fp:
        shields = json.load(fp)

    if shield_to_add in shields and shield_to_add not in user_data_player["shield"]:
        user_data_player["shield"].append(shield_to_add)

        with open(f"Json/users/{user_id}.json", "w") as fp:
            json.dump(user_data, fp, indent=4)

        await update.message.reply_text(f"Your shield set has been updated: {user_data[f'{pc}']['shield']}")
    else:
        await update.message.reply_text("Aborted: enter a valid armor from the following")
        shields_to_show = [shield for shield in shields if shield not in user_data_player["shield"]]
        await update.message.reply_text(shields_to_show)


async def add_equipment(update: Update, context: CallbackContext):
    """Assign the inserted equipment to the chosen character"""
    user_id = update.effective_user.name

    # Checking input format
    pattern = "^[^,]+,[^,]+$"
    if not re.fullmatch(pattern, "".join(context.args)):
        await update.message.reply_text("Correct usage:\n\"/add_equipment <character name>, <equipment to add>\"")
        return

    input_text = (" ".join(context.args)).split(", ")
    pc_name = " ".join(input_text[0].split())
    pc = "_".join(input_text[0].lower().split())
    equipment_to_add = input_text[1].strip()

    # Making sure the selected character exists
    try:
        with open(f"Json/users/{user_id}.json", "r") as fp:
            user_data = json.load(fp)
            user_data_player = user_data[f"{pc}"]
    except KeyError:
        await update.message.reply_text(f"You have no character named {pc_name}")
        return

    # Adding equipment to character
    user_data_player["equipment"].append(equipment_to_add)
    with open(f"Json/users/{user_id}.json", "w") as fp:
        json.dump(user_data, fp, indent=4)

    await update.message.reply_text("The equipment has been correctly assigned")


async def save_currency(update: Update, context: CallbackContext):
    """Gives currency to a character"""
    user_id = update.effective_user.name

    # Checking input format
    pattern = "^[^,]+,[0-9]+$"
    if not re.fullmatch(pattern, "".join(context.args)):
        await update.message.reply_text("Correct usage:\n\"/save_currency <character name>, <quantity>\"")
        return

    input_text = (" ".join(context.args)).split(", ")
    pc_name = " ".join(input_text[0].split())
    pc = "_".join(input_text[0].lower().split())
    balance_modifier = input_text[1]

    correct_input = r"[0-9]*"

    try:
        with open(f"Json/users/{user_id}.json", "r") as fp:
            user_data = json.load(fp)
            user_data_player = user_data[f"{pc}"]
    except KeyError:
        await update.message.reply_text(f"You have no character named {pc_name}")
        return

    if re.fullmatch(correct_input, balance_modifier):
        user_data[f"{pc}"]["cash"] += int(balance_modifier)

        with open(f"Json/users/{user_id}.json", "w") as fp:
            json.dump(user_data, fp, indent=4)

        await update.message.reply_text(f"New balance: {user_data[f'{pc}']['cash']}")
    else:
        await update.message.reply_text("aborted: enter a valid number")


async def pay_currency(update: Update, context: CallbackContext):
    """takes currency from a character"""
    user_id = update.effective_user.name

    # Checking input format
    pattern = "^[^,]+,[0-9]+$"
    if not re.fullmatch(pattern, "".join(context.args)):
        await update.message.reply_text("Correct usage:\n\"/pay_currency <character name>, <quantity>\"")
        return

    input_text = (" ".join(context.args)).split(", ")
    pc_name = " ".join(input_text[0].split())
    pc = "_".join(input_text[0].lower().split())
    balance_modifier = input_text[1]

    correct_input = r"[0-9]*"

    try:
        with open(f"Json/users/{user_id}.json", "r") as fp:
            user_data = json.load(fp)
            user_data_player = user_data[f"{pc}"]
    except KeyError:
        await update.message.reply_text(f"You have no character named {pc_name}")
        return

    if re.fullmatch(correct_input, balance_modifier):
        if user_data[f"{pc}"]["cash"] >= int(balance_modifier):
            user_data[f"{pc}"]["cash"] -= int(balance_modifier)

            with open(f"Json/users/{user_id}.json", "w") as fp:
                json.dump(user_data, fp, indent=4)
            await update.message.reply_text(f"New balance: {user_data[f'{pc}']['cash']}")
        else:
            await update.message.reply_text("aborted: you can't spend money you don't have!")
    else:
        await update.message.reply_text("aborted: enter a valid number")


async def ability_roll(update: Update, context: CallbackContext):
    """
        Perform ability dice roll to see if ability's use has been a success
        (in this case it is checked the condition for special success) of a failure
    """
    user_id = update.effective_user.name

    # Checking input format
    pattern = "^[^,]+,[^,]+$"
    if not re.fullmatch(pattern, "".join(context.args)):
        await update.message.reply_text("Correct usage:\n\"/ability_roll <character name>, <skill to use>\"")
        return

    input_text = (" ".join(context.args)).split(", ")
    pc_name = " ".join(input_text[0].split())
    pc = "_".join(input_text[0].lower().split())
    skill_to_use = input_text[1].strip()

    # Making sure the selected character exists
    try:
        with open(f"Json/users/{user_id}.json", "r") as fp:
            user_data = json.load(fp)
            user_data_player = user_data[f"{pc}"]
    except KeyError:
        await update.message.reply_text(f"You have no character named {pc_name}")
        return

    if skill_to_use in user_data[f"{pc}"]["skills"]:
        return_message = dice_roll_check(1, 100, "/roll 1d100")

        await update.message.reply_text(return_message["message"])

        dice_roll_result = return_message["rolls_total"]
        skill_level = user_data_player["skills"][skill_to_use]
        if dice_roll_result <= skill_level:
            # Extracting special_success levels from json
            with open(f"Json/special_success.json", "r") as fp:
                special_success = json.load(fp)

            if dice_roll_result in range(special_success[user_data_player["skills"][skill_to_use]]):
                await update.message.reply_text("You obtained a special success!")
            else:
                await update.message.reply_text("You obtained a success!")

        else:
            await update.message.reply_text(f"You failed to use the skill {skill_to_use}")
    else:
        await update.message.reply_text("Abort: please choose a skill your character possesses")
        return


async def ability_vs_ability(update: Update, context: CallbackContext):
    """Ménage the use of a character skill against another ability"""
    user_id = update.effective_user.name

    # Checking input format
    pattern_format = r"^[^:]+:[^,]+,\d+$"
    pattern_level = r"^(100|[1-9]?[0-9])$"
    if not re.fullmatch(pattern_format, "".join(context.args)):
        await update.message.reply_text("Correct usage:\n\"/ability_vs_ability <character name>: <skill used> , <enemy skill level>\"")
        return

    input_text = " ".join(context.args).split(": ")
    pc_name = input_text[0].strip()
    pc = "_".join(input_text[0].lower().split())
    details = input_text[1].split(", ")
    skill_used = details[0].strip()
    enemy_skill_level = details[1].strip()

    # Making sure the selected character exists
    try:
        with open(f"Json/users/{user_id}.json", "r") as fp:
            user_data = json.load(fp)
            user_data_player = user_data[f"{pc}"]
    except KeyError:
        await update.message.reply_text(f"You have no character named {pc_name}")
        return

    # Making sure the character possesses the skill
    if skill_used in user_data[f"{pc}"]["skills"]:
        player_skill_level = user_data_player["skills"][skill_used]
    else:
        await update.message.reply_text(f"{pc_name} does not posses the skill {skill_used}")
        return

    if re.fullmatch(pattern_level, enemy_skill_level):
        # Calculating dice rolls
        player_roll = dice_roll(1, 100)
        player_roll = player_roll["rolls_total"]
        enemy_roll = dice_roll(1, 100)
        enemy_roll = enemy_roll["rolls_total"]

        # Extracting special_success levels from json
        with open(f"Json/special_success.json", "r") as fp:
            special_success = json.load(fp)

        # Managing player dice roll result
        if player_roll <= player_skill_level:
            if player_roll in range(special_success[f"{player_skill_level}"]):
                skill_result_player = 2
                await update.message.reply_text(f"You got a SPECIAL SUCCESS! (dice_roll: {player_roll})")
            else:
                skill_result_player = 1
                await update.message.reply_text(f"You got a SUCCESS! (dice_roll: {player_roll})")
        else:
            await update.message.reply_text(f"You got a FAILURE! (dice_roll: {player_roll})")
            skill_result_player = 0

        # Managing enemy dice roll result
        if enemy_roll <= int(enemy_skill_level):
            if enemy_roll in range(special_success[enemy_skill_level]):
                await update.message.reply_text(f"The enemy got a SPECIAL SUCCESS! (dice_roll: {enemy_roll})")
                skill_result_enemy = 2
            else:
                await update.message.reply_text(f"The enemy got a SUCCESS! (dice_roll: {enemy_roll})")
                skill_result_enemy = 1
        else:
            await update.message.reply_text(f"The enemy got a FAILURE! (dice_roll: {enemy_roll})")
            skill_result_enemy = 0

        # Printing to user the event based on the 2 rolls
        if skill_result_player > skill_result_enemy:
            await update.message.reply_text(f"{pc_name} was able to use the skill {skill_used}")
        elif skill_result_player < skill_result_enemy:
            await update.message.reply_text(f"{pc_name} was not able to use the skill {skill_used}")
        elif skill_result_player == skill_result_enemy:
            await update.message.reply_text("The skills canceled out each other")

    else:
        await update.message.reply_text("Abort: please type a valid skill level (between 1 and 100)")


async def resistance_roll(update: Update, context: CallbackContext):
    """Ménage the use of a character stat against an obstacle"""
    user_id = update.effective_user.name

    # Checking input format
    pattern_format = r"^[^:]+:[^,]+,\d+$"
    pattern_level = r"^(21|[1-9]|1[0-9]|20)$"
    if not re.fullmatch(pattern_format, "".join(context.args)):
        await update.message.reply_text(
            "Correct usage:\n\"/resistance_roll <character name>: <stat used> , <obstacle stat value>\"")
        return

    input_text = " ".join(context.args).split(": ")
    pc_name = input_text[0].strip()
    pc = "_".join(input_text[0].lower().split())
    details = input_text[1].split(", ")
    stat_used = details[0].strip().lower()
    obstacle_stat_level = details[1].strip()

    # Making sure the selected character exists
    try:
        with open(f"Json/users/{user_id}.json", "r") as fp:
            user_data = json.load(fp)
            user_data_player = user_data[f"{pc}"]
    except KeyError:
        await update.message.reply_text(f"You have no character named {pc_name}")
        return

    # Making sure the character possesses the stat
    if stat_used in user_data[f"{pc}"]["stats"]:
        player_stat_level = user_data_player["stats"][f"{stat_used}"]["value"]
        if player_stat_level > 21:
            player_stat_level = 21
    else:
        await update.message.reply_text(f"{pc_name} does not posses the '{stat_used}' stat")
        return

    if re.fullmatch(pattern_level, obstacle_stat_level):
        # Calculating dice rolls
        dice_roll_result = dice_roll(1, 100)
        dice_roll_result = dice_roll_result["rolls_total"]

        # Extracting special_success levels from json
        with open(f"Json/resistance_table.json", "r") as fp:
            resistance_table = json.load(fp)

        # Extracting success probability based on the resistance_table
        success_probability = resistance_table[f"{obstacle_stat_level}"][f"{player_stat_level}"]
        await update.message.reply_text(
            "Your success probability is " + str(success_probability) + "against the obstacle")

        if dice_roll_result <= success_probability:
            await update.message.reply_text(f"Success! Your stat prevailed (You got a {dice_roll_result})")
        else:
            await update.message.reply_text(
                f"Failure! The obstacle was too strong for your stat (You got a {dice_roll_result})")

    else:
        await update.message.reply_text("Abort: please type a valid stat level (between 1 and 21)")


async def stat_roll(update: Update, context: CallbackContext):
    """Dice roll to determine whether the use of a particular character's stat is successful or not"""
    user_id = update.effective_user.name

    # Checking input format
    pattern = r"^[^,]+,[a-zA-Z]{3}$"
    if not re.fullmatch(pattern, "".join(context.args)):
        await update.message.reply_text("Correct usage:\n\"/stat_roll <character name>, <stat to use>\"")
        return

    input_text = (" ".join(context.args)).split(", ")
    pc_name = " ".join(input_text[0].split())
    pc = "_".join(input_text[0].lower().split())
    stat_to_use = input_text[1].strip()

    # Making sure the selected character exists
    try:
        with open(f"Json/users/{user_id}.json", "r") as fp:
            user_data = json.load(fp)
            user_data_player = user_data[f"{pc}"]
    except KeyError:
        await update.message.reply_text(f"You have no character named {pc_name}")
        return

    # Checking for stat existence
    stat_to_use = stat_to_use.lower()
    if stat_to_use in user_data_player["stats"]:
        stat_level = user_data_player["stats"][f"{stat_to_use}"]["value"]
        success_probability = stat_level * 4

        # Managing dice roll
        dice_roll_result = dice_roll(1, 100)
        dice_roll_result = dice_roll_result["rolls_total"]
        await update.message.reply_text(f"You got a {dice_roll_result} on your dice roll while the "
                                        f"probability to correctly use '{stat_to_use}' is {success_probability}%")

        if dice_roll_result <= success_probability:
            # Extracting special_success levels from json
            with open(f"Json/special_success.json", "r") as fp:
                special_success = json.load(fp)

            if dice_roll_result in range(special_success[f"{success_probability}"]):
                await update.message.reply_text("You obtained a special success!")
            else:
                await update.message.reply_text("You obtained a success!")

        else:
            await update.message.reply_text(f"You failed to use the stat '{stat_to_use}'")

    else:
        await update.message.reply_text("Abort: please type a valid stat")


async def roll(update: Update, context: CallbackContext):
    """
        /roll command handler. Supports multiple dice throws, modifier addition/subtraction,
        and an inline keyboard mode
    """
    input_text = ''.join(context.args)
    pattern_v3 = r"(?!ABC)(([1-9][0-9]*d[1-9][0-9]*)(,[1-9][0-9]*d[1-9][0-9]*)*)([\+|-][0-9]+)?(?<!ABC)"

    if len(input_text) == 0:
        keyboard = [
            [
                InlineKeyboardButton("d3", callback_data="3"), InlineKeyboardButton("d4", callback_data="4")
            ],
            [
                InlineKeyboardButton("d6", callback_data="6"), InlineKeyboardButton("d8", callback_data="8")
            ],
            [
                InlineKeyboardButton("d10", callback_data="10"), InlineKeyboardButton("d12", callback_data="12")
            ],
            [
                InlineKeyboardButton("d20", callback_data="20"), InlineKeyboardButton("d100", callback_data="100")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text("Choose your dice roll", reply_markup=reply_markup)

    elif re.fullmatch(pattern_v3, input_text):
        input_components = re.split(r'(\+|-)', input_text)
        roll_groups = input_components[0].split(',')

        result = 0
        roll_log = []
        for group in roll_groups:
            entries = group.split(sep="d")
            rolls = int(entries[0])
            dice_type = int(entries[1])

            outcome = dice_roll(rolls, dice_type)
            result += outcome['rolls_total']
            roll_log += outcome['rolls_log']

        if len(input_components) > 1:
            roll_modifier = int(input_components[2])
            if input_components[1] == '+':
                result += roll_modifier
            elif input_components[1] == '-':
                result -= roll_modifier

            await context.bot.send_message(chat_id=update.effective_chat.id,
                                           text=f"{' + '.join(str(r) for r in roll_log)} ({input_components[1]}{roll_modifier}) = {result}")
        else:
            if len(roll_log) > 1:
                await context.bot.send_message(chat_id=update.effective_chat.id,
                                               text=f"{' + '.join(str(r) for r in roll_log)} = {result}")
            else:
                await context.bot.send_message(chat_id=update.effective_chat.id, text=f"{result}")
    else:
        await context.bot.send_message(chat_id=update.effective_chat.id, text="Invalid command arguments, please try again.")


async def attack(update: Update, context: CallbackContext):
    user_id = update.effective_user.name

    # Checking input format
    pattern = r"^[^,]+->\d+,.+$"
    if not re.fullmatch(pattern, "".join(context.args)):
        await update.message.reply_text("Correct usage:\n\""
                                        "/attack <attacker name> -> <enemy distance>, <weapon used>\"")
        return

    input_text = " ".join(context.args).split(" -> ")
    attacker_name = input_text[0].strip()
    pc = "_".join(input_text[0].lower().split())
    distance_and_weapon = input_text[1].split(", ")
    enemy_distance = distance_and_weapon[0].strip()
    weapon_used = distance_and_weapon[1].strip()

    # Making sure the selected character exists
    try:
        with open(f"Json/users/{user_id}.json", "r") as fp:
            user_data = json.load(fp)
            user_data_player = user_data[f"{pc}"]
    except KeyError:
        await update.message.reply_text(f"You have no character named {attacker_name}")
        return

    weapons = user_data_player["weapons"]

    def check_weapon(weapon_name, weapons_dict):
        print(weapon_name)
        for weapon_category, weapon_list in weapons_dict.items():
            print(weapon_list)
            if weapon_name in weapon_list:
                return True, weapon_category
        return False, None

    possesses_weapon, weapon_type = check_weapon(weapon_used, weapons)
    if possesses_weapon:
        # Extracting weapon's info
        with open(f"Json/weapons/{weapon_type}.json", "r") as fp:
            list_of_weapons = json.load(fp)
        weapon_info = list_of_weapons[f"{weapon_used}"]

        # Rolling 100 sides dice looking for successful skill usage
        dice_roll_result = dice_roll(1, 100)["rolls_total"]

        # Getting skill name from weapon type
        weapon_type_skill = {
            "firearm": "Arma da Fuoco",
            "melee": "Arma da Mischia",
            "ranged": "Arma a Distanza",
            "heavy": "Arma Pesante"
        }
        skill = weapon_type_skill.get(weapon_type)

        # Extracting skill level
        skill_level = 0
        if skill in user_data_player["skills"]:
            skill_level = user_data_player["skills"][f"{skill}"]

        # Calculating success_probability
        success_probability = skill_level + weapon_info["base"]
        weapon_range = weapon_info["range"]
        updated_success_probability = calculate_hit_probability(int(enemy_distance), weapon_info["range"], success_probability)
        await update.message.reply_text(f"Since the target is {enemy_distance}m away and your weapon has a range of "
                                        f"{weapon_range}, your success probability is {updated_success_probability}%")

        # Analyzing dice roll
        if dice_roll_result <= updated_success_probability:
            # Extracting special_success levels from json
            with open(f"Json/special_success.json", "r") as fp:
                special_success = json.load(fp)

            if dice_roll_result in range(special_success[f"{success_probability}"]):
                await update.message.reply_text(f"SPECIAL SUCCESS: You got a {dice_roll_result} on your dice ")
            else:
                await update.message.reply_text(f"SUCCESS: You got a {dice_roll_result} on your dice ")

            # Calculating damage
            for_stat = user_data_player["stats"]["for"]["value"]
            tag_stat = user_data_player["stats"]["tag"]["value"]
            sum_for_tag = for_stat + tag_stat

            def damage_bonus_calculator(for_tag):
                if 2 <= for_tag <= 12:
                    return "-1D6"
                elif 13 <= for_tag <= 16:
                    return "-1D4"
                elif 17 <= for_tag <= 24:
                    return "+0"
                elif 25 <= for_tag <= 32:
                    return "+1D4"
                elif 33 <= for_tag <= 40:
                    return "+1D6"
                elif 41 <= for_tag <= 56:
                    return "+2D6"
                else:
                    return "+3D6"

            damage_bonus = damage_bonus_calculator(sum_for_tag)
            damage = calculate_roll_expression(weapon_info["damage"] + damage_bonus)

            await update.message.reply_text(f"The attack will inflict a total of {damage} damage")

        else:
            await update.message.reply_text(f"FAILURE: You got a {dice_roll_result} on your dice ")

    else:
        await update.message.reply_text("Aborted: enter a valid weapon your character possesses")


async def evade(update: Update, context: CallbackContext):
    user_id = update.effective_user.name

    # Checking input format
    pattern = r"^[\w\s]+<-[\w\s]+,\d+$"
    if not re.fullmatch(pattern, "".join(context.args)):
        await update.message.reply_text("Correct usage:\n\""
                                        "/evade <defender name> <- <type of success>, <damage>\"")
        return

    input_text = " ".join(context.args).split(" <- ")
    defender_name = input_text[0].strip()
    pc = "_".join(input_text[0].lower().split())
    rest_of_input = input_text[1].split(", ")
    type_of_success = rest_of_input[0].strip().lower().replace(" ", "_")
    damage = rest_of_input[1].strip()

    # Making sure the selected character exists
    try:
        with open(f"Json/users/{user_id}.json", "r") as fp:
            user_data = json.load(fp)
            user_data_player = user_data[f"{pc}"]
    except KeyError:
        await update.message.reply_text(f"You have no character named {defender_name}")
        return

    # Checking validity of success type
    if type_of_success not in ["special_success", "success"]:
        await update.message.reply_text("Abort: please enter a valid type of success")
        return

    if "Schivare" in user_data_player["skills"]:
        dice_roll_result = dice_roll(1, 100)["rolls_total"]

        skill_level = user_data_player["skills"]["Schivare"]
        if dice_roll_result <= skill_level:
            # Extracting special_success levels from json
            with open(f"Json/special_success.json", "r") as fp:
                special_success = json.load(fp)

            if dice_roll_result in range(special_success[f"{skill_level}"]):
                await update.message.reply_text("You obtained a special success!")
                success_result = "ss"
            else:
                await update.message.reply_text("You obtained a success!")
                success_result = "s"

        else:
            await update.message.reply_text("You failed to evade the attack")
            success_result = "f"

        results_combinations = {
            ("special_success", "ss"): "*0",
            ("special_success", "s"): "/2",
            ("special_success", "f"): "*2",
            ("success", "ss"): "*0",
            ("success", "s"): "*0",
            ("success", "f"): "+0",
        }

        # Calculating damage based on the type of success obtained
        expression = f"{damage}{results_combinations.get((type_of_success, success_result))}"
        damage_result = eval(expression)

        # Extracting armors info
        with open(f"Json/armors.json", "r") as fp:
            all_armors = json.load(fp)
        extra_hp = 0
        for armor in user_data_player["armor"]:
            extra_hp += all_armors[f"{armor}"]["Armor Points"]

        # Subtracting damage
        current_hp = user_data_player["hit_points"]["current"]
        remaining_damage = extra_hp - damage_result
        if remaining_damage < 0:
            new_hp = current_hp + remaining_damage
        else:
            new_hp = current_hp

        if new_hp < 0:
            new_hp = 0
        user_data_player["hit_points"]["current"] = new_hp

        # Saving the new hit points value
        with open(f"Json/users/{user_id}.json", "w") as fp:
            json.dump(user_data, fp, indent=4)

        hp = user_data_player["hit_points"]["current"]
        if hp == 0:
            await update.message.reply_text("You got a fatal wound! Your hp dropped to 0")
        elif 0 < hp < 3:
            await update.message.reply_text(f"Because of the attack {defender_name} passed out")
        else:
            await update.message.reply_text(f"Current hit_points: {hp}")

    else:
        await update.message.reply_text("Abort: you are not able to evade the attack since you do not possess the skill 'Schivare'")


async def shield(update: Update, context: CallbackContext):
    user_id = update.effective_user.name

    # Checking input format
    pattern = r"^[\w\s]+\([\w\s]+\) <- [\w\s]+, \d+$"
    if not re.fullmatch(pattern, " ".join(context.args)):
        await update.message.reply_text("Correct usage:\n"
                                        "\"/shield <defender name>(<item used to defend>) <- <type of success>, <damage>\"")
        return

    input_text = " ".join(context.args).split(" <- ")
    defender_info = input_text[0].strip()
    rest_of_input = input_text[1].split(", ")
    defender_name, skill_used = defender_info[:-1].split('(')
    pc = "_".join(defender_name.lower().split())
    defender_name = defender_name.strip()
    item_used = skill_used.strip()
    type_of_success = rest_of_input[0].strip().lower().replace(" ", "_")
    damage = rest_of_input[1].strip()

    # Making sure the selected character exists
    try:
        with open(f"Json/users/{user_id}.json", "r") as fp:
            user_data = json.load(fp)
            user_data_player = user_data[f"{pc}"]
    except KeyError:
        await update.message.reply_text(f"You have no character named {defender_name}")
        return

    # Checking validity of success type
    if type_of_success not in ["special_success", "success"]:
        await update.message.reply_text("Abort: please enter a valid type of success")
        return

    # Extracting skill based on the item used to parry the attack
    item = find_item(item_used, user_data_player)
    item_related_skills = {
        "firearm": "Arma da Fuoco",
        "melee": "Arma da Mischia",
        "ranged": "Arma a Distanza",
        "heavy": "Arma Pesante",
        "shield": "Scudo"
    }
    general_skill_used = item_related_skills.get(item)
    skill_used = get_actual_skill(general_skill_used, user_data_player)

    if skill_used in user_data_player["skills"]:
        # Preparing the shields info if needed
        if skill_used == "Scudo":
            with open(f"Json/shields.json", "r") as fp:
                all_shields = json.load(fp)

        dice_roll_result = dice_roll(1, 100)["rolls_total"]
        skill_level = user_data_player["skills"][f"{skill_used}"]

        # Managing shield case
        if skill_used == "Scudo":
            probability_to_add = all_shields[f"{item_used}"]["Base Probability"]
            skill_level += probability_to_add
            if skill_level > 100:
                skill_level = 100

        if dice_roll_result <= skill_level:
            # Extracting special_success levels from json
            with open(f"Json/special_success.json", "r") as fp:
                special_success = json.load(fp)

            if dice_roll_result in range(special_success[f"{skill_level}"]):
                await update.message.reply_text("You obtained a special success!")
                success_result = "ss"
            else:
                await update.message.reply_text("You obtained a success!")
                success_result = "s"

        else:
            await update.message.reply_text("You failed to evade the attack")
            success_result = "f"

        results_combinations = {
            ("special_success", "ss"): "*0",
            ("special_success", "s"): "/2",
            ("special_success", "f"): "*2",
            ("success", "ss"): "*0",
            ("success", "s"): "*0",
            ("success", "f"): "+0",
        }

        # Calculating damage based on the type of success obtained
        expression = f"{damage}{results_combinations.get((type_of_success, success_result))}"
        damage_result = eval(expression)

        # Extracting armors info
        with open(f"Json/armors.json", "r") as fp:
            all_armors = json.load(fp)
        extra_hp = 0
        for armor in user_data_player["armor"]:
            extra_hp += all_armors[f"{armor}"]["Armor Points"]

        # Subtracting damage
        current_hp = user_data_player["hit_points"]["current"]
        remaining_damage = extra_hp - damage_result
        if remaining_damage < 0:
            new_hp = current_hp + remaining_damage
        else:
            new_hp = current_hp

        if new_hp < 0:
            new_hp = 0
        user_data_player["hit_points"]["current"] = new_hp

        # Saving the new hit points value
        with open(f"Json/users/{user_id}.json", "w") as fp:
            json.dump(user_data, fp, indent=4)

        hp = user_data_player["hit_points"]["current"]
        if hp == 0:
            await update.message.reply_text("You got a fatal wound! Your hp dropped to 0")
        elif 0 < hp < 3:
            await update.message.reply_text(f"Because of the attack {defender_name} passed out")
        else:
            await update.message.reply_text(f"Current hit_points: {hp}")

    else:
        await update.message.reply_text(f"Abort: you are not able to parry the attack since you do not possess the skill '{skill_used}'")


def find_item(item, character):
    """
        Helping function used to extract list's name in which the item is contained t
        :param item: Item to look for
        :param character: Character info with the lists to analyze
        :return: Name of the list containing the item
    """
    weapon_categories = ["firearm", "melee", "ranged", "heavy"]

    # Checking all 4 weapons list
    for category in weapon_categories:
        if item in character["weapons"][category]:
            return category

    # Checking shield list
    if item in character["shield"]:
        return "shield"

    return None  # In case no object has been found


def get_actual_skill(general_skill, character):
    """
        Helping function used to extract a specialized skill
        given the general one that is supposed to contain it
        :param general_skill: Skill with multiple specializations
        :param character: Character info used to point the specific skill needed
        :return: Specialized skill
    """
    with open(f"Json/skills.json", "r") as fp:
        all_skills = json.load(fp)

    specialized_skills = all_skills[f"{general_skill}"]["specializations"]

    for skill in specialized_skills:
        if skill in character["skills"]:
            return skill

    return None     # In case no skill has been found


async def remove_hp(update: Update, context: CallbackContext):
    user_id = update.effective_user.name

    # Checking input format
    pattern = r"^[^,]+,\s*\d+$"
    correct_input = r"\d+"
    if not re.fullmatch(pattern, "".join(context.args)):
        await update.message.reply_text("Correct usage:\n\"/remove_hp <character name>, <hp to remove>\"")
        return

    input_text = (" ".join(context.args)).split(", ")
    pc_name = " ".join(input_text[0].split())
    pc = "_".join(input_text[0].lower().split())
    hp_to_remove = input_text[1]

    # Making sure the selected character exists
    try:
        with open(f"Json/users/{user_id}.json", "r") as fp:
            user_data = json.load(fp)
            user_data_player = user_data[f"{pc}"]
    except KeyError:
        await update.message.reply_text(f"You have no character named {pc_name}")
        return

    if re.fullmatch(correct_input, hp_to_remove):
        current_hp = user_data_player["hit_points"]["current"]
        new_hp = current_hp - int(hp_to_remove)

        if new_hp < 0:
            user_data_player["hit_points"]["current"] = 0
        else:
            user_data_player["hit_points"]["current"] = new_hp

        # Saving the new hit points value
        with open(f"Json/users/{user_id}.json", "w") as fp:
            json.dump(user_data, fp, indent=4)
        hp = user_data_player["hit_points"]["current"]
        await update.message.reply_text(f"Current hit_points: {hp}")

    else:
        await update.message.reply_text("Aborted: enter a valid 'hp' number")


async def heal(update: Update, context: CallbackContext):
    """Increment a character hit_points by the number given in input"""
    user_id = update.effective_user.name

    # Checking input format
    pattern = r"^[^,]+,\s*\d+$"
    correct_input = r"\d+"
    if not re.fullmatch(pattern, "".join(context.args)):
        await update.message.reply_text("Correct usage:\n\"/heal <character name>, <hp to add>\"")
        return

    input_text = (" ".join(context.args)).split(", ")
    pc_name = " ".join(input_text[0].split())
    pc = "_".join(input_text[0].lower().split())
    hp_to_add = input_text[1]

    # Making sure the selected character exists
    try:
        with open(f"Json/users/{user_id}.json", "r") as fp:
            user_data = json.load(fp)
            user_data_player = user_data[f"{pc}"]
    except KeyError:
        await update.message.reply_text(f"You have no character named {pc_name}")
        return

    if re.fullmatch(correct_input, hp_to_add):
        current_hp = user_data_player["hit_points"]["current"]
        max_hp = user_data_player["hit_points"]["max"]
        new_hp = current_hp + int(hp_to_add)

        if new_hp > max_hp:
            user_data_player["hit_points"]["current"] = max_hp
        else:
            user_data_player["hit_points"]["current"] = new_hp

        # Saving the new hit points value
        with open(f"Json/users/{user_id}.json", "w") as fp:
            json.dump(user_data, fp, indent=4)
        hp = user_data_player["hit_points"]["current"]
        await update.message.reply_text(f"Current hit_points: {hp}")

    else:
        await update.message.reply_text("Aborted: enter a valid 'hp' number")


async def remove_item(update: Update, context: CallbackContext):
    user_id = update.effective_user.name

    # Checking input format
    pattern = r"^[a-zA-Z\s]+,\s*[a-zA-Z\s]+:\s*[a-zA-Z0-9_]+\s*$"
    if not re.fullmatch(pattern, "".join(context.args)):
        await update.message.reply_text("Correct usage:\n\""
                                        "/remove_item <character name>, <type of item>: <item to remove>\"")
        return

    input_text = " ".join(context.args).split(", ")
    pc_name = " ".join(input_text[0].split())
    pc = "_".join(pc_name.lower().split())
    item_info = input_text[1].split(": ")
    item_type = " ".join(item_info[0].split()).lower()
    item_to_remove = " ".join(item_info[1].split())

    # Making sure the selected character exists
    try:
        with open(f"Json/users/{user_id}.json", "r") as fp:
            user_data = json.load(fp)
            user_data_player = user_data[f"{pc}"]
    except KeyError:
        await update.message.reply_text(f"You have no character named {pc_name}")
        return

    item_types = {
        "skill": "skills",
        "weapon": "weapons",
        "armor": "armor",
        "shield": "shield",
        "equipment": "equipment"
    }
    # Checking validity of item type
    if item_type not in item_types:
        await update.message.reply_text("Aborted: enter a valid item type")
        return

    def get_all_weapons(character):
        weapons = character.get("weapons", {})

        all_weapons = []
        for weapon_list in weapons.values():
            all_weapons.extend(weapon_list)

        return all_weapons

    # Checking for item existence
    if item_type == "weapon":
        list_of_items = get_all_weapons(user_data_player)
    else:
        list_of_items = user_data_player[f"{item_types.get(item_type)}"]

    if item_to_remove in list_of_items:
        def remove_item(collection, item):
            if isinstance(collection, list):
                try:
                    collection.remove(item)
                    return True
                except ValueError:
                    return False
            elif isinstance(collection, dict):
                if item in collection:
                    del collection[item]
                    return True
                else:
                    return False
            else:
                return False

        def remove_weapon(character, weapon_name):
            weapons = character.get("weapons", {})

            for category, weapon_list in weapons.items():
                if weapon_name in weapon_list:
                    weapon_list.remove(weapon_name)
                    return True

            return False

        if item_type == "weapon":
            outcome = remove_weapon(user_data_player, item_to_remove)
        else:
            outcome = remove_item(user_data_player[f"{item_types.get(item_type)}"], item_to_remove)

        if outcome:
            await update.message.reply_text("Your item has been successfully removed")
            # Saving updated character
            with open(f"Json/users/{user_id}.json", "w") as fp:
                json.dump(user_data, fp, indent=4)
        else:
            await update.message.reply_text("An error occurred")

    else:
        await update.message.reply_text("Aborted: enter a valid item type")


async def help_f(update: Update, context: CallbackContext):
    """help message"""
    help_text = (
        "Welcome to the game! Here are the commands you can use:\n\n"
        "/start - Start the game and get the initial instructions.\n"
        "/new_pc - Starts the guided process of new character creation.\n"
        "/cancel - Command available only during character creation to stop the process without saving\n"
        "/view_character - View your character's details.\n"
        "/assign_skill - Assign skill to your character.\n"   
        "/level_up_skill - Dice roll to upgrade a skill.\n"
        "/add_weapon - Add weapon to a character. \n"
        "/add_armor - Add armor to a character. \n"
        "/add_shield - Add a shield to your character.\n"
        "/add_equipment - Add an equipment to your character.\n"
        "/remove_item - Remove na item or skill from a given character.\n"
        "/save_currency - Add money to a character.\n"
        "/pay_currency - Remove money from a character.\n"
        "/ability_roll - Dice roll to use a character ability \n"   
        "/ability_vs_ability - Decide winner between two ability used at the same time.\n"  
        "/resistance_roll - Dice roll to use a stat against some resistance.\n"
        "/stat_roll - Dice roll to use a stat\n"
        "/attack - Calculate damage and result of an attack given target distance and weapon used\n"
        "/evade - Returns the result of an attempt to evade the attack given the damage e type of success\n"
        "/shield - Returns the result of an attempt to shield the attack given the damage e type of success\n"
        "/remove_hp - Used to inflict damage in case the defender has neither the skill 'Schivare' neither a shield\n"
        "/heal - Regenerate the character hp by the given number\n"
        "/roll - Generic dice roll with multiple dice option\n"
        "/help - Show all possible commands.\n\n"
        "For more information about each command, you can click the buttons below."
    )

    # Define the keyboard layout
    keyboard = [
        ["/start", "/new_pc"],
        ["/view_character", "/assign_skill"],
        ["/level_up_skill", "/add_weapon"],
        ["/add_armor", "/add_shield"],
        ["/add_equipment", "/help"],
        ["/save_currency", "/pay_currency"],
        ["/ability_roll", "/ability_vs_ability"],
        ["/resistance_roll", "/stat_roll"],
        ["/roll", "/attack"],
        ["/evade", "/shield"],
        ["/heal", "/cancel"],
        ["/remove_hp", "/remove_hp"]
    ]

    reply_markup = ReplyKeyboardMarkup(keyboard, resize_keyboard=True, one_time_keyboard=True)

    await update.message.reply_text(help_text, reply_markup=reply_markup)


async def preparing_assign_skill_points_state(user_id: str, update: Update, context: ContextTypes.DEFAULT_TYPE):
    context.user_data.clear()
    context.user_data['skill_points'] = 300

    skills = tmp_user_data[f"{user_id}"]["tmp_character"]["skills"]
    for skill in skills:
        tmp_user_data[f"{user_id}"]["tmp_character"]["skills"][skill] = calculate_skill_level(
            tmp_user_data[f"{user_id}"]["tmp_character"],
            tmp_user_data[f"{user_id}"]["tmp_character"]["skills"][skill])

    context.user_data['all_skills'] = skills
    skills_message = "Here are your skills levels:\n"
    for skill, level in skills.items():
        skill_info = f"{skill}: {level}"
        skills_message += skill_info + "\n"

    print(context.user_data)

    await update.message.reply_text(skills_message)
    await update.message.reply_text("You currently have 300 points to increase your skills' level. Please type the "
                                    "skill you want to improve followed by the number of points to use on it")

    return


async def gui_dice_roll(update: Update, context: CallbackContext):
    """callback function for dice keyboard"""
    dice = int(update.callback_query.data)
    await context.bot.send_message(chat_id=update.effective_chat.id,
                                   text=f"Result for d{dice}: {dice_roll(1, dice)['rolls_total']}")


def main():
    application = Application.builder().token('7123849260:AAEai7w3pLmZl1RpsYB-mFiLVaxObtaryQE').build()

    # Handler for '/start' command
    start_handler = CommandHandler('start', start)
    application.add_handler(start_handler)

    # handler for /roll
    roll_handler = CommandHandler('roll', roll)
    application.add_handler(roll_handler)

    # handler for dice roll inline keyboard
    application.add_handler(CallbackQueryHandler(gui_dice_roll))

    # handler for /view_character
    view_character_handler = CommandHandler('view_character', view_character)
    application.add_handler(view_character_handler)

    # handler for /assign_skill
    assign_skill_handler = CommandHandler('assign_skill', assign_skill)
    application.add_handler(assign_skill_handler)

    # handler for /level_up_skill
    level_up_skill_handler = CommandHandler('level_up_skill', level_up_skill)
    application.add_handler(level_up_skill_handler)

    # handler for /add_weapon
    add_weapon_handler = CommandHandler('add_weapon', add_weapon)
    application.add_handler(add_weapon_handler)

    # handler for /add_armor
    add_armor_handler = CommandHandler('add_armor', add_armor)
    application.add_handler(add_armor_handler)

    # handler for /add_shield
    add_shield_handler = CommandHandler('add_shield', add_shield)
    application.add_handler(add_shield_handler)

    # handler for /add_equipment
    add_equipment_handler = CommandHandler('add_equipment', add_equipment)
    application.add_handler(add_equipment_handler)

    # handler for /save_currency
    save_currency_handler = CommandHandler('save_currency', save_currency)
    application.add_handler(save_currency_handler)

    # handler for /pay_currency
    pay_currency_handler = CommandHandler('pay_currency', pay_currency)
    application.add_handler(pay_currency_handler)

    # handler for /ability_roll
    ability_roll_handler = CommandHandler('ability_roll', ability_roll)
    application.add_handler(ability_roll_handler)

    # handler for /ability_vs_ability
    ability_vs_ability_handler = CommandHandler('ability_vs_ability', ability_vs_ability)
    application.add_handler(ability_vs_ability_handler)

    # handler for /resistance_roll
    resistance_roll_handler = CommandHandler('resistance_roll', resistance_roll)
    application.add_handler(resistance_roll_handler)

    # handler for /stat_roll
    stat_roll_handler = CommandHandler('stat_roll', stat_roll)
    application.add_handler(stat_roll_handler)

    # handler for /attack
    attack_handler = CommandHandler('attack', attack)
    application.add_handler(attack_handler)

    # handler for /evade
    evade_handler = CommandHandler('evade', evade)
    application.add_handler(evade_handler)

    # handler for /shield
    shield_handler = CommandHandler('shield', shield)
    application.add_handler(shield_handler)

    # handler for /remove_hp
    remove_hp_handler = CommandHandler('remove_hp', remove_hp)
    application.add_handler(remove_hp_handler)

    # handler for /heal
    heal_handler = CommandHandler('heal', heal)
    application.add_handler(heal_handler)

    # handler for /remove_item
    remove_item_handler = CommandHandler('remove_item', remove_item)
    application.add_handler(remove_item_handler)

    # handler for /help
    help_handler = CommandHandler('help', help_f)
    application.add_handler(help_handler)

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
            DISTINCTIVE_TRAITS: [MessageHandler(filters.TEXT & ~filters.COMMAND, new_pc_distinctive_traits)]
        },
        fallbacks=[CommandHandler('cancel', cancel)]
    )

    application.add_handler(pc_creation_handler)

    application.run_polling()


if __name__ == '__main__':
    main()
