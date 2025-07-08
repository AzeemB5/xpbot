import discord
from discord.ext import commands
from collections import defaultdict
import random

intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix="!", intents=intents)

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

bot.run(os.getenv("MTM5MTc1OTAzNDA4NzkwMzMyMg.GgZl2m.Mosjbrj7TaeUSYYh89f9WKUXo9zzftkier6PWY"))
