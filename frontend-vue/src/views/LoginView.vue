<script setup lang="ts">
import { reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import { useUserStore } from '@/stores/user'

const router = useRouter()
const userStore = useUserStore()

const form = reactive({ username: '', password: '' })
const loading = ref(false)

const submit = async () => {
  if (!form.username.trim() || !form.password) {
    return ElMessage.warning('请输入用户名与密码')
  }
  loading.value = true
  try {
    const user = await userStore.login(form.username.trim(), form.password)
    ElMessage.success(`欢迎回来，${user.username}`)
    router.push('/dashboard')
  } catch (e: any) {
    ElMessage.error(e.response?.data?.detail || '登录失败')
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="login-wrap">
    <el-card class="login-card">
      <div class="login-title">WMS 仓储管理系统</div>
      <el-form :model="form" label-width="0" @submit.prevent="submit">
        <el-form-item>
          <el-input v-model="form.username" placeholder="用户名" size="large" clearable />
        </el-form-item>
        <el-form-item>
          <el-input v-model="form.password" type="password" placeholder="密码" size="large" show-password @keyup.enter="submit" />
        </el-form-item>
        <el-button type="primary" size="large" style="width: 100%" :loading="loading" @click="submit">
          登 录
        </el-button>
      </el-form>
    </el-card>
  </div>
</template>

<style scoped>
.login-wrap {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #0f2440 0%, #1f3a5f 100%);
}
.login-card {
  width: 380px;
  padding: 12px 8px;
  border-radius: 10px;
}
.login-title {
  font-size: 20px;
  font-weight: 700;
  text-align: center;
  letter-spacing: 1px;
  margin-bottom: 28px;
}
</style>
