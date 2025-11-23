import discord
from discord.ext import commands
from discord import app_commands, ui, Interaction
import os
import json
import math

class Area:
    def __init__(self, name, food, wood, stone, steel, gold, population, port, fort, city):
        self.name = name
        self.growth = {"food": food, "wood": wood, "stone": stone, "steel": steel, "gold": gold}
        self.population = population
        self.port = port
        self.fort = fort
        self.city = city
        self.owner = None
    
    def weekly_addition(self, resources):
        for resource in self.growth:    # only cumulative resources
            resources[resource] += self.growth[resource]
        return resources
    
    def resources(self):
        resources = self.growth.copy()
        resources.update({"population": self.population, "port": self.port, "fort": self.fort, "city": self.city})
        return resources

    def __str__(self):
        return self.name
    
    def __repr__(self):
        return self.name

class Player:
    def __init__(self, name: str, username: str, channel: discord.TextChannel, raven_limit: int):
        self.name = name
        self.resources = {"food": 0, "wood": 0, "stone": 0, "steel": 0, "gold": 0}
        self.army = {"men_at_arms": 0, "cavalry": 0, "archers": 0, "siege_weapons": 0, "fleet": 0, "war_galley": 0}
        self.seals = set()
        self.areas = set()
        self.username = username
        self.channel = channel
        self.raven_limit = raven_limit
        self.ravens_left = raven_limit
    
    def __str__(self):
        return self.name

    def weekly_addition(self):
        self.ravens_left = self.raven_limit     # refill ravens
        for area in self.areas:
            self.resources = area.weekly_addition(self.resources)
        self.resources["food"] -= self.army["men_at_arms"] + 2*self.army["cavalry"] + self.army["archers"]
    
    def port(self):
        ports = 0
        for area in self.areas:
            ports += area.port
        return ports
    def fort(self):
        forts = 0
        for area in self.areas:
            forts += area.fort
        return forts
    def population(self):
        population = 0
        for area in self.areas:
            population += area.population
        for troop in self.army:
            population -= self.army[troop]
        return max(0,population)
    def city(self):
        cities = 0
        for area in self.areas:
            cities += area.city
        return cities

    
class Storage:
    def __init__(self, players):
        self.players = {name: Player(name, username, channel, raven_limit) for (name, username, channel, raven_limit) in players}
        self.areas = {}

    def to_dict(self):
        return {
            player.name: {
                "resources": player.resources,
                "areas": [area.name for area in player.areas],
                "army": player.army,
                "seals": list(player.seals),
            } for player in self.players.values()
        }
    
    def from_dict(self, data):
        players = {}
        for player_name, info in data.items():
            p = self.players[player_name]

            p.resources = info.get("resources", {})
            p.army = info.get("army", {})
            area_names = info.get("areas", [])
            p.seals = set(info.get("seals", []))
            for area_name in area_names:
                if area_name in self.areas:
                    p.areas.add(self.areas[area_name])
                    self.areas[area_name].owner = p
            players[player_name] = p
        self.players = players


DEFAULT_RAVEN = 1432351712160518224
players=[
    ("ADMIN", "smazzz_", 1432351712160518224, 10000),
    ("flo", "ftomlin", 1432352198045597777, 3),
    ("rico", "thiccboiseal", 1432352106819616873, 3), 
    ("toby", "tob33", 1432351866183749703, 4), 
    ("tom", "tom7061", 1432351681030389790, 3), 
    ("connor", "c.sissle", 1432352340790345828, 3),
    ("callum", "callum300524", 1438155998677434460, 3), 
    ("dom", "?", 0, 3), 
    ("ethan", "vocalpaladin507", 1433834384288645210, 3), 
    ("olive", "shortolive", 1433834460046163988, 3),
    ("lucas", "quacamole.", 1433834445705707520, 3)
]

info = Storage(players=players)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
with open(os.path.join(BASE_DIR,"resources.csv")) as file:
    for line in file.readlines():
        name,food,wood,stone,steel,gold,population,port,fort,city = line.split(",")
        info.areas[name] = Area(name,int(food),int(wood),int(stone),int(steel),int(gold),int(population),int(port),int(fort),int(city))

def store_info(info: Storage):
    filename = os.path.join(BASE_DIR,"values.csv")
    with open(filename, "w") as f:
        json.dump(info.to_dict(), f, indent=2)

def retrieve_info(info: Storage):
    filename = os.path.join(BASE_DIR,"values.csv")
    if not os.path.exists(filename):
        store_info(info)
    with open(filename, "r") as f:
        data = json.load(f)
    info.from_dict(data)

def username_to_name(username: str):
    for player in players:
        if player[1] == username:
            return player[0]

intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents)
retrieve_info(info=info)

# ------------------------------------
# Slash Commands
# ------------------------------------
@bot.tree.error
async def on_app_command_error(interaction: discord.Interaction, error: app_commands.AppCommandError):
    if isinstance(error, app_commands.errors.MissingRole):
        await interaction.response.send_message("🚫 You don’t have permission to use this command.", ephemeral=True)
    else:
        raise error

@app_commands.checks.has_role("BOT-Control")
@bot.tree.command(name="players", description="Show player profiles")
async def players_cmd(interaction: discord.Interaction):
    retrieve_info(info=info)
    await interaction.response.send_message(f"Player profiles\n{list(info.players.keys())}")

@bot.tree.command(name="resources", description="Show your current resources")
async def resources_cmd(interaction: discord.Interaction, player_name: str | None = None):
    if player_name == None:
        player_name = username_to_name(interaction.user.name)
    else:
        if not any(role.name == "BOT-Control" for role in interaction.user.roles):
            await interaction.response.send_message("🚫 You don’t have permission to use this command.", ephemeral=True)
            return
    if player_name not in info.players:
        await interaction.response.send_message("❌ That is not a valid user, use /players to see them all.")
        return
    p = info.players[player_name]
    res = p.resources.copy()
    res.update({"port": p.port(), "fort": p.fort(), "population": p.population(), "city": p.city()})
    formatted = "\n".join(f"**{k.title()}**: {v}" for k, v in res.items())
    await interaction.response.send_message(f"📦 **{player_name}'s Resources:**\n{formatted}")


@bot.tree.command(name="areas", description="Show your controlled areas")
async def areas_cmd(interaction: discord.Interaction, player_name: str | None = None):
    if player_name == None:
        player_name = username_to_name(interaction.user.name)
    else:
        if not any(role.name == "BOT-Control" for role in interaction.user.roles):
            await interaction.response.send_message("🚫 You don’t have permission to use this command.", ephemeral=True)
            return
    if player_name not in info.players:
        await interaction.response.send_message("❌ That is not a valid user, use /players to see them all.")
        return
    area_list = ", ".join(a.name for a in info.players[player_name].areas) or "None"
    await interaction.response.send_message(f"🏰 **{player_name}'s Areas:** {area_list}")

@bot.tree.command(name="army", description="Show your army amounts")
async def army_cmd(interaction: discord.Interaction, player_name: str | None = None):
    if player_name == None:
        player_name = username_to_name(interaction.user.name)
    else:
        if not any(role.name == "BOT-Control" for role in interaction.user.roles):
            await interaction.response.send_message("🚫 You don’t have permission to use this command.", ephemeral=True)
            return
    if player_name not in info.players:
        await interaction.response.send_message("❌ That is not a valid user, use /players to see them all.")
        return
    army = info.players[player_name].army
    formatted = "\n".join(f"**{k.title()}**: {v}" for k, v in army.items())
    await interaction.response.send_message(f"⚔️ **{player_name}'s Army:**\n{formatted}")

@app_commands.checks.has_role("BOT-Control")
@bot.tree.command(name="addarea", description="Claim an area")
@app_commands.describe(area_name="The name of the area to claim")
async def addarea(interaction: discord.Interaction, player_name: str, area_name: str):
    area_name = area_name.capitalize()
    if player_name not in info.players:
        await interaction.response.send_message("❌ That is not a valid user, use /players to see them all.")
        return
    if area_name not in info.areas:
        await interaction.response.send_message("❌ That area doesn't exist.")
        return
    area = info.areas[area_name]
    info.players[player_name].areas.add(area)
    previous_owner = area.owner
    message = f"✅ {player_name} has claimed the area **{area_name}**!"
    if not (previous_owner is None):
        area.owner.areas.remove(area)
        message += f" It has been stolen from {previous_owner.name}!!"
    area.owner = info.players[player_name]
    store_info(info=info)
    await interaction.response.send_message(message)

@app_commands.checks.has_role("BOT-Control")
@bot.tree.command(name="removearea", description="Lose an area to a non-player")
@app_commands.describe(area_name="The name of the area to lose")
async def removearea(interaction: discord.Interaction, player_name: str, area_name: str):
    area_name = area_name.capitalize()
    if player_name not in info.players:
        await interaction.response.send_message("❌ That is not a valid user, use /players to see them all.")
        return
    if area_name not in info.areas:
        await interaction.response.send_message("❌ That area doesn't exist.")
        return
    if info.areas[area_name].owner != info.players[player_name]:
        await interaction.response.send_message("❌ That player does not seem to own that area.")
        return
    info.areas[area_name].owner = None
    info.players[player_name].areas.remove(info.areas[area_name])
    store_info(info=info)
    await interaction.response.send_message(f"✅ {player_name} has lost the area **{area_name}**!")

@app_commands.checks.has_role("BOT-Control")
@bot.tree.command(name="weekly_update", description="Apply weekly resource growth from your areas")
async def weekly_update(interaction: discord.Interaction):
    for player_name in info.players:
        info.players[player_name].weekly_addition()
    store_info(info=info)
    await interaction.response.send_message(f"📈 Weekly resources added!")


## RAVENS ##
@app_commands.checks.has_role("BOT-Control")
@bot.tree.command(name="add_raven_seal", description="Give player a seal of a house")
async def add_raven_seal(interaction: discord.Interaction, player_name: str, house_name: str):
    if player_name not in info.players:
        await interaction.response.send_message("❌ That is not a valid user, use /players to see them all.")
        return
    if house_name not in info.areas:
        await interaction.response.send_message("❌ That house doesn't exist.")
        return
    player = info.players[player_name]
    player.seals.add(house_name)
    store_info(info=info)
    await interaction.response.send_message(f"💮 {player_name.capitalize()} has been given the {house_name} seal!")

@app_commands.checks.has_role("BOT-Control")
@bot.tree.command(name="remove_raven_seal", description="Give player a seal of a house")
async def remove_raven_seal(interaction: discord.Interaction, player_name: str, house_name: str):
    if player_name not in info.players:
        await interaction.response.send_message("❌ That is not a valid user, use /players to see them all.")
        return
    if house_name not in info.areas:
        await interaction.response.send_message("❌ That house doesn't exist.")
        return
    player = info.players[player_name]
    player.seals.remove(house_name)
    store_info(info=info)
    await interaction.response.send_message(f"💮 {player_name.capitalize()} has lost the {house_name} seal!")

class RavenModal(ui.Modal, title="Compose Your Raven"):
    def __init__(self, recipient: str, sender_name: str, seal: str | None):
        super().__init__(title=f"Raven to {recipient.title()}")
        self.recipient = recipient
        self.sender_name = sender_name
        self.seal = None if seal == "no seal" else seal

        if self.recipient == "Choose NPC":
            self.recipient = ui.TextInput(
                label="Recipient (NPC name)",
                placeholder="Type the NPC's name",
                required=True,
                max_length=100,
                style=discord.TextStyle.short
            )
            self.add_item(self.recipient)
        self.message = ui.TextInput(
            label="Your message",
            style=discord.TextStyle.paragraph,
            placeholder="Type your message here...",
            required=True,
            max_length=2000
        )
        self.add_item(self.message)

    async def on_submit(self, interaction: Interaction):
        await interaction.response.defer(ephemeral=True)
        player_name = self.recipient
        if type(player_name) == ui.TextInput:
            player_name = player_name.value
        message = self.message.value
        seal = f"the **{self.seal.title()} seal**" if self.seal else "no seal"
        destination = None
        player_sender = info.players[username_to_name(interaction.user.name)]
        if player_sender.ravens_left <= 0:
            sender_destination = interaction.client.get_channel(info.players[username_to_name(interaction.user.name)].channel)
            await sender_destination.send(f"❌ You have send all your ravens this week.\nYour message was:\n{message}")
            return
        if self.recipient == "Everyone":
            if player_sender.ravens_left != player_sender.raven_limit and player_sender.name != "ADMIN":
                sender_destination = interaction.client.get_channel(info.players[username_to_name(interaction.user.name)].channel)
                await sender_destination.send(f"❌ You can only send a raven to ALL if no other ravens have been sent this week.\nYour message was:\n{message}")
                return
            for name in info.players:
                if name != "ADMIN":
                    destination = interaction.client.get_channel(info.players[name].channel)
                    await destination.send(f"🪶 **Raven to {name.title()}, sealed with {seal}:**\n{message}")
            if player_sender.name != "ADMIN":
                player_sender.ravens_left = 0
        elif player_name in info.players:
            destination = interaction.client.get_channel(info.players[player_name].channel)
            await destination.send(f"🪶 **Raven to {player_name.title()}, sealed with {seal}:**\n{message}")
        destination = interaction.client.get_channel(DEFAULT_RAVEN)   # all ravens go to Charlie too
        await destination.send(f"🪶 **Raven to {player_name.title()}, sealed with {seal} (from {self.sender_name}):**\n{message}")
        sender_destination = interaction.client.get_channel(info.players[username_to_name(interaction.user.name)].channel)
        if self.recipient != "Everyone":
            player_sender.ravens_left -= 1
        await sender_destination.send(f"✅ Raven sent to {player_name.title()} (seal {seal}). You have {player_sender.ravens_left} Ravens left.\nYour message was:\n{message}")

class RavenRecipientView(ui.View):
    def __init__(self, players: list[str]):
        super().__init__(timeout=60)
        options = [
            discord.SelectOption(label=name.title(), value=name)
            for name in players
        ]
        self.add_item(RavenRecipientSelect(options))

class RavenRecipientSelect(ui.Select):
    def __init__(self, options):
        super().__init__(
            placeholder="Choose the recipient of your raven...",
            min_values=1,
            max_values=1,
            options=options
        )

    async def callback(self, interaction: Interaction):
        recipient = self.values[0]
        sender_name = next((n for n, p in info.players.items() if p.username == interaction.user.name), None)
        if not sender_name:
            await interaction.response.send_message("❌ You are not registered as a player.", ephemeral=True)
            return
        view = RavenSealView(sender_name, recipient)
        if len(info.players[sender_name].seals) == 0:
            await interaction.response.send_message("", view=view, ephemeral=True)
        else:
            await interaction.response.send_message("💮 Choose a seal to affix (if any):", view=view, ephemeral=True)

class RavenSealView(ui.View):
    def __init__(self, sender_name: str, recipient: str):
        super().__init__(timeout=60)
        self.sender_name = sender_name
        self.recipient = recipient
        self.selected_seal = None

        player = info.players[sender_name]
        if player.seals:
            options = [discord.SelectOption(label=seal.title(), value=seal) for seal in player.seals]
            options.append(discord.SelectOption(label="No seal", value="no seal"))
            self.add_item(RavenSealSelect(options))
        else:
            self.selected_seal = "no seal"

        self.add_item(RavenSealConfirmButton(recipient))

class RavenSealSelect(ui.Select):
    def __init__(self, options):
        super().__init__(
            placeholder="Choose a seal to affix to your raven...",
            min_values=1,
            max_values=1,
            options=options
        )

    async def callback(self, interaction: Interaction):
        view: RavenSealView = self.view
        view.selected_seal = self.values[0]
        await interaction.response.defer(ephemeral=True)

class RavenSealConfirmButton(ui.Button):
    def __init__(self, recipient):
        super().__init__(label=f"Write your raven to {recipient}...", style=discord.ButtonStyle.primary)

    async def callback(self, interaction: Interaction):
        view: RavenSealView = self.view
        await interaction.response.send_modal(RavenModal(view.recipient, view.sender_name, view.selected_seal))

@bot.tree.command(name="raven", description="Send a raven to another character.")
async def raven(interaction: Interaction):
    player_name = username_to_name(interaction.user.name)
    player = info.players[player_name]
    if player.ravens_left <= 0:
        await interaction.response.send_message("❌ You have no Ravens left this week :(", ephemeral=True)
        return
    players = list(info.players.keys())+["Choose NPC", "Everyone"]
    view = RavenRecipientView(players)
    await interaction.response.send_message(f"🪶 You have {player.ravens_left} Ravens remaining.\nChoose who you wish to send your raven to:",view=view,ephemeral=True)

@bot.tree.command(name="raven_refund", description="Send a raven to another character.")
@app_commands.describe(player_name="Which player is being refunded a Raven?")
async def raven_refund(interaction: Interaction, player_name: str):
    if player_name not in info.players:
        await interaction.response.send_message("❌ Invalid player name.", ephemeral=True)
        return
    player = info.players[player_name]
    player.ravens_left += 1
    await interaction.response.send_message(f"🪶 {player_name.capitalize()} now up to {player.ravens_left} Ravens",ephemeral=True)


## BUY TROOPS ##
class ArmyView(ui.View):
    def __init__(self, player_name: str):
        super().__init__(timeout=60)
        self.player_name = player_name
        self.num_selected = None
        self.troop_selected = None

        self.add_item(ArmyNumberSelect())
        self.add_item(ArmyTypeSelect())

    async def on_timeout(self):
        for item in self.children:
            item.disabled = True

class ArmyBuyView(ArmyView):
    def __init__(self, player_name: str):
        super().__init__(player_name)
        self.confirm_button = ArmyBuyConfirmButton()
        self.add_item(self.confirm_button)

class ArmyGiveView(ArmyView):
    def __init__(self, player_name: str):
        super().__init__(player_name)
        self.confirm_button = ArmyGiveConfirmButton()
        self.add_item(self.confirm_button)

class ArmySellView(ArmyView):
    def __init__(self, player_name: str):
        super().__init__(player_name)
        self.confirm_button = ArmySellConfirmButton()
        self.add_item(self.confirm_button)

class ArmyRefundView(ArmyView):
    def __init__(self, player_name: str):
        super().__init__(player_name)
        self.confirm_button = ArmyRefundConfirmButton()
        self.add_item(self.confirm_button)

class ArmyNumberSelect(ui.Select):
    def __init__(self):
        options = [
            discord.SelectOption(label=str(i), value=str(i))
            for i in range(1, 10)
        ]
        super().__init__(
            placeholder="Choose how many units...",
            min_values=1,
            max_values=1,
            options=options
        )

    async def callback(self, interaction: Interaction):
        view: ArmyBuyView = self.view
        view.num_selected = int(self.values[0])
        await interaction.response.defer(ephemeral=True)

class ArmyTypeSelect(ui.Select):
    def __init__(self):
        options = [
            discord.SelectOption(label="Men at Arms", value="men_at_arms", description="Cost: 1 food"),
            discord.SelectOption(label="Archers", value="archers", description="Cost: 1 food, 1 wood"),
            discord.SelectOption(label="Cavalry", value="cavalry", description="Cost: 2 food, 1 steel"),
            discord.SelectOption(label="Siege Weapons", value="siege_weapons", description="Cost: 10 wood, 10 stone, 5 steel"),
            discord.SelectOption(label="Fleet of Ships", value="fleet", description="Cost: 20 wood, 10 steel"),
            discord.SelectOption(label="War Galley", value="war_galley", description="Cost: 10 wood, 10 steel"),
        ]
        super().__init__(
            placeholder="Choose which troop type...",
            min_values=1,
            max_values=1,
            options=options
        )

    async def callback(self, interaction: Interaction):
        view: ArmyBuyView = self.view
        view.troop_selected = self.values[0]
        await interaction.response.defer(ephemeral=True)

class ArmyBuyConfirmButton(ui.Button):
    def __init__(self):
        super().__init__(label="Confirm Purchase", style=discord.ButtonStyle.success)

    async def callback(self, interaction: Interaction):
        view: ArmyBuyView = self.view
        if not view.num_selected or not view.troop_selected:
            await interaction.response.send_message("⚠️ Please select **both** the number of units and troop type before confirming.",ephemeral=True)
            return
        if info.players[view.player_name].population() < view.num_selected:
            await interaction.response.send_message("⚠️ Player lacks sufficient population")
            return

        resources = info.players[view.player_name].resources
        if view.troop_selected == "men_at_arms":
            if resources["food"] >= view.num_selected:
                resources["food"]-=view.num_selected
            else:
                await interaction.response.send_message("⚠️ Player lacks sufficient resources")
                return
        elif view.troop_selected == "archers":
            if resources["food"] >= view.num_selected and resources["wood"] >= view.num_selected:
                resources["food"]-=view.num_selected
                resources["wood"]-=view.num_selected
            else:
                await interaction.response.send_message("⚠️ Player lacks sufficient resources")
                return
        elif view.troop_selected == "cavalry":
            if resources["food"] >= view.num_selected*2 and resources["steel"] >= view.num_selected:
                resources["food"]-= view.num_selected*2
                resources["steel"]-= view.num_selected
            else:
                await interaction.response.send_message("⚠️ Player lacks sufficient resources")
                return
        elif view.troop_selected == "siege_weapons":
            if resources["steel"] >= view.num_selected*5 and resources["wood"] >= view.num_selected*10 and resources["stone"] >= view.num_selected*10:
                resources["steel"]-= view.num_selected*5
                resources["wood"]-= view.num_selected*10
                resources["stone"]-= view.num_selected*10
            else:
                await interaction.response.send_message("⚠️ Player lacks sufficient resources")
                return
        elif view.troop_selected == "fleet":
            if resources["steel"] >= view.num_selected*10 and resources["wood"] >= view.num_selected*20:
                resources["steel"]-= view.num_selected*10
                resources["wood"]-= view.num_selected*20
            else:
                await interaction.response.send_message("⚠️ Player lacks sufficient resources")
                return
        elif view.troop_selected == "war_galley":
            if resources["steel"] >= view.num_selected*10 and resources["wood"] >= view.num_selected*10:
                resources["steel"]-= view.num_selected*10
                resources["wood"]-= view.num_selected*10
            else:
                await interaction.response.send_message("⚠️ Player lacks sufficient resources")
                return
        info.players[view.player_name].army[view.troop_selected] += view.num_selected
        await interaction.response.send_message(
            f"🛡️ **{view.player_name.title()}** purchased **{view.num_selected} {view.troop_selected.title()}** units!",
            ephemeral=False)
        self.disabled = True
        store_info(info=info)

class ArmyRefundConfirmButton(ui.Button):
    def __init__(self):
        super().__init__(label="Confirm Refund", style=discord.ButtonStyle.success)

    async def callback(self, interaction: Interaction):
        view: ArmySellView = self.view
        if not view.num_selected or not view.troop_selected:
            await interaction.response.send_message("⚠️ Please select **both** the number of units and troop type before confirming.",ephemeral=True)
            return
        info.players[view.player_name].army[view.troop_selected] = max(0, info.players[view.player_name].army[view.troop_selected]-view.num_selected)
        if view.troop_selected == "men_at_arms":
            info.players[view.player_name].resources["food"]+=view.num_selected
        elif view.troop_selected == "archers":
            info.players[view.player_name].resources["food"]+=view.num_selected
            info.players[view.player_name].resources["wood"]+=view.num_selected
        elif view.troop_selected == "cavalry":
            info.players[view.player_name].resources["food"]+=view.num_selected*2
            info.players[view.player_name].resources["steel"]+=view.num_selected
        elif view.troop_selected == "siege_weapons":
            info.players[view.player_name].resources["stone"]+=view.num_selected*10
            info.players[view.player_name].resources["wood"]+=view.num_selected*10
            info.players[view.player_name].resources["steel"]+=view.num_selected*5
        elif view.troop_selected == "fleet":
            info.players[view.player_name].resources["wood"]+=view.num_selected*20
            info.players[view.player_name].resources["steel"]+=view.num_selected*10
        elif view.troop_selected == "war_galley":
            info.players[view.player_name].resources["wood"]+=view.num_selected*10
            info.players[view.player_name].resources["steel"]+=view.num_selected*10
        await interaction.response.send_message(
            f"🛡️ **{view.player_name.title()}** refunded **{view.num_selected} {view.troop_selected.title()}** units!",
            ephemeral=False)
        self.disabled = True
        store_info(info=info)

class ArmySellConfirmButton(ui.Button):
    def __init__(self):
        super().__init__(label="Confirm Sale", style=discord.ButtonStyle.success)

    async def callback(self, interaction: Interaction):
        view: ArmySellView = self.view
        if not view.num_selected or not view.troop_selected:
            await interaction.response.send_message("⚠️ Please select **both** the number of units and troop type before confirming.",ephemeral=True)
            return
        info.players[view.player_name].army[view.troop_selected] = max(0, info.players[view.player_name].army[view.troop_selected]-view.num_selected)
        await interaction.response.send_message(
            f"🛡️ **{view.player_name.title()}** sold **{view.num_selected} {view.troop_selected.title()}** units!",
            ephemeral=False)
        self.disabled = True
        store_info(info=info)

class ArmyGiveConfirmButton(ui.Button):
    def __init__(self):
        super().__init__(label="Confirm Gift", style=discord.ButtonStyle.success)

    async def callback(self, interaction: Interaction):
        view: ArmyGiveView = self.view
        if not view.num_selected or not view.troop_selected:
            await interaction.response.send_message("⚠️ Please select **both** the number of units and troop type before confirming.",ephemeral=True)
            return
        info.players[view.player_name].army[view.troop_selected] += view.num_selected
        await interaction.response.send_message(
            f"🛡️ **{view.player_name.title()}** gained **{view.num_selected} {view.troop_selected.title()}** units!",
            ephemeral=False)
        self.disabled = True
        store_info(info=info)

@app_commands.checks.has_role("BOT-Control")
@bot.tree.command(name="armybuy", description="Purchase army resources.")
@app_commands.describe(player_name="Which player is buying troops?")
async def armybuy(interaction: Interaction, player_name: str):
    if player_name not in info.players:
        await interaction.response.send_message("❌ Invalid player name.", ephemeral=True)
        return
    view = ArmyBuyView(player_name)
    store_info(info=info)
    await interaction.response.send_message(f"⚔️ **{player_name.title()}**, choose how many troops and what type to buy:",view=view,ephemeral=True)

@app_commands.checks.has_role("BOT-Control")
@bot.tree.command(name="armysell", description="Sell army resources.")
@app_commands.describe(player_name="Which player is selling troops?")
async def armybuy(interaction: Interaction, player_name: str):
    if player_name not in info.players:
        await interaction.response.send_message("❌ Invalid player name.", ephemeral=True)
        return
    view = ArmySellView(player_name)
    store_info(info=info)
    await interaction.response.send_message(f"⚔️ **{player_name.title()}**, choose how many troops and what type to sell:",view=view,ephemeral=True)

@app_commands.checks.has_role("BOT-Control")
@bot.tree.command(name="armyrefund", description="Refund mistakenly bought army resources.")
@app_commands.describe(player_name="Which player is refunding troops?")
async def armybuy(interaction: Interaction, player_name: str):
    if player_name not in info.players:
        await interaction.response.send_message("❌ Invalid player name.", ephemeral=True)
        return
    view = ArmyRefundView(player_name)
    store_info(info=info)
    await interaction.response.send_message(f"⚔️ **{player_name.title()}**, choose how many troops and what type to refund:",view=view,ephemeral=True)

@app_commands.checks.has_role("BOT-Control")
@bot.tree.command(name="armygive", description="Give army for free.")
@app_commands.describe(player_name="Which player is refunding troops?")
async def armybuy(interaction: Interaction, player_name: str):
    if player_name not in info.players:
        await interaction.response.send_message("❌ Invalid player name.", ephemeral=True)
        return
    view = ArmyGiveView(player_name)
    store_info(info=info)
    await interaction.response.send_message(f"⚔️ **{player_name.title()}**, choose how many troops and what type to give:",view=view,ephemeral=True)


## REDISTRICT AREAS ##
class RedistrictView(ui.View):
    def __init__(self, area_from, area_to):
        super().__init__(timeout=60)
        self.area_from = area_from
        self.area_to = area_to
        self.resource = None
        self.confirm_button = RedistrictConfirmButton()
        self.add_item(self.confirm_button)
        self.add_item(RedistricResourceSelect(area_from, area_to))

    async def on_timeout(self):
        for item in self.children:
            item.disabled = True

class RedistricResourceSelect(ui.Select):
    def __init__(self, area_from, area_to):
        options = [
            discord.SelectOption(label=resource.title(), value=resource, 
                    description=f"{area_from.name.title()} has {area_from.resources()[resource]}, {area_to.name.title()} has {area_to.resources()[resource]}")
            for resource in area_from.resources() if area_from.resources()[resource]>0
        ]
        super().__init__(
            placeholder="Resource-square to reallocate...",
            min_values=1,
            max_values=1,
            options=options
        )
    async def callback(self, interaction: Interaction):
        view: RedistrictView = self.view
        view.resource = self.values[0]
        await interaction.response.defer(ephemeral=True)

class RedistrictConfirmButton(ui.Button):
    def __init__(self):
        super().__init__(label="Confirm Reallocation", style=discord.ButtonStyle.success)

    async def callback(self, interaction: Interaction):
        view: ArmySellView = self.view
        if not view.area_from or not view.area_to or not view.resource:
            await interaction.response.send_message("⚠️ Please select **both** areas and the resource before confirming.",ephemeral=True)
            return
        if view.resource in view.area_from.growth:
            view.area_from.growth[view.resource] -= 1
            view.area_to.growth[view.resource] += 1
        else:
            if view.resource == "population":
                view.area_from.population -= 1
                view.area_to.population += 1
            elif view.resource == "fort":
                view.area_from.fort -= 1
                view.area_to.fort += 1
            elif view.resource == "port":
                view.area_from.port -= 1
                view.area_to.port += 1
            elif view.resource == "city":
                view.area_from.city -= 1
                view.area_to.city += 1
        await interaction.response.send_message(
            f"🔁 **{view.area_from.name.title()}** lost 1 **{view.resource} to {view.area_to.name.title()}**!",
            ephemeral=False)
        self.disabled = True
        store_info(info=info)

@app_commands.checks.has_role("BOT-Control")
@bot.tree.command(name="redistrictarea", description="Redistrict the areas")
@app_commands.describe(area_from="Which area is losing a square?")
@app_commands.describe(area_to="Which area is gaining a square?")
async def redistrictarea(interaction: Interaction, area_from: str, area_to: str):
    area_choices = info.areas.copy()
    area_choices["DM"] = Area("DM", math.inf,math.inf,math.inf,math.inf,math.inf,math.inf,math.inf,math.inf,math.inf)
    if area_from not in area_choices or area_to not in area_choices:
        await interaction.response.send_message("❌ Invalid area name.", ephemeral=True)
        return
    view = RedistrictView(area_choices[area_from], area_choices[area_to])
    await interaction.response.send_message("Choose where resources are allocated from and to",view=view,ephemeral=True)

exchange_rate = {"gold": 1, "food": 3, "steel": 3, "wood": 6, "stone": 6}
@bot.tree.command(name="trade", description="Trade resources")
@app_commands.describe(player_name="Name of player making trade.")
@app_commands.describe(resource_from="Which resource is being sold?")
@app_commands.describe(resource_to="Which resource is being bought?")
async def trade(interaction: Interaction, player_name: str, resource_from: str, resource_to: str):
    if player_name not in info.players:
        await interaction.response.send_message("❌ Invalid player name.", ephemeral=True)
        return
    player = info.players[player_name]
    if "DM" in resource_to or "DM" in resource_from:
        if not any(role.name == "BOT-Control" for role in interaction.user.roles):
            await interaction.response.send_message("🚫 You don’t have permission to use this command.", ephemeral=True)
            return
        if "DM" in resource_to:   # take resources away
            amount = int(resource_to[2:])
            if player.resources[resource_from] < amount:
                await interaction.response.send_message(f"❌ Not enough of {resource_from}.", ephemeral=True)
            else:
                player.resources[resource_from] -= amount
                await interaction.response.send_message(f"🔁 **{player_name.title()}** lost {amount} {resource_from}.", ephemeral=True)
            return
        if "DM" in resource_from:   # give resources for free
            amount = int(resource_from[2:])
            player.resources[resource_to] += amount
            await interaction.response.send_message(f"🔁 **{player_name.title()}** was given {amount} {resource_to}.", ephemeral=True)
            return
    else:
        resources_city = {"food", "wood", "stone", "steel", "gold"}
        resources_port = {"food", "wood", "stone"}
        if player.city() < 1 and player.port() < 1:
            await interaction.response.send_message("❌ This player does not own a city or port.", ephemeral=True)
            return
        elif player.city()<1 and (resource_from not in resources_port or resource_to not in resources_port):
            await interaction.response.send_message("❌ Cannot trade this resource at port (only food, wood and stone).", ephemeral=True)
            return
        if resource_from not in resources_city or resource_to not in resources_city:
            await interaction.response.send_message("❌ Invalid resource name (food,wood,stone,steel,gold).", ephemeral=True)
            return
        if player.resources[resource_from] < exchange_rate[resource_from]:
            await interaction.response.send_message("❌ Not enough resources to make trade.", ephemeral=True)
            return
        player.resources[resource_to] += exchange_rate[resource_to]
        player.resources[resource_from] -= exchange_rate[resource_from]

        store_info(info=info)
        await interaction.response.send_message(f"**{player_name.title()}** traded {exchange_rate[resource_from]} **{resource_from}** for {exchange_rate[resource_to]} **{resource_to}**", ephemeral=True)

GUILD_ID = 1423782088494157896
@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")

    synced = await bot.tree.sync()  # global sync
    print(f"🔁 Synced {len(synced)} commands.")
    print("Commands in tree:", bot.tree.get_commands())

# -----------------------------
# RUN THE BOT
# -----------------------------
bot.run(os.getenv("DISCORD_API_TOKEN"))
