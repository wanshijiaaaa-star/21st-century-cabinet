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

        internal static string DefaultInstallRoot
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

        internal static string PreviousInstallRoot
        {
            get
            {
                using (RegistryKey key = Registry.CurrentUser.OpenSubKey(RegistryKey))
                {
                    string registered = key == null ? null : key.GetValue("InstallLocation") as string;
                    if (!String.IsNullOrWhiteSpace(registered))
                    {
                        return Path.GetFullPath(registered).TrimEnd(Path.DirectorySeparatorChar);
                    }
                }
                return IsManagedInstall(DefaultInstallRoot) ? DefaultInstallRoot : null;
            }
        }

        internal static void ValidateInstallRoot(string path)
        {
            if (String.IsNullOrWhiteSpace(path) || !Path.IsPathRooted(path))
            {
                throw new InvalidOperationException("请选择完整的安装目录。请使用 C:\\ 或其他磁盘上的路径。");
            }
            string actual = Path.GetFullPath(path).TrimEnd(Path.DirectorySeparatorChar);
            string driveRoot = Path.GetPathRoot(actual).TrimEnd(Path.DirectorySeparatorChar);
            if (String.Equals(actual, driveRoot, StringComparison.OrdinalIgnoreCase))
            {
                throw new InvalidOperationException("不能直接安装在磁盘根目录，请选择其中的子文件夹。");
            }
            string dataRoot = Path.GetFullPath(UserRoot).TrimEnd(Path.DirectorySeparatorChar);
            if (IsSameOrBelow(dataRoot, actual) || IsSameOrBelow(actual, dataRoot))
            {
                throw new InvalidOperationException("安装目录不能与个人数据目录重叠。请另选文件夹。");
            }
            foreach (string protectedRoot in new[] {
                Environment.GetFolderPath(Environment.SpecialFolder.Windows),
                Environment.GetFolderPath(Environment.SpecialFolder.System),
                Environment.GetFolderPath(Environment.SpecialFolder.ProgramFiles),
                Environment.GetFolderPath(Environment.SpecialFolder.ProgramFilesX86),
                Environment.GetFolderPath(Environment.SpecialFolder.UserProfile)
            })
            {
                if (!String.IsNullOrWhiteSpace(protectedRoot) &&
                    (String.Equals(actual, Path.GetFullPath(protectedRoot).TrimEnd(Path.DirectorySeparatorChar), StringComparison.OrdinalIgnoreCase) ||
                     IsBelow(actual, protectedRoot) &&
                     (protectedRoot == Environment.GetFolderPath(Environment.SpecialFolder.Windows) ||
                      protectedRoot == Environment.GetFolderPath(Environment.SpecialFolder.System))))
                {
                    throw new InvalidOperationException("不能安装到 Windows 系统目录或用户主目录。请另选文件夹。");
                }
            }
            for (string current = actual; !String.IsNullOrEmpty(current); current = Path.GetDirectoryName(current))
            {
                if (Directory.Exists(current) &&
                    (new DirectoryInfo(current).Attributes & FileAttributes.ReparsePoint) != 0)
                {
                    throw new InvalidOperationException("安装路径包含目录链接，无法安全更新或卸载。请另选文件夹。");
                }
                string parent = Path.GetDirectoryName(current);
                if (String.IsNullOrEmpty(parent) || String.Equals(parent, current, StringComparison.OrdinalIgnoreCase))
                {
                    break;
                }
            }
        }

        internal static bool IsManagedInstall(string path)
        {
            if (String.IsNullOrWhiteSpace(path) || !Directory.Exists(path))
            {
                return false;
            }
            return File.Exists(Path.Combine(path, "VERSION")) &&
                File.Exists(Path.Combine(path, "App", "site", "local_server.py")) &&
                File.Exists(Path.Combine(path, "Runtime", "pythonw.exe"));
        }

        internal static bool IsSameOrBelow(string candidate, string root)
        {
            string fullCandidate = Path.GetFullPath(candidate).TrimEnd(Path.DirectorySeparatorChar);
            string fullRoot = Path.GetFullPath(root).TrimEnd(Path.DirectorySeparatorChar);
            return String.Equals(fullCandidate, fullRoot, StringComparison.OrdinalIgnoreCase) ||
                fullCandidate.StartsWith(fullRoot + Path.DirectorySeparatorChar, StringComparison.OrdinalIgnoreCase);
        }

        internal static void StopManagedProcesses(string installRoot)
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
                    if (IsBelow(executable, installRoot))
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
        private readonly TextBox installPath;

        internal InstallerForm()
        {
            Text = "安装21世纪内阁";
            ClientSize = new Size(520, 364);
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

            installPath = new TextBox();
            installPath.Text = InstallerProgram.PreviousInstallRoot ?? InstallerProgram.DefaultInstallRoot;
            installPath.Location = new Point(36, 174);
            installPath.Size = new Size(354, 28);
            installPath.AccessibleName = "安装位置";
            Controls.Add(installPath);

            Button browseButton = new Button();
            browseButton.Text = "浏览…";
            browseButton.Location = new Point(398, 171);
            browseButton.Size = new Size(86, 31);
            browseButton.Click += ChooseInstallPath;
            Controls.Add(browseButton);

            progress = new ProgressBar();
            progress.Location = new Point(38, 226);
            progress.Size = new Size(444, 16);
            progress.Style = ProgressBarStyle.Continuous;
            Controls.Add(progress);

            statusLabel = new Label();
            statusLabel.Text = "个人数据将单独保存在本机用户目录，升级和卸载默认保留。";
            statusLabel.Location = new Point(36, 254);
            statusLabel.Size = new Size(448, 42);
            statusLabel.ForeColor = Color.FromArgb(101, 109, 115);
            Controls.Add(statusLabel);

            launchAfterInstall = new CheckBox();
            launchAfterInstall.Text = "安装后启动21世纪内阁";
            launchAfterInstall.Checked = true;
            launchAfterInstall.Location = new Point(38, 312);
            launchAfterInstall.AutoSize = true;
            Controls.Add(launchAfterInstall);

            installButton = new Button();
            installButton.Text = InstallerProgram.PreviousInstallRoot != null ? "更新" : "安装";
            installButton.Location = new Point(394, 304);
            installButton.Size = new Size(88, 38);
            installButton.Click += Install;
            Controls.Add(installButton);
            AcceptButton = installButton;
        }

        private void ChooseInstallPath(object sender, EventArgs arguments)
        {
            using (FolderBrowserDialog dialog = new FolderBrowserDialog())
            {
                dialog.Description = "选择21世纪内阁的程序安装目录（个人数据另存于本机用户目录）";
                dialog.SelectedPath = Directory.Exists(installPath.Text)
                    ? installPath.Text : Path.GetDirectoryName(installPath.Text);
                if (dialog.ShowDialog(this) == DialogResult.OK)
                {
                    string selected = dialog.SelectedPath;
                    if (Directory.Exists(selected) &&
                        Directory.GetFileSystemEntries(selected).Length > 0 &&
                        !InstallerProgram.IsManagedInstall(selected))
                    {
                        selected = Path.Combine(selected, "CenturyCabinet");
                    }
                    installPath.Text = selected;
                }
            }
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
                string destination = Path.GetFullPath(installPath.Text.Trim()).TrimEnd(Path.DirectorySeparatorChar);
                InstallerProgram.ValidateInstallRoot(destination);
                string previous = InstallerProgram.PreviousInstallRoot;
                if (!String.IsNullOrEmpty(previous) &&
                    !String.Equals(previous, destination, StringComparison.OrdinalIgnoreCase) &&
                    (InstallerProgram.IsSameOrBelow(destination, previous) ||
                     InstallerProgram.IsSameOrBelow(previous, destination)))
                {
                    throw new InvalidOperationException("新安装目录不能包含旧程序目录，也不能位于旧程序目录内。请另选文件夹。");
                }
                if (Directory.Exists(destination) &&
                    Directory.GetFileSystemEntries(destination).Length > 0 &&
                    !InstallerProgram.IsManagedInstall(destination))
                {
                    throw new InvalidOperationException("所选文件夹已有其他文件。请选择空文件夹或原有的21世纪内阁安装目录。");
                }
                if (!String.IsNullOrEmpty(previous) &&
                    !String.Equals(previous, destination, StringComparison.OrdinalIgnoreCase) &&
                    InstallerProgram.IsManagedInstall(destination))
                {
                    throw new InvalidOperationException("所选目录已有另一份21世纪内阁。请先选择空文件夹。");
                }
                if (!String.IsNullOrEmpty(previous) && Directory.Exists(previous))
                {
                    InstallerProgram.ValidateInstallRoot(previous);
                    if (!InstallerProgram.IsManagedInstall(previous))
                    {
                        throw new InvalidOperationException("检测到的旧安装目录不完整，已停止迁移：\r\n" + previous);
                    }
                    InstallerProgram.StopManagedProcesses(previous);
                }
                else if (InstallerProgram.IsManagedInstall(destination))
                {
                    InstallerProgram.StopManagedProcesses(destination);
                }

                string parent = Path.GetDirectoryName(destination);
                Directory.CreateDirectory(parent);
                string staging = Path.Combine(parent, ".CenturyCabinet-install-" + Guid.NewGuid().ToString("N"));
                string backup = Path.Combine(parent, ".CenturyCabinet-backup-" + Guid.NewGuid().ToString("N"));
                Directory.CreateDirectory(staging);
                try
                {
                    statusLabel.Text = "正在解压应用文件…";
                    Refresh();
                    ExtractPayload(staging);
                    ValidatePayload(staging);

                    if (Directory.Exists(destination))
                    {
                        if (Directory.GetFileSystemEntries(destination).Length == 0)
                        {
                            Directory.Delete(destination);
                        }
                        else
                        {
                            Directory.Move(destination, backup);
                        }
                    }
                    try
                    {
                        Directory.Move(staging, destination);
                    }
                    catch
                    {
                        if (Directory.Exists(backup) && !Directory.Exists(destination))
                        {
                            Directory.Move(backup, destination);
                        }
                        throw;
                    }
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
                CreateShortcuts(destination);
                RegisterUninstaller(destination);
                try
                {
                    if (Directory.Exists(backup))
                    {
                        Directory.Delete(backup, true);
                    }
                    if (!String.IsNullOrEmpty(previous) &&
                        !String.Equals(previous, destination, StringComparison.OrdinalIgnoreCase) &&
                        Directory.Exists(previous) && InstallerProgram.IsManagedInstall(previous))
                    {
                        Directory.Delete(previous, true);
                    }
                }
                catch (IOException)
                {
                    statusLabel.Text = "安装完成；旧程序目录未能清理，可稍后手动检查。";
                }
                catch (UnauthorizedAccessException)
                {
                    statusLabel.Text = "安装完成；旧程序目录未能清理，可稍后手动检查。";
                }

                progress.Style = ProgressBarStyle.Continuous;
                progress.Value = 100;
                if (!statusLabel.Text.StartsWith("安装完成；", StringComparison.Ordinal))
                {
                    statusLabel.Text = "安装完成。以后直接点击“21世纪内阁”即可使用。";
                }
                installButton.Text = "完成";
                installButton.Click -= Install;
                installButton.Click += delegate { Close(); };
                installButton.Enabled = true;
                UseWaitCursor = false;

                if (launchAfterInstall.Checked)
                {
                    Process.Start(new ProcessStartInfo(
                        Path.Combine(destination, "CenturyCabinet.exe"))
                    {
                        UseShellExecute = true,
                        WorkingDirectory = destination
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
                installPath.Focus();
            }
        }

        private static void ValidatePayload(string root)
        {
            foreach (string relative in new[] {
                "CenturyCabinet.exe",
                "Uninstall-CenturyCabinet.exe",
                "VERSION",
                @"App\site\local_server.py",
                @"Runtime\pythonw.exe"
            })
            {
                if (!File.Exists(Path.Combine(root, relative)))
                {
                    throw new InvalidDataException("安装包内文件不完整：" + relative);
                }
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
                using (ZipArchive archive = new ZipArchive(resource, ZipArchiveMode.Read, false, System.Text.Encoding.UTF8))
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

        private static void CreateShortcuts(string installRoot)
        {
            string executable = Path.Combine(installRoot, "CenturyCabinet.exe");
            string uninstaller = Path.Combine(installRoot, "Uninstall-CenturyCabinet.exe");
            string icon = Path.Combine(installRoot, "cabinet-icon.ico");
            string desktop = Environment.GetFolderPath(Environment.SpecialFolder.DesktopDirectory);
            string startMenu = Path.Combine(
                Environment.GetFolderPath(Environment.SpecialFolder.Programs),
                "21世纪内阁");
            Directory.CreateDirectory(startMenu);
            ShortcutWriter.Create(
                Path.Combine(desktop, "21世纪内阁.lnk"),
                executable,
                installRoot,
                "启动21世纪内阁",
                icon);
            ShortcutWriter.Create(
                Path.Combine(startMenu, "21世纪内阁.lnk"),
                executable,
                installRoot,
                "启动21世纪内阁",
                icon);
            ShortcutWriter.Create(
                Path.Combine(startMenu, "卸载21世纪内阁.lnk"),
                uninstaller,
                installRoot,
                "卸载21世纪内阁",
                uninstaller);
        }

        private static void RegisterUninstaller(string installRoot)
        {
            string versionPath = Path.Combine(installRoot, "VERSION");
            string version = File.Exists(versionPath) ? File.ReadAllText(versionPath).Trim() : "1.1.0";
            using (RegistryKey key = Registry.CurrentUser.CreateSubKey(InstallerProgram.RegistryKey))
            {
                if (key == null)
                {
                    throw new InvalidOperationException("无法注册卸载程序。");
                }
                key.SetValue("DisplayName", InstallerProgram.ProductName);
                key.SetValue("DisplayVersion", version);
                key.SetValue("Publisher", "21世纪内阁");
                key.SetValue("InstallLocation", installRoot);
                key.SetValue("DisplayIcon", Path.Combine(installRoot, "cabinet-icon.ico"));
                key.SetValue("UninstallString", "\"" + Path.Combine(installRoot, "Uninstall-CenturyCabinet.exe") + "\"");
                key.SetValue("NoModify", 1, RegistryValueKind.DWord);
                key.SetValue("NoRepair", 1, RegistryValueKind.DWord);
            }
        }
    }
}
