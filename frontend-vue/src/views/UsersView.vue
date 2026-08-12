<script setup lang="ts">
/**
 * 用户管理页（仅 admin）— 账号 CRUD / 重置密码 / 停用启用
 * 对标领星WMS：权限分层，操作员只能执行业务单据，管理员管理系统用户。
 */
import { ref, reactive, computed, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { getUsers, createUser, updateUser, deleteUser, type UserInfo } from '@/api'

const users = ref<UserInfo[]>([])
const total = ref(0)
const page = ref(1)
const pageSize = ref(20)
const loading = ref(false)

const dialogVisible = ref(false)
const submitting = ref(false)
const form = reactive({ username: '', password: '', role: 'operator' as 'admin' | 'operator' })

const resetPwdId = ref<number | null>(null)
const pwdForm = reactive({ password: '' })
// v-model 需可赋值表达式，用 computed 包装布尔判断
const resetPwdVisible = computed({
  get: () => resetPwdId.value !== null,
  set: (v: boolean) => { if (!v) resetPwdId.value = null },
})

const loadUsers = async () => {
  loading.value = true
  try {
    const res = await getUsers({ page: page.value, pageSize: pageSize.value })
    users.value = res.data.list
    total.value = res.data.total
  } catch (e: any) {
    ElMessage.error(e.response?.data?.detail || '加载用户失败')
  } finally {
    loading.value = false
  }
}

const openCreate = () => {
  form.username = ''
  form.password = ''
  form.role = 'operator'
  dialogVisible.value = true
}

const submitCreate = async () => {
  if (!form.username.trim() || form.password.length < 6) {
    return ElMessage.warning('用户名必填，密码至少 6 位')
  }
  submitting.value = true
  try {
    const res = await createUser({ username: form.username.trim(), password: form.password, role: form.role })
    ElMessage.success(`用户 ${res.data.username} 创建成功`)
    dialogVisible.value = false
    await loadUsers()
  } catch (e: any) {
    ElMessage.error(e.response?.data?.detail || '创建失败')
  } finally {
    submitting.value = false
  }
}

const toggleStatus = async (row: UserInfo) => {
  const next = row.status === 'ACTIVE' ? 'INACTIVE' : 'ACTIVE'
  try {
    await updateUser(row.id, { status: next })
    ElMessage.success(next === 'ACTIVE' ? '已启用' : '已停用')
    await loadUsers()
  } catch (e: any) {
    ElMessage.error(e.response?.data?.detail || '操作失败')
  }
}

const openResetPwd = (row: UserInfo) => {
  resetPwdId.value = row.id
  pwdForm.password = ''
}

const submitResetPwd = async () => {
  if (!pwdForm.password || pwdForm.password.length < 6) {
    return ElMessage.warning('新密码至少 6 位')
  }
  try {
    await updateUser(resetPwdId.value!, { password: pwdForm.password })
    ElMessage.success('密码已重置')
    resetPwdId.value = null
  } catch (e: any) {
    ElMessage.error(e.response?.data?.detail || '重置失败')
  }
}

const removeUser = async (row: UserInfo) => {
  try {
    await ElMessageBox.confirm(`确认删除用户「${row.username}」？删除后其 token 将全部失效。`, '提示', { type: 'warning' })
  } catch {
    return
  }
  try {
    await deleteUser(row.id)
    ElMessage.success('已删除')
    await loadUsers()
  } catch (e: any) {
    ElMessage.error(e.response?.data?.detail || '删除失败')
  }
}

const formatTime = (t: string) => (t ? t.replace('T', ' ').split('.')[0] : '-')

onMounted(loadUsers)
</script>

<template>
  <div>
    <div style="display: flex; gap: 12px; margin-bottom: 16px">
      <el-button type="success" @click="openCreate">新建用户</el-button>
      <el-button type="primary" @click="loadUsers">刷新</el-button>
    </div>

    <el-table :data="users" v-loading="loading" border stripe>
      <el-table-column prop="id" label="ID" width="70" />
      <el-table-column prop="username" label="用户名" min-width="140" />
      <el-table-column label="角色" width="110">
        <template #default="{ row }">
          <el-tag :type="row.role === 'admin' ? 'danger' : 'info'">
            {{ row.role === 'admin' ? '管理员' : '操作员' }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column label="状态" width="100">
        <template #default="{ row }">
          <el-tag :type="row.status === 'ACTIVE' ? 'success' : 'warning'">
            {{ row.status === 'ACTIVE' ? '启用' : '停用' }}
          </el-tag>
        </template>
      </el-table-column>
      <el-table-column label="创建时间" width="170">
        <template #default="{ row }">{{ formatTime(row.createdAt) }}</template>
      </el-table-column>
      <el-table-column label="操作" width="260" fixed="right">
        <template #default="{ row }">
          <el-button size="small" @click="openResetPwd(row)">重置密码</el-button>
          <el-button size="small" :type="row.status === 'ACTIVE' ? 'warning' : 'success'" @click="toggleStatus(row)">
            {{ row.status === 'ACTIVE' ? '停用' : '启用' }}
          </el-button>
          <el-button size="small" type="danger" @click="removeUser(row)">删除</el-button>
        </template>
      </el-table-column>
    </el-table>

    <div style="margin-top: 16px; text-align: right">
      <el-pagination
        v-model:current-page="page"
        :page-size="pageSize"
        :total="total"
        layout="total, prev, pager, next, jumper"
        @current-change="page = $event; loadUsers()"
      />
    </div>

    <!-- 新建用户 -->
    <el-dialog v-model="dialogVisible" title="新建用户" width="420px">
      <el-form :model="form" label-width="80px">
        <el-form-item label="用户名">
          <el-input v-model="form.username" placeholder="登录名（2-64 字符）" />
        </el-form-item>
        <el-form-item label="初始密码">
          <el-input v-model="form.password" type="password" placeholder="至少 6 位" show-password />
        </el-form-item>
        <el-form-item label="角色">
          <el-radio-group v-model="form.role">
            <el-radio value="operator">操作员</el-radio>
            <el-radio value="admin">管理员</el-radio>
          </el-radio-group>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="submitting" @click="submitCreate">创建</el-button>
      </template>
    </el-dialog>

    <!-- 重置密码 -->
    <el-dialog v-model="resetPwdVisible" title="重置密码" width="380px">
      <el-form label-width="80px">
        <el-form-item label="新密码">
          <el-input v-model="pwdForm.password" type="password" placeholder="至少 6 位" show-password />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="resetPwdId = null">取消</el-button>
        <el-button type="primary" @click="submitResetPwd">确认</el-button>
      </template>
    </el-dialog>
  </div>
</template>
