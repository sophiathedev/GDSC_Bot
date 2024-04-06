#coding: utf-8
# discord stuff
# for type hint
from typing import * # pyright: ignore

import discord, asyncio
import pandas as pd
from discord.ext import commands, tasks
from discord.abc import *

from main import SERVER_GUILD_ID, SERVER_VERIFY_CHANNEL_ID, SERVER_WELCOME_CHANNEL_ID
from main import SERVER_TECH_ROLE, SERVER_CORE_ROLE, SERVER_DES_ROLE, SERVER_HR_ROLE, SERVER_PR_ROLE, SERVER_MEDIA_ROLE
from .otp import OTP

from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.header import Header

# view in verify channel
class GlobalVerifyMsgView(discord.ui.View):
    def __init__(self, verifyCallback: Callable) -> None:
        super().__init__()
        self.verifyCallback: Callable = verifyCallback

    @discord.ui.button(label="Xác minh danh tính", style=discord.ButtonStyle.green)
    async def buttonCallback( self, interaction: discord.Interaction, button ) -> None:
        member: discord.Member = interaction.guild.get_member(interaction.user.id)
        await interaction.response.send_message("Tin nhắn xác minh danh tính đã được gửi tới bạn !", ephemeral=True)
        await self.verifyCallback(member)

class DoesntReceiveOTPView(discord.ui.View):
    def __init__(self, sendOTPCallback: Callable, userEmail: str, currentOTP: str) -> None:
        super().__init__()

        self.sendOTPCallback: Callable = sendOTPCallback
        self.userEmail: str = userEmail
        self.currentOTP: str = currentOTP

    @discord.ui.button(label="Tôi chưa nhận được mã", style=discord.ButtonStyle.red)
    async def buttonCallback( self, interaction: discord.Interaction, button: discord.Button ) -> None:
        button.disabled = True
        await interaction.response.send_message(f"Mã OTP đã được gửi lại vào **{self.userEmail}** !")
        self.sendOTPCallback(self.userEmail, self.currentOTP)

# verify cog
class Verify( commands.Cog ):
    def __init__( self, bot: commands.Bot ):
        # some stupid dataset
        self.user_df = pd.read_csv('verify/data.csv')
        self.user_df = self.user_df[["Role", "Tên", "Business Email"]]

        self.bot = bot

        self.createGlobalVerifyMessage.start()

    @tasks.loop(count=1)
    async def createGlobalVerifyMessage( self ) -> None:
        verifyChannel: discord.TextChannel = self.bot.get_guild(SERVER_GUILD_ID).get_channel(SERVER_VERIFY_CHANNEL_ID)
        await verifyChannel.send("**Dành cho những bạn chưa xác minh danh tính**\n\nCó một số bạn quên chưa điền mail trong quá trình xác nhận hoặc nhập mã OTP sai quá nhiều lần hoặc không nhận được mã OTP trong quá trình xác minh.\n\nCác bạn có thể tiến hành xác minh danh tính bằng cách ấn vào nút dưới đây !", view=GlobalVerifyMsgView(verifyCallback=self.verifyUser))

    #@commands.Cog.listener()
    #async def on_member_join( self, member: discord.Member ) -> None:
    #    await self.verifyUser(member)

    async def verifyUser(self, member: discord.Member) -> None:
        await member.send("**CHÀO MỪNG BẠN ĐẾN VỚI DISCORD SERVER CỦA GDSC PTIT**\n\nBut, One more thing...\n\nBạn vui lòng gửi email của bạn để xác minh danh tính (<name>@gdscptit.dev). **Lưu ý: admin sẽ nhìn thấy mail mà bạn sử dụng để xác minh danh tính.**")

        def emailCheck( m: discord.Message ):
            return ("@gdscptit.dev" in m.content)

        # server verify channel for mention
        verifyChannel: discord.TextChannel = self.bot.get_guild(SERVER_GUILD_ID).get_channel(SERVER_VERIFY_CHANNEL_ID)

        # get user email from user prompt
        try:
            userEmailMessage: discord.Message = await self.bot.wait_for('message', check=emailCheck, timeout=300.0)
        except asyncio.TimeoutError:
            await member.send(f"**Đã hết 5 phút nhưng bạn vẫn chưa điền email xác minh danh tính**.\nĐể xác minh danh tính bạn vui lòng vào discord server của Muốn Mở Mang để xác minh lại tại channel {verifyChannel.mention}")

        # store as another variable for easier reading and using
        userEmail: str = userEmailMessage.content
        searched: bool = False
        for index in range(len(self.user_df)):
            if userEmail == self.user_df.loc[index, "Business Email"]:
                searched = True
                break
        if searched == False:
            await member.send(f"**Không tìm thấy email trên cơ sở dữ liệu !**, Để tiến hành verify vui lòng ghé channel {verifyChannel.mention}.")
            return None
        generatorOTP: OTP = OTP(intervalTime=900) # OTP generator with expried time is 15 minutes as 900 seconds
        # store as another variable for easie reading and using
        currentOTPCode: str = generatorOTP.currentOTP

        # if message sent success
        if self.sendOTP(userEmail, currentOTPCode):
            await member.send(f"Chắc hẳn bạn là **{self.user_df.loc[index, 'Tên']}** bạn cần xác minh danh tính thông qua email.\n\nMail chứa mã xác nhận đã được gửi tới **{userEmail}**. Vui lòng **check mail trong trang chính hoặc thư mục spam** để nhận được mã OTP có 8 chữ số.", view=DoesntReceiveOTPView(self.sendOTP, userEmail, currentOTPCode))
            failCount = 0
            verifyComplete = False
            countMessage: discord.Message = await member.send(f"Bạn còn **{3 - failCount}** lần thử mã.")
            while failCount < 3:
                await countMessage.edit(content=f"Bạn còn **{3 - failCount}** lần thử mã.")
                try:
                    userProvideOTP: discord.Message = await self.bot.wait_for('message', check=lambda x: True, timeout=120.0)
                except asyncio.TimeoutError:
                    await member.send(f"**Đã hết 2 phút nhưng bạn vẫn chưa điền OTP**.\nĐể xác minh danh tính bạn vui lòng vào discord server của GDSC PTIT để xác minh lại tại channel {verifyChannel.mention}")

                userProvideOTP.content = userProvideOTP.content.replace(' ', '')
                if generatorOTP.verify(userProvideOTP.content):
                    verifyComplete = True
                    break
                else:
                    failCount += 1

            if verifyComplete == False:
                await countMessage.delete()
                await member.send(f"**Xác minh danh tính thất bại**.\nĐể xác minh danh tính bạn vui lòng vào discord server của Muốn Mở Mang để xác minh lại tại channel {verifyChannel.mention}")
            else:
                self.bot.sql.execute(f'insert or ignore into User(name, discord_id, email) values(\"{self.user_df.loc[index, 'Tên']}\", {member.id}, \"{userEmail}\")')
                # welcome channel
                welcomeChannel: discord.TextChannel = self.bot.get_guild(SERVER_GUILD_ID).get_channel(SERVER_WELCOME_CHANNEL_ID)
                # when verified complete
                serverGuild: discord.Guild = self.bot.get_guild(SERVER_GUILD_ID)
                #verifiedRole: discord.Role = serverGuild.get_role(1223587437716967534)
                verifiedRole: Dict[str, discord.Role] = {
                    "Tech": serverGuild.get_role(SERVER_TECH_ROLE),
                    "HR": serverGuild.get_role(SERVER_HR_ROLE),
                    "DES": serverGuild.get_role(SERVER_DES_ROLE),
                    "PR": serverGuild.get_role(SERVER_PR_ROLE),
                    "Media": serverGuild.get_role(SERVER_MEDIA_ROLE),
                    "Core": serverGuild.get_role(SERVER_CORE_ROLE),
                }
                verifiedMember: discord.Member = member
                try:
                    memberRole: str = self.user_df.loc[index, 'Role']
                    if "Lead" in memberRole or "Core" in memberRole:
                        await verifiedMember.add_roles(verifiedRole["Core"])
                    else:
                        await verifiedMember.add_roles(verifiedRole[memberRole])
                    await verifiedMember.edit(nick=f"{self.user_df.loc[index, 'Tên']} - {self.user_df.loc[index, 'Role']}")
                    #await verifiedMember.add_roles(verifiedRole)
                    pass
                except discord.Forbidden as e:
                    raise e

                await countMessage.delete()
                await member.send(f"**Xác minh danh tính thành công !**, Một lần nữa chào mừng bạn đến với Discord server của GDSC PTIT :partying_face:\n\nHãy cùng bắt đầu với {welcomeChannel.mention}")

    # rewrite for reuseable
    def sendOTP(self, userEmail: str, OTP: str) -> bool:

        # create multipart utf-8 message
        message: MIMEMultipart = MIMEMultipart("alternative")
        message["Subject"] = Header("Mã xác nhận danh tính cho Discord server GDSC PTIT", 'utf-8')

        otpPart_vi: MIMEText = MIMEText(u"""
            <body>
                <h2>Chào mừng tới với Discord của GDSC PTIT.</h2>
                <br/><br/>
                Dưới đây là mã xác nhận để bạn có thể xác minh danh tính khi tham gia server.
                Vui lòng gửi đoạn code sau tới GDSC PTIT Bot để nhận được quyền truy cập. Vui lòng không gửi mã này tới bất kì ai ngoài GDSC PTIT Bot.
                <br/><br/>
                Mã xác nhận danh tính của bạn: <b>{0} {1}</b>.
            </body>
        """.format(OTP[0:4], OTP[4:]), 'html')

        # attach part to message
        message.attach(otpPart_vi)
        # return the result after send email
        return self.bot.email.send(userEmail, message)

# setup function for discord.py load cog
async def setup( bot ):
    await bot.add_cog( Verify(bot) )
