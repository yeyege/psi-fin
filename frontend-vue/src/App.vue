<script setup lang="ts">
import { computed } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { useUserStore } from '@/stores/user'

const route = useRoute()
const router = useRouter()
const userStore = useUserStore()

const activeMenu = computed(() => {
  // 高亮一级菜单；子路由也归到对应一级菜单（本应用为扁平路由）
  return route.path
})
// 登录页全屏展示，不渲染侧边栏布局
const isLoginPage = computed(() => route.path === '/login')
const displayName = computed(() => userStore.user?.username || '未登录')
const roleLabel = computed(() => (userStore.user?.role === 'admin' ? '管理员' : '操作员'))

const handleLogin = () => router.push('/login')

const handleLogout = async () => {
  await userStore.logout()
  ElMessage.success('已退出登录')
  router.push('/login')
}
</script>

<template>
  <el-container v-if="!isLoginPage" style="min-height: 100vh">
    <el-aside width="220px" style="background: #001529; color: #fff">
      <div class="logo">WMS 仓储管理系统</div>
      <el-menu
        :default-active="activeMenu"
        router
        background-color="#001529"
        text-color="rgba(255,255,255,0.68)"
        active-text-color="#fff"
        style="border-right: none"
      >
        <el-menu-item index="/dashboard">
          <el-icon><Odometer /></el-icon><span>数据看板</span>
        </el-menu-item>
        <el-menu-item index="/inventory">
          <el-icon><DataBoard /></el-icon><span>库存查询</span>
        </el-menu-item>
        <el-menu-item index="/flows">
          <el-icon><List /></el-icon><span>库存流水</span>
        </el-menu-item>
        <el-menu-item index="/batches">
          <el-icon><Box /></el-icon><span>批次管理</span>
        </el-menu-item>
        <el-menu-item index="/inbound">
          <el-icon><Download /></el-icon><span>入库管理</span>
        </el-menu-item>
        <el-menu-item index="/outbound">
          <el-icon><Upload /></el-icon><span>出库管理</span>
        </el-menu-item>
        <el-menu-item index="/waves">
          <el-icon><Files /></el-icon><span>波次拣货</span>
        </el-menu-item>
        <el-menu-item index="/returns">
          <el-icon><RefreshLeft /></el-icon><span>退货管理</span>
        </el-menu-item>
        <el-menu-item index="/transfers">
          <el-icon><Switch /></el-icon><span>库内移库</span>
        </el-menu-item>
        <el-menu-item index="/adjustments">
          <el-icon><EditPen /></el-icon><span>库存调整</span>
        </el-menu-item>
        <el-menu-item index="/products">
          <el-icon><Goods /></el-icon><span>商品管理</span>
        </el-menu-item>
        <el-menu-item index="/customers">
          <el-icon><User /></el-icon><span>客户管理</span>
        </el-menu-item>
        <el-menu-item index="/warehouses">
          <el-icon><OfficeBuilding /></el-icon><span>仓库库位</span>
        </el-menu-item>
        <el-menu-item v-if="userStore.isAdmin" index="/users">
          <el-icon><Setting /></el-icon><span>用户管理</span>
        </el-menu-item>
      </el-menu>
    </el-aside>

    <el-container>
      <el-header class="app-header">
        <span class="page-title">{{ route.meta?.title || 'WMS' }}</span>
        <div class="header-right">
          <template v-if="userStore.isLoggedIn">
            <el-tag size="small" :type="userStore.isAdmin ? 'danger' : 'info'">{{ roleLabel }}</el-tag>
            <span class="user-name">{{ displayName }}</span>
            <el-button size="small" @click="handleLogout">退出</el-button>
          </template>
          <el-button v-else size="small" type="primary" @click="handleLogin">登录</el-button>
        </div>
      </el-header>
      <el-main style="padding: 20px; background: #f5f7fa">
        <router-view />
      </el-main>
    </el-container>
  </el-container>
  <router-view v-else />
</template>

<style>
body {
  margin: 0;
  font-family: 'Helvetica Neue', Helvetica, 'PingFang SC', 'Hiragino Sans GB', Arial, sans-serif;
}
.logo {
  height: 56px;
  line-height: 56px;
  text-align: center;
  font-size: 16px;
  font-weight: 700;
  color: #fff;
  border-bottom: 1px solid rgba(255, 255, 255, 0.1);
}
.app-header {
  background: #fff;
  display: flex;
  align-items: center;
  justify-content: space-between;
  border-bottom: 1px solid #e4e7ed;
}
.page-title {
  font-size: 16px;
  font-weight: 600;
}
.header-right {
  display: flex;
  align-items: center;
  gap: 10px;
}
.user-name {
  font-size: 14px;
  color: #303133;
}
</style>
