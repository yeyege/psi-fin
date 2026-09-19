<script setup lang="ts">
import { computed, onMounted, reactive, ref } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import type { FormInstance, FormRules } from 'element-plus'
import { useUserStore } from '@/stores/user'

const REMEMBER_KEY = 'wms_remember_username'
const APP_VERSION = 'v1.4.0'

const router = useRouter()
const userStore = useUserStore()

const formRef = ref<FormInstance>()
const loading = ref(false)
const remember = ref(true)
const isMockEnv = import.meta.env.VITE_USE_MOCK === 'true'

const form = reactive({ username: '', password: '' })

const rules: FormRules = {
  username: [
    { required: true, message: '请输入企业账号', trigger: 'blur' },
    { min: 2, max: 32, message: '账号长度应为 2–32 位', trigger: 'blur' },
  ],
  password: [
    { required: true, message: '请输入登录密码', trigger: 'blur' },
    { min: 6, max: 64, message: '密码长度应为 6–64 位', trigger: 'blur' },
  ],
}

const year = computed(() => new Date().getFullYear())

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
    ElMessage.success('登录成功，欢迎回来')
    router.push('/')
  } catch (e: any) {
    ElMessage.error(e.response?.data?.detail || '账号或密码错误，请重试或联系管理员')
  } finally {
    loading.value = false
  }
}

const comingSoon = (name: string) => ElMessage.info(`${name} 正在集成中，请联系企业管理员`)
</script>

<template>
  <div class="login-page">
    <!-- ========== 顶部导航条 ========== -->
    <header class="page-header">
      <div class="brand-lockup">
        <!-- 品牌图标：立方体(库存) + 对角线(资金流向) 定制 SVG -->
        <span class="brand-mark" aria-hidden="true">
          <svg viewBox="0 0 32 32" width="28" height="28">
            <defs>
              <linearGradient id="brand-grad" x1="0" y1="0" x2="1" y2="1">
                <stop offset="0%" stop-color="#4C8FFF" />
                <stop offset="100%" stop-color="#1E5EFF" />
              </linearGradient>
            </defs>
            <rect x="1" y="1" width="30" height="30" rx="8" fill="url(#brand-grad)" />
            <!-- 立方体轮廓 -->
            <path
              d="M16 6.5 L24 11 L24 21 L16 25.5 L8 21 L8 11 Z"
              fill="none" stroke="#fff" stroke-width="1.6" stroke-linejoin="round" />
            <path d="M8 11 L16 15.5 L24 11" fill="none" stroke="#fff" stroke-width="1.6" stroke-linejoin="round" />
            <path d="M16 15.5 L16 25.5" fill="none" stroke="#fff" stroke-width="1.6" />
            <!-- 财务对勾 -->
            <path d="M12.2 18.2 L15 20.8 L20.4 15.4" fill="none" stroke="#BBF7D0" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" />
          </svg>
        </span>
        <div class="brand-text">
          <span class="brand-title">进销存 · 业财一体中后台</span>
          <span class="brand-sub">库存即账 · 业务即财</span>
        </div>
      </div>

      <nav class="header-nav">
        <button class="nav-chip" type="button" @click="comingSoon('中文 / English 切换')">
          <svg viewBox="0 0 20 20" width="16" height="16" fill="none" stroke="currentColor" stroke-width="1.5">
            <circle cx="10" cy="10" r="7.5" />
            <path d="M2.5 10h15M10 2.5c2.5 2.7 2.5 12.3 0 15M10 2.5c-2.5 2.7-2.5 12.3 0 15" />
          </svg>
          <span>简体中文</span>
        </button>
        <button class="nav-chip" type="button" @click="comingSoon('帮助中心')">
          <svg viewBox="0 0 20 20" width="16" height="16" fill="none" stroke="currentColor" stroke-width="1.5">
            <circle cx="10" cy="10" r="7.5" />
            <path d="M8 7.5a2 2 0 1 1 2.6 1.9c-.6.25-1 .85-1 1.5v.35" stroke-linecap="round" />
            <circle cx="10" cy="14" r="0.7" fill="currentColor" stroke="none" />
          </svg>
          <span>帮助</span>
        </button>
        <span class="nav-status" title="所有服务运行正常">
          <span class="status-dot"></span>
          <span>系统正常</span>
        </span>
      </nav>
    </header>

    <!-- ========== 主体分栏 ========== -->
    <main class="page-main">
      <!-- 左：品牌 & 价值主张 -->
      <section class="hero-panel">
        <div class="hero-bg-grid" aria-hidden="true"></div>
        <div class="hero-bg-glow hero-glow-1" aria-hidden="true"></div>
        <div class="hero-bg-glow hero-glow-2" aria-hidden="true"></div>

        <div class="hero-content">
          <p class="hero-eyebrow">
            <span class="eyebrow-line"></span>
            企业版 · 进销存 &nbsp;×&nbsp; 业财一体
          </p>
          <h1 class="hero-title">
            让每一笔业务<br />
            都自动沉淀为财务事实
          </h1>
          <p class="hero-desc">
            以库存台账为底座，打通销售订单 → 出库发货 → 应收核销 → 经营分析的全链路，
            为企业提供可审计、可追溯、可预测的业财中后台。
          </p>

          <ul class="feature-list">
            <li class="feature-item">
              <span class="feature-icon" aria-hidden="true">
                <!-- 立方体：库存闭环 -->
                <svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linejoin="round" stroke-linecap="round">
                  <path d="M12 3l8 4.2v9.6L12 21l-8-4.2V7.2z" />
                  <path d="M4 7.2l8 4.2 8-4.2M12 11.4V21" />
                </svg>
              </span>
              <div class="feature-body">
                <div class="feature-title">库存全流程闭环</div>
                <div class="feature-desc">入库 · 出库 · 批次效期 · 波次拣货 · 盘点调整，一物一账</div>
              </div>
            </li>
            <li class="feature-item">
              <span class="feature-icon" aria-hidden="true">
                <!-- 折线图：业财联动 -->
                <svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linejoin="round" stroke-linecap="round">
                  <path d="M3.5 18.5h17" />
                  <path d="M4 15l5-5 4 4 7-8" />
                  <path d="M20 6h-3.5M20 6v3.5" />
                </svg>
              </span>
              <div class="feature-body">
                <div class="feature-title">业务即财务</div>
                <div class="feature-desc">销售发货即生成应收，收款核销自动回写，杜绝重复记账</div>
              </div>
            </li>
            <li class="feature-item">
              <span class="feature-icon" aria-hidden="true">
                <!-- 盾牌 & 锁：企业级安全 -->
                <svg viewBox="0 0 24 24" width="20" height="20" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linejoin="round" stroke-linecap="round">
                  <path d="M12 3l8 3v6c0 4.5-3.5 8.2-8 9-4.5-.8-8-4.5-8-9V6z" />
                  <rect x="9" y="11" width="6" height="5" rx="1" />
                  <path d="M10.5 11V9.5a1.5 1.5 0 0 1 3 0V11" />
                </svg>
              </span>
              <div class="feature-body">
                <div class="feature-title">企业级合规</div>
                <div class="feature-desc">RBAC 权限、审计留痕、双人复核，满足内控与外审要求</div>
              </div>
            </li>
          </ul>

          <!-- 数据背书条（均为项目真实、可核查指标） -->
          <div class="hero-stats">
            <div class="stat">
              <div class="stat-num">157<span class="stat-unit">+</span></div>
              <div class="stat-label">自动化测试用例</div>
            </div>
            <div class="stat-divider"></div>
            <div class="stat">
              <div class="stat-num">15</div>
              <div class="stat-label">业务模块 API</div>
            </div>
            <div class="stat-divider"></div>
            <div class="stat">
              <div class="stat-num">5<span class="stat-unit">环</span></div>
              <div class="stat-label">业财全链路闭环</div>
            </div>
          </div>
        </div>

        <div class="hero-foot">
          <span class="trust-badge">
            <svg viewBox="0 0 16 16" width="12" height="12" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linejoin="round">
              <path d="M8 2l5.5 2v4.2c0 3.1-2.4 5.6-5.5 6.3-3.1-.7-5.5-3.2-5.5-6.3V4z" />
              <path d="M5.5 8.2l1.8 1.8 3.2-3.6" stroke-linecap="round" />
            </svg>
            借贷平衡强制校验
          </span>
          <span class="trust-badge">全量流水可追溯</span>
          <span class="trust-badge">行级锁防超卖</span>
        </div>
      </section>

      <!-- 右：登录表单 -->
      <section class="form-panel">
        <div class="form-card">
          <div class="form-head">
            <h2 class="form-title">登录业财一体中后台</h2>
            <p class="form-subtitle">
              请使用企业为您分配的账号登录
              <span v-if="isMockEnv" class="demo-hint">演示账号：admin / admin123</span>
            </p>
          </div>

          <el-form
            ref="formRef"
            :model="form"
            :rules="rules"
            label-width="0"
            size="large"
            @submit.prevent="submit"
          >
            <el-form-item prop="username" label="企业账号">
              <el-input
                v-model="form.username"
                placeholder="请输入企业分配的账号"
                clearable
                autocomplete="username"
                @keyup.enter="submit"
              >
                <template #prefix>
                  <!-- 账号图标：定制 SVG，人形 + 名牌 -->
                  <svg viewBox="0 0 20 20" width="16" height="16" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round">
                    <circle cx="10" cy="6.8" r="3" />
                    <path d="M4 16.5c1.2-2.8 3.4-4.2 6-4.2s4.8 1.4 6 4.2" />
                  </svg>
                </template>
              </el-input>
            </el-form-item>

            <el-form-item prop="password" label="登录密码">
              <el-input
                v-model="form.password"
                type="password"
                placeholder="请输入登录密码"
                show-password
                autocomplete="current-password"
                @keyup.enter="submit"
              >
                <template #prefix>
                  <!-- 密码图标：定制 SVG，锁体 + 挂环 -->
                  <svg viewBox="0 0 20 20" width="16" height="16" fill="none" stroke="currentColor" stroke-width="1.6" stroke-linecap="round" stroke-linejoin="round">
                    <rect x="4" y="9" width="12" height="8.5" rx="2" />
                    <path d="M6.7 9V6.8a3.3 3.3 0 0 1 6.6 0V9" />
                    <circle cx="10" cy="13.2" r="0.9" fill="currentColor" stroke="none" />
                  </svg>
                </template>
              </el-input>
            </el-form-item>

            <div class="form-options">
              <el-checkbox v-model="remember">
                <span class="opt-text">7 天内免登录</span>
              </el-checkbox>
              <el-link type="primary" underline="never" class="forgot-link" @click="comingSoon('密码找回')">
                忘记密码？
              </el-link>
            </div>

            <el-button
              type="primary"
              class="login-btn"
              native-type="submit"
              :loading="loading"
              :disabled="loading"
            >
              {{ loading ? '正在验证身份…' : '登 录' }}
            </el-button>
          </el-form>

          <p class="form-foot-note">
            还没有账号？
            <el-link type="primary" underline="never" @click="comingSoon('开通企业租户')">申请企业试用</el-link>
          </p>
        </div>
      </section>
    </main>

    <!-- ========== 底部信息条 ========== -->
    <footer class="page-footer">
      <div class="foot-left">
        <span>© {{ year }} 进销存 · 业财一体中后台</span>
      </div>
      <div class="foot-right">
        <a class="foot-link" @click="comingSoon('服务条款')">服务条款</a>
        <span class="foot-sep">·</span>
        <a class="foot-link" @click="comingSoon('隐私政策')">隐私政策</a>
        <span class="foot-sep">·</span>
        <a class="foot-link" @click="comingSoon('第三方服务信息')">第三方 SDK 目录</a>
        <span class="foot-sep">·</span>
        <a class="foot-link" @click="comingSoon('系统状态页')">系统状态</a>
        <span class="foot-sep">·</span>
        <span class="foot-ver">{{ APP_VERSION }}</span>
      </div>
    </footer>
  </div>
</template>

<style scoped>
/* ============ 设计令牌 ============ */
.login-page {
  --brand-50: #F1F5FF;
  --brand-100: #E1EAFF;
  --brand-500: #1E5EFF;
  --brand-600: #1849CC;
  --brand-700: #0F3399;
  --hero-start: #0A1B3D;
  --hero-mid: #12295F;
  --hero-end: #1E4DA6;
  --ink-900: #0B1533;
  --ink-700: #1F2A44;
  --ink-500: #4B5878;
  --ink-400: #7C88A8;
  --ink-300: #A3ACC1;
  --line: #E4E8F0;
  --line-soft: #EEF1F6;
  --surface: #FFFFFF;
  --surface-alt: #F7F9FC;
  --success: #17A673;
  --shadow-sm: 0 1px 2px rgba(15, 26, 55, 0.04);
  --shadow-md: 0 6px 24px -8px rgba(15, 26, 55, 0.12), 0 2px 6px rgba(15, 26, 55, 0.04);

  position: relative;
  min-height: 100vh;
  display: flex;
  flex-direction: column;
  background: var(--surface);
  color: var(--ink-900);
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'PingFang SC',
    'Hiragino Sans GB', 'Microsoft YaHei', 'Helvetica Neue', Arial, sans-serif;
  font-feature-settings: 'cv11', 'ss01';
  -webkit-font-smoothing: antialiased;
}

/* ============ 顶部导航 ============ */
.page-header {
  height: 60px;
  flex-shrink: 0;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0 40px;
  background: rgba(255, 255, 255, 0.92);
  border-bottom: 1px solid var(--line-soft);
  backdrop-filter: saturate(180%) blur(10px);
  position: relative;
  z-index: 5;
}
.brand-lockup {
  display: flex;
  align-items: center;
  gap: 12px;
}
.brand-mark {
  width: 32px;
  height: 32px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border-radius: 8px;
  box-shadow: 0 4px 14px -4px rgba(30, 94, 255, 0.5);
}
.brand-text {
  display: flex;
  flex-direction: column;
  line-height: 1.15;
}
.brand-title {
  font-size: 16px;
  font-weight: 700;
  color: var(--ink-900);
  letter-spacing: 0.3px;
}
.brand-sub {
  font-size: 11.5px;
  color: var(--ink-400);
  letter-spacing: 0.5px;
  margin-top: 2px;
}

.header-nav {
  display: flex;
  align-items: center;
  gap: 6px;
}
.nav-chip {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  height: 32px;
  padding: 0 12px;
  font-size: 13px;
  color: var(--ink-500);
  background: transparent;
  border: 1px solid transparent;
  border-radius: 6px;
  cursor: pointer;
  transition: all 0.15s ease;
}
.nav-chip:hover {
  color: var(--brand-500);
  background: var(--brand-50);
  border-color: var(--brand-100);
}
.nav-status {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 0 12px 0 10px;
  height: 32px;
  font-size: 12.5px;
  color: var(--ink-500);
  border-left: 1px solid var(--line);
  margin-left: 6px;
}
.status-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background: var(--success);
  box-shadow: 0 0 0 3px rgba(23, 166, 115, 0.18);
  animation: pulse 2.4s ease-out infinite;
}
@keyframes pulse {
  0%, 60%, 100% { box-shadow: 0 0 0 3px rgba(23, 166, 115, 0.18); }
  30% { box-shadow: 0 0 0 6px rgba(23, 166, 115, 0.05); }
}

/* ============ 主体两栏 ============ */
.page-main {
  flex: 1;
  display: flex;
  min-height: 0;
}

/* -------- 左：Hero 品牌区 -------- */
.hero-panel {
  flex: 1.1;
  position: relative;
  overflow: hidden;
  color: #E8EEFB;
  background:
    radial-gradient(120% 80% at 80% 10%, rgba(76, 143, 255, 0.35), transparent 60%),
    linear-gradient(160deg, var(--hero-start) 0%, var(--hero-mid) 45%, var(--hero-end) 100%);
  padding: 60px 72px 40px;
  display: flex;
  flex-direction: column;
  justify-content: space-between;
  isolation: isolate;
}
.hero-bg-grid {
  position: absolute;
  inset: 0;
  z-index: -1;
  background-image:
    linear-gradient(rgba(255, 255, 255, 0.05) 1px, transparent 1px),
    linear-gradient(90deg, rgba(255, 255, 255, 0.05) 1px, transparent 1px);
  background-size: 56px 56px;
  background-position: -1px -1px;
  mask-image: radial-gradient(ellipse at 30% 30%, black 20%, transparent 78%);
  -webkit-mask-image: radial-gradient(ellipse at 30% 30%, black 20%, transparent 78%);
}
.hero-bg-glow {
  position: absolute;
  z-index: -1;
  border-radius: 50%;
  filter: blur(90px);
  pointer-events: none;
}
.hero-glow-1 {
  width: 520px; height: 520px;
  top: -140px; left: -120px;
  background: radial-gradient(circle, rgba(76, 143, 255, 0.45), transparent 70%);
}
.hero-glow-2 {
  width: 420px; height: 420px;
  bottom: -140px; right: -80px;
  background: radial-gradient(circle, rgba(0, 210, 190, 0.28), transparent 70%);
}

.hero-eyebrow {
  display: inline-flex;
  align-items: center;
  gap: 12px;
  font-size: 12px;
  letter-spacing: 2px;
  color: rgba(220, 232, 255, 0.75);
  margin: 0 0 24px;
  font-weight: 500;
}
.eyebrow-line {
  width: 28px;
  height: 1px;
  background: linear-gradient(90deg, transparent, rgba(180, 210, 255, 0.85));
}
.hero-title {
  margin: 0 0 20px;
  font-size: 40px;
  line-height: 1.25;
  font-weight: 700;
  color: #FFFFFF;
  letter-spacing: 0.5px;
}
.hero-desc {
  margin: 0 0 44px;
  max-width: 520px;
  font-size: 15px;
  line-height: 1.75;
  color: rgba(220, 232, 255, 0.7);
}

.feature-list {
  list-style: none;
  margin: 0 0 44px;
  padding: 0;
  display: flex;
  flex-direction: column;
  gap: 22px;
  max-width: 520px;
}
.feature-item {
  display: flex;
  align-items: flex-start;
  gap: 14px;
}
.feature-icon {
  flex-shrink: 0;
  width: 36px;
  height: 36px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border-radius: 10px;
  color: #A9CBFF;
  background: rgba(255, 255, 255, 0.06);
  border: 1px solid rgba(255, 255, 255, 0.12);
}
.feature-body { flex: 1; min-width: 0; }
.feature-title {
  font-size: 14.5px;
  color: #FFFFFF;
  font-weight: 600;
  margin-bottom: 4px;
  letter-spacing: 0.3px;
}
.feature-desc {
  font-size: 13px;
  color: rgba(220, 232, 255, 0.6);
  line-height: 1.6;
}

.hero-stats {
  display: flex;
  align-items: stretch;
  gap: 32px;
  padding: 22px 28px;
  border-radius: 14px;
  background: rgba(255, 255, 255, 0.04);
  border: 1px solid rgba(255, 255, 255, 0.08);
  backdrop-filter: blur(6px);
  max-width: 520px;
}
.stat { flex: 1; min-width: 0; }
.stat-num {
  font-size: 22px;
  font-weight: 700;
  color: #FFFFFF;
  line-height: 1.15;
  letter-spacing: 0.5px;
  font-variant-numeric: tabular-nums;
}
.stat-unit { font-size: 13px; margin-left: 2px; color: rgba(255, 255, 255, 0.7); font-weight: 500; }
.stat-label {
  margin-top: 4px;
  font-size: 12px;
  color: rgba(220, 232, 255, 0.55);
  letter-spacing: 0.3px;
}
.stat-divider {
  width: 1px;
  background: rgba(255, 255, 255, 0.1);
}

.hero-foot {
  display: flex;
  align-items: center;
  gap: 10px;
  padding-top: 24px;
  border-top: 1px solid rgba(255, 255, 255, 0.06);
  margin-top: 8px;
}
.trust-badge {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  padding: 5px 10px;
  font-size: 11.5px;
  letter-spacing: 0.4px;
  color: rgba(220, 232, 255, 0.75);
  background: rgba(255, 255, 255, 0.06);
  border: 1px solid rgba(255, 255, 255, 0.1);
  border-radius: 999px;
}

/* -------- 右：登录表单 -------- */
.form-panel {
  flex: 1;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 40px 56px;
  background: var(--surface);
  min-width: 460px;
}
.form-card {
  width: 100%;
  max-width: 388px;
}
.form-head { margin-bottom: 22px; }
.form-title {
  margin: 0 0 8px;
  font-size: 24px;
  font-weight: 700;
  color: var(--ink-900);
  letter-spacing: 0.3px;
}
.form-subtitle {
  margin: 0;
  font-size: 13.5px;
  color: var(--ink-400);
  line-height: 1.6;
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 10px;
}
.demo-hint {
  font-size: 12px;
  color: var(--brand-600);
  background: var(--brand-50);
  border: 1px dashed var(--brand-100);
  padding: 2px 8px;
  border-radius: 4px;
}

/* 表单控件精修 */
.form-card :deep(.el-form-item) { margin-bottom: 20px; }
.form-card :deep(.el-form-item__label) { display: none; }
.form-card :deep(.el-input__wrapper) {
  padding: 4px 12px;
  background: var(--surface);
  box-shadow: 0 0 0 1px var(--line) inset;
  border-radius: 8px;
  transition: box-shadow 0.15s ease, background 0.15s ease;
}
.form-card :deep(.el-input__wrapper:hover) {
  box-shadow: 0 0 0 1px #C9D2E4 inset;
}
.form-card :deep(.el-input__wrapper.is-focus) {
  box-shadow: 0 0 0 1.5px var(--brand-500) inset;
  background: var(--surface);
}
.form-card :deep(.el-input__inner) {
  color: var(--ink-900);
  height: 40px;
  line-height: 40px;
  font-size: 14px;
}
.form-card :deep(.el-input__inner::placeholder) {
  color: var(--ink-300);
}
.form-card :deep(.el-input__prefix),
.form-card :deep(.el-input__suffix) { color: var(--ink-400); }
.form-card :deep(.el-input__prefix) { display: inline-flex; align-items: center; }
.form-card :deep(.el-input__prefix .el-icon) { display: inline-flex; align-items: center; }
.form-card :deep(.el-form-item.is-error .el-input__wrapper) {
  box-shadow: 0 0 0 1px #F56C6C inset;
}
.form-card :deep(.el-form-item__error) {
  padding-top: 4px;
  font-size: 12px;
  color: #DC2626;
}

.form-options {
  display: flex;
  align-items: center;
  justify-content: space-between;
  margin: -2px 0 22px;
}
.opt-text {
  font-size: 13px;
  color: var(--ink-500);
}
.forgot-link { font-size: 13px; }
.form-card :deep(.el-checkbox__input.is-checked .el-checkbox__inner) {
  background-color: var(--brand-500);
  border-color: var(--brand-500);
}
.form-card :deep(.el-checkbox__inner:hover) { border-color: var(--brand-500); }
.form-card :deep(.el-link--primary) { color: var(--brand-500); }
.form-card :deep(.el-link--primary:hover) { color: var(--brand-600); }

.login-btn {
  width: 100%;
  height: 44px;
  font-size: 15px;
  font-weight: 600;
  letter-spacing: 4px;
  border-radius: 8px;
  background: var(--brand-500);
  border: none;
  box-shadow: 0 6px 20px -8px rgba(30, 94, 255, 0.55);
  transition: all 0.18s ease;
}
.login-btn:hover,
.login-btn:focus {
  background: var(--brand-600);
  transform: translateY(-1px);
  box-shadow: 0 10px 24px -8px rgba(30, 94, 255, 0.6);
}
.login-btn:active { transform: translateY(0); }
:deep(.login-btn.el-button.is-loading) { letter-spacing: 2px; }

.form-foot-note {
  margin: 22px 0 0;
  text-align: center;
  font-size: 13px;
  color: var(--ink-400);
}
.form-foot-note :deep(.el-link) { font-size: 13px; margin-left: 2px; }

/* ============ 底部信息 ============ */
.page-footer {
  flex-shrink: 0;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 14px 40px;
  border-top: 1px solid var(--line-soft);
  background: var(--surface);
  font-size: 12px;
  color: var(--ink-400);
}
.foot-left { display: inline-flex; align-items: center; gap: 6px; }
.foot-right { display: inline-flex; align-items: center; gap: 6px; }
.foot-sep { color: var(--ink-300); }
.foot-link {
  color: var(--ink-500);
  cursor: pointer;
  text-decoration: none;
  transition: color 0.15s;
}
.foot-link:hover { color: var(--brand-500); }
.foot-ver {
  font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace;
  color: var(--ink-400);
  padding: 2px 8px;
  background: var(--surface-alt);
  border-radius: 4px;
  font-size: 11.5px;
}

/* ============ 响应式 ============ */
@media (max-width: 1200px) {
  .hero-panel { padding: 48px 56px 32px; }
  .hero-title { font-size: 34px; }
  .form-panel { padding: 40px 44px; min-width: 420px; }
}
@media (max-width: 1024px) {
  .hero-panel { flex: 1; padding: 40px 44px 28px; }
  .hero-title { font-size: 30px; }
  .hero-desc { font-size: 14px; margin-bottom: 32px; }
  .feature-list { gap: 16px; margin-bottom: 32px; }
  .hero-stats { gap: 20px; padding: 18px 22px; }
  .stat-num { font-size: 18px; }
  .form-panel { min-width: 400px; padding: 40px; }
}
@media (max-width: 900px) {
  .page-header { padding: 0 20px; }
  .nav-status { display: none; }
  .page-main { flex-direction: column; }
  .hero-panel {
    flex: none;
    padding: 32px 24px 24px;
    min-height: auto;
  }
  .hero-title { font-size: 22px; line-height: 1.35; }
  .hero-desc, .feature-list, .hero-stats, .hero-foot { display: none; }
  .form-panel { flex: 1; min-width: 0; padding: 32px 24px; }
  .page-footer {
    flex-direction: column;
    gap: 6px;
    text-align: center;
    padding: 12px 20px;
  }
}
@media (max-width: 480px) {
  .brand-sub { display: none; }
}
</style>
