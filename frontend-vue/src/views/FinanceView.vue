<script setup lang="ts">
/**
 * 财务页 — 应收台账 / 收款核销(支持部分核销与预收) / 往来账龄
 * 业财一体的"账"在这里:应收由销售订单发货自动生成,不手工录
 */
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { Money } from '@element-plus/icons-vue'
import { getReceivables, getAging, registerReceipt, type FinanceEntry, type AgingRow } from '@/api'

const activeTab = ref('receivables')

const STATUS_LABEL: Record<string, string> = { OPEN: '未结清', PARTIAL: '部分结清', SETTLED: '已结清' }
const STATUS_TYPE: Record<string, string> = { OPEN: 'danger', PARTIAL: 'warning', SETTLED: 'success' }

// ============ 应收台账 ============
const rows = ref<FinanceEntry[]>([])
const loading = ref(false)
const partnerName = ref('')
const onlyOutstanding = ref(false)
const onlyOverdue = ref(false)
const page = ref(1)
const pageSize = ref(10)
const total = ref(0)

const load = async () => {
  loading.value = true
  try {
    const res = await getReceivables({
      partnerName: partnerName.value || undefined,
      onlyOutstanding: onlyOutstanding.value || undefined,
      onlyOverdue: onlyOverdue.value || undefined,
      page: page.value,
      pageSize: pageSize.value,
    })
    rows.value = res.data.list
    total.value = res.data.total
  } catch (e: any) {
    ElMessage.error('加载失败: ' + (e.response?.data?.detail || e.message))
  } finally {
    loading.value = false
  }
}

// ============ 账龄 ============
const aging = ref<AgingRow[]>([])
const loadAging = async () => {
  try {
    const res = await getAging()
    aging.value = res.data
  } catch (e: any) {
    ElMessage.error('账龄加载失败: ' + (e.response?.data?.detail || e.message))
  }
}

// ============ 收款登记与核销 ============
const dialogVisible = ref(false)
const submitting = ref(false)
const current = ref<FinanceEntry | null>(null)
const receiptForm = ref({ amount: 0, settleAmount: 0, remark: '' })

const openReceipt = (row: FinanceEntry) => {
  current.value = row
  // 默认按未结余额全额核销;到账金额可改大(差额自动成为预收余额)
  receiptForm.value = { amount: row.outstanding, settleAmount: row.outstanding, remark: '' }
  dialogVisible.value = true
}

const submitReceipt = async () => {
  if (!current.value) return
  const amount = Number(receiptForm.value.amount)
  const settle = Number(receiptForm.value.settleAmount)
  if (amount <= 0) return ElMessage.warning('到账金额必须大于 0')
  if (settle < 0 || settle > amount) return ElMessage.warning('核销金额不能小于 0 或超过到账金额')
  if (settle > current.value.outstanding) return ElMessage.warning('核销金额不能超过该应收未结余额')
  submitting.value = true
  try {
    await registerReceipt({
      partnerName: current.value.partnerName,
      partnerType: current.value.partnerType,
      partnerId: current.value.partnerId || undefined,
      amount,
      remark: receiptForm.value.remark || undefined,
      allocations: settle > 0 ? [{ targetEntryId: current.value.id, amount: settle }] : [],
    })
    ElMessage.success(settle > 0 ? '收款已登记并核销' : '收款已登记（预收余额已保留）')
    dialogVisible.value = false
    await Promise.all([load(), loadAging()])
  } catch (e: any) {
    ElMessage.error(e.response?.data?.detail || '操作失败')
  } finally {
    submitting.value = false
  }
}

const onPageChange = (p: number) => { page.value = p; load() }

onMounted(() => { load(); loadAging() })
</script>

<template>
  <div>
    <el-tabs v-model="activeTab">
      <!-- 应收台账 -->
      <el-tab-pane label="应收台账" name="receivables">
        <div style="display: flex; gap: 12px; margin-bottom: 16px; flex-wrap: wrap; align-items: center">
          <el-input v-model="partnerName" placeholder="搜索往来方..." style="width: 220px" clearable
            @keyup.enter="page = 1; load()" @clear="page = 1; load()" />
          <el-checkbox v-model="onlyOutstanding" @change="page = 1; load()">只看未结清</el-checkbox>
          <el-checkbox v-model="onlyOverdue" @change="page = 1; load()">只看逾期</el-checkbox>
          <el-button type="primary" @click="page = 1; load()">查询</el-button>
        </div>

        <el-table :data="rows" v-loading="loading" border stripe>
          <el-table-column prop="entryNo" label="应收单号" width="160" />
          <el-table-column prop="partnerName" label="往来方" min-width="140" />
          <el-table-column prop="sourceOrderNo" label="来源订单" width="170">
            <template #default="{ row }">{{ row.sourceOrderNo || '-' }}</template>
          </el-table-column>
          <el-table-column label="应收金额" width="120" align="right">
            <template #default="{ row }">¥{{ row.amount.toFixed(2) }}</template>
          </el-table-column>
          <el-table-column label="已核销" width="110" align="right">
            <template #default="{ row }">¥{{ row.settledAmount.toFixed(2) }}</template>
          </el-table-column>
          <el-table-column label="未结余额" width="120" align="right">
            <template #default="{ row }">
              <span :style="{ color: row.outstanding > 0 ? '#f56c6c' : '#67c23a', fontWeight: 600 }">
                ¥{{ row.outstanding.toFixed(2) }}
              </span>
            </template>
          </el-table-column>
          <el-table-column label="到期日" width="120">
            <template #default="{ row }">
              {{ row.dueDate || '-' }}
              <el-tag v-if="row.overdue" type="danger" size="small" style="margin-left: 6px">逾期</el-tag>
            </template>
          </el-table-column>
          <el-table-column label="状态" width="100">
            <template #default="{ row }">
              <el-tag :type="STATUS_TYPE[row.status] || 'info'">{{ STATUS_LABEL[row.status] || row.status }}</el-tag>
            </template>
          </el-table-column>
          <el-table-column label="操作" width="110" fixed="right">
            <template #default="{ row }">
              <el-button size="small" type="primary" :icon="Money" :disabled="row.outstanding <= 0"
                @click="openReceipt(row)">收款</el-button>
            </template>
          </el-table-column>
        </el-table>

        <div style="margin-top: 16px; text-align: right">
          <el-pagination v-model:current-page="page" :page-size="pageSize" :total="total"
            layout="total, prev, pager, next, jumper" @current-change="onPageChange" />
        </div>
      </el-tab-pane>

      <!-- 往来账龄 -->
      <el-tab-pane label="往来账龄" name="aging">
        <el-alert type="info" :closable="false" show-icon style="margin-bottom: 12px"
          title="账龄以【到期日】为基准实时计算：未到期 / 逾期1-30天 / 31-60天 / 60天以上" />
        <el-table :data="aging" border stripe>
          <el-table-column prop="partnerName" label="往来方" min-width="160" />
          <el-table-column label="应收合计" width="130" align="right">
            <template #default="{ row }">¥{{ row.receivableTotal.toFixed(2) }}</template>
          </el-table-column>
          <el-table-column label="已收回" width="130" align="right">
            <template #default="{ row }">¥{{ row.settledTotal.toFixed(2) }}</template>
          </el-table-column>
          <el-table-column label="未结余额" width="130" align="right">
            <template #default="{ row }">
              <span style="color: #f56c6c; font-weight: 600">¥{{ row.balance.toFixed(2) }}</span>
            </template>
          </el-table-column>
          <el-table-column label="未到期" width="120" align="right">
            <template #default="{ row }">¥{{ row.notDue.toFixed(2) }}</template>
          </el-table-column>
          <el-table-column label="逾期1-30天" width="130" align="right">
            <template #default="{ row }">¥{{ row.days1to30.toFixed(2) }}</template>
          </el-table-column>
          <el-table-column label="逾期31-60天" width="135" align="right">
            <template #default="{ row }">¥{{ row.days31to60.toFixed(2) }}</template>
          </el-table-column>
          <el-table-column label="逾期60天以上" width="140" align="right">
            <template #default="{ row: r }">¥{{ r.days60plus.toFixed(2) }}</template>
          </el-table-column>
        </el-table>
      </el-tab-pane>
    </el-tabs>

    <el-dialog v-model="dialogVisible" title="收款登记与核销" width="560px">
      <el-descriptions v-if="current" :column="2" border size="small" style="margin-bottom: 14px">
        <el-descriptions-item label="应收单号">{{ current.entryNo }}</el-descriptions-item>
        <el-descriptions-item label="往来方">{{ current.partnerName }}</el-descriptions-item>
        <el-descriptions-item label="应收金额">¥{{ current.amount.toFixed(2) }}</el-descriptions-item>
        <el-descriptions-item label="未结余额">
          <span style="color: #f56c6c">¥{{ current.outstanding.toFixed(2) }}</span>
        </el-descriptions-item>
      </el-descriptions>
      <el-form :model="receiptForm" label-width="110px">
        <el-form-item label="到账金额">
          <el-input-number v-model="receiptForm.amount" :min="0.01" :precision="2" style="width: 200px" />
          <span style="margin-left: 10px; color: #909399; font-size: 12px">可大于核销金额，差额成为预收余额</span>
        </el-form-item>
        <el-form-item label="本次核销">
          <el-input-number v-model="receiptForm.settleAmount" :min="0" :precision="2"
            :max="current?.outstanding ?? 0" style="width: 200px" />
        </el-form-item>
        <el-form-item label="备注">
          <el-input v-model="receiptForm.remark" maxlength="200" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="submitting" @click="submitReceipt">提交</el-button>
      </template>
    </el-dialog>
  </div>
</template>
