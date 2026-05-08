<script setup lang="ts">
/**
 * ============================================
 *  入库管理页 — 候选人需要实现（任务1）
 * ============================================
 *
 * 需求：
 * 1. 表单：供应商名称 + 入库明细列表
 * 2. 每行明细：选择商品（下拉搜索）→ 选择仓库 → 选择库位 → 输入数量
 * 3. 支持添加/删除明细行
 * 4. 提交按钮（调用 createInboundOrder API）
 *
 * 建议使用 AI 协作完成此页面，参考 ProductsView.vue 的实现风格
 */
import { ref } from 'vue'
import { ElMessage } from 'element-plus'
import { createInboundOrder } from '@/api'

const supplierName = ref('')
const items = ref<any[]>([])
const submitting = ref(false)

// TODO: 候选人实现添加/删除明细行的逻辑

const addItem = () => {
  items.value.push({
    productId: undefined,
    quantity: 1,
    locationCode: '',
  })
}

const removeItem = (index: number) => {
  items.value.splice(index, 1)
}

// TODO: 候选人实现提交逻辑
const handleSubmit = async () => {
  // 提示：调用 createInboundOrder({ supplierName, items })
}
</script>

<template>
  <div>
    <h3> 入库管理</h3>

    <!-- 表单 — 候选人实现 -->
    <el-form label-width="100px" style="max-width: 800px">
      <el-form-item label="供应商名称" required>
        <el-input v-model="supplierName" placeholder="请输入供应商名称" />
      </el-form-item>

      <el-form-item label="入库明细">
        <el-button type="primary" @click="addItem">+ 添加明细</el-button>
      </el-form-item>
    </el-form>

    <!-- 明细列表 — 候选人实现 -->
    <div v-for="(item, index) in items" :key="index" style="margin-bottom: 12px; display: flex; gap: 12px; align-items: center">
      <!-- TODO: 商品下拉选择 -->
      <!-- TODO: 仓库下拉 → 库位级联选择 -->
      <!-- TODO: 数量输入 -->
      <el-button type="danger" size="small" @click="removeItem(index)">删除</el-button>
    </div>

    <!-- 提交按钮 -->
    <el-button type="success" :loading="submitting" @click="handleSubmit" :disabled="items.length === 0">
      提交入库单
    </el-button>

    <el-empty v-if="items.length === 0" description="请点击"添加明细"按钮添加入库商品" />
  </div>
</template>
