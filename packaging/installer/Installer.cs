using Microsoft.Win32;
using System;
using System.Diagnostics;
using System.Drawing;
using System.IO;
using System.IO.Compression;
using System.Reflection;
using System.Windows.Forms;

namespace CenturyCabinet.Setup
{
    internal static class InstallerProgram
    {
        internal const string ProductName = "21世纪内阁";
        internal const string RegistryKey = @"Software\Microsoft\Windows\CurrentVersion\Uninstall\CenturyCabinet";

        [STAThread]
        private static void Main()
        {
            Application.EnableVisualStyles();
            Application.SetCompatibleTextRenderingDefault(false);
            Application.Run(new InstallerForm());
        }

        internal static string InstallRoot
        {
            get
            {
                return Path.Combine(
                    Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData),
                    "Programs",
                    "CenturyCabinet");
            }
        }

        internal static string UserRoot
        {
            get
            {
                return Path.Combine(
                    Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData),
                    "CenturyCabinet");
            }
        }

        internal static void ValidateInstallRoot(string path)
        {
            string expected = Path.GetFullPath(InstallRoot).TrimEnd(Path.DirectorySeparatorChar);
            string actual = Path.GetFullPath(path).TrimEnd(Path.DirectorySeparatorChar);
            if (!String.Equals(expected, actual, StringComparison.OrdinalIgnoreCase))
            {
                throw new InvalidOperationException("安装目录校验失败。\r\n" + actual);
            }
        }

        internal static void StopManagedProcesses()
        {
            string logRoot = Path.Combine(UserRoot, "Data", "logs");
            foreach (string name in new[] { "site.pid", "collector.pid" })
            {
                string path = Path.Combine(logRoot, name);
                try
                {
                    if (!File.Exists(path))
                    {
                        continue;
                    }
                    int pid;
                    if (!Int32.TryParse(File.ReadAllText(path).Trim(), out pid))
                    {
                        continue;
                    }
                    Process process = Process.GetProcessById(pid);
                    string executable = process.MainModule == null ? "" : process.MainModule.FileName;
                    if (IsBelow(executable, InstallRoot))
                    {
                        process.Kill();
                        process.WaitForExit(5000);
                    }
                }
                catch
                {
                }
                try
                {
                    File.Delete(path);
                }
                catch
                {
                }
            }
        }

        internal static bool IsBelow(string candidate, string root)
        {
            if (String.IsNullOrEmpty(candidate))
            {
                return false;
            }
            string fullCandidate = Path.GetFullPath(candidate);
            string fullRoot = Path.GetFullPath(root).TrimEnd(Path.DirectorySeparatorChar) + Path.DirectorySeparatorChar;
            return fullCandidate.StartsWith(fullRoot, StringComparison.OrdinalIgnoreCase);
        }
    }

    internal sealed class InstallerForm : Form
    {
        private readonly Button installButton;
        private readonly Label statusLabel;
        private readonly ProgressBar progress;
        private readonly CheckBox launchAfterInstall;

        internal InstallerForm()
        {
            Text = "安装21世纪内阁";
            ClientSize = new Size(520, 330);
            FormBorderStyle = FormBorderStyle.FixedDialog;
            StartPosition = FormStartPosition.CenterScreen;
            MaximizeBox = false;
            MinimizeBox = false;
            BackColor = Color.FromArgb(247, 245, 239);
            Font = new Font("Microsoft YaHei UI", 9F);

            Label title = new Label();
            title.Text = "安装21世纪内阁";
            title.Font = new Font("Microsoft YaHei UI", 19F, FontStyle.Bold);
            title.ForeColor = Color.FromArgb(31, 36, 41);
            title.AutoSize = true;
            title.Location = new Point(34, 28);
            Controls.Add(title);

            Label description = new Label();
            description.Text =
                "这是面向普通用户的完整发行版。应用自带私有运行环境，" +
                "不会安装 Python、npm，不会修改 PATH，也不会弹出命令行窗口。";
            description.Location = new Point(36, 82);
            description.Size = new Size(448, 52);
            description.ForeColor = Color.FromArgb(75, 82, 87);
            Controls.Add(description);

            Label locationTitle = new Label();
            locationTitle.Text = "安装位置";
            locationTitle.Location = new Point(36, 150);
            locationTitle.AutoSize = true;
            Controls.Add(locationTitle);

            Label location = new Label();
            location.Text = InstallerProgram.InstallRoot;
            location.Location = new Point(36, 176);
            location.Size = new Size(448, 25);
            location.ForeColor = Color.FromArgb(101, 109, 115);
            Controls.Add(location);

            progress = new ProgressBar();
            progress.Location = new Point(38, 211);
            progress.Size = new Size(444, 16);
            progress.Style = ProgressBarStyle.Continuous;
            Controls.Add(progress);

            statusLabel = new Label();
            statusLabel.Text = "个人数据将单独保存在本机用户目录，升级和卸载默认保留。";
            statusLabel.Location = new Point(36, 238);
            statusLabel.Size = new Size(448, 24);
            statusLabel.ForeColor = Color.FromArgb(101, 109, 115);
            Controls.Add(statusLabel);

            launchAfterInstall = new CheckBox();
            launchAfterInstall.Text = "安装后启动21世纪内阁";
            launchAfterInstall.Checked = true;
            launchAfterInstall.Location = new Point(38, 278);
            launchAfterInstall.AutoSize = true;
            Controls.Add(launchAfterInstall);

            installButton = new Button();
            installButton.Text = Directory.Exists(InstallerProgram.InstallRoot) ? "更新" : "安装";
            installButton.Location = new Point(394, 270);
            installButton.Size = new Size(88, 38);
            installButton.Click += Install;
            Controls.Add(installButton);
            AcceptButton = installButton;
        }

        private void Install(object sender, EventArgs arguments)
        {
            installButton.Enabled = false;
            UseWaitCursor = true;
            progress.Style = ProgressBarStyle.Marquee;
            try
            {
                statusLabel.Text = "正在关闭旧版本…";
                Refresh();
                InstallerProgram.ValidateInstallRoot(InstallerProgram.InstallRoot);
                InstallerProgram.StopManagedProcesses();

                string staging = Path.Combine(Path.GetTempPath(), "CenturyCabinet-install-" + Guid.NewGuid().ToString("N"));
                Directory.CreateDirectory(staging);
                try
                {
                    statusLabel.Text = "正在解压应用文件…";
                    Refresh();
                    ExtractPayload(staging);

                    if (Directory.Exists(InstallerProgram.InstallRoot))
                    {
                        Directory.Delete(InstallerProgram.InstallRoot, true);
                    }
                    Directory.CreateDirectory(Path.GetDirectoryName(InstallerProgram.InstallRoot));
                    Directory.Move(staging, InstallerProgram.InstallRoot);
                }
                finally
                {
                    if (Directory.Exists(staging))
                    {
                        Directory.Delete(staging, true);
                    }
                }

                statusLabel.Text = "正在创建桌面和开始菜单入口…";
                Refresh();
                CreateShortcuts();
                RegisterUninstaller();

                progress.Style = ProgressBarStyle.Continuous;
                progress.Value = 100;
                statusLabel.Text = "安装完成。以后直接点击“21世纪内阁”即可使用。";
                installButton.Text = "完成";
                installButton.Click -= Install;
                installButton.Click += delegate { Close(); };
                installButton.Enabled = true;
                UseWaitCursor = false;

                if (launchAfterInstall.Checked)
                {
                    Process.Start(new ProcessStartInfo(
                        Path.Combine(InstallerProgram.InstallRoot, "21世纪内阁.exe"))
                    {
                        UseShellExecute = true,
                        WorkingDirectory = InstallerProgram.InstallRoot
                    });
                }
            }
            catch (Exception error)
            {
                progress.Style = ProgressBarStyle.Continuous;
                statusLabel.Text = "安装失败。";
                installButton.Enabled = true;
                UseWaitCursor = false;
                MessageBox.Show(error.Message, "安装失败", MessageBoxButtons.OK, MessageBoxIcon.Error);
            }
        }

        private static void ExtractPayload(string destination)
        {
            Assembly assembly = Assembly.GetExecutingAssembly();
            using (Stream resource = assembly.GetManifestResourceStream("CenturyCabinet.Payload"))
            {
                if (resource == null)
                {
                    throw new InvalidDataException("安装包中缺少应用负载。");
                }
                using (ZipArchive archive = new ZipArchive(resource, ZipArchiveMode.Read))
                {
                    string safeRoot = Path.GetFullPath(destination).TrimEnd(Path.DirectorySeparatorChar) + Path.DirectorySeparatorChar;
                    foreach (ZipArchiveEntry entry in archive.Entries)
                    {
                        string relative = entry.FullName.Replace('/', Path.DirectorySeparatorChar);
                        string target = Path.GetFullPath(Path.Combine(destination, relative));
                        if (!target.StartsWith(safeRoot, StringComparison.OrdinalIgnoreCase))
                        {
                            throw new InvalidDataException("安装包包含不安全的文件路径。");
                        }
                        if (String.IsNullOrEmpty(entry.Name))
                        {
                            Directory.CreateDirectory(target);
                            continue;
                        }
                        Directory.CreateDirectory(Path.GetDirectoryName(target));
                        using (Stream input = entry.Open())
                        using (FileStream output = new FileStream(target, FileMode.Create, FileAccess.Write, FileShare.None))
                        {
                            input.CopyTo(output);
                        }
                        if (entry.LastWriteTime != DateTimeOffset.MinValue)
                        {
                            File.SetLastWriteTimeUtc(target, entry.LastWriteTime.UtcDateTime);
                        }
                    }
                }
            }
        }

        private static void CreateShortcuts()
        {
            string executable = Path.Combine(InstallerProgram.InstallRoot, "21世纪内阁.exe");
            string uninstaller = Path.Combine(InstallerProgram.InstallRoot, "卸载21世纪内阁.exe");
            string icon = Path.Combine(InstallerProgram.InstallRoot, "cabinet-icon.ico");
            string desktop = Environment.GetFolderPath(Environment.SpecialFolder.DesktopDirectory);
            string startMenu = Path.Combine(
                Environment.GetFolderPath(Environment.SpecialFolder.Programs),
                "21世纪内阁");
            Directory.CreateDirectory(startMenu);
            ShortcutWriter.Create(
                Path.Combine(desktop, "21世纪内阁.lnk"),
                executable,
                InstallerProgram.InstallRoot,
                "启动21世纪内阁",
                icon);
            ShortcutWriter.Create(
                Path.Combine(startMenu, "21世纪内阁.lnk"),
                executable,
                InstallerProgram.InstallRoot,
                "启动21世纪内阁",
                icon);
            ShortcutWriter.Create(
                Path.Combine(startMenu, "卸载21世纪内阁.lnk"),
                uninstaller,
                InstallerProgram.InstallRoot,
                "卸载21世纪内阁",
                uninstaller);
        }

        private static void RegisterUninstaller()
        {
            string versionPath = Path.Combine(InstallerProgram.InstallRoot, "VERSION");
            string version = File.Exists(versionPath) ? File.ReadAllText(versionPath).Trim() : "1.0.2";
            using (RegistryKey key = Registry.CurrentUser.CreateSubKey(InstallerProgram.RegistryKey))
            {
                if (key == null)
                {
                    throw new InvalidOperationException("无法注册卸载程序。");
                }
                key.SetValue("DisplayName", InstallerProgram.ProductName);
                key.SetValue("DisplayVersion", version);
                key.SetValue("Publisher", "21世纪内阁");
                key.SetValue("InstallLocation", InstallerProgram.InstallRoot);
                key.SetValue("DisplayIcon", Path.Combine(InstallerProgram.InstallRoot, "cabinet-icon.ico"));
                key.SetValue("UninstallString", "\"" + Path.Combine(InstallerProgram.InstallRoot, "卸载21世纪内阁.exe") + "\"");
                key.SetValue("NoModify", 1, RegistryValueKind.DWord);
                key.SetValue("NoRepair", 1, RegistryValueKind.DWord);
            }
        }
    }
}
