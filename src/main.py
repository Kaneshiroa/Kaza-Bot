import discord
import requests
from discord.ext import commands,tasks
from dotenv import load_dotenv
import os
import base64

load_dotenv()

SPOTIFY_CLIENT_ID = os.getenv("SPOTIFY_CLIENT_ID")
SPOTIFY_CLIENT_SECRET = os.getenv("SPOTIFY_CLIENT_SECRET")
SPOTIFY_ARTIST_ID = "30Yst1sldseUyWpZ7ldDIP"
auth_str = f"{SPOTIFY_CLIENT_ID}:{SPOTIFY_CLIENT_SECRET}"
b64_auth_str = base64.b64encode(auth_str.encode()).decode()
headers = {"Authorization": f"Basic {b64_auth_str}"}

last_seen_track = None

CHANNEL_ID_INT = int(os.getenv('ANNOUNCEMENT_CHANNEL_ID'))
MEMBER_ROLE_ID_INT = int(os.getenv('MEMBER_ROLE_ID'))

token = os.getenv('DISCORD_TOKEN')


intents = discord.Intents.default()
intents.message_content = True
intents.members = True

#Ensure correct command prefix and intents are set
bot = commands.Bot(command_prefix=';', intents=intents)
@bot.event
async def on_ready():
    print(f'We have logged in as {bot.user.name} - {bot.user.id}')
    print('------')
    check_new_drop.start()

@bot.event
async def on_member_join(member):
    await member.send(f"Welcome to FGB {member.name}")

@bot.event
async def on_message(message):
    if message.author.bot:
        return

    await bot.process_commands(message)


@bot.command()
async def assign(ctx):
    role_assign = ctx.guild.get_role(MEMBER_ROLE_ID_INT)

    if role_assign is None:
        await ctx.send("Role doesn't exist.")
        return

    if role_assign in ctx.author.roles:
        await ctx.send(f"{ctx.author.mention}, you already have the '{role_assign.name}' role.")
        return

    await ctx.author.add_roles(role_assign)
    await ctx.send(
        f"{ctx.author.mention} has been given the <@&{MEMBER_ROLE_ID_INT}> role.",
        allowed_mentions=discord.AllowedMentions(roles=False)
    )


@bot.command()
async def remove(ctx):
    role_assign = ctx.guild.get_role(MEMBER_ROLE_ID_INT)

    if role_assign is None:
        await ctx.send("Role doesn't exist.")
        return

    if role_assign not in ctx.author.roles:
        await ctx.send(f"{ctx.author.mention}, you don't have the '{role_assign.name}' role.")
        return

    await ctx.author.remove_roles(role_assign)
    await ctx.send(
        f"{ctx.author.mention} has had the <@&{MEMBER_ROLE_ID_INT}> role removed.",
        allowed_mentions=discord.AllowedMentions(roles=False)
    )

@bot.command()
async def reply(ctx):
    await ctx.reply("This is a reply to your message")

@bot.command()
async def poll(ctx, *, msg):
    formatted_msg = msg.title()
    embed = discord.Embed(title="New Poll", description=formatted_msg)
    poll_message = await ctx.send(embed=embed)
    await poll_message.add_reaction("👍")
    await poll_message.add_reaction("👎")


def get_spotify_token():
    # Check for missing credentials
    if not SPOTIFY_CLIENT_ID or not SPOTIFY_CLIENT_SECRET:
        raise Exception("Missing Spotify credentials: SPOTIFY_CLIENT_ID or SPOTIFY_CLIENT_SECRET is not set.")

    auth_str = f"{SPOTIFY_CLIENT_ID}:{SPOTIFY_CLIENT_SECRET}"
    b64_auth_str = base64.b64encode(auth_str.encode()).decode()
    print(f"Requesting Spotify token with client_id={SPOTIFY_CLIENT_ID!r} and client_secret={'*' * len(SPOTIFY_CLIENT_SECRET) if SPOTIFY_CLIENT_SECRET else None}")


    response = requests.post(
        "https://accounts.spotify.com/api/token",
        headers={"Authorization": f"Basic {b64_auth_str}"},
        data={"grant_type": "client_credentials"}
    )
    print(f"Spotify token response status: {response.status_code}")
    print(f"Spotify token response body: {response.text}")
    data = response.json()
    if "access_token" not in data:
        raise Exception(f"Failed to obtain Spotify access token: {data}")
    return data["access_token"]


@tasks.loop(seconds=60)
async def check_new_drop():
    global last_seen_track
    print("Checking Spotify API for new track...")

    token1 = get_spotify_token()
    headers1 = {"Authorization": f"Bearer {token1}"}
    response = requests.get(
        f"https://api.spotify.com/v1/artists/{SPOTIFY_ARTIST_ID}/albums?include_groups=single,album&limit=1",
        headers=headers1
    )
    data = response.json()
    latest_album = data["items"][0]
    track_name = latest_album["name"]
    track_url = latest_album["external_urls"]["spotify"]

    print(f"Latest track: {track_name} - {track_url}")
    print(f"Last seen track: {last_seen_track}")

    if last_seen_track is None or latest_album["id"] != last_seen_track:
        last_seen_track = latest_album["id"]
        channel = await bot.fetch_channel(CHANNEL_ID_INT)
        if channel:
            await channel.send(
                f"<@&{MEMBER_ROLE_ID_INT}> 🎶 **{track_name}** just dropped!\n{track_url}",
                allowed_mentions=discord.AllowedMentions(roles=True)
            )

@bot.command()
@commands.has_role(MEMBER_ROLE_ID_INT)
async def secret(ctx):
    await ctx.send("You have a secret role :)")

@secret.error
async def secret_error(ctx, error):
    if isinstance(error, commands.MissingRole):
        await ctx.send("You do not have permission to do that!")


bot.run(token)