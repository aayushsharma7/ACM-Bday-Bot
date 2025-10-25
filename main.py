import discord
from discord.ext import commands, tasks
import dotenv
import logging
import os
from dotenv import load_dotenv
import asyncio
from itertools import cycle
import json
import re
from datetime import datetime, timedelta
import discord.ui

from keep import keep_alive
load_dotenv()
token = os.getenv('DISCORD_TOKEN')
handler = logging.FileHandler(filename='discord.log', encoding='utf-8', mode='w') 
keep_alive()

bot = commands.Bot(command_prefix="-", intents=discord.Intents.all()) 
status=cycle(["🎂 Happy Birthday! 🎂"]) 

BIRTHDAYS_FILE = 'birthdays.json'
CHANNEL_ID = 1431731505671176272

def load_birthdays():
    try:
        with open(BIRTHDAYS_FILE, 'r') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}

def save_birthdays(data):
    with open(BIRTHDAYS_FILE, 'w') as f:
        json.dump(data, f, indent=4)

@bot.command(name='sendbday') 
async def send_registration_message(ctx):
    if ctx.channel.id != CHANNEL_ID:
        await ctx.send("Please run this command in the designated announcements channel.", ephemeral=True)
        return

    embed = discord.Embed(
        title="🎂 Enter Your Birthday! 🎂",
        description=(
            "Click the button below to enter your birthday!\n\n"
            "The bot will send you a DM\n\n"
        ),
        color=discord.Color.blue()
    )
    embed.set_footer(text="ACM Birthdays")
    await ctx.send(embed=embed, view=RegisterView(bot))
    await ctx.message.delete() #delete og msg

class RegisterView(discord.ui.View):
    def __init__(self, bot):
        # Pass the bot instance so we can access its methods (like fetch_user)
        super().__init__(timeout=None)
        self.bot = bot
        
    @discord.ui.button(label="Click to Register Birthday", style=discord.ButtonStyle.primary, custom_id="register_bday")
    async def register_button_callback(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Acknowledge the interaction immediately to prevent the 'Interaction Failed' error
        await interaction.response.defer(ephemeral=True) 
        user = interaction.user
        
        try:
            # 1. Send the Initial DM
            await user.send(
                "🎉 **Welcome to the ACM Birthdays!**\n"
                "Please reply to this message with your birthday in the **MM-DD** format (e.g., **10-26** for October 26th)."
            )
            
            # 2. Wait for the user's next message in the DM
            def check(m):
                # Ensure the message is from the user, in a DM, and not empty
                return m.author.id == user.id and m.channel.type == discord.ChannelType.private and m.content
            
            # Wait for up to 60 seconds for the user to reply
            try:
                dm_response = await self.bot.wait_for('message', check=check, timeout=60.0)
            except asyncio.TimeoutError:
                await user.send("⏰ Time's up! Registration failed due to timeout. Please click the button in the server again to start over.")
                return

            bday = dm_response.content.strip()

            # 3. Validation
            if not re.match(r'^(0[1-9]|1[0-2])-(0[1-9]|[1-2][0-9]|3[0-1])$', bday):
                await user.send(
                    f"🛑 Invalid format: `{bday}`. Please restart the process and use the **MM-DD** format (e.g., 03-25)."
                )
                return

            # 4. Save to JSON
            data = load_birthdays()
            data[str(user.id)] = bday
            save_birthdays(data)
            
            # 5. Confirmation
            await user.send(
                f"✅ Success! Your birthday, **{bday}**, has been saved.\n"
            )
            
            # Check for immediate birthday (just like the previous fix)
            today_mm_dd = datetime.now().strftime("%m-%d")
            if bday == today_mm_dd:
                channel = self.bot.get_channel(CHANNEL_ID)
                if channel:
                    message = (
                        f"🎂🎉 **Happy Birthday** {user.mention}!"
                    )
                    await channel.send(message)

        except discord.Forbidden:
            # If the bot cannot DM the user (e.g., they have DMs disabled)
            await interaction.followup.send(
                "❌ I couldn't send you a DM. Please check your privacy settings and ensure DMs are enabled for this server.",
                ephemeral=True
            )
        except Exception as e:
            print(f"Error during birthday registration process: {e}")
            await interaction.followup.send(
                "An unexpected error occurred during registration. Please try again later.",
                ephemeral=True
            )

@tasks.loop(seconds=10)
async def change_status():
    await bot.change_presence(activity=discord.Game(next(status))) 

@tasks.loop(hours=24)
async def birthday_checker():
    today_mm_dd = datetime.now().strftime("%m-%d")
    birthdays = load_birthdays()
    channel = bot.get_channel(CHANNEL_ID)
    
    if not channel:
        print(f"ERROR: Target channel ID {CHANNEL_ID} not found.")
        return
    for user_id, bday in birthdays.items():
        if bday == today_mm_dd:
            try:
                user = await bot.fetch_user(int(user_id)) 
                message = (
                    f"🎂🎉 **Happy Birthday** {user.mention}!"
                )
                await channel.send(message)
            except discord.NotFound:
                print(f"Warning: User ID {user_id} in JSON not found in server.")
            except Exception as e:
                print(f"Error processing birthday for {user_id}: {e}")

@bot.event
async def on_ready():
    print(f"Lesgoo, {bot.user.name}")
    change_status.start()

@bot.event
async def on_message(message):
    if message.author == bot.user:
        return 
    if bot.user.mentioned_in(message):
        await message.channel.send("bolo")
    await bot.process_commands(message)

@bot.remove_command("help")
@bot.command(name='mybday')
async def set_birthday(ctx, bday: str):
    #Format must be MM-DD (e.g., 03-25).
    if not re.match(r'^(0[1-9]|1[0-2])-(0[1-9]|[1-2][0-9]|3[0-1])$', bday):
        await ctx.send(
            f"{ctx.author.mention} 🛑 Invalid format! Please enter your birthday as **MM-DD** (e.g., 03-25 for March 25th)."
        )
        return
    #storing
    data = load_birthdays()
    data[str(ctx.author.id)] = bday
    save_birthdays(data)
    #check if today
    today_mm_dd = datetime.now().strftime("%m-%d")
    if bday == today_mm_dd:
        channel = bot.get_channel(CHANNEL_ID)
        if channel:
            message = (
                f"🎂 **Happy Birthday** {ctx.author.mention}!"
            )
            await channel.send(message)
            await ctx.send(
                f"🎉 Happy Birthday, {ctx.author.mention}! Your birthday, **{bday}**, has been registered, and we just sent the official wish to the general channel!"
            )
            return
        else:
             print(f"ERROR: Could not find channel with ID {CHANNEL_ID} for immediate wish.")
    await ctx.send(
        f"🎉 Got it, {ctx.author.mention}! Your birthday, **{bday}**, has been saved. We'll celebrate when the day arrives!"
    )

@bot.command()
async def help(ctx):
    hel=discord.Embed(title="Help", description="All commands available are listed here", color=discord.Color.random())
    hel.set_author(name="ACM Birthdays", icon_url=bot.user.avatar)
    hel.add_field(name="hi",value="Says Hi! and mentions the author", inline=False)
    hel.add_field(name="mybday <MM-DD>", value="Registers your birthday (e.g., `-mybday 12-31`).", inline=False)
    await ctx.send(embed=hel)

@bot.command()
async def hi(ctx):
    await ctx.send(f"Hi!, {ctx.author.mention}")

bot.run(token, log_handler=handler, log_level=logging.DEBUG)