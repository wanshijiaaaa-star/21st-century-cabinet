using System;
using System.Diagnostics;
using System.Drawing;
using System.IO;
using System.Net;
using System.Threading;
using System.Windows.Forms;

namespace CenturyCabinet.Launcher
{
    internal static class Program
    {
        private const string CabinetUrl = "http://127.0.0.1:4173/";
        private const string CabinetStatusUrl = "http://127.0.0.1:4173/api/status";
        private const string CollectorUrl = "http://127.0.0.1:8001/";

        [STAThread]
        private static void Main()
        {
            Application.EnableVisualStyles();
            Application.SetCompatibleTextRenderingDefault(false);

            try
            {
                string installRoot = AppDomain.CurrentDomain.BaseDirectory.TrimEnd(Path.DirectorySeparatorChar);
                string appRoot = Path.Combine(installRoot, "App");
                string runtimeRoot = Path.Combine(installRoot, "Runtime");
                string userRoot = Path.Combine(
                    Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData),
                    "CenturyCabinet");
                string dataRoot = Path.Combine(userRoot, "Data");
                string siteData = Path.Combine(dataRoot, "site");
                string collectorWork = Path.Combine(dataRoot, "collector-root");
                string collectorData = Path.Combine(collectorWork, "data");
                string logRoot = Path.Combine(dataRoot, "logs");

                ValidateRelease(installRoot, appRoot, runtimeRoot);
                PrepareUserData(appRoot, siteData, collectorWork, collectorData, logRoot);
                ConfigureEnvironment(appRoot, runtimeRoot, siteData, collectorWork, collectorData, logRoot);

                string password = null;
                bool collectorNeedsInitialization = !File.Exists(Path.Combine(collectorData, "db.db"));
                if (collectorNeedsInitialization && !UrlReady(CollectorUrl, 800))
                {
                    using (PasswordDialog dialog = new PasswordDialog())
                    {
                        if (dialog.ShowDialog() != DialogResult.OK)
                        {
                            return;
                        }
                        password = dialog.Password;
                    }
                }

                using (StartupDialog status = new StartupDialog())
                {
                    status.Show();
                    Application.DoEvents();

                    if (!UrlReady(CollectorUrl, 800))
                    {
                        status.SetStatus("正在启动公众号采集器…");
                        StartService(appRoot, runtimeRoot, "collector", password);
                    }

                    if (!UrlReady(CabinetStatusUrl, 800))
                    {
                        status.SetStatus("正在启动21世纪内阁…");
                        StartService(appRoot, runtimeRoot, "site", null);
                    }

                    status.SetStatus("正在打开主页…");
                    if (!WaitForUrl(CabinetStatusUrl, 30000))
                    {
                        throw new InvalidOperationException(
                            "本机服务未能在 30 秒内启动。\r\n\r\n请查看日志：\r\n" + logRoot);
                    }
                    status.Close();
                }

                Process.Start(new ProcessStartInfo(CabinetUrl) { UseShellExecute = true });
            }
            catch (Exception error)
            {
                MessageBox.Show(
                    error.Message,
                    "21世纪内阁启动失败",
                    MessageBoxButtons.OK,
                    MessageBoxIcon.Error);
            }
        }

        private static void ValidateRelease(string installRoot, string appRoot, string runtimeRoot)
        {
            string[] required =
            {
                Path.Combine(appRoot, "runtime_bootstrap.py"),
                Path.Combine(appRoot, "site", "local_server.py"),
                Path.Combine(appRoot, "site", "dist", "index.html"),
                Path.Combine(appRoot, "we-mp-rss", "main.py"),
                Path.Combine(runtimeRoot, "pythonw.exe")
            };
            foreach (string path in required)
            {
                if (!File.Exists(path))
                {
                    throw new FileNotFoundException("发行版文件不完整，请重新安装。", path);
                }
            }
        }

        private static void PrepareUserData(
            string appRoot,
            string siteData,
            string collectorWork,
            string collectorData,
            string logRoot)
        {
            Directory.CreateDirectory(siteData);
            Directory.CreateDirectory(collectorWork);
            Directory.CreateDirectory(collectorData);
            Directory.CreateDirectory(logRoot);

            string collectorApp = Path.Combine(appRoot, "we-mp-rss");
            SyncDirectory(Path.Combine(collectorApp, "static"), Path.Combine(collectorWork, "static"));
            SyncDirectory(Path.Combine(collectorApp, "public"), Path.Combine(collectorWork, "public"));

            string config = Path.Combine(collectorData, "config.yaml");
            if (!File.Exists(config))
            {
                File.Copy(Path.Combine(collectorApp, "config.example.yaml"), config);
            }
        }

        private static void SyncDirectory(string source, string destination)
        {
            if (!Directory.Exists(source))
            {
                return;
            }
            Directory.CreateDirectory(destination);
            foreach (string sourceFile in Directory.GetFiles(source))
            {
                string destinationFile = Path.Combine(destination, Path.GetFileName(sourceFile));
                FileInfo from = new FileInfo(sourceFile);
                FileInfo to = new FileInfo(destinationFile);
                if (!to.Exists || to.Length != from.Length || to.LastWriteTimeUtc != from.LastWriteTimeUtc)
                {
                    File.Copy(sourceFile, destinationFile, true);
                    File.SetLastWriteTimeUtc(destinationFile, from.LastWriteTimeUtc);
                }
            }
            foreach (string sourceDirectory in Directory.GetDirectories(source))
            {
                SyncDirectory(
                    sourceDirectory,
                    Path.Combine(destination, Path.GetFileName(sourceDirectory)));
            }
        }

        private static void ConfigureEnvironment(
            string appRoot,
            string runtimeRoot,
            string siteData,
            string collectorWork,
            string collectorData,
            string logRoot)
        {
            Environment.SetEnvironmentVariable("CENTURY_CABINET_RELEASE", "1");
            Environment.SetEnvironmentVariable("CENTURY_CABINET_SITE_DATA_DIR", siteData);
            Environment.SetEnvironmentVariable(
                "CENTURY_CABINET_COLLECTOR_ROOT",
                Path.Combine(appRoot, "we-mp-rss"));
            Environment.SetEnvironmentVariable("CENTURY_CABINET_COLLECTOR_WORKDIR", collectorWork);
            Environment.SetEnvironmentVariable("CENTURY_CABINET_COLLECTOR_DATA_DIR", collectorData);
            Environment.SetEnvironmentVariable(
                "CENTURY_CABINET_COLLECTOR_CONFIG",
                Path.Combine(collectorData, "config.yaml"));
            Environment.SetEnvironmentVariable(
                "CENTURY_CABINET_PYTHON",
                Path.Combine(runtimeRoot, "python.exe"));
            Environment.SetEnvironmentVariable("CENTURY_CABINET_LOG_DIR", logRoot);
            Environment.SetEnvironmentVariable("PYTHONHOME", runtimeRoot);
            Environment.SetEnvironmentVariable("PYTHONNOUSERSITE", "1");
            Environment.SetEnvironmentVariable("PYTHONUTF8", "1");
        }

        private static void StartService(
            string appRoot,
            string runtimeRoot,
            string service,
            string password)
        {
            ProcessStartInfo start = new ProcessStartInfo();
            start.FileName = Path.Combine(runtimeRoot, "pythonw.exe");
            start.Arguments = Quote(Path.Combine(appRoot, "runtime_bootstrap.py")) + " " + service;
            start.WorkingDirectory = appRoot;
            start.UseShellExecute = false;
            start.CreateNoWindow = true;
            start.WindowStyle = ProcessWindowStyle.Hidden;
            start.EnvironmentVariables["WERSS_ADMIN_USER"] = "admin";
            if (!String.IsNullOrEmpty(password))
            {
                start.EnvironmentVariables["WERSS_ADMIN_PASSWORD"] = password;
            }
            Process process = Process.Start(start);
            if (process == null)
            {
                throw new InvalidOperationException("无法启动" + service + "服务。");
            }
        }

        private static string Quote(string value)
        {
            return "\"" + value.Replace("\"", "\\\"") + "\"";
        }

        private static bool WaitForUrl(string url, int timeoutMilliseconds)
        {
            Stopwatch timer = Stopwatch.StartNew();
            while (timer.ElapsedMilliseconds < timeoutMilliseconds)
            {
                if (UrlReady(url, 900))
                {
                    return true;
                }
                Application.DoEvents();
                Thread.Sleep(350);
            }
            return false;
        }

        private static bool UrlReady(string url, int timeoutMilliseconds)
        {
            try
            {
                HttpWebRequest request = (HttpWebRequest)WebRequest.Create(url);
                request.Timeout = timeoutMilliseconds;
                request.ReadWriteTimeout = timeoutMilliseconds;
                request.AllowAutoRedirect = false;
                request.Proxy = null;
                using (HttpWebResponse response = (HttpWebResponse)request.GetResponse())
                {
                    return (int)response.StatusCode < 500;
                }
            }
            catch (WebException error)
            {
                HttpWebResponse response = error.Response as HttpWebResponse;
                return response != null && (int)response.StatusCode < 500;
            }
            catch
            {
                return false;
            }
        }
    }

    internal sealed class StartupDialog : Form
    {
        private readonly Label statusLabel;

        internal StartupDialog()
        {
            Text = "21世纪内阁";
            ClientSize = new Size(360, 118);
            FormBorderStyle = FormBorderStyle.FixedDialog;
            StartPosition = FormStartPosition.CenterScreen;
            MaximizeBox = false;
            MinimizeBox = false;
            ControlBox = false;
            ShowInTaskbar = true;
            BackColor = Color.FromArgb(247, 245, 239);

            Label title = new Label();
            title.Text = "21世纪内阁";
            title.Font = new Font("Microsoft YaHei UI", 14F, FontStyle.Bold);
            title.ForeColor = Color.FromArgb(31, 36, 41);
            title.AutoSize = true;
            title.Location = new Point(24, 20);
            Controls.Add(title);

            statusLabel = new Label();
            statusLabel.Text = "正在准备本机资料库…";
            statusLabel.Font = new Font("Microsoft YaHei UI", 9F);
            statusLabel.ForeColor = Color.FromArgb(101, 109, 115);
            statusLabel.AutoSize = true;
            statusLabel.Location = new Point(26, 68);
            Controls.Add(statusLabel);
        }

        internal void SetStatus(string value)
        {
            statusLabel.Text = value;
            Refresh();
            Application.DoEvents();
        }
    }

    internal sealed class PasswordDialog : Form
    {
        private readonly TextBox passwordBox;
        private readonly TextBox confirmationBox;
        internal string Password { get; private set; }

        internal PasswordDialog()
        {
            Text = "首次启动 · 设置管理员密码";
            ClientSize = new Size(430, 250);
            FormBorderStyle = FormBorderStyle.FixedDialog;
            StartPosition = FormStartPosition.CenterScreen;
            MaximizeBox = false;
            MinimizeBox = false;
            BackColor = Color.FromArgb(247, 245, 239);
            Font = new Font("Microsoft YaHei UI", 9F);

            Label intro = new Label();
            intro.Text = "请为本机公众号采集器设置管理员密码。\r\n用户名固定为 admin；密码只保存在这台电脑上。";
            intro.Location = new Point(24, 20);
            intro.Size = new Size(380, 48);
            Controls.Add(intro);

            Label passwordLabel = new Label();
            passwordLabel.Text = "密码";
            passwordLabel.Location = new Point(24, 82);
            passwordLabel.AutoSize = true;
            Controls.Add(passwordLabel);

            passwordBox = new TextBox();
            passwordBox.Location = new Point(112, 78);
            passwordBox.Size = new Size(286, 26);
            passwordBox.UseSystemPasswordChar = true;
            Controls.Add(passwordBox);

            Label confirmationLabel = new Label();
            confirmationLabel.Text = "确认密码";
            confirmationLabel.Location = new Point(24, 124);
            confirmationLabel.AutoSize = true;
            Controls.Add(confirmationLabel);

            confirmationBox = new TextBox();
            confirmationBox.Location = new Point(112, 120);
            confirmationBox.Size = new Size(286, 26);
            confirmationBox.UseSystemPasswordChar = true;
            Controls.Add(confirmationBox);

            Button cancelButton = new Button();
            cancelButton.Text = "取消";
            cancelButton.Location = new Point(224, 184);
            cancelButton.Size = new Size(82, 34);
            cancelButton.DialogResult = DialogResult.Cancel;
            Controls.Add(cancelButton);

            Button okButton = new Button();
            okButton.Text = "保存并启动";
            okButton.Location = new Point(316, 184);
            okButton.Size = new Size(82, 34);
            okButton.Click += SavePassword;
            Controls.Add(okButton);

            AcceptButton = okButton;
            CancelButton = cancelButton;
        }

        private void SavePassword(object sender, EventArgs arguments)
        {
            if (passwordBox.Text.Length < 6)
            {
                MessageBox.Show("密码至少需要 6 个字符。", "密码太短", MessageBoxButtons.OK, MessageBoxIcon.Warning);
                passwordBox.Focus();
                return;
            }
            if (!String.Equals(passwordBox.Text, confirmationBox.Text, StringComparison.Ordinal))
            {
                MessageBox.Show("两次输入的密码不一致。", "请重新确认", MessageBoxButtons.OK, MessageBoxIcon.Warning);
                confirmationBox.SelectAll();
                confirmationBox.Focus();
                return;
            }
            Password = passwordBox.Text;
            DialogResult = DialogResult.OK;
            Close();
        }
    }
}
