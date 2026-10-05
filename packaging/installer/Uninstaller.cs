using Microsoft.Win32;
using System;
using System.Diagnostics;
using System.Drawing;
using System.IO;
using System.Runtime.InteropServices;
using System.Threading;
using System.Windows.Forms;

namespace CenturyCabinet.Uninstall
{
    internal static class UninstallerProgram
    {
        private const string RegistryKey = @"Software\Microsoft\Windows\CurrentVersion\Uninstall\CenturyCabinet";

        [DllImport("kernel32.dll", CharSet = CharSet.Unicode, SetLastError = true)]
        private static extern bool MoveFileEx(string existingFile, string newFile, int flags);

        [STAThread]
        private static void Main(string[] arguments)
        {
            Application.EnableVisualStyles();
            Application.SetCompatibleTextRenderingDefault(false);

            string installRoot = ResolveInstallRoot();
            string currentExecutable = Application.ExecutablePath;
            if (IsBelow(currentExecutable, installRoot) &&
                (arguments.Length == 0 || arguments[0] != "--from-temp"))
            {
                string temporaryCopy = Path.Combine(
                    Path.GetTempPath(),
                    "CenturyCabinet-uninstall-" + Guid.NewGuid().ToString("N") + ".exe");
                File.Copy(currentExecutable, temporaryCopy, true);
                Process.Start(new ProcessStartInfo(temporaryCopy, "--from-temp") { UseShellExecute = true });
                return;
            }

            if (arguments.Length > 0 && arguments[0] == "--from-temp")
            {
                Thread.Sleep(750);
            }

            Application.Run(new UninstallerForm(installRoot));

            if (arguments.Length > 0 && arguments[0] == "--from-temp")
            {
                MoveFileEx(currentExecutable, null, 4);
            }
        }

        internal static string ResolveInstallRoot()
        {
            using (RegistryKey key = Registry.CurrentUser.OpenSubKey(RegistryKey))
            {
                string registered = key == null ? null : key.GetValue("InstallLocation") as string;
                if (!String.IsNullOrWhiteSpace(registered))
                {
                    return registered;
                }
            }
            return Path.Combine(
                Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData),
                "Programs",
                "CenturyCabinet");
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

        internal static void ValidateExactPath(string path, string expected)
        {
            string fullPath = Path.GetFullPath(path).TrimEnd(Path.DirectorySeparatorChar);
            string fullExpected = Path.GetFullPath(expected).TrimEnd(Path.DirectorySeparatorChar);
            if (!String.Equals(fullPath, fullExpected, StringComparison.OrdinalIgnoreCase))
            {
                throw new InvalidOperationException("卸载目录校验失败。\r\n" + fullPath);
            }
        }

        internal static bool IsBelow(string candidate, string root)
        {
            if (String.IsNullOrWhiteSpace(candidate) || String.IsNullOrWhiteSpace(root))
            {
                return false;
            }
            string fullCandidate = Path.GetFullPath(candidate);
            string fullRoot = Path.GetFullPath(root).TrimEnd(Path.DirectorySeparatorChar) + Path.DirectorySeparatorChar;
            return fullCandidate.StartsWith(fullRoot, StringComparison.OrdinalIgnoreCase);
        }

        internal static void StopManagedProcesses(string installRoot)
        {
            string logRoot = Path.Combine(UserRoot, "Data", "logs");
            foreach (string name in new[] { "site.pid", "collector.pid" })
            {
                string path = Path.Combine(logRoot, name);
                try
                {
                    int pid;
                    if (!File.Exists(path) || !Int32.TryParse(File.ReadAllText(path).Trim(), out pid))
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

        internal static void DeleteDirectory(string path)
        {
            if (!Directory.Exists(path))
            {
                return;
            }
            foreach (string file in Directory.GetFiles(path, "*", SearchOption.AllDirectories))
            {
                File.SetAttributes(file, FileAttributes.Normal);
            }
            Directory.Delete(path, true);
        }

        internal static void RemoveShortcuts()
        {
            string desktopShortcut = Path.Combine(
                Environment.GetFolderPath(Environment.SpecialFolder.DesktopDirectory),
                "21世纪内阁.lnk");
            string startMenu = Path.Combine(
                Environment.GetFolderPath(Environment.SpecialFolder.Programs),
                "21世纪内阁");
            if (File.Exists(desktopShortcut))
            {
                File.Delete(desktopShortcut);
            }
            if (Directory.Exists(startMenu))
            {
                Directory.Delete(startMenu, true);
            }
            Registry.CurrentUser.DeleteSubKeyTree(RegistryKey, false);
        }
    }

    internal sealed class UninstallerForm : Form
    {
        private readonly string installRoot;
        private readonly CheckBox deleteData;
        private readonly Button uninstallButton;
        private readonly Label statusLabel;

        internal UninstallerForm(string installRootValue)
        {
            installRoot = installRootValue;
            Text = "卸载21世纪内阁";
            ClientSize = new Size(500, 288);
            FormBorderStyle = FormBorderStyle.FixedDialog;
            StartPosition = FormStartPosition.CenterScreen;
            MaximizeBox = false;
            MinimizeBox = false;
            BackColor = Color.FromArgb(247, 245, 239);
            Font = new Font("Microsoft YaHei UI", 9F);

            Label title = new Label();
            title.Text = "卸载21世纪内阁";
            title.Font = new Font("Microsoft YaHei UI", 18F, FontStyle.Bold);
            title.AutoSize = true;
            title.Location = new Point(32, 28);
            Controls.Add(title);

            Label description = new Label();
            description.Text =
                "将删除应用程序和桌面、开始菜单入口。\r\n" +
                "默认保留订阅、文章、阅读进度、札记、Cookie 和本机配置，便于以后重装。";
            description.Location = new Point(34, 82);
            description.Size = new Size(430, 58);
            description.ForeColor = Color.FromArgb(75, 82, 87);
            Controls.Add(description);

            deleteData = new CheckBox();
            deleteData.Text = "同时永久删除全部个人数据（不可恢复）";
            deleteData.Location = new Point(36, 158);
            deleteData.Size = new Size(420, 28);
            deleteData.ForeColor = Color.FromArgb(148, 54, 52);
            Controls.Add(deleteData);

            statusLabel = new Label();
            statusLabel.Text = "个人数据位置：" + UninstallerProgram.UserRoot;
            statusLabel.Location = new Point(34, 195);
            statusLabel.Size = new Size(430, 30);
            statusLabel.ForeColor = Color.FromArgb(101, 109, 115);
            Controls.Add(statusLabel);

            Button cancelButton = new Button();
            cancelButton.Text = "取消";
            cancelButton.Location = new Point(284, 232);
            cancelButton.Size = new Size(82, 36);
            cancelButton.Click += delegate { Close(); };
            Controls.Add(cancelButton);

            uninstallButton = new Button();
            uninstallButton.Text = "卸载";
            uninstallButton.Location = new Point(378, 232);
            uninstallButton.Size = new Size(86, 36);
            uninstallButton.Click += Uninstall;
            Controls.Add(uninstallButton);
            AcceptButton = uninstallButton;
            CancelButton = cancelButton;
        }

        private void Uninstall(object sender, EventArgs arguments)
        {
            if (deleteData.Checked)
            {
                DialogResult confirmation = MessageBox.Show(
                    "这会永久删除全部订阅、文章、阅读进度、札记、Cookie 和配置，且无法恢复。\r\n\r\n确定继续吗？",
                    "确认删除个人数据",
                    MessageBoxButtons.YesNo,
                    MessageBoxIcon.Warning,
                    MessageBoxDefaultButton.Button2);
                if (confirmation != DialogResult.Yes)
                {
                    return;
                }
            }

            uninstallButton.Enabled = false;
            UseWaitCursor = true;
            try
            {
                string expectedInstall = Path.Combine(
                    Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData),
                    "Programs",
                    "CenturyCabinet");
                UninstallerProgram.ValidateExactPath(installRoot, expectedInstall);
                UninstallerProgram.StopManagedProcesses(installRoot);
                UninstallerProgram.RemoveShortcuts();
                UninstallerProgram.DeleteDirectory(installRoot);

                if (deleteData.Checked)
                {
                    string expectedData = Path.Combine(
                        Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData),
                        "CenturyCabinet");
                    UninstallerProgram.ValidateExactPath(UninstallerProgram.UserRoot, expectedData);
                    UninstallerProgram.DeleteDirectory(UninstallerProgram.UserRoot);
                }

                UseWaitCursor = false;
                MessageBox.Show(
                    deleteData.Checked
                        ? "21世纪内阁及其个人数据已卸载。"
                        : "21世纪内阁已卸载，个人数据已保留。",
                    "卸载完成",
                    MessageBoxButtons.OK,
                    MessageBoxIcon.Information);
                Close();
            }
            catch (Exception error)
            {
                UseWaitCursor = false;
                uninstallButton.Enabled = true;
                statusLabel.Text = "卸载未完成。";
                MessageBox.Show(error.Message, "卸载失败", MessageBoxButtons.OK, MessageBoxIcon.Error);
            }
        }
    }
}
