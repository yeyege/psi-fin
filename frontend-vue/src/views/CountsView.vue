<script setup lang="ts">
/**
 * 盘点管理页 — 库存准确率闭环
 * 创建盘点单（按库位/库区/商品/全部）→ 录入实盘数量 → 完成自动生成盘盈/盘亏调整单
 */
import { ref, reactive, onMounted, computed } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import {
  createCount, getCounts, getCount, submitCount, completeCount,
  getProducts, getLocations, getZones,
  SCOPE_TYPE_LABELS,
  type CountOrder, type Product, type Location, type Zone,
} from '@/api'

const orders = ref<CountOrder[]>([])
const loading = ref(false)
const total = ref(0)
const page = ref(1)
const pageSize = ref(20)

// 创建表单
const dialogVisible = ref(false)
const submitting = ref(false)
const createForm = reactive({
  scopeType: 'LOCATION',
  scopeValue: '',
  remark: '',
})
const locations = ref<Location[]>([])
const zones = ref<Zone[]>([])
const products = ref<Product[]>([])

// 详情抽屉
const detailVisible = ref(false)
const detailLoading = ref(false)
const detail = ref<CountOrder | null>(null)

const statusTag = (s: string) => (s === 'COMPLETED' ? 'success' : 'warning')
const statusLabel = (s: string) => (s === 'COMPLETED' ? '已完成' : '待盘点')
const fmtRate = (r: number | null | undefined) => (r === null || r === undefined ? '-' : `${(r * 100).toFixed(1)}%`)
const formatTime = (t: string) => (t ? t.replace('T', ' ').split('.')[0] : '-')

const scopeOptions = computed(() => {
  if (createForm.scopeType === 'LOCATION') return locations.value.map((l) => ({ label: l.code, value: l.code }))
  if (createForm.scopeType === 'ZONE') return zones.value.map((z) => ({ label: `${z.name}(${z.code})`, value: String(z.id) }))
  if (createForm.scopeType === 'PRODUCT') return products.value.map((p) => ({ label: `${p.name} (${p.sku})`, value: String(p.id) }))
  return []
})

const loadOrders = async () => {
  loading.value = true
  try {
    const res = await getCounts({ page: page.value, pageSize: pageSize.value })
    orders.value = res.data.list
    total.value = res.data.total
  } catch (e: any) {
    ElMessage.error('加载盘点单失败: ' + (e.response?.data?.detail || e.message))
  } finally {
    loading.value = false
  }
}

const openCreate = () => {
  createForm.scopeType = 'LOCATION'
  createForm.scopeValue = ''
  createForm.remark = ''
  dialogVisible.value = true
}

const submitCreate = async () => {
  if (createForm.scopeType !== 'ALL' && !createForm.scopeValue) {
    return ElMessage.warning('请选择盘点范围值')
  }
  submitting.value = true
  try {
    const res = await createCount({
      scopeType: createForm.scopeType,
      scopeValue: createForm.scopeType === 'ALL' ? null : createForm.scopeValue,
      remark: createForm.remark || undefined,
    })
    ElMessage.success(`盘点单 ${res.data.countNo} 创建成功（${res.data.items.length} 行明细）`)
    dialogVisible.value = false
    page.value = 1
    await loadOrders()
  } catch (e: any) {
    ElMessage.error(e.response?.data?.detail || '创建盘点单失败')
  } finally {
    submitting.value = false
  }
}

// ============ 详情 ============

const openDetail = async (id: number) => {
  detailVisible.value = true
  detailLoading.value = true
  detail.value = null
  try {
    const res = await getCount(id)
    detail.value = res.data
  } catch (e: any) {
    ElMessage.error('加载盘点单详情失败: ' + (e.response?.data?.detail || e.message))
  } finally {
    detailLoading.value = false
  }
}

const allRecorded = computed(() => {
  const d = detail.value
  return !!d && d.items.length > 0 && d.items.every((it) => it.countedQty !== null)
})

const submitDetail = async () => {
  const d = detail.value
  if (!d) return
  const unrecorded = d.items.filter((it) => it.countedQty === null || it.countedQty === undefined)
  if (unrecorded.length) {
    return ElMessage.warning(`还有 ${unrecorded.length} 行未录入实盘数量`)
  }
  submitting.value = true
  try {
    const res = await submitCount(d.id, d.items.map((it) => ({ itemId: it.id, countedQty: it.countedQty as number })))
    detail.value = res.data
    ElMessage.success('实盘数量已保存')
    await loadOrders()
  } catch (e: any) {
    ElMessage.error(e.response?.data?.detail || '保存失败')
  } finally {
    submitting.value = false
  }
}

const handleComplete = async () => {
  const d = detail.value
  if (!d) return
  if (!allRecorded.value) {
    return ElMessage.warning('请先提交全部实盘数量再完成盘点')
  }
  try {
    await ElMessageBox.confirm(
      `完成盘点后将自动对差异行生成盘盈/盘亏调整单（差异总量 ${d.stats?.totalDiffQty ?? 0}），确认完成？`,
      '完成盘点',
      { type: 'warning', confirmButtonText: '确认完成', cancelButtonText: '取消' },
    )
  } catch {
    return
  }
  submitting.value = true
  try {
    const res = await completeCount(d.id)
    detail.value = res.data
    ElMessage.success('盘点完成，差异已自动调整并写入库存流水')
    await loadOrders()
  } catch (e: any) {
    ElMessage.error(e.response?.data?.detail || '完成盘点失败')
  } finally {
    submitting.value = false
  }
}

onMounted(async () => {
  const [locRes, zoneRes, pRes] = await Promise.all([
    getLocations({}),
    getZones(),
    getProducts({ page: 1, pageSize: 100 }),
  ])
  locations.value = locRes.data
  zones.value = zoneRes.data
  products.value = pRes.data.list
  await loadOrders()
})
</script>

<template>
  <div>
    <div style="display: flex; gap: 12px; margin-bottom: 16px">
      <el-button type="primary" @click="openCreate">新建盘点单</el-button>
      <el-button @click="loadOrders">刷新</el-button>
    </div>

    <el-table :data="orders" v-loading="loading" border stripe>
      <el-table-column prop="countNo" label="盘点单号" width="180" />
      <el-table-column label="范围" width="110">
        <template #default="{ row }">
          <el-tag size="small">{{ SCOPE_TYPE_LABELS[row.scopeType] }}</el-tag>
          <span v-if="row.scopeValue" style="margin-left: 4px">{{ row.scopeValue }}</span>
        </template>
      </el-table-column>
      <el-table-column label="状态" width="90">
        <template #default="{ row }">
          <el-tag size="small" :type="statusTag(row.status)">{{ statusLabel(row.status) }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column label="明细行数" width="90">
        <template #default="{ row }">{{ row.items.length }}</template>
      </el-table-column>
      <el-table-column label="库存准确率" width="110">
        <template #default="{ row }">{{ fmtRate(row.stats?.accuracyRate) }}</template>
      </el-table-column>
      <el-table-column label="库位准确率" width="110">
        <template #default="{ row }">{{ fmtRate(row.stats?.locationAccuracyRate) }}</template>
      </el-table-column>
      <el-table-column label="差异总量" width="90">
        <template #default="{ row }">
          <span :style="{ color: row.stats?.totalDiffQty ? '#e6a23c' : 'inherit', fontWeight: row.stats?.totalDiffQty ? 600 : 'inherit' }">
            {{ row.stats?.totalDiffQty ?? '-' }}
          </span>
        </template>
      </el-table-column>
      <el-table-column label="创建时间" width="170">
        <template #default="{ row }">{{ formatTime(row.createdAt) }}</template>
      </el-table-column>
      <el-table-column label="操作" width="90" fixed="right">
        <template #default="{ row }">
          <el-button size="small" type="primary" link @click="openDetail(row.id)">查看</el-button>
        </template>
      </el-table-column>
    </el-table>

    <div style="margin-top: 16px; text-align: right">
      <el-pagination
        v-model:current-page="page"
        :page-size="pageSize"
        :total="total"
        layout="total, prev, pager, next, jumper"
        @current-change="page = $event; loadOrders()"
      />
    </div>

    <!-- 新建盘点单 -->
    <el-dialog v-model="dialogVisible" title="新建盘点单" width="520px">
      <el-form :model="createForm" label-width="90px">
        <el-form-item label="盘点范围">
          <el-select v-model="createForm.scopeType" style="width: 100%">
            <el-option v-for="(label, key) in SCOPE_TYPE_LABELS" :key="key" :label="label" :value="key" />
          </el-select>
        </el-form-item>
        <el-form-item v-if="createForm.scopeType !== 'ALL'" label="范围值">
          <el-select v-model="createForm.scopeValue" filterable placeholder="选择范围" style="width: 100%">
            <el-option v-for="opt in scopeOptions" :key="opt.value" :label="opt.label" :value="opt.value" />
          </el-select>
        </el-form-item>
        <el-form-item label="备注">
          <el-input v-model="createForm.remark" maxlength="200" placeholder="如 月度循环盘点" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="submitting" @click="submitCreate">创建并生成盘点明细</el-button>
      </template>
    </el-dialog>

    <!-- 盘点单详情 -->
    <el-drawer v-model="detailVisible" title="盘点单详情" size="720px">
      <div v-loading="detailLoading">
        <template v-if="detail">
          <div style="display: flex; gap: 12px; align-items: center; margin-bottom: 16px; flex-wrap: wrap">
            <el-tag size="large">{{ detail.countNo }}</el-tag>
            <el-tag :type="statusTag(detail.status)">{{ statusLabel(detail.status) }}</el-tag>
            <span>{{ SCOPE_TYPE_LABELS[detail.scopeType] }}{{ detail.scopeValue ? '：' + detail.scopeValue : '' }}</span>
            <div style="flex: 1" />
            <template v-if="detail.status === 'PENDING'">
              <el-button type="primary" :disabled="!allRecorded" :loading="submitting" @click="submitDetail">提交实盘数量</el-button>
              <el-button type="success" :disabled="!allRecorded" :loading="submitting" @click="handleComplete">完成盘点</el-button>
            </template>
          </div>

          <el-alert v-if="detail.status === 'PENDING'" type="info" :closable="false" style="margin-bottom: 12px"
            title="逐行录入实盘数量后点击「提交实盘数量」，确认无误后「完成盘点」将自动生成盘盈/盘亏调整单并写库存流水。" />

          <el-table :data="detail.items" border size="small" max-height="380">
            <el-table-column prop="productName" label="商品" min-width="140">
              <template #default="{ row }">{{ row.productName }} ({{ row.sku }})</template>
            </el-table-column>
            <el-table-column prop="locationCode" label="库位" width="90" />
            <el-table-column prop="systemQty" label="账面数量" width="90" align="center" />
            <el-table-column label="实盘数量" width="130" align="center">
              <template #default="{ row }">
                <el-input-number v-if="detail.status === 'PENDING'" v-model="row.countedQty"
                  :min="0" :max="999999" controls-position="right" size="small" style="width: 110px" />
                <span v-else>{{ row.countedQty }}</span>
              </template>
            </el-table-column>
            <el-table-column label="差异" width="90" align="center">
              <template #default="{ row }">
                <span v-if="row.diffQty !== null && row.diffQty !== undefined"
                  :style="{ color: row.diffQty > 0 ? '#67c23a' : row.diffQty < 0 ? '#f56c6c' : 'inherit', fontWeight: 600 }">
                  {{ row.diffQty > 0 ? '+' : '' }}{{ row.diffQty }}
                </span>
                <span v-else>-</span>
              </template>
            </el-table-column>
          </el-table>

          <template v-if="detail.stats">
            <div style="margin-top: 16px; font-weight: 600; margin-bottom: 8px">盘点准确率指标</div>
            <el-row :gutter="12">
              <el-col :span="8">
                <el-card shadow="never" style="text-align: center">
                  <div style="font-size: 22px; font-weight: 700; color: #409eff">{{ fmtRate(detail.stats.accuracyRate) }}</div>
                  <div style="color: #909399; font-size: 12px; margin-top: 4px">库存准确率（{{ detail.stats.accurateItems }}/{{ detail.stats.totalItems }} 行）</div>
                </el-card>
              </el-col>
              <el-col :span="8">
                <el-card shadow="never" style="text-align: center">
                  <div style="font-size: 22px; font-weight: 700; color: #67c23a">{{ fmtRate(detail.stats.locationAccuracyRate) }}</div>
                  <div style="color: #909399; font-size: 12px; margin-top: 4px">库位准确率（{{ detail.stats.accurateLocationCount }}/{{ detail.stats.locationCount }} 个）</div>
                </el-card>
              </el-col>
              <el-col :span="8">
                <el-card shadow="never" style="text-align: center">
                  <div style="font-size: 22px; font-weight: 700; color: #e6a23c">{{ detail.stats.totalDiffQty }}</div>
                  <div style="color: #909399; font-size: 12px; margin-top: 4px">差异总量（件）</div>
                </el-card>
              </el-col>
            </el-row>
          </template>
        </template>
      </div>
    </el-drawer>
  </div>
</template>
