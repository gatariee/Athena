from dotenv import load_dotenv
import os
import discord
import asyncio


from tabulate import tabulate
from discord.ext import commands, tasks

import Athena.agents
import Athena.handler

intents = discord.Intents.default()
intents.message_content = True


load_dotenv()
token = os.getenv("token")
teamserver = os.getenv("teamserver")
http_listener = os.getenv("http_listener")
channel_id = int(os.getenv("channel_id"))
alert_id = int(os.getenv("alert_id"))
active_beacon_sessions = {}

authorized_users = []

class Context(commands.Context):
    async def tick(self, value):
        """Add a reaction to the message based on the provided value."""
        emoji = "\N{WHITE HEAVY CHECK MARK}" if value else "\N{CROSS MARK}"
        try:
            await self.message.add_reaction(emoji)
        except discord.HTTPException:
            pass

    async def send_tick(self):
        """Add a tick reaction to the message."""
        await self.tick(True)

    async def send_cross(self):
        """Add a cross reaction to the message."""
        await self.tick(False)

    async def send(
        self,
        content=None,
        *,
        tts=False,
        embed=None,
        file=None,
        files=None,
        delete_after=None,
        nonce=None,
        allowed_mentions=None,
        reference=None,
        mention_author=None,
        view=None,
    ):
        """Send a message to the channel."""
        if content or embed or file or files:
            return await super().send(
                content=content,
                tts=tts,
                embed=embed,
                file=file,
                files=files,
                delete_after=delete_after,
                nonce=nonce,
                allowed_mentions=allowed_mentions,
                reference=reference,
                mention_author=mention_author,
                view=view,
            )
        else:
            return await super().send("No output returned from command.")


class MyBot(commands.Bot):
    def __init__(self, command_prefix, intents):
        self.agents = []
        self.update_channel = None
        super().__init__(command_prefix, intents=intents, help_command=None)

    @tasks.loop(seconds=15)
    async def beacon_update_task(self):
        new_agents = await self.update_beacons()
        if new_agents and len(new_agents) > len(self.agents):
            new_agent = new_agents[-1]
            embed = discord.Embed(title="⚠️  New Beacon Alert", color=0x00ff00)
            embed.add_field(name="Hostname", value=new_agent['Hostname'], inline=True)
            embed.add_field(name="IP Address", value=new_agent['IP'], inline=True)
            embed.add_field(name="Operating System", value=new_agent['OS'], inline=True)
            embed.add_field(name="Sleep Time", value=f"{new_agent['Sleep']}s", inline=True)
            embed.add_field(name="Jitter", value=f"{new_agent['Jitter']}", inline=True)
            embed.add_field(name="Process ID", value=new_agent['PID'], inline=True)
            embed.set_footer(text="Beacon Information")

            # only auth ppl should be pinged, but can change this to @here if need
            mention_users = ', '.join([f'<@{user_id}>' for user_id in authorized_users])
            mention_text = f"||{mention_users}||"

            print(f"[*] Sending new beacon info to channel #{self.alert_channel}")
            if self.alert_channel:
                await self.alert_channel.send(content=mention_text, embed=embed)
                # send to general as well for debug and im lazy :D
                #await self.update_channel.send(content=mention_text, embed=embed)
            else:
                print(
                    f"[!] Uh oh, looks like we have nowhere to send this message to. (channel_id: {channel_id})"
                )
        self.agents = new_agents

    async def on_ready(self):
        """Notify when the bot is ready and has logged in."""
        print(f"[*] Logged in as {self.user} (ID: {self.user.id})")
        self.update_channel = self.get_channel(channel_id)
        self.alert_channel = self.get_channel(alert_id)
        self.beacon_update_task.start()

    async def get_context(self, message: discord.Message, *, cls=Context):
        """Log message details and get context."""
        print(f"[*] {message.author} (ID: {message.author.id}): {message.content}")
        return await super().get_context(message, cls=cls)

    async def update_beacons(self):
        agents = Athena.agents.update_beacons(http_listener, listener="http")
        return agents


bot = MyBot(command_prefix="!", intents=intents)


@bot.command()
async def help(ctx: Context):
    """Display help menu"""

    help_menu = """
    ```
    Commands (General):
        !help - Display this help menu
        !agents - List active agents (optional args: `desktop` or `mobile` for friendlier-formatting)
        !select <UID> - Select an agent to interact with
    
    Commands (Beacon Sessions):
        !ls - List files in current directory
        !exit - Exit beacon session
    ```
    """
    await ctx.send(help_menu)


@bot.command()
async def agents(ctx: Context, format_type: str = "desktop"):
    """List active agents."""
    if bot.agents:
        table_data = [
            [
                agent["UID"],
                agent["IP"],
                agent["ExtIP"],
                agent["Hostname"],
                agent["Sleep"],
                agent["Jitter"],
                agent["OS"],
                agent["PID"],
            ]
            for agent in bot.agents
        ]

        headers = ["UID", "IP", "ExtIP", "Hostname", "Sleep", "Jitter", "OS", "PPID"]

        msg_data = ""
        msg_data += f"There are currently {len(bot.agents)} active agents.\n\n"

        match format_type:
            case "desktop":
                msg_data += tabulate(
                    table_data, headers, tablefmt="heavy_grid", stralign="center"
                )

            case "mobile":
                for agent in bot.agents:
                    msg_data += f"""[{agent['UID']}] {agent['Hostname']} @ ({agent['IP']}) via PPID {agent['PID']} (Sleep: {agent['Sleep']}, Jitter: {agent['Jitter']})"""
            case _:
                msg_data += "unsupported format type: try `desktop` or `mobile`"

        await ctx.send(f"```\n{msg_data}\n```")
    else:
        await ctx.send("No agents are currently active.")


@bot.command()
async def select(ctx: Context, uid: str):
    """Select an agent to interact with."""
    agent = next((agent for agent in bot.agents if agent["UID"] == uid), None)
    if agent:
        initial_msg = await ctx.send(f"Selected {agent['Hostname']} ({agent['IP']})")
        confirm_msg = await ctx.send("Start beacon session?")

        await confirm_msg.add_reaction("\N{WHITE HEAVY CHECK MARK}")
        await confirm_msg.add_reaction("\N{CROSS MARK}")

        def check(reaction, user):
            return (
                user == ctx.author
                and str(reaction.emoji)
                in ["\N{WHITE HEAVY CHECK MARK}", "\N{CROSS MARK}"]
                and reaction.message.id == confirm_msg.id
            )

        try:
            reaction, user = await bot.wait_for(
                "reaction_add", timeout=10.0, check=check
            )
            print(f"[*] Reaction received: {reaction.emoji}")
            print(f"[*] User: {user}")
            if str(reaction.emoji) == "\N{WHITE HEAVY CHECK MARK}":
                thread_name = f"Beacon session with {agent['Hostname']} ({agent['IP']}) | Operator: {ctx.author}"
                print(f"[*] Starting beacon session: {thread_name}")
                try:
                    thread = await initial_msg.create_thread(name=thread_name)
                    active_beacon_sessions[thread.id] = uid
                    await ctx.send(f"Beacon session started in {thread.mention}")

                except discord.errors.HTTPException:
                    await ctx.send("Failed to start beacon session.")
            else:
                await ctx.send("Beacon session cancelled.")
        except asyncio.TimeoutError:
            await ctx.send("No reaction within 10 seconds.")
    else:
        await ctx.send(f"Could not find agent with UID {uid}")


@bot.event
async def on_message(message: discord.message.Message):
    if message.author == bot.user:  # are you yourself?
        return

    if (message.author.id not in authorized_users) and (message.content.startswith("!")):
        await message.channel.send("You are not authorized to use this bot.")
        return

    # everything here is for beacon sessions via threads
    if message.channel.id in active_beacon_sessions:
        uid = active_beacon_sessions[message.channel.id]
        agent = next((agent for agent in bot.agents if agent["UID"] == uid), None)

        if message.content == "!exit":
            await message.channel.send("Exiting beacon session...")
            await message.channel.delete()
            del active_beacon_sessions[message.channel.id]
            return
        
        if message.content.startswith("!"):
            content = message.content[1:]
            ok, res = await Athena.handler.handle_command(
                content,
                uid,
                message,
                http_listener,
                int(agent["Sleep"]),
                agent["Hostname"],
            )
            if ok:
                await message.channel.send(res)
            else:
                pass

    await bot.process_commands(message)


async def cleanup():
    print("[*] Cleaning up...")
    bot.beacon_update_task.cancel()
    for thread_id in active_beacon_sessions:
        thread = bot.get_channel(thread_id)
        if thread:
            await thread.delete()
    print("[*] Done.")


if __name__ == "__main__":
    try:
        if token:
            bot.run(token)
        else:
            print(
                "Error: Bot token not found. Please set the `token` environment variable."
            )
    except KeyboardInterrupt:
        asyncio.run(cleanup())
