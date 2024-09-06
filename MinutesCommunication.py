import os
import random
import discord
from discord.ext import tasks
from discord.utils import get
from datetime import datetime
import asyncio
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Final
import csv

# CSVからメッセージを読み込む関数
# CSVファイルからリアクション用のメッセージを読み込み、リストとして返します
def load_reaction_messages(filename: str) -> list[str]:
    with open(filename, newline='', encoding='utf-8') as csvfile:
        reader = csv.DictReader(csvfile)
        return [row['message'] for row in reader]

# チャンネル設定の基本クラス
# 抽象クラスとして、各チャンネル設定の基本構造を提供します
@dataclass(frozen=True, slots=True)
class ChannelConfigBase(ABC):
    channel_id: int
    role_id: int
    weekday: int  # 0: 月曜日, 1: 火曜日, ..., 6: 日曜日
    time: str  # "HH:MM"形式で設定
    
    
    # "HH:MM"形式の時間を検証するメソッド
    @staticmethod
    def _validate_time_format(time_str: str) -> bool:
        try:
            # 時間の解析を試みます（先頭にゼロを付ける）
            time_obj = datetime.strptime(time_str.zfill(5), '%H:%M').time()
            
            # 時間が有効な範囲内であるかどうかを確認
            # 負の値や24時以上の時間、無効な時間を弾く
            if time_obj.hour < 0 or time_obj.minute < 0:
                return False
            
            if time_obj >= datetime.strptime("23:59", "%H:%M").time():
                return False

            return True
        except ValueError:
            return False

    # コンストラクタ後の追加の検証を行います
    def __post_init__(self):
        if not (0 <= self.weekday <= 6):
            raise ValueError("曜日は0から6までの値で指定してください")
        if not self._validate_time_format(self.time):
            raise ValueError("時間は'HH:MM'形式で指定してください")


    # メッセージを生成する抽象メソッド（具体的な実装はサブクラスで定義）
    @abstractmethod
    def generate_message(self) -> str:
        pass

# チャンネル設定の具体クラス
# 議事録のリンクを含むメッセージを生成します
@dataclass(frozen=True, slots=True)
class ChannelConfig(ChannelConfigBase):
    meeting_type: str
    meeting_url: str

    # 役職にメンションを付けた議事録のリンク付きメッセージを生成します
    def generate_message(self) -> str:
        return (f'<@&{self.role_id}>\r\nお疲れ様です、{self.meeting_type}の議事録はこちら↓\r\n'
                f'https://github.com/○○/main/{self.meeting_url}\r\n'
                '確認できた人は必ずリアクションしてね！！')

# チャンネル設定を作成するファクトリクラス
# チャンネルタイプに応じて適切な設定オブジェクトを生成します
class ChannelConfigFactory:
    @staticmethod
    def create(channel_type: str, **kwargs) -> ChannelConfigBase:
        if channel_type == "standard":
            return ChannelConfig(**kwargs)
        raise ValueError(f"Unknown channel_type: {channel_type}")

# リアクションに応じた処理を担当するクラス
# メッセージに対してリアクションが追加されたときに実行される処理を定義します
class ReactionHandler:
    def __init__(self, bot: discord.Client, reaction_messages: list[str]):
        self.bot = bot
        self.reaction_messages = reaction_messages
    
    # メッセージIDからチャンネル設定を検索するメソッド
    def _find_channel_config(self, message_id: int, channel_configs: list[ChannelConfig], 
                             reaction_message_ids: dict[int, int]) -> ChannelConfig | None:
        for config in channel_configs:
            if message_id == reaction_message_ids.get(config.channel_id):
                return config
        return None

    # リアクションが追加されたときの処理を行うメソッド
    async def handle_reaction_add(self, reaction: discord.Reaction, user: discord.User, 
                                  channel_configs: list[ChannelConfig], reaction_message_ids: dict[int, int]) -> None:
        if user.bot:  # ボットがリアクションした場合は無視
            return

        # メッセージIDに対応するチャンネル設定を取得
        config = self._find_channel_config(reaction.message.id, channel_configs, reaction_message_ids)
        if not config:
            return

        # ギルドと役職を取得し、ユーザーが該当役職を持っているか確認
        guild = self.bot.get_guild(GUILD_ID)
        role = get(guild.roles, id=config.role_id)
        if not role or role not in user.roles:
            return

        # ランダムなメッセージを選択して送信
        random_message = random.choice(self.reaction_messages)
        await reaction.message.channel.send(f'{user.mention} {random_message}')


# Discordのボットクラス
# ボットの初期化やスケジュールされたタスクの管理、リアクション処理を行います
class DiscordBot(discord.Client):
    def __init__(self, token: str, channel_configs: list[ChannelConfig], reaction_handler: ReactionHandler):
        intents = discord.Intents.all()  # すべてのインテントを有効化
        super().__init__(intents=intents)
        self.token: Final[str] = token
        self.channel_configs: Final[list[ChannelConfig]] = channel_configs
        self.reaction_message_ids: dict[int, int] = {}  # メッセージIDを保存
        self.reaction_handler = reaction_handler
        self.wait_time: Final[int] = 24*60*60  # リアクションを確認するまでの待ち時間（秒単位）

    # ボットを開始するためのメソッド
    async def start_bot(self) -> None:
        await self.start(self.token)
        
    # 現在の時間が議事録送信時間かどうかを確認するメソッド
    def _should_send_meeting_minutes(self, config: ChannelConfig, now: datetime) -> bool:
        return now.weekday() == config.weekday and now.strftime('%H:%M') == config.time

    # 1分ごとに実行されるスケジュールされたタスク
    @tasks.loop(minutes=1)
    async def scheduled_task(self) -> None:
        now = datetime.now()
        for config in self.channel_configs:
            if self._should_send_meeting_minutes(config, now):
                # 非同期タスクとして議事録送信とリアクション確認を開始
                asyncio.create_task(self.send_meeting_minutes(config))

    # 議事録を送信するメソッド
    async def send_meeting_minutes(self, config: ChannelConfig) -> None:
        channel = self.get_channel(config.channel_id)
        if channel:
            # メッセージを生成して送信
            message = await channel.send(config.generate_message())
            self.reaction_message_ids[config.channel_id] = message.id  # メッセージIDを保存

            # リアクション確認のために一定時間待機
            await asyncio.sleep(self.wait_time)

            # リアクションの確認処理を実行
            await self.check_reactions(config)



    # リアクションを確認し、リアクションしていないメンバーに通知するメソッド
    async def check_reactions(self, config: ChannelConfig) -> None:
        guild = self.get_guild(GUILD_ID)
        role = get(guild.roles, id=config.role_id)
        specified_members = role.members if role else []

        message = await self._fetch_latest_message(config)
        if message:
            reacted_users = await self._get_reacted_users(message)
            non_reacted_members = [m for m in specified_members if m not in reacted_users]
            if non_reacted_members:
                await self._notify_non_reacted_members(non_reacted_members, message.channel)

    # 最新のメッセージを取得するメソッド
    async def _fetch_latest_message(self, config: ChannelConfig) -> discord.Message | None:
        channel = self.get_channel(config.channel_id)
        if channel:
            return await channel.fetch_message(self.reaction_message_ids[config.channel_id])
        return None

    # リアクションしたユーザーを取得するメソッド
    async def _get_reacted_users(self, message: discord.Message) -> list[discord.User]:
        if message.reactions:
            return [user async for user in message.reactions[0].users() if not user.bot]
        return []

    # リアクションしていないメンバーに通知するメソッド
    async def _notify_non_reacted_members(self, non_reacted_members: list[discord.Member], channel: discord.TextChannel) -> None:
        mention_text = 'リアクションしていない人: ' + ' '.join(
            member.mention for member in non_reacted_members) + '\r\n議事録を読んで必ずリアクションしてね！'
        await channel.send(mention_text)



    # リアクションが追加されたときに呼び出されるメソッド
    # async def on_reaction_add(self, reaction: discord.Reaction, user: discord.User) -> None:
    #     await self.reaction_handler.handle_reaction_add(reaction, user, self.channel_configs, self.reaction_message_ids)

    # ボットが準備完了したときに呼び出されるメソッド
    async def on_ready(self) -> None:
        self.scheduled_task.start()  # スケジュールされたタスクを開始
        print(f'Logged in as {self.user}')  # ログイン情報を出力

if __name__ == '__main__':
    TOKEN: Final[str] = os.getenv('DISCORD_TOKEN')  # ボットのトークンを取得
    GUILD_ID: Final[int] = 'GUILD_ID'# サーバーID
    REACTION_MESSAGES: Final[list[str]] = load_reaction_messages('reaction_messages.csv')  # CSVからリアクションメッセージをロード
    
    # チャンネル設定をリストとして定義
    channel_configs: Final[list[ChannelConfig]] = [
        ChannelConfigFactory.create(
            channel_type="standard",
            channel_id=,  # チャンネル1のID
            role_id=,  # チャンネル1の役職ID
            meeting_type='修士ゼミ',  # ゼミの種類
            meeting_url='',  # 議事録のURL
            weekday=3,  # 木曜日
            time='12:40'  # 更新する時間
        ),
        ChannelConfigFactory.create(
            channel_type="standard",
            channel_id=,  # チャンネル2のID
            role_id=,  # チャンネル2の役職ID
            meeting_type='卒研ゼミ',  # ゼミの種類
            meeting_url='',  # 議事録のURL
            weekday=4,  # 金曜日
            time='17:00'  # 更新する時間
        ),
        ChannelConfigFactory.create(
            channel_type="standard",
            channel_id=, # チャンネル3のID
            role_id= ,  # チャンネル3の役職ID
            meeting_type='B3ゼミ',  # ゼミの種類
            meeting_url='',  # 議事録のURL
            weekday=1,  # 火曜日
            time='12:40'  # 更新する時間
        )
    ]

    # Discordボットのインスタンスを作成して実行
    discordbot = DiscordBot(token=TOKEN, channel_configs=channel_configs, reaction_handler=ReactionHandler(bot=None, reaction_messages=REACTION_MESSAGES))
    discordbot.reaction_handler.bot = discordbot  # ReactionHandlerにボットの参照を設定
    discordbot.run(TOKEN)  # ボットを実行
