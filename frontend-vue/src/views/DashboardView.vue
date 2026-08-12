<script setup lang="ts">
/**
 * 数据看板（首页）— 对标领星 WMS
 * 统计卡片：今日出入库单数、待处理单据、库存总量、低库存预警、商品/客户数
 */
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { getDashboardSummary, type DashboardSummary } from '@/api'

const summary = ref<DashboardSummary | null>(null)

const loadSummary = async () => {
  try {
    const res = await getDashboardSummary()
    summary.value = res.data
  } catch (e: any) {
    ElMessage.error('看板加载失败: ' + (e.response?.data?.detail || e.message))
  }
}

onMounted(loadSummary)

const cards = [
  { key: 'todayInboundCount', label: '今日入库单', icon: 'Download', color: '#409EFF' },
  { key: 'todayOutboundCount', label: '今日出库单', icon: 'Upload', color: '#67C23A' },
  { key: 'pendingInboundCount', label: '待收货入库', icon: 'Box', color: '#E6A23C' },
  { key: 'pendingOutboundCount', label: '待发货出库', icon: 'Van', color: '#F56C6C' },
  { key: 'totalInventoryQty', label: '库存总量(件)', icon: 'Goods', color: '#909399' },
  { key: 'lowStockProductCount', label: '低库存商品', icon: 'Warning', color: '#F56C6C' },
  { key: 'activeProductCount', label: '在售商品数', icon: 'ShoppingCart', color: '#409EFF' },
  { key: 'activeCustomerCount', label: '合作客户数', icon: 'User', color: '#67C23A' },
] as const
</script>

<template>
  <div>
    <el-row :gutter="16">
      <el-col v-for="c in cards" :key="c.key" :span="6" style="margin-bottom: 16px">
        <el-card shadow="hover" class="stat-card">
          <div class="stat-inner">
            <el-icon :size="36" :color="c.color"><component :is="c.icon" /></el-icon>
            <div>
              <div class="stat-value">{{ summary ? (summary as any)[c.key] ?? 0 : '-' }}</div>
              <div class="stat-label">{{ c.label }}</div>
            </div>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <el-card shadow="never">
      <template #header>系统公告</template>
      <p>WMS MVP 已上线：支持客户分层管理、入库/出库/移库/调整全流程、批次与流水追溯。</p>
      <p>提示：库存总量统计的是「可用 + 锁定」，低库存商品阈值 10 件。</p>
    </el-card>
  </div>
</template>

<style scoped>
.stat-card {
  border-radius: 8px;
}
.stat-inner {
  display: flex;
  align-items: center;
  gap: 16px;
}
.stat-value {
  font-size: 26px;
  font-weight: 700;
  line-height: 1.2;
}
.stat-label {
  color: #909399;
  font-size: 13px;
}
</style>
