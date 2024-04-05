#coding: utf-8
import random, json

from typing import Any, List, Optional
from datetime import date, datetime, time, timedelta

CURRENT_YEAR = datetime.now().year
DEADLINE_DATETIME_FMT = "%d/%m/%Y"

# discord stuff
import discord
from discord.ext import commands, tasks

from deadline.utils.api import DeadlineSerializer, SheetAPI

# google color :))) only blue green yellow and red
COLOR_PALLETE = [
    discord.Color.from_rgb(66, 134, 244),
    discord.Color.from_rgb(52, 168, 83),
    discord.Color.from_rgb(249, 170, 0),
    discord.Color.from_rgb(234, 67, 53),
]

# setup global timezone at 7h
LOOP_TIME = time(hour=7) # default by 07:00

class Deadline( commands.Cog ):
    def __init__( self, bot ):
        self.bot = bot
        # setup a task loop
        self.deadline_annouce.start()

    #@tasks.loop(time=LOOP_TIME)
    @tasks.loop(minutes=1)
    async def deadline_annouce( self ):
        self.bot.deadline_data  = {}
        # refresh deadline
        deadline_db = self.bot.sql.execute("select id, url from Deadline").fetchall()
        for fetch_dl in deadline_db:
            await self.process_deadline(fetch_dl[1], int(fetch_dl[0]))

        for u, dl in self.bot.deadline_data.items():
            user_id = self.bot.sql.execute(f'select discord_id from User where email = \"{u}\"').fetchone()[0]
            user: discord.User = self.bot.get_user(int(user_id))

            n_deadline = len(dl)
            total_dl: str = str()
            for k, v in enumerate(dl):
                total_dl += f"#{k + 1}. {str(v)}\n"
            annouce_card = discord.Embed(color=random.choice(COLOR_PALLETE), title=f"Bạn còn tổng cộng {n_deadline} deadline chưa hoàn thành")
            annouce_card.add_field(name="Các deadline còn lại", value=total_dl)
            await user.send(embed=annouce_card)

    @commands.command(
        name="deadline_delete",
        aliases=['dl_del'],
        description="Xoá một hoặc nhiều deadline trong danh sách deadline",
        brief="Xoá deadline hiện tại"
    )
    async def deadline_delete( self, ctx: commands.Context[Any], *deadline_id: int ) -> None:
        for dl_id in deadline_id:
            # clear current deadline list that influence into currnet deadline
            for human, his_deadline in self.bot.deadline_data.items():
                for deadline in his_deadline:
                    if deadline.deadline_id == dl_id:
                        his_deadline.remove(deadline)
            self.bot.sql.execute(f"delete from Deadline where id = {dl_id}")

        await ctx.message.add_reaction("✅")

    async def process_deadline( self, url: str, dl_id: int ) -> bool:
        try:
            # clear current deadline list that influence into currnet deadline
            for human, his_deadline in self.bot.deadline_data.items():
                for deadline in his_deadline:
                    if deadline.deadline_id == dl_id:
                        his_deadline.remove(deadline)

            sheet_api = SheetAPI( url )
            deadline_list = sheet_api.serialize()

            for obj in deadline_list:
                assigned_to = obj["assigned_to"].split(' ')
                start_day, start_month = map(int, obj["start"].split('/'))
                dl_day, dl_month = map(int, obj["deadline"].split('/'))

                # convert text datetime to datetime object
                obj["start"] = date(year=CURRENT_YEAR, month=start_month, day=start_day)
                obj["deadline"] = date(year=CURRENT_YEAR, month=dl_month, day=dl_day)
                obj["url"] = url
                obj["deadline_id"] = dl_id

                for human in assigned_to:
                    if not human in self.bot.deadline_data:
                        self.bot.deadline_data[human] = []

                # handle deadline serializer is done
                deadline_serializer = DeadlineSerializer( obj )
                if deadline_serializer.extract_status == 0:
                    for human in assigned_to:
                        self.bot.deadline_data[human].append( DeadlineSerializer( obj ) )
                #await ctx.send(f"{obj['start']} {obj['deadline']}")

            # clear deadline if this human doesnt have any deadline
            for human, his_deadline in self.bot.deadline_data.items():
                if not his_deadline:
                    del self.bot.deadline_data[human]

            return True
        except Exception as e:
            self.bot.log.error(e)
            return False

    @commands.command(
        name="deadline_refresh",
        aliases=['dl_ref'],
        description="Refresh một deadline hiện có trong database",
        brief="Refresh một deadline hiện tại trong database"
    )
    async def deadline_refresh( self, ctx: commands.Context[Any], deadline_id: int ) -> None:
        deadline_url = self.bot.sql.execute(f"select url from Deadline where id = {deadline_id}").fetchone()[0]
        result =  await self.process_deadline(deadline_url, deadline_id)

        if result:
            await ctx.message.add_reaction("✅")
        else:
            await ctx.message.add_reaction("❎")


    @commands.command(
        name="deadline",
        aliases=['dl'],
        description="Tạo một deadline mới bao gồm đường dẫn tới sheet deadline và tên deadline mới",
        brief="Tạo một deadline mới"
    )
    async def deadline( self, ctx: commands.Context[Any], url: str, *name ) -> None:
        name = ' '.join(list(name))
        last_id = int(self.bot.sql.execute(f"select seq from sqlite_sequence where name=\"Deadline\"").fetchone()[0]) + 1
        self.bot.sql.execute(f"insert into Deadline( name, url ) values(\"{name}\", \"{url}\")")
        result = await self.process_deadline( url, last_id )
        if result:
            await ctx.message.add_reaction("✅")
        else:
            await ctx.message.add_reaction("❎")
        #await ctx.send(f"{json.dumps(deadline_list, indent=2)}")


    @commands.command(
        name="deadline_list",
        aliases=['dl_list'],
        description="Hiện danh sách deadline hiện tại",
        brief="Lấy thông tin về danh sách deadline hiện tại"
    )
    async def deadline_list( self, ctx: commands.Context[Any] ) -> None:
        select_query = "select * from Deadline"
        all_deadline = self.bot.sql.execute(select_query).fetchall()[:5]
        if len(all_deadline) == 0:
            not_found_card = discord.Embed( color=random.choice(COLOR_PALLETE), description="Hiện tại không có deadline nào." )
            await ctx.send( embed=not_found_card )
        else:
            text_deadline_list = [ f"[#{row[0]:,}. {row[3]}]({row[1]}) - {row[2]}" for row in all_deadline ]
            list_card = discord.Embed( color=random.choice(COLOR_PALLETE), title="Danh sách deadline hiện tại" )
            list_card.add_field(name="Tên - Ngày khởi tạo", value=('\n'.join(text_deadline_list)))
            await ctx.send( embed=list_card )

# setup function for discord.py load cog
async def setup( bot ):
    await bot.add_cog( Deadline(bot) )
