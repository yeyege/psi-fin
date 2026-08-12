<script setup lang="ts">
import { onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import type { FormInstance, FormRules } from 'element-plus'
import { useUserStore } from '@/stores/user'

const REMEMBER_KEY = 'wms_remember_username'

const router = useRouter()
const userStore = useUserStore()

const formRef = ref<FormInstance>()
const loading = ref(false)
const remember = ref(true)

const form = reactive({ username: '', password: '' })

const rules: FormRules = {
  username: [{ required: true, message: '请输入用户名', trigger: 'blur' }],
  password: [{ required: true, message: '请输入密码', trigger: 'blur' }],
}

// 记住我：勾选时缓存用户名，下次登录自动填充
onMounted(() => {
  const saved = localStorage.getItem(REMEMBER_KEY)
  if (saved) {
    form.username = saved
    remember.value = true
  }
})

const submit = async () => {
  if (loading.value) return
  const valid = await formRef.value?.validate().catch(() => false)
  if (!valid) return
  loading.value = true
  try {
    await userStore.login(form.username.trim(), form.password)
    if (remember.value) {
      localStorage.setItem(REMEMBER_KEY, form.username.trim())
    } else {
      localStorage.removeItem(REMEMBER_KEY)
    }
    ElMessage.success('登录成功，欢迎回来！')
    router.push('/')
  } catch (e: any) {
    ElMessage.error(e.response?.data?.detail || '用户名或密码错误')
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="login-wrap">
    <!-- 背景装饰：光晕与网格 -->
    <div class="bg-orb bg-orb-1"></div>
    <div class="bg-orb bg-orb-2"></div>
    <div class="bg-orb bg-orb-3"></div>
    <div class="bg-grid"></div>

    <div class="login-shell">
      <!-- 左侧：品牌展示区 -->
      <section class="brand-panel">
        <div class="brand-inner">
          <div class="brand-logo">
            <el-icon :size="34"><Box /></el-icon>
          </div>
          <h1 class="brand-name">WMS · </h1>
          <p class="brand-slogan">仓库全链路数字化管理平台</p>

          <ul class="brand-features">
            <li>
              <el-icon><DataAnalysis /></el-icon>
              <span>入库 / 出库 / 库内作业全流程闭环</span>
            </li>
            <li>
              <el-icon><Cpu /></el-icon>
              <span>实时库存与波次策略智能协同</span>
            </li>
            <li>
              <el-icon><Lock /></el-icon>
              <span>角色权限与数据安全多重保障</span>
            </li>
          </ul>

          <p class="brand-copyright">© 2026 WMS · 领星 All rights reserved</p>
        </div>
      </section>

      <!-- 右侧：登录表单 -->
      <section class="form-panel">
        <div class="form-card">
          <h2 class="form-title">欢迎回来</h2>
          <p class="form-subtitle">登录您的账号，继续管理仓库</p>

          <el-form
            ref="formRef"
            :model="form"
            :rules="rules"
            label-width="0"
            size="large"
            @submit.prevent="submit"
          >
            <el-form-item prop="username">
              <el-input
                v-model="form.username"
                placeholder="用户名"
                clearable
                autocomplete="username"
                @keyup.enter="submit"
              >
                <template #prefix>
                  <el-icon><User /></el-icon>
                </template>
              </el-input>
            </el-form-item>

            <el-form-item prop="password">
              <el-input
                v-model="form.password"
                type="password"
                placeholder="密码"
                show-password
                autocomplete="current-password"
                @keyup.enter="submit"
              >
                <template #prefix>
                  <el-icon><Lock /></el-icon>
                </template>
              </el-input>
            </el-form-item>

            <div class="form-options">
              <el-checkbox v-model="remember">记住我</el-checkbox>
              <el-link type="primary" underline="never" class="forgot-link">忘记密码？</el-link>
            </div>

            <el-button
              type="primary"
              class="login-btn"
              native-type="submit"
              :loading="loading"
              :disabled="loading"
            >
              {{ loading ? '登录中...' : '登 录' }}
            </el-button>
          </el-form>
        </div>
      </section>
    </div>
  </div>
</template>

<style scoped>
.login-wrap {
  position: relative;
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  overflow: hidden;
  background: linear-gradient(135deg, #0b1026 0%, #141f3d 50%, #0d2b45 100%);
}

/* ---------- 背景装饰 ---------- */
.bg-orb {
  position: absolute;
  border-radius: 50%;
  filter: blur(90px);
  opacity: 0.55;
  pointer-events: none;
}
.bg-orb-1 {
  width: 480px;
  height: 480px;
  top: -120px;
  left: -80px;
  background: radial-gradient(circle, rgba(64, 156, 255, 0.55), transparent 70%);
}
.bg-orb-2 {
  width: 520px;
  height: 520px;
  bottom: -160px;
  right: -100px;
  background: radial-gradient(circle, rgba(124, 77, 255, 0.5), transparent 70%);
}
.bg-orb-3 {
  width: 360px;
  height: 360px;
  top: 45%;
  left: 55%;
  background: radial-gradient(circle, rgba(0, 210, 190, 0.35), transparent 70%);
}
.bg-grid {
  position: absolute;
  inset: 0;
  pointer-events: none;
  background-image:
    linear-gradient(rgba(255, 255, 255, 0.04) 1px, transparent 1px),
    linear-gradient(90deg, rgba(255, 255, 255, 0.04) 1px, transparent 1px);
  background-size: 56px 56px;
  mask-image: radial-gradient(ellipse at center, black 20%, transparent 75%);
}

/* ---------- 主体布局 ---------- */
.login-shell {
  position: relative;
  z-index: 1;
  display: flex;
  width: min(1080px, 94vw);
  min-height: 600px;
  border-radius: 24px;
  overflow: hidden;
  background: rgba(255, 255, 255, 0.05);
  border: 1px solid rgba(255, 255, 255, 0.12);
  box-shadow: 0 24px 80px rgba(0, 0, 0, 0.45);
  backdrop-filter: blur(20px);
  -webkit-backdrop-filter: blur(20px);
}

/* ---------- 左侧品牌区 ---------- */
.brand-panel {
  flex: 1.15;
  position: relative;
  display: flex;
  align-items: center;
  padding: 56px 48px;
  background:
    radial-gradient(ellipse at 20% 15%, rgba(64, 156, 255, 0.22), transparent 55%),
    linear-gradient(160deg, rgba(20, 33, 66, 0.9), rgba(13, 30, 52, 0.9));
  border-right: 1px solid rgba(255, 255, 255, 0.08);
}
.brand-inner {
  max-width: 420px;
}
.brand-logo {
  width: 64px;
  height: 64px;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #fff;
  border-radius: 18px;
  background: linear-gradient(135deg, #409eff 0%, #7c4dff 100%);
  box-shadow: 0 12px 32px rgba(64, 156, 255, 0.4);
  margin-bottom: 26px;
}
.brand-name {
  margin: 0 0 10px;
  font-size: 34px;
  font-weight: 700;
  color: #fff;
  letter-spacing: 2px;
}
.brand-slogan {
  margin: 0 0 40px;
  font-size: 15px;
  color: rgba(255, 255, 255, 0.65);
  letter-spacing: 1px;
}
.brand-features {
  list-style: none;
  margin: 0;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 18px;
}
.brand-features li {
  display: flex;
  align-items: center;
  gap: 12px;
  color: rgba(255, 255, 255, 0.78);
  font-size: 14px;
}
.brand-features .el-icon {
  color: #66b1ff;
  font-size: 18px;
}
.brand-copyright {
  position: absolute;
  bottom: 28px;
  left: 48px;
  margin: 0;
  font-size: 12px;
  color: rgba(255, 255, 255, 0.35);
}

/* ---------- 右侧表单区 ---------- */
.form-panel {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 56px 48px;
  background: rgba(255, 255, 255, 0.03);
}
.form-card {
  width: 100%;
  max-width: 380px;
}
.form-title {
  margin: 0 0 8px;
  font-size: 26px;
  font-weight: 700;
  color: #fff;
}
.form-subtitle {
  margin: 0 0 32px;
  font-size: 14px;
  color: rgba(255, 255, 255, 0.55);
}
.form-options {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin: 2px 0 24px;
}
.forgot-link {
  font-size: 13px;
}
.login-btn {
  width: 100%;
  height: 44px;
  font-size: 15px;
  letter-spacing: 4px;
  border-radius: 10px;
  background: linear-gradient(135deg, #409eff 0%, #7c4dff 100%);
  border: none;
}
.login-btn:hover,
.login-btn:focus {
  background: linear-gradient(135deg, #5aacff 0%, #8f63ff 100%);
}

/* 表单内部文字颜色适配深色背景 */
.form-card :deep(.el-input__wrapper) {
  background: rgba(255, 255, 255, 0.08);
  box-shadow: 0 0 0 1px rgba(255, 255, 255, 0.14) inset;
  border-radius: 10px;
}
.form-card :deep(.el-input__wrapper.is-focus) {
  box-shadow: 0 0 0 1px #409eff inset;
  background: rgba(255, 255, 255, 0.12);
}
.form-card :deep(.el-input__inner) {
  color: #fff;
}
.form-card :deep(.el-input__inner::placeholder) {
  color: rgba(255, 255, 255, 0.45);
}
.form-card :deep(.el-input__prefix .el-icon),
.form-card :deep(.el-input__suffix .el-icon) {
  color: rgba(255, 255, 255, 0.55);
}
.form-card :deep(.el-checkbox__label) {
  color: rgba(255, 255, 255, 0.75);
  font-size: 13px;
}
.form-card :deep(.el-checkbox__input.is-checked .el-checkbox__inner) {
  background-color: #409eff;
  border-color: #409eff;
}
.form-card :deep(.el-form-item__error) {
  color: #ff7d8a;
}

/* ---------- 响应式 ---------- */
@media (max-width: 900px) {
  .login-shell {
    min-height: auto;
  }
  .brand-panel {
    display: none;
  }
  .form-panel {
    padding: 48px 32px;
  }
}
</style>
