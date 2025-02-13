# Telegram Bot for Basic Roleplaying (BRP) 

## Table of Contents
- [Overview](#overview)
- [Features](#features)
- [Usage](#usage)
  - [Commands](#commands)
- [Evaluation](#evaluation)
- [License](#license)
- [Acknowledgments](#acknowledgments)

## Overview
This project is a Telegram bot designed to manage multiple games of **Basic Roleplaying (BRP)**, a tabletop role-playing game system. The bot facilitates game sessions by helping players and Game Masters (GMs) manage character sheets, dice rolls, combat, and other game mechanics. The rules for the game are based on the **Basic Roleplaying System Reference Document (BRP SRD)**, which is provided in the attached PDF.

The bot is built to streamline the gameplay experience, making it easier for players to focus on storytelling and role-playing rather than manual calculations and rule lookups.

## Features

- **Character Sheet Management**: Create, update, and manage character sheets directly within the bot.
- **Dice Rolling**: Roll dice for skill checks, combat, and other in-game actions using simple commands.
- **Combat Management**: Automate combat sequences, including attack rolls, damage calculation, and turn order.
- **Skill Checks**: Perform skill checks with modifiers based on difficulty levels (Easy, Normal, Difficult, Impossible).
- **Game Session Tracking**: Keep track of ongoing game sessions, including player actions, NPC interactions, and story progression.
- **Rule Lookup**: Quickly reference rules from the BRP SRD using in-bot commands.


## Usage
### Commands
- /start - Start the game and get the initial instructions.
- /new_pc - Starts the guided process of new character creation.
- /cancel - Command available only during character creation to stop the process without saving.
- /view_character - View your character's details.
- /assign_skill - Assign skill to your character.
- /level_up_skill - Dice roll to upgrade a skill.
- /add_weapon - Add weapon to a character.
- /add_armor - Add armor to a character.
- /add_shield - Add a shield to your character.
- /add_equipment - Add an equipment to your character.
- /remove_item - Remove na item or skill from a given character.
- /save_currency - Add money to a character.
- /pay_currency - Remove money from a character.
- /ability_roll - Dice roll to use a character ability.
- /ability_vs_ability - Decide winner between two ability used at the same time.
- /resistance_roll - Dice roll to use a stat against some resistance.
- /stat_roll - Dice roll to use a stat.
- /attack - Calculate damage and result of an attack given target distance and weapon used.
- /evade - Returns the result of an attempt to evade the attack given the damage e type of success.
- /shield - Returns the result of an attempt to shield the attack given the damage e type of success.
- /remove_hp - Used to inflict damage in case the defender has neither the skill 'Schivare' neither a shield.
- /heal - Regenerate the character hp by the given number.
- /roll - Generic dice roll with multiple dice option.
- /help - Show all possible commands.

## Evaluation
This project was developed as part of a course at the Polytechnic of Milan, where I received an evaluation of **30/30** for my work.

## License
This project is licensed under the MIT License. See the LICENSE file for more details.

## Acknowledgments
- Chaosium Inc.: For creating the Basic Roleplaying system and providing the SRD.
- Telegram: For their robust bot API that makes this project possible.
