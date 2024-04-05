#coding: utf-8
# discord stuff
# for type hint
from typing import * # pyright: ignore

import discord
from discord.ext import commands

import re, random
# google color :))) only blue green yellow and red
COLOR_PALLETE = [
    discord.Color.from_rgb(66, 134, 244),
    discord.Color.from_rgb(52, 168, 83),
    discord.Color.from_rgb(249, 170, 0),
    discord.Color.from_rgb(234, 67, 53),
]

class Basic( commands.Cog ):
    def __init__( self, bot ):
        self.bot = bot

    # ping command first basical command for discord bot
    @commands.command( name="ping", description="Lấy thời gian phàn hồi của bot", brief="Lấy thời gian phản hồi của bot" )
    async def ping( self, ctx: commands.Context[Any] ) -> None:
        # calculate ping as milliseconds
        packet_ping: int = int(self.bot.latency * 1000)
        await ctx.send(':ping_pong: **Pong! {0:,}ms**'.format(packet_ping))

    @commands.command(
        name="profile",
        aliases=['p'],
        description="Hiện thông tin cá nhân đã được định danh.",
        brief="Hiện thông tin cá nhân được được định danh."
    )
    async def profile( self, ctx: commands.Context[Any], user: Optional[discord.User] ) -> None:
        # get current profile to view if user is none use ctx except
        p_user: Union[discord.User, discord.Member] = user if not user is None else ctx.author
        uid_query = user.id if not user is None else ctx.author.id
        user_info = self.bot.sql.execute(f"""
            select
                name,
                email
            from User where discord_id = \"{uid_query}\"
        """).fetchone()

        if user_info is None:
            unknown_card = discord.Embed( color=random.choice(COLOR_PALLETE), description="Hồ sơ không được tìm thấy do chưa định danh." )
            unknown_card.set_author(name=f"Hồ sơ {p_user.global_name}", icon_url=p_user.display_avatar.url)
            await ctx.send( embed=unknown_card )

            return None

        # create profile card with random choice from color pallete
        total_deadline = str()
        if user_info[1] in self.bot.deadline_data:
            for k, v in enumerate(self.bot.deadline_data[user_info[1]]):
                total_deadline += f"#{k + 1}. {str(v)}\n"
        else:
            total_deadline = "Hiện tại không có deadline."

        profile_card = discord.Embed(color=random.choice(COLOR_PALLETE))
        profile_card.add_field(name="Tên (email)", value=f"{user_info[0]} ||({user_info[1]})||")
        profile_card.add_field(name="Deadline", value=total_deadline)
        profile_card.set_author(name=f"Hồ sơ {p_user.global_name}", icon_url=p_user.display_avatar.url)
        profile_card.set_thumbnail(url=p_user.display_avatar.url)
        await ctx.send( embed=profile_card )

    # modify command for edit identified user in database
    @commands.command(
        name="modify",
        description="Thay đổi thông tin định danh trên discrod với các thông tin như tên, email ...",
        brief="Thay đổi thông tin đã được định danh"
    )
    async def modify( self, ctx: commands.Context[Any], field: str, *value ) -> None:
        # convert greedy string into string
        value = ' '.join(list(value))
        # query user
        user_exists_query = self.bot.sql.execute(f"select discord_id from User where discord_id = \"{ctx.author.id}\"").fetchone()
        user_update_query = "update User set {0} = \"{1}\" where discord_id = \"{2}\""
        valid_field: Dict[str, str] = {
            "name": "tên",
        }
        # if user try edit another field
        if not field in valid_field:
            await ctx.send(f'{ctx.author.mention}, **Bạn chỉ được thay đổi name, các field khác bạn không được thay đổi.** :face_with_symbols_over_mouth:', ephemeral=True)
            return

        if user_exists_query is not None:
            # perform modify
            self.bot.sql.execute( user_update_query.format(field, value, ctx.author.id) )
            await ctx.message.add_reaction("✅")
        else:
            await ctx.send(f'{ctx.author.mention}, **Bạn chưa được định danh trên bot, vui dòng xác minh danh tính trước khi thay đổi thông tin.** :x:', ephemeral=True)

# setup function for discord.py load cog
async def setup( bot ):
    await bot.add_cog( Basic(bot) )
