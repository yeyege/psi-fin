<script setup lang="ts">
/**
 * 商品管理页（SKU）
 * 服务端分页 + 新增/编辑弹窗（含尺寸重量）+ 删除（有库存禁止删除，后端校验）
 */
import { ref, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Goods, ShoppingCart, Warning, Files } from '@element-plus/icons-vue'
import {
  getProducts, createProduct, updateProduct, deleteProduct,
  type Product,
} from '@/api'
import SummaryCards, { GRADIENTS } from '@/components/SummaryCards.vue'

// ============ 多维度汇总（Mock） ============
const summaryCards = [
  { label: '商品总数', value: 326, unit: '个', icon: Goods, gradient: GRADIENTS.cyan },
  { label: '在售商品', value: 298, unit: '个', icon: ShoppingCart, gradient: GRADIENTS.green },
  { label: '低库存商品', value: 12, unit: '个', icon: Warning, gradient: GRADIENTS.red },
  { label: '商品分类数', value: 8, unit: '类', icon: Files, gradient: GRADIENTS.purple },
]

const products = ref<Product[]>([])
const keyword = ref('')
const loading = ref(false)
const dialogVisible = ref(false)
const dialogTitle = ref('新增商品')
const form = ref({
  id: 0, name: '', sku: '', fnsKu: '', caseQty: 1,
  unit: '个', width: 0, height: 0, length: 0, weight: 0,
})
const page = ref(1)
const pageSize = ref(10)
const total = ref(0)

const loadProducts = async () => {
  loading.value = true
  try {
    const res = await getProducts({
      keyword: keyword.value || undefined,
      page: page.value,
      pageSize: pageSize.value,
    })
    products.value = res.data.list
    total.value = res.data.total
  } catch (e: any) {
    ElMessage.error('加载失败: ' + (e.response?.data?.detail || e.message))
  } finally {
    loading.value = false
  }
}

const resetForm = () => {
  form.value = { id: 0, name: '', sku: '', fnsKu: '', caseQty: 1, unit: '个', width: 0, height: 0, length: 0, weight: 0 }
}

const handleAdd = () => {
  dialogTitle.value = '新增商品'
  resetForm()
  dialogVisible.value = true
}

const handleEdit = (product: Product) => {
  dialogTitle.value = '编辑商品'
  form.value = {
    id: product.id, name: product.name, sku: product.sku, fnsKu: product.fnsKu || '',
    caseQty: product.caseQty, unit: product.unit,
    width: product.width, height: product.height, length: product.length, weight: product.weight,
  }
  dialogVisible.value = true
}

const handleSubmit = async () => {
  try {
    const isEdit = !!form.value.id
    if (isEdit) {
      await updateProduct(form.value.id, {
        name: form.value.name, fnsKu: form.value.fnsKu || null, caseQty: form.value.caseQty,
        unit: form.value.unit,
        width: form.value.width, height: form.value.height,
        length: form.value.length, weight: form.value.weight,
      })
      ElMessage.success('更新成功')
    } else {
      await createProduct({ ...form.value })
      ElMessage.success('创建成功')
      // 仅新增后跳回第 1 页；编辑保留当前页码
      page.value = 1
    }
    dialogVisible.value = false
    await loadProducts()
  } catch (e: any) {
    ElMessage.error(e.response?.data?.detail || '操作失败')
  }
}

const handleDelete = async (id: number) => {
  try {
    await ElMessageBox.confirm('确定删除该商品吗？有关联库存的商品将无法删除。', '确认删除', { type: 'warning' })
    await deleteProduct(id)
    ElMessage.success('删除成功')
    await loadProducts()
  } catch (e: any) {
    if (e?.response?.data?.detail) ElMessage.error(e.response.data.detail)
  }
}

const onPageChange = (p: number) => {
  page.value = p
  loadProducts()
}

onMounted(loadProducts)
</script>

<template>
  <div>
    <!-- 多维度汇总 KPI（Mock） -->
    <SummaryCards :cards="summaryCards" />

    <div style="display: flex; gap: 12px; margin-bottom: 16px">
      <el-input v-model="keyword" placeholder="搜索商品名称/SKU..." style="width: 300px" clearable
        @keyup.enter="page = 1; loadProducts()" @clear="page = 1; loadProducts()" />
      <el-button type="primary" @click="page = 1; loadProducts()">搜索</el-button>
      <el-button type="success" @click="handleAdd">新增商品</el-button>
    </div>

    <el-table :data="products" v-loading="loading" border stripe>
      <el-table-column prop="id" label="ID" width="70" />
      <el-table-column prop="name" label="商品名称" min-width="140" />
      <el-table-column prop="sku" label="SKU" width="110" />
      <el-table-column prop="fnsKu" label="FNSKU" width="130">
        <template #default="{ row }">{{ row.fnsKu || '-' }}</template>
      </el-table-column>
      <el-table-column prop="caseQty" label="箱规" width="80">
        <template #default="{ row }">{{ row.caseQty }} 个/箱</template>
      </el-table-column>
      <el-table-column prop="unit" label="单位" width="80" />
      <el-table-column label="尺寸(cm)" width="180">
        <template #default="{ row }">{{ row.length }}×{{ row.width }}×{{ row.height }}</template>
      </el-table-column>
      <el-table-column prop="weight" label="重量(kg)" width="100" />
      <el-table-column label="状态" width="90">
        <template #default="{ row }">
          <el-tag :type="row.status === 'ACTIVE' ? 'success' : 'info'">{{ row.status }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column label="操作" width="160" fixed="right">
        <template #default="{ row }">
          <el-button size="small" @click="handleEdit(row)">编辑</el-button>
          <el-button size="small" type="danger" @click="handleDelete(row.id)">删除</el-button>
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
        <el-form-item label="商品名称">
          <el-input v-model="form.name" maxlength="200" />
        </el-form-item>
        <el-form-item label="SKU" v-if="!form.id">
          <el-input v-model="form.sku" maxlength="50" placeholder="如 SKU-006" />
        </el-form-item>
        <el-form-item label="FNSKU">
          <el-input v-model="form.fnsKu" maxlength="50" placeholder="FBA 库内标识，如 X0007EL2Q1" clearable />
        </el-form-item>
        <el-form-item label="箱规(个/箱)">
          <el-input-number v-model="form.caseQty" :min="1" />
        </el-form-item>
        <el-form-item label="单位">
          <el-input v-model="form.unit" maxlength="20" />
        </el-form-item>
        <el-form-item label="长/宽/高(cm)">
          <div style="display: flex; gap: 8px">
            <el-input-number v-model="form.length" :min="0" placeholder="长" />
            <el-input-number v-model="form.width" :min="0" placeholder="宽" />
            <el-input-number v-model="form.height" :min="0" placeholder="高" />
          </div>
        </el-form-item>
        <el-form-item label="重量(kg)">
          <el-input-number v-model="form.weight" :min="0" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="dialogVisible = false">取消</el-button>
        <el-button type="primary" @click="handleSubmit">确定</el-button>
      </template>
    </el-dialog>
  </div>
</template>
