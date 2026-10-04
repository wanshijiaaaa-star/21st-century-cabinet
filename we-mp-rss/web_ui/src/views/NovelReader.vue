<template>
  <div class="novel-reader">
    <!-- 顶部搜索栏 -->
    <div class="search-bar">
      <input type="text" placeholder="搜索小说" />
      <button>搜索</button>
    </div>

    <!-- 公告 -->
    <div class="announcement">
      <p>最新公告：欢迎使用小说阅读器！</p>
    </div>

    <!-- 分类导航 -->
    <div class="category-nav">
      <div class="category-item" v-for="category in categories" :key="category.id">
        {{ category.name }}
      </div>
    </div>

    <!-- 小说列表 -->
    <div class="novel-list">
      <div class="novel-item" v-for="novel in novels" :key="novel.id">
        <h3>{{ novel.title }}</h3>
        <p>{{ novel.description }}</p>
      </div>
    </div>

    <!-- 阅读页面 -->
    <div class="reading-page" v-if="isReading">
      <div class="content" @click="toggleMenu">
        {{ currentContent }}
      </div>

      <!-- 左侧滑出目录 -->
      <div class="drawer" :class="{ 'open': isDrawerOpen }">
        <div class="drawer-content">
          <h3>目录</h3>
          <ul>
            <li v-for="chapter in chapters" :key="chapter.id">
              {{ chapter.title }}
            </li>
          </ul>
        </div>
      </div>

      <!-- 菜单和设置 -->
      <div class="menu" v-if="isMenuOpen">
        <button @click="prevPage">上一页</button>
        <button @click="nextPage">下一页</button>
        <button @click="toggleDrawer">目录</button>
      </div>
    </div>

    <!-- 出错界面 -->
    <div class="error-page" v-if="hasError">
      <p>网络错误，请重试！</p>
      <button @click="retry">重试</button>
    </div>
  </div>
</template>

<script>
export default {
  data() {
    return {
      categories: [
        { id: 1, name: '玄幻' },
        { id: 2, name: '都市' },
        { id: 3, name: '科幻' },
      ],
      novels: [
        { id: 1, title: '小说1', description: '这是一本小说' },
        { id: 2, title: '小说2', description: '这是另一本小说' },
      ],
      chapters: [
        { id: 1, title: '第一章' },
        { id: 2, title: '第二章' },
      ],
      currentContent: '这里是小说正文内容...',
      isReading: false,
      isDrawerOpen: false,
      isMenuOpen: false,
      hasError: false,
    };
  },
  methods: {
    toggleMenu() {
      this.isMenuOpen = !this.isMenuOpen;
    },
    toggleDrawer() {
      this.isDrawerOpen = !this.isDrawerOpen;
    },
    prevPage() {
      // 上一页逻辑
    },
    nextPage() {
      // 下一页逻辑
    },
    retry() {
      // 重试逻辑
    },
  },
};
</script>

<style scoped>
.novel-reader {
  font-family: Arial, sans-serif;
  max-width: 800px;
  margin: 0 auto;
  padding: 20px;
}

.search-bar {
  display: flex;
  margin-bottom: 20px;
}

.search-bar input {
  flex: 1;
  padding: 10px;
  border: 1px solid #ccc;
  border-radius: 4px;
}

.search-bar button {
  padding: 10px;
  margin-left: 10px;
  background-color: #007bff;
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
}

.announcement {
  background-color: #f8f9fa;
  padding: 10px;
  margin-bottom: 20px;
  border-radius: 4px;
}

.category-nav {
  display: flex;
  margin-bottom: 20px;
}

.category-item {
  padding: 10px;
  margin-right: 10px;
  background-color: #e9ecef;
  border-radius: 4px;
  cursor: pointer;
}

.novel-list {
  margin-bottom: 20px;
}

.novel-item {
  padding: 15px;
  margin-bottom: 10px;
  background-color: #f8f9fa;
  border-radius: 4px;
}

.reading-page {
  position: relative;
}

.content {
  padding: 20px;
  background-color: #fff;
  border-radius: 4px;
  cursor: pointer;
}

.drawer {
  position: fixed;
  top: 0;
  left: -300px;
  width: 300px;
  height: 100%;
  background-color: #fff;
  transition: left 0.3s;
  z-index: 1000;
}

.drawer.open {
  left: 0;
}

.drawer-content {
  padding: 20px;
}

.menu {
  position: fixed;
  bottom: 20px;
  left: 50%;
  transform: translateX(-50%);
  display: flex;
  background-color: rgba(0, 0, 0, 0.7);
  padding: 10px;
  border-radius: 4px;
}

.menu button {
  margin: 0 5px;
  padding: 5px 10px;
  background-color: #007bff;
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
}

.error-page {
  text-align: center;
  padding: 20px;
  background-color: #f8d7da;
  border-radius: 4px;
}

.error-page button {
  padding: 10px;
  background-color: #dc3545;
  color: white;
  border: none;
  border-radius: 4px;
  cursor: pointer;
}
</style>