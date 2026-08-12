<script setup lang="ts">
/**
 * 客户管理页（分层 A/B/C）
 * 服务端分页 + 新增/编辑弹窗 + 软删除
 */
import { ref, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { User, Medal, UserFilled, Plus } from '@element-plus/icons-vue'
import {
  getCustomers, createCustomer, updateCustomer, deleteCustomer,
  type Customer,
} from '@/api'
import SummaryCards, { GRADIENTS } from '@/components/SummaryCards.vue'

// ============ 多维度汇总（Mock） ============
const summaryCards = [
  { label: '客户总数', value: 84, unit: '个', icon: User, gradient: GRADIENTS.orange },
  { label: 'A 层战略客户', value: 12, unit: '个', icon: Medal, gradient: GRADIENTS.red },
  { label: 'B 层成长客户', value: 26, unit: '个', icon: UserFilled, gradient: GRADIENTS.blue },
  { label: '本月新增', value: 8, unit: '个', icon: Plus, gradient: GRADIENTS.green },
]

const customers = ref<Customer[]>([])
const keyword = ref('')
const loading = ref(false)
const dialogVisible = ref(false)
const dialogTitle = ref('新增客户')
const form = ref({
  id: 0, code: '', name: '', tier: 'C', contact: '', phone: '',
})
const page = ref(1)
const pageSize = ref(10)
const total = ref(0)

const tierTag = (tier: string) =>
  tier === 'A' ? 'danger' : tier === 'B' ? 'warning' : 'info'

const loadCustomers = async () => {
  loading.value = true
  try {
    const res = await getCustomers({
      keyword: keyword.value || undefined,
      page: page.value,
      pageSize: pageSize.value,
    })
    customers.value = res.data.list
    total.value = res.data.total
  } catch (e: any) {
    ElMessage.error('加载失败: ' + (e.response?.data?.detail || e.message))
  } finally {
    loading.value = false
  }
}

const resetForm = () => {
  form.value = { id: 0, code: '', name: '', tier: 'C', contact: '', phone: '' }
}

const handleAdd = () => {
  dialogTitle.value = '新增客户'
  resetForm()
  dialogVisible.value = true
}

const handleEdit = (customer: Customer) => {
  dialogTitle.value = '编辑客户'
  form.value = {
    id: customer.id, code: customer.code, name: customer.name, tier: customer.tier,
    contact: customer.contact || '', phone: customer.phone || '',
  }
  dialogVisible.value = true
}

const handleSubmit = async () => {
  try {
    const isEdit = !!form.value.id
    if (isEdit) {
      await updateCustomer(form.value.id, {
        name: form.value.name, tier: form.value.tier,
        contact: form.value.contact || null, phone: form.value.phone || null,
      })
      ElMessage.success('更新成功')
    } else {
      await createCustomer({
        code: form.value.code, name: form.value.name, tier: form.value.tier,
        contact: form.value.contact || null, phone: form.value.phone || null,
      })
      ElMessage.success('创建成功')
      page.value = 1
    }
    dialogVisible.value = false
    await loadCustomers()
  } catch (e: any) {
    ElMessage.error(e.response?.data?.detail || '操作失败')
  }
}

const handleDelete = async (id: number) => {
  try {
    await ElMessageBox.confirm('确定停用该客户吗？历史单据将保留可追溯。', '确认停用', { type: 'warning' })
    await deleteCustomer(id)
    ElMessage.success('停用成功')
    await loadCustomers()
  } catch (e: any) {
    if (e?.response?.data?.detail) ElMessage.error(e.response.data.detail)
  }
}

const onPageChange = (p: number) => {
  page.value = p
  loadCustomers()
}

onMounted(loadCustomers)
</script>

<template>
  <div>
    <!-- 多维度汇总 KPI（Mock） -->
    <SummaryCards :cards="summaryCards" />

    <div style="display: flex; gap: 12px; margin-bottom: 16px">
      <el-input v-model="keyword" placeholder="搜索客户名称/编码..." style="width: 300px" clearable
        @keyup.enter="page = 1; loadCustomers()" @clear="page = 1; loadCustomers()" />
      <el-button type="primary" @click="page = 1; loadCustomers()">搜索</el-button>
      <el-button type="success" @click="handleAdd">新增客户</el-button>
    </div>

    <el-table :data="customers" v-loading="loading" border stripe>
      <el-table-column prop="id" label="ID" width="70" />
      <el-table-column prop="code" label="客户编码" width="120" />
      <el-table-column prop="name" label="客户名称" min-width="180" />
      <el-table-column label="分层" width="90">
        <template #default="{ row }">
          <el-tag :type="tierTag(row.tier)">Tier {{ row.tier }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="contact" label="联系人" width="110">
        <template #default="{ row }">{{ row.contact || '-' }}</template>
      </el-table-column>
      <el-table-column prop="phone" label="联系电话" width="130">
        <template #default="{ row }">{{ row.phone || '-' }}</template>
      </el-table-column>
      <el-table-column label="状态" width="90">
        <template #default="{ row }">
          <el-tag :type="row.status === 'ACTIVE' ? 'success' : 'info'">{{ row.status }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column label="操作" width="160" fixed="right">
        <template #default="{ row }">
          <el-button size="small" @click="handleEdit(row)">编辑</el-button>
          <el-button size="small" type="danger" @click="handleDelete(row.id)">停用</el-button>
        </template>
      </el-table-column>
    </el-table>

    <div style="margin-top: 16px; text-align: right">
      <el-pagination
        v-model:current-page="page"
        :page-size="pageSize"
        :total="total"
        layout="total, prev, pager, next, jumper"
        @current-change="onPageChange"
      />
    </div>

    <el-dialog v-model="dialogVisible" :title="dialogTitle" width="520px">
      <el-form :model="form" label-width="90px">
        <el-form-item label="客户编码" v-if="!form.id">
          <el-input v-model="form.code" maxlength="50" placeholder="如 CUST-A04" />
        </el-form-item>
        <el-form-item label="客户名称">
          <el-input v-model="form.name" maxlength="200" />
        </el-form-item>
        <el-form-item label="客户分层">
          <el-radio-group v-model="form.tier">
            <el-radio-button value="A">A 层（战略客户）</el-radio-button>
            <el-radio-button value="B">B 层（成长客户）</el-radio-button>
            <el-radio-button value="C">C 层（普通客户）</el-radio-button>
          </el-radio-group>
        </el-form-item>
        <el-form-item label="联系人">
          <el-input v-model="form.contact" maxlength="50" />
        </el-form-item>
        <el-form-item label="联系电话">
          <el-input v-model="form.phone" maxlength="50" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleSubmit">确定</el-button>
      </template>
    </el-dialog>
  </div>
</template>
