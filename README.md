# MinutesCommunication

## 概要

この Discord ボットは、指定された時間に自動的にメッセージを送信し、特定の役職を持つメンバーがメッセージにリアクションしたかどうかを確認します。また、リアクションしていないメンバーに通知を送る機能も含まれています。ボットは、CSV ファイルからメッセージを読み込み、複数のチャンネルで動作します。

## ファイル構成

- `main.py`: ボットのメインファイル。全体のロジックを含んでいます。
- `reaction_messages.csv`: リアクション用のメッセージが保存された CSV ファイル。

## 必要な環境

- Python 3.8 以上
- discord.py ライブラリ（`pip install discord.py`）
- `.env`ファイルに`DISCORD_TOKEN`と`GUILD_ID`を設定

## 主要なクラスと関数

### 1. `load_reaction_messages(filename: str) -> list[str]`

- **説明**: CSV ファイルからリアクション用のメッセージを読み込み、リストとして返します。
- **引数**:
  - `filename`: 読み込む CSV ファイルの名前。
- **戻り値**: メッセージのリスト。

### 2. `ChannelConfigBase`

- **説明**: チャンネル設定の基本クラス。抽象クラスとして、各チャンネル設定の基本構造を提供します。また、このクラスでweekdayとtimeのバリデーションチェックを行っています。
- **属性**:
  - `channel_id`: メッセージを送信するチャンネルの ID。
  - `role_id`: リアクションを求める役職の ID。
  - `weekday`: メッセージを送信する曜日（0: 月曜日, 1: 火曜日, ..., 6: 日曜日）。
  - `time`: メッセージを送信する時間（"HH"形式）。

### 3. `ChannelConfig(ChannelConfigBase)`

- **説明**: `ChannelConfigBase`を継承した具体クラス。議事録のリンクを含むメッセージを生成します。
- **属性**:
  - `meeting_type`: ゼミの種類。
  - `meeting_url`: 議事録の URL。
- **メソッド**:
  - `generate_message() -> str`: 役職にメンションを付けた議事録のリンク付きメッセージを生成します。

### 4. `ChannelConfigFactory`

- **説明**: チャンネル設定を作成するファクトリクラス。チャンネルタイプに応じて適切な設定オブジェクトを生成します。
- **メソッド**:
  - `create(channel_type: str, **kwargs) -> ChannelConfigBase`: チャンネルタイプに応じた設定オブジェクトを生成します。

### 5. `ReactionHandler`

- **説明**: リアクションに応じた処理を担当するクラス。メッセージに対してリアクションが追加されたときに実行される処理を定義します。
- **メソッド**:
  - `handle_reaction_add(reaction: discord.Reaction, user: discord.User, channel_configs: list[ChannelConfig], reaction_message_ids: dict[int, int]) -> None`: リアクションが追加されたときの処理を行います。

### 6. `DiscordBot(discord.Client)`

- **説明**: Discord のボットクラス。ボットの初期化やスケジュールされたタスクの管理、リアクション処理を行います。
- **属性**:
  - `token`: ボットのトークン。
  - `channel_configs`: 各チャンネルの設定オブジェクトのリスト。
  - `reaction_message_ids`: メッセージ ID を保存する辞書。
  - `reaction_handler`: リアクション処理を担当するハンドラクラスのインスタンス。
  - `wait_time`: リアクションを確認するまでの待ち時間（秒単位）　現在は 1 日待つようにしている
- **メソッド**:
  - `start_bot() -> None`: ボットを開始します。
  - `scheduled_task() -> None`: 1 分ごとに実行されるスケジュールされたタスク。
  - `send_meeting_minutes(config: ChannelConfig) -> None`: 指定されたチャンネルに議事録を送信します。
  - `check_reactions(config: ChannelConfig) -> None`: リアクションを確認し、リアクションしていないメンバーに通知します。
  - `on_reaction_add(reaction: discord.Reaction, user: discord.User) -> None`: リアクションが追加されたときに呼び出されるメソッド。＊現在は、メッセージが流れてチャンネルが見づらいと指摘があったためコメントアウトしています（別のチャンネルを用意するなどで対応する案を考えています）
  - `on_ready() -> None`: ボットが準備完了したときに呼び出されるメソッド。

## 設定と起動

### 1. `.env`ファイルの設定

- `DISCORD_TOKEN`: Discord のボットトークンを設定します。
- `GUILD_ID`: ボットが動作するサーバーの ID を設定します。

### 2. チャンネル設定の定義

ボットを起動する前に、`channel_configs`リストに各チャンネルの設定を追加します。

```python
channel_configs: Final[list[ChannelConfig]] = [
    ChannelConfigFactory.create(
        channel_type="standard",
        channel_id=,  # チャンネル1のID
        role_id=,  # チャンネル1の役職ID
        meeting_type='修士ゼミ',  # ゼミの種類
        meeting_url='',  # 議事録のURL
        weekday=,  # 曜日
        time='12:40'  # 更新する時間
    ),
    # 他のチャンネル設定を追加
]
```

## 注意点

- メッセージの送信時間と曜日が一致しない場合、メッセージは送信されません。
- リアクションメッセージは`reaction_messages.csv`から読み込まれるため、事前にメッセージを CSV に記載してください。

## 拡張

- **チャンネル設定の追加**: 新しいチャンネル設定を追加するには、`channel_configs`リストに新しい設定を追加してください。
- **メッセージのカスタマイズ**: `generate_message`メソッドをカスタマイズすることで、送信メッセージの内容を変更できます。
