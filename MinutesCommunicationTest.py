import unittest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime
from MinutesCommunication import ChannelConfig, ChannelConfigFactory, ReactionHandler, DiscordBot  # 必要なクラスをインポート
import discord
import asyncio


class TestChannelConfig(unittest.TestCase):
    def test_validate_time_format(self):
        self.assertTrue(ChannelConfig._validate_time_format("00:00"))
        self.assertTrue(ChannelConfig._validate_time_format("12:59"))
        self.assertTrue(ChannelConfig._validate_time_format("1:59"))
        self.assertFalse(ChannelConfig._validate_time_format("24:00"))
        self.assertFalse(ChannelConfig._validate_time_format("12:60"))
        self.assertFalse(ChannelConfig._validate_time_format("abc"))

    def test_channel_config_initialization(self):
        config = ChannelConfig(
            channel_id=123456789,
            role_id=987654321,
            weekday=1,
            time="12:30",
            meeting_type="修士ゼミ",
            meeting_url="meetings/001"
        )
        self.assertEqual(config.channel_id, 123456789)
        self.assertEqual(config.role_id, 987654321)
        self.assertEqual(config.weekday, 1)
        self.assertEqual(config.time, "12:30")
        self.assertEqual(config.meeting_type, "修士ゼミ")
        self.assertEqual(config.meeting_url, "meetings/001")

    def test_invalid_weekday(self):
        # weekdayが範囲外のときにエラーが発生するか確認
        with self.assertRaises(ValueError) as context:
            ChannelConfig(
                channel_id=123456789,
                role_id=987654321,
                weekday=7,  # 範囲外
                time="12:30",
                meeting_type="修士ゼミ",
                meeting_url="meetings/001"
            )
        self.assertEqual(str(context.exception), "曜日は0から6までの値で指定してください")

        # weekdayが負の値の場合もエラーが発生するか確認
        with self.assertRaises(ValueError) as context:
            ChannelConfig(
                channel_id=123456789,
                role_id=987654321,
                weekday=-1,  # 範囲外
                time="12:30",
                meeting_type="修士ゼミ",
                meeting_url="meetings/001"
            )
        self.assertEqual(str(context.exception), "曜日は0から6までの値で指定してください")




if __name__ == '__main__':
    # テストランナーの設定
    with open('test_results.txt', 'w') as f:
        runner = unittest.TextTestRunner(stream=f, verbosity=2)
        unittest.main(testRunner=runner)
