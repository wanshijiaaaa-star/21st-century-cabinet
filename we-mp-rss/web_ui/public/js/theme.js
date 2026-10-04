// 主题切换功能
document.addEventListener('DOMContentLoaded', function() {
    // 移动端菜单切换
    var menuToggle = document.getElementById('menuToggle');
    var nav = document.getElementById('nav-menu');
    
    if (menuToggle && nav) {
        menuToggle.addEventListener('click', function(e) {
            e.stopPropagation();
            nav.classList.toggle('active');
        });
    }
    
    // 点击外部关闭菜单
    document.addEventListener('click', function(event) {
        if (nav && menuToggle && !nav.contains(event.target) && !menuToggle.contains(event.target)) {
            nav.classList.remove('active');
        }
    });
    
    // 主题切换按钮
    var themeToggleBtn = document.getElementById('themeToggleBtn');
    var themeDropdown = document.getElementById('themeDropdown');
    
    if (themeToggleBtn && themeDropdown) {
        themeToggleBtn.addEventListener('click', function(e) {
            e.stopPropagation();
            themeDropdown.classList.toggle('show');
        });
    }
    
    // 主题选项点击
    var themeOptions = document.querySelectorAll('.theme-option');
    themeOptions.forEach(function(option) {
        option.addEventListener('click', function(e) {
            e.stopPropagation();
            var theme = this.getAttribute('data-theme');
            setTheme(theme);
        });
    });
    
    // 点击外部关闭主题下拉菜单
    document.addEventListener('click', function(event) {
        if (themeDropdown && themeToggleBtn) {
            if (!themeDropdown.contains(event.target) && !themeToggleBtn.contains(event.target)) {
                themeDropdown.classList.remove('show');
            }
        }
    });
    
    // 页面加载时恢复主题
    var savedTheme = localStorage.getItem('theme') || 'default';
    if (savedTheme !== 'default') {
        document.documentElement.setAttribute('data-theme', savedTheme);
    }
    updateThemeActiveState(savedTheme);
});

function setTheme(theme) {
    if (theme === 'default') {
        document.documentElement.removeAttribute('data-theme');
    } else {
        document.documentElement.setAttribute('data-theme', theme);
    }
    localStorage.setItem('theme', theme);
    updateThemeActiveState(theme);
    var dropdown = document.getElementById('themeDropdown');
    if (dropdown) dropdown.classList.remove('show');
}

function updateThemeActiveState(theme) {
    var options = document.querySelectorAll('.theme-option');
    options.forEach(function(option) {
        option.classList.remove('active');
        if (option.getAttribute('data-theme') === theme) {
            option.classList.add('active');
        }
    });
}
