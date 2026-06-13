import json
import discord
from discord import app_commands
from discord.ext import commands
from pathlib import Path

TEMPLATE_PATH = Path("templates/recruit.json")


def load_template() -> dict:
    with open(TEMPLATE_PATH, encoding="utf-8") as f:
        return json.load(f)


def build_content(template: dict, game: str, time: str, members: list[str], note: str, closed: bool = False) -> str:
    t = template["text_closed"] if closed else template["text"]
    member_lines = "\n".join(f"{i+1}. {m}" for i, m in enumerate(members)) if members else "없음"
    return (
        t
        .replace("{game}", game)
        .replace("{time}", time)
        .replace("{members}", member_lines)
        .replace("{count}", str(len(members)))
        .replace("{note}", note)
    )


class RecruitView(discord.ui.View):
    def __init__(self, game: str, time: str, members: list[str], note: str):
        super().__init__(timeout=None)
        self.game = game
        self.time = time
        self.members = members
        self.note = note

        template = load_template()
        join_btn = discord.ui.Button(
            label=template["buttons"]["join"],
            style=discord.ButtonStyle.success,
            custom_id="recruit_join",
        )
        leave_btn = discord.ui.Button(
            label=template["buttons"]["leave"],
            style=discord.ButtonStyle.danger,
            custom_id="recruit_leave",
        )
        close_btn = discord.ui.Button(
            label=template["buttons"]["close"],
            style=discord.ButtonStyle.secondary,
            custom_id="recruit_close",
        )
        join_btn.callback = self.join_callback
        leave_btn.callback = self.leave_callback
        close_btn.callback = self.close_callback
        self.add_item(join_btn)
        self.add_item(leave_btn)
        self.add_item(close_btn)

    async def _update(self, interaction: discord.Interaction):
        template = load_template()
        content = build_content(template, self.game, self.time, self.members, self.note)
        await interaction.response.edit_message(content=content, view=self)

    async def join_callback(self, interaction: discord.Interaction):
        name = interaction.user.display_name
        if name not in self.members:
            self.members.append(name)
            await self._update(interaction)
        else:
            await interaction.response.send_message("이미 참가 중입니다.", ephemeral=True)

    async def leave_callback(self, interaction: discord.Interaction):
        name = interaction.user.display_name
        if name in self.members:
            self.members.remove(name)
            await self._update(interaction)
        else:
            await interaction.response.send_message("참가 목록에 없습니다.", ephemeral=True)

    async def close_callback(self, interaction: discord.Interaction):
        template = load_template()
        content = build_content(template, self.game, self.time, self.members, self.note, closed=True)

        # 버튼 모두 비활성화
        for item in self.children:
            item.disabled = True

        await interaction.response.edit_message(content=content, view=self)

        # 포스트 제목 변경 + 아카이브(잠금)
        thread = interaction.channel
        if isinstance(thread, discord.Thread):
            closed_title = template["post_title_closed"].replace("{game}", self.game).replace("{time}", self.time)
            await thread.edit(name=closed_title, archived=True, locked=True)


class Recruit(commands.Cog):
    def __init__(self, bot: commands.Bot):
        self.bot = bot

    @app_commands.command(name="구인", description="구인 포스트를 생성합니다.")
    @app_commands.describe(
        game="게임 이름",
        time="모집 시간 (예: 오후 9시)",
        note="특이사항 (없으면 없음 입력)",
    )
    async def recruit(
        self,
        interaction: discord.Interaction,
        game: str,
        time: str,
        note: str,
    ):
        from config import RECRUIT_FORUM_CHANNEL_ID

        forum: discord.ForumChannel = interaction.guild.get_channel(RECRUIT_FORUM_CHANNEL_ID)
        if forum is None or not isinstance(forum, discord.ForumChannel):
            await interaction.response.send_message("구인 포럼 채널을 찾을 수 없습니다. 관리자에게 문의하세요.", ephemeral=True)
            return

        template = load_template()
        post_title = template["post_title"].replace("{game}", game).replace("{time}", time)
        members = [interaction.user.display_name]

        content = build_content(template, game, time, members, note)
        view = RecruitView(game, time, members, note)

        await interaction.response.defer(ephemeral=True)
        thread, _ = await forum.create_thread(name=post_title, content=content, view=view)
        await interaction.followup.send(f"구인 포스트가 생성됐습니다! {thread.mention}", ephemeral=True)


async def setup(bot: commands.Bot):
    await bot.add_cog(Recruit(bot))
