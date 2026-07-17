"""
Data Scheduler — periodic CSV pull + auto-reload + email notification service.
Singleton, configurable, with execution history.
"""
import os
import shutil
import threading
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from pathlib import Path


class DataScheduler:
    _instance = None
    _lock = threading.Lock()

    def __init__(self):
        self.watch_dir = os.environ.get('DATA_WATCH_DIR', '')
        self.interval_hours = float(os.environ.get('DATA_PULL_INTERVAL', '24'))
        self.enabled = os.environ.get('DATA_SCHEDULER_ENABLED', 'false').lower() == 'true'
        self.data_dir = os.path.join(os.path.dirname(__file__), '..', '..', 'data')

        # R2: Email notification config
        self.notify_email = os.environ.get('NOTIFY_EMAIL', '')
        self.email_enabled = os.environ.get('EMAIL_ENABLED', 'false').lower() == 'true'
        self.smtp_host = os.environ.get('SMTP_HOST', 'smtp.example.com')
        self.smtp_port = int(os.environ.get('SMTP_PORT', '587'))
        self.smtp_user = os.environ.get('SMTP_USER', '')
        self.smtp_pass = os.environ.get('SMTP_PASS', '')

        self._timer = None
        self._running = False
        self.history = []
        self._max_history = 20

    @classmethod
    def get_instance(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = cls()
            return cls._instance

    def configure(self, watch_dir=None, interval_hours=None, enabled=None, data_dir=None,
                  notify_email=None, email_enabled=None, smtp_host=None, smtp_port=None,
                  smtp_user=None, smtp_pass=None):
        if watch_dir is not None:
            self.watch_dir = watch_dir
        if interval_hours is not None:
            self.interval_hours = float(interval_hours)
        if enabled is not None:
            self.enabled = bool(enabled)
        if data_dir is not None:
            self.data_dir = data_dir
        # R2: Email config
        if notify_email is not None:
            self.notify_email = notify_email
        if email_enabled is not None:
            self.email_enabled = bool(email_enabled)
        if smtp_host is not None:
            self.smtp_host = smtp_host
        if smtp_port is not None:
            self.smtp_port = int(smtp_port)
        if smtp_user is not None:
            self.smtp_user = smtp_user
        if smtp_pass is not None:
            self.smtp_pass = smtp_pass

        if self.enabled and not self._running:
            self.start()
        elif not self.enabled and self._running:
            self.stop()

        return self.get_config()

    def get_config(self):
        return {
            'enabled': self.enabled,
            'watch_dir': self.watch_dir,
            'interval_hours': self.interval_hours,
            'running': self._running,
            'history': self.history[-5:],
            # R2: Email config in response
            'notify_email': self.notify_email,
            'email_enabled': self.email_enabled,
            'smtp_host': self.smtp_host,
            'smtp_port': self.smtp_port,
        }

    def start(self):
        if self._running:
            return True
        if not self.watch_dir or not os.path.isdir(self.watch_dir):
            self._log('start_failed', 'watch dir not found: ' + str(self.watch_dir))
            return False

        self._running = True
        self._schedule_next()
        self._log('started', 'every ' + str(self.interval_hours) + 'h scanning ' + self.watch_dir)
        return True

    def stop(self):
        self._running = False
        if self._timer:
            self._timer.cancel()
            self._timer = None
        self._log('stopped', 'scheduler stopped')

    def _schedule_next(self):
        if not self._running:
            return
        seconds = self.interval_hours * 3600
        self._timer = threading.Timer(seconds, self._run_once)
        self._timer.daemon = True
        self._timer.start()

    def _run_once(self):
        if not self._running:
            return
        try:
            result = self.pull_and_reload()
            files_pulled = result.get('files_pulled', 0)
            self._log('success', 'pulled ' + str(files_pulled) + ' files')

            # R2: Send email notification if enabled and files were pulled
            if self.email_enabled and self.notify_email and files_pulled > 0:
                try:
                    self._send_email_notification(result)
                except Exception as e:
                    self._log('email_error', str(e))
        except Exception as e:
            self._log('error', str(e))
        finally:
            self._schedule_next()

    def pull_and_reload(self):
        if not self.watch_dir or not os.path.isdir(self.watch_dir):
            return {'files_pulled': 0, 'message': 'invalid watch dir'}

        pulled = []
        watch = Path(self.watch_dir)

        file_mapping = {
            'BI_Dashboard_Ready_Data.csv': 'BI_Dashboard_Ready_Data.csv',
            'coupon.csv': 'BI_Dashboard_Ready_Data.csv',
            'input.csv': 'BI_Dashboard_Ready_Data.csv',
            '销售查询.csv': '销售查询.csv',
            'sales.csv': '销售查询.csv',
            'output.csv': '销售查询.csv',
        }

        for src_file in watch.glob('*.csv'):
            target_name = file_mapping.get(src_file.name)
            if target_name:
                dest = os.path.join(self.data_dir, target_name)
                shutil.copy2(str(src_file), dest)
                pulled.append({'src': src_file.name, 'dest': target_name})

        if pulled:
            # Only reload if data dir is the real one (not temp test dir)
            real_data = os.path.join(os.path.dirname(__file__), '..', '..', 'data')
            if os.path.abspath(self.data_dir) == os.path.abspath(real_data):
                try:
                    from webapp.services.data_service import ds
                    ds.reload()
                except Exception as e:
                    self._log('reload_error', str(e))
            self._log('pull_done', 'pulled ' + str(len(pulled)) + ' files')
        else:
            self._log('pull_empty', 'no new files found')

        return {
            'files_pulled': len(pulled),
            'files': pulled,
            'timestamp': datetime.now().isoformat(),
        }

    # R2: Email notification
    def _send_email_notification(self, pull_result):
        """Send email notification with data update summary and AI insights."""
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        files = pull_result.get('files', [])
        files_list = '\n'.join(f'  - {f["src"]} → {f["dest"]}' for f in files)

        # Try to get KPI summary
        kpi_summary = ''
        try:
            from webapp.services.data_service import ds
            from webapp.services.kpi_service import compute_all_kpis
            df_c, df_s = ds.filter()
            kpis = compute_all_kpis(df_c, df_s)
            kpi_summary = (
                f'总发券量: {kpis.get("total_issued", 0):,} 张\n'
                f'核销转化率: {kpis.get("conversion_rate", 0):.2f}%\n'
                f'总销售额: CNY {kpis.get("total_sales", 0):,.0f}\n'
                f'营销 ROI: {kpis.get("roi", 0):.1f}%\n'
                f'核销率: {kpis.get("redeem_rate", 0):.2f}%\n'
                f'客单价: CNY {kpis.get("aov", 0):,.0f}\n'
                f'会员贡献占比: {kpis.get("member_contribution", 0):.1f}%'
            )
        except Exception as e:
            kpi_summary = f'(KPI 数据获取失败: {e})'

        # Try to get AI insight summary
        ai_insight = ''
        try:
            from webapp.services.ai_service import generate_insight
            from webapp.services.kpi_service import compute_coupon_structure, compute_cohort_data, compute_lag_data
            from webapp.services.ml_service import detect_anomalies
            df_c, df_s = ds.filter()
            kpis = compute_all_kpis(df_c, df_s)
            structure = compute_coupon_structure(df_c)
            cohorts = compute_cohort_data(df_c, df_s)
            lag_data = compute_lag_data(df_c, df_s)
            anomalies = detect_anomalies(df_c, df_s)
            insight = generate_insight(kpis, structure, cohorts, lag_data, anomalies)
            ai_insight = insight.get('executive_summary', '')
            alerts = insight.get('alerts', [])
            if alerts:
                ai_insight += '\n\n关键告警:\n' + '\n'.join(
                    f'  [{a.get("severity", "")}] {a.get("message", "")}' for a in alerts[:3]
                )
        except Exception:
            ai_insight = '(AI 洞察生成失败)'

        subject = f'[侨福芳草地战情室] 数据更新通知 - {now}'
        body = f"""侨福芳草地 · 营销效能战情室 — 自动数据更新通知

更新时间: {now}
拉取文件数: {pull_result.get('files_pulled', 0)}

拉取文件:
{files_list}

核心 KPI 概览:
{kpi_summary}

AI 洞察摘要:
{ai_insight}

---
此邮件由战情室 Agent 自动生成。如需调整通知频率，请登录战情室修改配置。
"""

        msg = MIMEMultipart()
        msg['From'] = self.smtp_user or 'noreply@parkviewgreen.com'
        msg['To'] = self.notify_email
        msg['Subject'] = subject
        msg.attach(MIMEText(body, 'plain', 'utf-8'))

        try:
            if self.smtp_port == 465:
                server = smtplib.SMTP_SSL(self.smtp_host, self.smtp_port, timeout=15)
            else:
                server = smtplib.SMTP(self.smtp_host, self.smtp_port, timeout=15)
                server.starttls()
            if self.smtp_user and self.smtp_pass:
                server.login(self.smtp_user, self.smtp_pass)
            server.sendmail(msg['From'], [self.notify_email], msg.as_string())
            server.quit()
            self._log('email_sent', f'通知邮件已发送至 {self.notify_email}')
        except Exception as e:
            self._log('email_error', f'邮件发送失败: {e}')
            raise

    def _log(self, status, message):
        entry = {
            'time': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
            'status': status,
            'message': message,
        }
        self.history.append(entry)
        if len(self.history) > self._max_history:
            self.history = self.history[-self._max_history:]
