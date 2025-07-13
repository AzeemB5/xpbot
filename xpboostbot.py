import discord
from discord.ext import commands
from collections import defaultdict
from keep_alive import keep_alive
import random
import json
from scenario import scenario_chapters
from scenario import side_quests

SAVE_FILE = "save_data.json"

def load_data():
    global user_data, current_chapter
    try:
        with open(SAVE_FILE, "r") as f:
            data = json.load(f)
            user_data = data.get("user_data", {})
            current_chapter = data.get("current_chapter", 0)
    except FileNotFoundError:
        user_data = {}
        current_chapter = 0

def save_data():
    data = {
        "user_data": user_data,
        "current_chapter": current_chapter
    }
    with open(SAVE_FILE, "w") as f:
        json.dump(data, f, indent=4)

intents = discord.Intents.default()
intents.message_content = True
intents.members = True

current_chapter = 0
completed_users = set()  # Optional quest tracking

bot = commands.Bot(command_prefix="!", intents=intents)
load_data()  # ✅ Load saved data when bot starts

# --- User XP Data ---
user_data = {}

def get_multiplier(level):
    return 1.0 + min(level // 5, 5) * 0.30  # caps at 2.5x

def get_required_xp(level):
    return 100 + (level * 50)

# --- Scenario Voting Data ---
scenario_active = False
scenario_choices = []
user_votes = defaultdict(str)

# --- Events ---
@bot.event
async def on_ready():
    print(f"{bot.user} has connected to Discord!")
    print(f"✅ Logged in as {bot.user}")

@bot.event
async def on_message(message):
    if message.author.bot:
        return

    user_id = message.author.id
    if user_id not in user_data:
        user_data[user_id] = {"xp": 0, "level": 1}

    data = user_data[user_id]
    if data["level"] < 30:
        multiplier = get_multiplier(data["level"])
        gained_xp = int(random.randint(5, 15) * multiplier)
        data["xp"] += gained_xp

        while data["xp"] >= get_required_xp(data["level"]) and data["level"] < 30:
            data["xp"] -= get_required_xp(data["level"])
            data["level"] += 1
            await message.channel.send(f"🎉 {message.author.mention} leveled up to {data['level']}!")

    await bot.process_commands(message)

# --- Commands ---
@bot.command(name="resetallxp")
@commands.has_permissions(administrator=True)
async def resetallxp(ctx):
    global user_data
    if not user_data:
        await ctx.send("⚠️ No XP data found to reset.")
        return

    for uid in user_data.keys():
        user_data[uid] = {"xp": 0, "level": 1}

    save_data()
    await ctx.send("🧹 All user XP and levels have been reset to default.")

@bot.command(name="resetstory")
@commands.has_permissions(administrator=True)
async def resetstory(ctx):
    global current_chapter
    current_chapter = 0
    save_data()
    await ctx.send("📖 Story progress reset to Chapter 0.")

@bot.command()
async def completequest(ctx, name: str):
    role = discord.utils.get(ctx.guild.roles, name="Event Completed")
    if role:
        await ctx.author.add_roles(role)
        await ctx.send(f"✅ Quest `{name}` completed. You’ve been awarded the **Event Completed** role!")
    else:
        await ctx.send("⚠️ Role `Event Completed` not found.")

        # Optional: unlock global quest once 5 users complete
        if len(completed_users) >= 5 and current_chapter >= 6:
            await ctx.send("🌟 A new faction quest has been unlocked for all players!")

        role = discord.utils.get(ctx.guild.roles, name="Event Completed")
        if role:
            await ctx.author.add_roles(role)

@bot.command()
async def scenario(ctx):
    global current_chapter
    if current_chapter < len(scenario_chapters):
        await ctx.send(scenario_chapters[current_chapter])
        current_chapter += 1
    else:
        await ctx.send("🏁 All chapters complete! You’ve unlocked the **Event Completed** role. 🎉")

        # Try to add role
        role = discord.utils.get(ctx.guild.roles, name="Event Completed")
        if role:
            await ctx.author.add_roles(role)
        else:
            await ctx.send("⚠️ Role not found: `Event Completed`. Please create it in the server settings.")

@bot.command()
async def quest(ctx, name: str):
    name = name.lower()
    if name in side_quests:
        await ctx.send(side_quests[name])
    else:
        await ctx.send(f"❌ Unknown quest: `{name}`. Try one of: {', '.join(side_quests.keys())}")

@bot.command()
async def scenario(ctx):
    global current_chapter
    if current_chapter < len(scenario_chapters):
        await ctx.send(scenario_chapters[current_chapter])
        current_chapter += 1
    else:
        await ctx.send("🏁 **End of Arc** — All chapters complete. Awaiting a new story to begin.")

@bot.command()
async def reset_scenario(ctx):
    global current_chapter
    current_chapter = 0
    await ctx.send("🔄 **Scenario reset!** The arc begins anew...")

@bot.command()
async def simulate(ctx, scenario: str):
    if scenario == "boost":
        await ctx.send("🚀 Boost scenario triggered! XP has been increased.")
        # You can add more logic here to simulate XP gain, role changes, etc.
    elif scenario == "downtime":
        await ctx.send("💤 Downtime scenario triggered. Bot is going idle.")
        # Maybe simulate the bot going offline or pausing features
    else:
        await ctx.send(f"❓ Unknown scenario: `{scenario}`")

@bot.command(name="xplevel")
async def xplevel(ctx):
    user_id = ctx.author.id
    if user_id in user_data:
        lvl = user_data[user_id]["level"]
        xp = user_data[user_id]["xp"]
        await ctx.send(f"{ctx.author.mention}, you're level {lvl} with {xp} XP!")
    else:
        await ctx.send(f"{ctx.author.mention}, you haven't started earning XP yet!")

@bot.command(name="xpboard")
async def xpboard(ctx):
    if not user_data:
        await ctx.send("No XP has been earned yet!")
        return

    top_users = sorted(user_data.items(), key=lambda x: x[1]['xp'], reverse=True)[:5]
    leaderboard_text = "**🏆 Top XP Earners 🏆**\n"
    for idx, (user_id, data) in enumerate(top_users, start=1):
        user = await bot.fetch_user(user_id)
        leaderboard_text += f"{idx}. {user.name} - Level {data['level']} ({data['xp']} XP)\n"

    await ctx.send(leaderboard_text)

@bot.command(name="xphelp")
async def xphelp(ctx):
    help_text = (
        "**📘 XP System Help**\n"
        "Welcome to the custom XP system! Here's how it works:\n\n"
        "• Earn XP by chatting in the server.\n"
        "• Every 5 levels, your XP multiplier increases by 0.30.\n"
        "• Max level is 30.\n"
        "• Use `!level` to check your level.\n"
        "• Use `!xpboard` to see top XP earners (separate from Arcane).\n"
        "• Vote in story scenarios with `!choose` to earn bonus XP.\n"
    )
    await ctx.send(help_text)

# --- Scenario Commands ---
@bot.command(name="scenario")
@commands.has_permissions(administrator=True)
async def scenario(ctx):
    global scenario_active, scenario_choices, user_votes
    if scenario_active:
        await ctx.send("A scenario is already active!")
        return

    scenario_choices = ["stab", "run", "call", "juke"]
    scenario_active = True
    user_votes.clear()

    choices_text = "\n".join([f"{idx+1}. {choice.capitalize()}" for idx, choice in enumerate(scenario_choices)])
    await ctx.send(
        "**🧩 Scenario Begins!**\n"
        "You’re being chased through the woods by a masked killer. You’ve got a phone and a pocketknife.\n"
        "What will you do?\n" +
        choices_text +
        "\n\nType `!choose <option>` to vote!"
    )

@bot.command(name="choose")
async def choose(ctx, *, choice: str):
    global scenario_active, user_votes
    if not scenario_active:
        await ctx.send("There is no active scenario.")
        return

    choice = choice.lower()
    if choice not in scenario_choices:
        await ctx.send(f"❌ Invalid choice. Choose from: {', '.join(scenario_choices)}")
        return

    user_votes[ctx.author.id] = choice
    await ctx.send(f"{ctx.author.mention}, your vote for '{choice}' has been recorded!")

@bot.command(name="end_scenario")
@commands.has_permissions(administrator=True)
async def end_scenario(ctx):
    global scenario_active, scenario_choices, user_votes

    if not scenario_active:
        await ctx.send("No scenario is currently active.")
        return

    if not user_votes:
        await ctx.send("No votes were cast.")
        scenario_active = False
        return

    # Count votes
    tally = defaultdict(int)
    for vote in user_votes.values():
        tally[vote] += 1

    max_votes = max(tally.values())
    winners = [opt for opt, count in tally.items() if count == max_votes]
    winning_choice = winners[0]  # First one if tie

    rewarded_users = [uid for uid, vote in user_votes.items() if vote == winning_choice]
    for uid in rewarded_users:
        if uid not in user_data:
            user_data[uid] = {"xp": 0, "level": 1}

        multiplier = get_multiplier(user_data[uid]["level"])
        gained_xp = int(50 * multiplier)
        user_data[uid]["xp"] += gained_xp

        while user_data[uid]["xp"] >= get_required_xp(user_data[uid]["level"]) and user_data[uid]["level"] < 30:
            user_data[uid]["xp"] -= get_required_xp(user_data[uid]["level"])
            user_data[uid]["level"] += 1

    await ctx.send(
        f"**📊 Scenario Over!**\n"
        f"Winning choice: **{winning_choice.capitalize()}** with {max_votes} votes.\n"
        f"{len(rewarded_users)} participants gained bonus XP!"
    )

    scenario_active = False
    scenario_choices = []
    user_votes.clear()

import os

keep_alive()
bot.run(os.getenv("DISCORD_BOT_TOKEN"))
