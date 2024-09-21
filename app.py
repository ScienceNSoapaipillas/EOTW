#!/usr/bin/env python3

from discord.ext import commands
from dotenv import load_dotenv
from flask import Flask
from table2ascii import table2ascii as t2a, PresetStyle

# import custom osrs tracking class
from src.EOTW import EOTW

import discord
import matplotlib
import os
import threading

matplotlib.use('Agg')  # Use a non-interactive backend
import matplotlib.pyplot as plt


import sys

# Load environment variables from .env file
if not os.path.exists('.env'):
    print('no .env file found!')
    sys.exit(1)

load_dotenv()

BOT_ATTEN = os.getenv("BOT_ATTENTION")
# Initialize Flask
app = Flask(__name__)

# Set up Discord bot, if ever needed the permissions integer is: 1689244997381120
intents = discord.Intents.default()
intents.message_content = True  # Ensure this intent is enabled
bot = commands.Bot(command_prefix=BOT_ATTEN, intents=intents, help_command=None)

# Initialize the competition (we'll make this dynamic later)
eotw_competition = None


# Flask route to check if the bot is running
@app.route("/", methods=["GET"])
def index():
    return "Bot is running!"


# Hello bot
@bot.command(name="hello")
async def hello_world(ctx):
    await ctx.send("Hello world!")

# Command to start a new competition
@bot.command(name="start-competition")
async def start_competition(ctx, activity: str, stop_date: str) -> None:
    global eotw_competition
    eotw_competition = EOTW(activity, stop_date)
    await ctx.send(f"Started competition for {activity}, ending at {stop_date}.")

# Command to add a player to the competition
@bot.command(name="add-player")
async def add_player(ctx, player_name: str, buyin: str = '250k', remainder: str = '0', player_timezone: str = 'EST'):
#async def add_player(ctx, player_name: str, buyin: str, remainder: str, player_timezone='EST': str):
    player_info = f'{player_name}, {player_timezone}, {buyin}, {remainder}'

    if remainder == '0' or remainder != '' or remainder != ' ':
        remainder_str = f', balance of {remainder}'
    else:
        remainder = ''

    #print(f'my player info is:{player_info}')
    global eotw_competition
    if eotw_competition is None:
        await ctx.send("No active competition. Use !start_competition first.")
        return
    eotw_competition.add_to_table(player_info)
    out = f"{player_name} is in {player_timezone}, bought in with {buyin}{remainder_str} to the competition."
    await ctx.send(out)

@bot.command(name='remove-player')
async def remove_player(ctx, player):
    global eotw_competition
    if eotw_competition is None:
        await ctx.send("No active competition. Use !start_competition first.")
        return
    
    eotw_competition.remove_from_table(player)
    await ctx.send(f'Removed "{player}" from the competition.')

@bot.command(name="jackpot")
async def jackpot(ctx):
    global eotw_competition
    if eotw_competition is None:
        await ctx.send("No active competition. Use !eotw-start_competition first.")
        return
    try:
        display_pot = eotw_competition.jackpot()
        await ctx.send(f"The total pot is: {display_pot}")
    except KeyError:
        await ctx.send("There is no 'Buy in (k)' column in the current competition.")
    except Exception as e:
        await ctx.send(f"An error occurred: {str(e)}")



# Command to view the competition table
@bot.command(name="view-table")
async def view_table(ctx):
    global eotw_competition
    if eotw_competition is None:
        await ctx.send(f"No active competition. Use {BOT_ATTN}start_competition first.")
        return

    if len(eotw_competition.table['Time Zone'].unique()) == 1:
        table = eotw_competition.table.drop(columns=['Time Zone'])
    else:
        table = eotw_competition.table
    
    # Prepare the table headers and body
    headers = list(table.columns)
    body = [list(row) for _, row in table.iterrows()]

    # Generate the ASCII table
    output = t2a(
        header=headers,
        body=body,
        style=PresetStyle.thin_compact  # Use thin compact style for better fit
    )
    
    # Send the table as a Discord message inside a code block
    await ctx.send(f"```\n{output}\n```")

@bot.command(name="view-table-img")
async def view_table_img(ctx):
    global eotw_competition
    if eotw_competition is None:
        await ctx.send("No active competition. Use !eotw-start_competition first.")
        return

    if len(eotw_competition.table['Time Zone'].unique()) == 1:
        dtable = eotw_competition.table.drop(columns=['Time Zone'])
    else:
        dtable = eotw_competition.table

    # Find the longest entry in each column (including header)
    column_lengths = {}
    for col in dtable.columns:
        max_length = len(col)  # Start with the column header length
        for entry in dtable[col]:
            max_length = max(max_length, len(str(entry)))  # Compare with each data entry's length
        column_lengths[col] = max_length

    # Calculate total length to scale proportionally
    total_length = sum(column_lengths.values())

    # Assign intelligent weights based on column length proportions
    column_widths = {col: length / total_length for col, length in column_lengths.items()}

    # Increase figure size dynamically based on the number of rows
    #fig, ax = plt.subplots(figsize=(18, len(eotw_competition.table) * 0.8), dpi=600)
    fig, ax = plt.subplots(figsize=(18, 1.5), dpi=600)
    ax.axis('tight')
    ax.axis('off')

    # Create the table from the DataFrame
    table = ax.table(
        cellText=dtable.values,
        colLabels=dtable.columns,
        cellLoc='center',
        loc='center'
    )

    # Adjust table properties
    table.auto_set_font_size(False)
    table.set_fontsize(14)  # Adjust font size as needed
    table.scale(1.6, 2.0)  # Scale the table (increase size to reduce crowding)

    # Apply the calculated column widths
    for col_idx, (col_name, width) in enumerate(column_widths.items()):
        for row in range(len(dtable) + 1):  # Include header row (0)
            table[(row, col_idx)].set_width(width)

    # Save the table as an image
    image_path = "./competition_table.png"
    plt.savefig(image_path, bbox_inches='tight', pad_inches=0.02, dpi=600)


    # Send the image to Discord
    with open(image_path, 'rb') as image_file:
        await ctx.send(file=discord.File(image_file, "competition_table.png"))

    plt.close(fig)


# Command to update the competition table
@bot.command(name="update-table")
async def update_table(ctx):
    global eotw_competition
    if eotw_competition is None:
        await ctx.send("No active competition. Use !start_competition first.")
        return
    eotw_competition.update_table()
    await ctx.send("Updated the competition table.")


@bot.command(name="sugma")
async def sugma(ctx):
    await ctx.send('Ninja says fuck you read the rules `!sb-rules`')
    return


@bot.command(name="rules")
async def rules(ctx):
    global eotw_competition
    if eotw_competition is None:
        await ctx.send("No active competition. Use !start_competition first.")
        return
    await ctx.send(eotw_competition.rules())
    return


@bot.command(name="help", aliases=["how-to", 'howto', 'how_to', 'faq', 'FAQ', 'Help', 'HELP', 'hep'])
async def sb_help(ctx):
    out  = """Here is a brief tutorial on how to use this bot!
    Before you can do anything, you must initiate the bot with a competition. Here is the general format:
    `!sb-start-competition *activity* *end_date*`, where end_date has format: `"YYYY-MM-DD hh:mm:ss"`
    This tells it the skill or the boss, and the stop time. For example, if we are doing fishing until September 14th, 2024 at 6:30 PM, we would initiate the bot with:
    `!sb-start-competition fishing "2024-09-14 18:30:00"`
    Here is another example with bosses. Note that boss names must be *exactly* how they appear on the OSRS highscores website! 'Jad', 'Zuk', 'Calvarion' are not adequate - you must provide it with 'TzTok-Jad', 'TzKal-Zuk', and 'Calvar'ion' respectively. Let's do Calvar'ion, with a stop date/time of November 23rd, 2024, at 6:12 in the morning:
    `!sb-start-competition "Calvar'ion" "2024-11-23 06:12:00"`
    Now that we have a bot up and running, lets give it some people to track! *OPTIONALLY* you can provide the bot with a timezone, buy in amount, and "balance" or "left over amount" for notekeeping, all-in-one-purposes. If you do not specify these, their defaults are EST, 250k, and 0 respectively. Here is the general format for adding a player:
    `!sb-add-player "*player_name*", *buyin_amount*, *balance*, *timezone*`
    Now lets do an example where we add "I Do Science" to the competition with a buyin amount of 1.5m
    `!sb-add-player "I Do Science" 5m`
    Now that we've added a player to the competition, lets take a quick look at the board!
"""
    await ctx.send(out)
    out = """we have 2 options for looking at the scoreboard; one is text in a pretty formatted table, the other is an image. While (subjectively) the text looks nicer, it only looks nicer if your screen is sufficently wide enough - basically only Desktop users with discord in full screen, and thats cringe. For every other sane human being, we have the image format.
    Text format: `!sb-view-table`
    Image format: `!sb-view-table-img`
    Lets add some competition for our friend:
    `!sb-add-player "amibis" 1m 50m`
    `!sb-add-player "Cheese Lady" 2400k 2.3m`
    `!sb-add-player "Choreomania" 250k 1750m`
    `!sb-add-player "uwuchi" 5m`
    Now that we have an adequately populated table, we have discovered weve made a mistake! Choreomania has an oustanding balance of nearly 2 billion - we definitely meant to make that 1750k! Lets remove her from the table, then readd her. The general format for removing a player is:
    `!sb-remove-player *player*`
    Therefore to remove her, we do: `!sb-remove-player Choreomania`
    Now lets add her back correctly so she can compete and is tracked: `!sb-add-player "Choreomania" 250k 1750k`
    The bot also has the ability to calculate the total amount thats in the jackpot with `!sb-jackpot`
    And he also has rules that are specific to both boss and skilling, dynamically changed depending on the given activity with `!sb-rules`

## TL;DR
    `!sb-start-competition "Calvar'ion" "2024-11-23 06:12:00"`
    `!sb-add-player "I Do Science" 5m`
    `!sb-remove-player "I Do Science"`
    `!sb-view-table`
    `!sb-view-table-img`
    `!sb-rules`
"""
    await ctx.send(out)


@bot.command(name='smegma')
async def sb_help(ctx):
    out  = 'The awful union between "cheese" and "sugma"\n'
    out += 'sugma ninja'
    await ctx.send(out)

    # Function to run the bot
def run_discord_bot():
    bot.run(os.getenv("DISCORD_TOKEN"))

# Function to run the Flask app
def run_flask_app():
    app.run(host="0.0.0.0", port=5001)

# Running both Flask and Discord bot
if __name__ == "__main__":

#    competition_list = {}

#    actvity, eotw = start_competition('fishing', 'NOW()')
#    competition_list[activity] = eotw
    

    # Create threads for Flask and Discord bot
    flask_thread = threading.Thread(target=run_flask_app)
    discord_thread = threading.Thread(target=run_discord_bot)

    # Start both threads
    flask_thread.start()
    discord_thread.start()

    # Wait for both threads to finish
    flask_thread.join()
    discord_thread.join()

