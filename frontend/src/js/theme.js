/**
 * 主题管理模块
 * 支持浅色/深色/自动三种模式
 */

const ThemeManager = {
  // 主题类型
  THEMES: {
    LIGHT: 'light',
    DARK: 'dark',
    SYSTEM: 'system'
  },

  // 存储键
  STORAGE_KEY: 'theme-preference',

  /**
   * 初始化主题系统
   */
  init() {
    // 获取保存的主题偏好，默认为系统主题
    const savedTheme = this.getStoredTheme() || this.THEMES.SYSTEM;
    this.setTheme(savedTheme);

    // 监听系统主题变化
    this.watchSystemTheme();
  },

  /**
   * 获取存储的主题偏好
   */
  getStoredTheme() {
    try {
      return localStorage.getItem(this.STORAGE_KEY);
    } catch (e) {
      console.warn('无法访问 localStorage:', e);
      return null;
    }
  },

  /**
   * 保存主题偏好
   */
  saveTheme(theme) {
    try {
      localStorage.setItem(this.STORAGE_KEY, theme);
    } catch (e) {
      console.warn('无法保存主题设置:', e);
    }
  },

  /**
   * 检测系统主题偏好
   */
  getSystemTheme() {
    if (window.matchMedia && window.matchMedia('(prefers-color-scheme: dark)').matches) {
      return this.THEMES.DARK;
    }
    return this.THEMES.LIGHT;
  },

  /**
   * 监听系统主题变化
   */
  watchSystemTheme() {
    if (!window.matchMedia) return;

    const mediaQuery = window.matchMedia('(prefers-color-scheme: dark)');

    // 使用新的 addEventListener API（如果可用）
    if (mediaQuery.addEventListener) {
      mediaQuery.addEventListener('change', (e) => {
        const currentTheme = this.getStoredTheme();
        // 只在使用系统主题时自动切换
        if (currentTheme === this.THEMES.SYSTEM) {
          this.applyTheme(e.matches ? this.THEMES.DARK : this.THEMES.LIGHT);
        }
      });
    } else {
      // 降级到旧的 API
      mediaQuery.addListener((e) => {
        const currentTheme = this.getStoredTheme();
        if (currentTheme === this.THEMES.SYSTEM) {
          this.applyTheme(e.matches ? this.THEMES.DARK : this.THEMES.LIGHT);
        }
      });
    }
  },

  /**
   * 设置主题
   */
  setTheme(theme) {
    this.saveTheme(theme);

    // 如果是系统主题，应用实际的系统主题
    if (theme === this.THEMES.SYSTEM) {
      const systemTheme = this.getSystemTheme();
      this.applyTheme(systemTheme);
    } else {
      this.applyTheme(theme);
    }
  },

  /**
   * 应用主题到 DOM
   */
  applyTheme(theme) {
    const root = document.documentElement;

    if (theme === this.THEMES.DARK) {
      root.classList.add('dark');
    } else {
      root.classList.remove('dark');
    }

    // 更新 meta 主题色（用于浏览器 UI）
    this.updateMetaThemeColor(theme);
  },

  /**
   * 更新浏览器主题色
   */
  updateMetaThemeColor(theme) {
    let metaThemeColor = document.querySelector('meta[name="theme-color"]');

    if (!metaThemeColor) {
      metaThemeColor = document.createElement('meta');
      metaThemeColor.name = 'theme-color';
      document.head.appendChild(metaThemeColor);
    }

    // 设置主题色
    metaThemeColor.content = theme === this.THEMES.DARK ? '#1f2937' : '#ffffff';
  },

  /**
   * 获取当前激活的主题
   */
  getActiveTheme() {
    return document.documentElement.classList.contains('dark')
      ? this.THEMES.DARK
      : this.THEMES.LIGHT;
  },

  /**
   * 获取当前主题偏好（包括 system）
   */
  getCurrentTheme() {
    return this.getStoredTheme() || this.THEMES.SYSTEM;
  },

  /**
   * 切换到下一个主题
   */
  cycleTheme() {
    const currentTheme = this.getCurrentTheme();
    const themes = [this.THEMES.LIGHT, this.THEMES.DARK, this.THEMES.SYSTEM];
    const currentIndex = themes.indexOf(currentTheme);
    const nextIndex = (currentIndex + 1) % themes.length;
    this.setTheme(themes[nextIndex]);
    return themes[nextIndex];
  }
};

// 在 DOM 加载前就初始化，避免闪烁
ThemeManager.init();

// 导出到全局，供 Alpine.js 使用
window.ThemeManager = ThemeManager;
