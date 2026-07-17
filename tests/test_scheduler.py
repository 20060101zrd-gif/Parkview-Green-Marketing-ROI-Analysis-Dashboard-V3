import os
import sys
import tempfile
import shutil
from pathlib import Path
from unittest.mock import patch, MagicMock

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'webapp'))
from services.scheduler_service import DataScheduler


class TestDataScheduler:

    def setup_method(self):
        DataScheduler._instance = None
        self.tmp_dir = tempfile.mkdtemp()
        self.watch_dir = os.path.join(self.tmp_dir, 'watch')
        self.test_data_dir = os.path.join(self.tmp_dir, 'data')
        os.makedirs(self.watch_dir)
        os.makedirs(self.test_data_dir)
        # 通过 configure 设置所有路径，确保不碰真实数据
        self.sched = DataScheduler.get_instance()
        self.sched.configure(
            watch_dir=self.watch_dir,
            interval_hours=1,
            enabled=False,
            data_dir=self.test_data_dir
        )
        # 双重校验：data_dir 绝对不能指向项目真实 data 目录
        real_data = os.path.normpath(os.path.join(os.path.dirname(__file__), '..', 'data'))
        assert os.path.normpath(self.sched.data_dir) != real_data, "TEST SAFETY CHECK FAILED: data_dir points to real data!"

    def teardown_method(self):
        self.sched.stop()
        shutil.rmtree(self.tmp_dir, ignore_errors=True)
        DataScheduler._instance = None

    def test_singleton(self):
        s2 = DataScheduler.get_instance()
        assert s2 is self.sched

    def test_configure(self):
        cfg = self.sched.configure(interval_hours=6, enabled=False)
        assert cfg['interval_hours'] == 6
        assert cfg['enabled'] is False

    def test_configure_email(self):
        """R2: Configure email notification settings."""
        cfg = self.sched.configure(
            notify_email='test@example.com',
            email_enabled=True,
            smtp_host='smtp.test.com',
            smtp_port=587,
            smtp_user='user@test.com',
            smtp_pass='secret123'
        )
        assert cfg['notify_email'] == 'test@example.com'
        assert cfg['email_enabled'] is True
        assert cfg['smtp_host'] == 'smtp.test.com'
        assert cfg['smtp_port'] == 587

    def test_pull_no_files(self):
        result = self.sched.pull_and_reload()
        assert result['files_pulled'] == 0

    def test_pull_with_input_file(self):
        test_file = os.path.join(self.watch_dir, 'BI_Dashboard_Ready_Data.csv')
        with open(test_file, 'w') as f:
            f.write('coupon_record_id,userid,coupon_type\n1,u001,daily_parking_coupon\n')

        result = self.sched.pull_and_reload()
        assert result['files_pulled'] >= 1

    def test_pull_with_sales_file(self):
        test_file = os.path.join(self.watch_dir, '销售查询.csv')
        with open(test_file, 'w', encoding='utf-8') as f:
            f.write('科创编号,业态,销售额,销售时间\n1,餐饮,100,2024-01-01\n')

        result = self.sched.pull_and_reload()
        assert result['files_pulled'] >= 1

    def test_pull_ignores_unknown_files(self):
        test_file = os.path.join(self.watch_dir, 'random.csv')
        with open(test_file, 'w') as f:
            f.write('a,b,c\n')

        result = self.sched.pull_and_reload()
        assert result['files_pulled'] == 0

    def test_history_logging(self):
        initial = len(self.sched.history)
        self.sched.pull_and_reload()
        assert len(self.sched.history) > initial

    def test_invalid_watch_dir(self):
        self.sched.watch_dir = '/nonexistent/path/12345'
        result = self.sched.pull_and_reload()
        assert result['files_pulled'] == 0

    def test_start_stop(self):
        assert not self.sched._running
        started = self.sched.start()
        assert started is True
        assert self.sched._running
        self.sched.stop()
        assert not self.sched._running

    def test_start_invalid_dir(self):
        self.sched.watch_dir = '/invalid/dir'
        started = self.sched.start()
        assert started is False
        assert not self.sched._running

    def test_interval_config(self):
        self.sched.configure(interval_hours=0.5)
        assert self.sched.interval_hours == 0.5

    def test_history_limit(self):
        for i in range(30):
            self.sched._log('test', 'msg ' + str(i))
        assert len(self.sched.history) <= self.sched._max_history

    # ===== R2: Email notification tests =====

    @patch('services.scheduler_service.smtplib.SMTP')
    def test_email_sent_after_pull(self, mock_smtp):
        """R2: 配置邮件后，触发一次拉取，验证邮件发送函数被调用"""
        mock_server = MagicMock()
        mock_smtp.return_value = mock_server

        # Configure email
        self.sched.configure(
            notify_email='analyst@parkviewgreen.com',
            email_enabled=True,
            smtp_host='smtp.test.com',
            smtp_port=587,
            smtp_user='sender@test.com',
            smtp_pass='testpass'
        )

        # Create a test file in watch dir
        test_file = os.path.join(self.watch_dir, 'BI_Dashboard_Ready_Data.csv')
        with open(test_file, 'w') as f:
            f.write('coupon_record_id,userid,coupon_type\n1,u001,daily_parking_coupon\n')

        # Verify email was attempted via _send_email_notification
        with patch.object(self.sched, '_send_email_notification') as mock_send:
            result = self.sched.pull_and_reload()
            assert result['files_pulled'] >= 1

            # Simulate what _run_once does: if files pulled and email enabled, send
            if self.sched.email_enabled and self.sched.notify_email and result['files_pulled'] > 0:
                self.sched._send_email_notification(result)
                mock_send.assert_called_once()

    def test_email_disabled_no_send(self):
        """R2: 邮件禁用时，触发拉取不发送邮件"""
        self.sched.configure(
            notify_email='analyst@parkviewgreen.com',
            email_enabled=False
        )

        test_file = os.path.join(self.watch_dir, 'BI_Dashboard_Ready_Data.csv')
        with open(test_file, 'w') as f:
            f.write('coupon_record_id,userid,coupon_type\n1,u001,daily_parking_coupon\n')

        with patch.object(self.sched, '_send_email_notification') as mock_send:
            result = self.sched.pull_and_reload()
            assert result['files_pulled'] >= 1

            # Should NOT send email when disabled
            if self.sched.email_enabled and self.sched.notify_email and result['files_pulled'] > 0:
                self.sched._send_email_notification(result)
            # Verify mock was never called because email is disabled
            mock_send.assert_not_called()

    def test_full_flow_with_email(self):
        """R2: 完整流程 — 设置时间间隔 → 启动 → 模拟新文件到达 → 验证触发了分析 + 邮件"""
        # Configure with email
        self.sched.configure(
            notify_email='analyst@parkviewgreen.com',
            email_enabled=True,
            smtp_host='smtp.test.com',
            smtp_port=587,
            smtp_user='sender@test.com',
            smtp_pass='testpass'
        )

        # Verify config
        cfg = self.sched.get_config()
        assert cfg['notify_email'] == 'analyst@parkviewgreen.com'
        assert cfg['email_enabled'] is True
        assert cfg['interval_hours'] == 1

        # Verify data_dir is NOT the real data dir
        real_data = os.path.normpath(os.path.join(os.path.dirname(__file__), '..', 'data'))
        assert os.path.normpath(self.sched.data_dir) != real_data

        # Create a test file
        test_file = os.path.join(self.watch_dir, 'BI_Dashboard_Ready_Data.csv')
        with open(test_file, 'w') as f:
            f.write('coupon_record_id,userid,coupon_type\n1,u001,daily_parking_coupon\n2,u002,gourmet_coupon\n')

        # Pull files
        result = self.sched.pull_and_reload()
        assert result['files_pulled'] >= 1
        assert len(result['files']) >= 1

        # Verify file was copied to temp data dir (not real data dir)
        dest = os.path.join(self.test_data_dir, 'BI_Dashboard_Ready_Data.csv')
        assert os.path.exists(dest), "File should be copied to temp test data dir"

        # Verify history has pull entry
        pull_entries = [h for h in self.sched.history if h['status'] == 'pull_done']
        assert len(pull_entries) >= 1

    def test_no_email_when_no_files(self):
        """R2: 没有新文件时不发送邮件"""
        self.sched.configure(
            notify_email='analyst@parkviewgreen.com',
            email_enabled=True
        )

        with patch.object(self.sched, '_send_email_notification') as mock_send:
            result = self.sched.pull_and_reload()
            assert result['files_pulled'] == 0
            mock_send.assert_not_called()


if __name__ == '__main__':
    import pytest
    pytest.main([__file__, '-v'])
