<script setup lang="ts">
/**
 * 波次拣货页 — 对标领星智能波次策略
 * 选中多张 PENDING 出库单生成波次 → 逐单生成拣货单（按库位优先级推荐路径）
 * 拣货时锁定库存（防超卖），全部拣货完成后波次自动 COMPLETED。
 */
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import {
  createWave, getWaves, getOutboundOrders, pickPickingOrder,
  type Wave, type PickingOrderRow, type OutboundOrder,
} from '@/api'

const waves = ref<Wave[]>([])
const statusFilter = ref('')
const loading = ref(false)
const total = ref(0)
const page = ref(1)
const pageSize = ref(20)

// 生成波次弹窗
const dialogVisible = ref(false)
const submitting = ref(false)
const selectedOrders = ref<OutboundOrder[]>([])
const remark = ref('')
const pendingOrders = ref<OutboundOrder[]>([])

const STATUS_MAP: Record<string, { label: string; type: 'info' | 'warning' | 'success' }> = {
  CREATED: { label: '待拣货', type: 'info' },
  PICKING: { label: '拣货中', type: 'warning' },
  COMPLETED: { label: '已完成', type: 'success' },
}

const PICK_STATUS_MAP: Record<string, { label: string; type: 'info' | 'success' }> = {
  CREATED: { label: '待拣货', type: 'info' },
  PICKED: { label: '已拣货', type: 'success' },
}

const loadWaves = async () => {
  loading.value = true
  try {
    const res = await getWaves({ status: statusFilter.value || undefined, page: page.value, pageSize: pageSize.value })
    waves.value = res.data.list
    total.value = res.data.total
  } catch (e: any) {
    ElMessage.error('加载波次失败: ' + (e.response?.data?.detail || e.message))
  } finally {
    loading.value = false
  }
}

const openCreate = async () => {
  remark.value = ''
  selectedOrders.value = []
  // 拉取待拣货出库单作为可选项
  const res = await getOutboundOrders({ status: 'PENDING', page: 1, pageSize: 100 })
  pendingOrders.value = res.data.list
  dialogVisible.value = true
}

const isSelected = (id: number) => selectedOrders.value.some((o) => o.id === id)

const toggleOrder = (order: OutboundOrder) => {
  const idx = selectedOrders.value.findIndex((o) => o.id === order.id)
  if (idx >= 0) selectedOrders.value.splice(idx, 1)
  else selectedOrders.value.push(order)
}

const submitCreate = async () => {
  if (!selectedOrders.value.length) return ElMessage.warning('请选择至少一张出库单')
  submitting.value = true
  try {
    const res = await createWave({
      outboundOrderIds: selectedOrders.value.map((o) => o.id),
      remark: remark.value || undefined,
    })
    ElMessage.success(`波次 ${res.data.waveNo} 生成成功，共 ${res.data.pickingOrders.length} 张拣货单`)
    dialogVisible.value = false
    page.value = 1
    await loadWaves()
  } catch (e: any) {
    ElMessage.error(e.response?.data?.detail || '波次生成失败')
  } finally {
    submitting.value = false
  }
}

const pick = async (row: PickingOrderRow) => {
  try {
    const res = await pickPickingOrder(row.id)
    ElMessage.success(`拣货完成：${res.data.pickingNo}，库存已锁定`)
    await loadWaves()
  } catch (e: any) {
    ElMessage.error(e.response?.data?.detail || '拣货失败')
  }
}

const formatTime = (t: string) => (t ? t.replace('T', ' ').split('.')[0] : '-')

onMounted(loadWaves)
</script>

<template>
  <div>
    <div style="display: flex; gap: 12px; margin-bottom: 16px">
      <el-select v-model="statusFilter" placeholder="全部状态" clearable style="width: 160px" @change="page = 1; loadWaves()">
        <el-option label="待拣货" value="CREATED" />
        <el-option label="拣货中" value="PICKING" />
        <el-option label="已完成" value="COMPLETED" />
      </el-select>
      <el-button type="success" @click="openCreate">生成波次</el-button>
      <el-button type="primary" @click="loadWaves">刷新</el-button>
    </div>

    <el-table :data="waves" v-loading="loading" border stripe>
      <el-table-column type="expand">
        <template #default="{ row }">
          <div style="padding: 8px 24px">
            <el-table :data="row.pickingOrders" size="small" border>
              <el-table-column prop="pickingNo" label="拣货单号" width="190" />
              <el-table-column prop="outboundOrderNo" label="关联出库单" width="190" />
              <el-table-column label="状态" width="100">
                <template #default="{ row: p }">
                  <el-tag :type="PICK_STATUS_MAP[p.status]?.type || 'info'">{{ PICK_STATUS_MAP[p.status]?.label || p.status }}</el-tag>
                </template>
              </el-table-column>
              <el-table-column label="拣货明细（按库位优先级排序）" min-width="260">
                <template #default="{ row: p }">
                  <el-tag v-for="(it, i) in p.items" :key="i" size="small" style="margin: 2px">
                    {{ it.productName }} ×{{ it.quantity }} @ {{ it.locationCode }}
                  </el-tag>
                </template>
              </el-table-column>
              <el-table-column label="操作" width="110">
                <template #default="{ row: p }">
                  <el-button v-if="p.status === 'CREATED'" size="small" type="primary" @click="pick(p)">拣货</el-button>
                </template>
              </el-table-column>
            </el-table>
          </div>
        </template>
      </el-table-column>
      <el-table-column prop="waveNo" label="波次号" width="190" />
      <el-table-column label="状态" width="100">
        <template #default="{ row }">
          <el-tag :type="STATUS_MAP[row.status]?.type || 'info'">{{ STATUS_MAP[row.status]?.label || row.status }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column label="拣货单数" width="100">
        <template #default="{ row }">{{ row.pickingOrders.length }}</template>
      </el-table-column>
      <el-table-column prop="remark" label="备注" min-width="120">
        <template #default="{ row }">{{ row.remark || '-' }}</template>
      </el-table-column>
      <el-table-column label="创建时间" width="170">
        <template #default="{ row }">{{ formatTime(row.createdAt) }}</template>
      </el-table-column>
    </el-table>

    <div style="margin-top: 16px; text-align: right">
      <el-pagination
        v-model:current-page="page"
        :page-size="pageSize"
        :total="total"
        layout="total, prev, pager, next, jumper"
        @current-change="page = $event; loadWaves()"
      />
    </div>

    <!-- 生成波次 -->
    <el-dialog v-model="dialogVisible" title="生成波次（智能波次策略）" width="720px">
      <el-form label-width="80px">
        <el-form-item label="待拣出库单">
          <el-table :data="pendingOrders" height="320" border size="small" style="width: 100%">
            <el-table-column width="50">
              <template #default="{ row }">
                <el-checkbox :model-value="isSelected(row.id)" @change="toggleOrder(row)" />
              </template>
            </el-table-column>
            <el-table-column prop="orderNo" label="出库单号" width="190" />
            <el-table-column prop="customerName" label="客户" min-width="140" />
            <el-table-column label="明细" min-width="200">
              <template #default="{ row }">
                <el-tag v-for="(it, i) in row.items" :key="i" size="small" style="margin: 1px">
                  {{ it.productName }} ×{{ it.quantity }}
                </el-tag>
              </template>
            </el-table-column>
          </el-table>
          <div style="color: #909399; font-size: 12px; margin-top: 4px">
            已选 {{ selectedOrders.length }} 张，生成后每张出库单对应一张拣货单（按库位优先级推荐拣货路径）
          </div>
        </el-form-item>
        <el-form-item label="备注">
          <el-input v-model="remark" maxlength="200" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="submitting" @click="submitCreate">生成波次</el-button>
      </template>
    </el-dialog>
  </div>
</template>
