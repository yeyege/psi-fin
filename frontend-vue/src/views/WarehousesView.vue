<script setup lang="ts">
/**
 * 仓库 / 库区 / 库位 管理（层级结构，对标领星WMS）
 */
import { ref, onMounted, watch } from 'vue'
import { ElMessage } from 'element-plus'
import {
  getWarehouses, createWarehouse,
  getZones, createZone,
  getLocations, createLocation,
  type Warehouse, type Zone, type Location,
} from '@/api'

const activeTab = ref('warehouses')

// ============ 仓库 ============
const warehouses = ref<Warehouse[]>([])
const whDialog = ref(false)
const whForm = ref({ code: '', name: '' })

const loadWarehouses = async () => {
  const res = await getWarehouses()
  warehouses.value = res.data
}

const submitWarehouse = async () => {
  await createWarehouse({ ...whForm.value })
  ElMessage.success('仓库创建成功')
  whDialog.value = false
  whForm.value = { code: '', name: '' }
  await loadWarehouses()
}

// ============ 库区 ============
const zones = ref<Zone[]>([])
const zoneDialog = ref(false)
const zoneForm = ref({ warehouseId: 0, code: '', name: '', zoneType: 'GOODS' })

const loadZones = async () => {
  const res = await getZones()
  zones.value = res.data
}

const submitZone = async () => {
  await createZone({ ...zoneForm.value })
  ElMessage.success('库区创建成功')
  zoneDialog.value = false
  zoneForm.value = { warehouseId: 0, code: '', name: '', zoneType: 'GOODS' }
  await loadZones()
}

// ============ 库位 ============
const locations = ref<Location[]>([])
const locDialog = ref(false)
const locForm = ref({ zoneId: 0, warehouseId: 0, code: '', priority: 0 })

const loadLocations = async () => {
  const res = await getLocations({})
  locations.value = res.data
}

const submitLocation = async () => {
  await createLocation({ ...locForm.value })
  ElMessage.success('库位创建成功')
  locDialog.value = false
  locForm.value = { zoneId: 0, warehouseId: 0, code: '', priority: 0 }
  await loadLocations()
}

watch(activeTab, async (tab) => {
  if (tab === 'warehouses') await loadWarehouses()
  else if (tab === 'zones') await loadZones()
  else await loadLocations()
})

onMounted(loadWarehouses)
</script>

<template>
  <div>
    <el-tabs v-model="activeTab">
      <el-tab-pane label="仓库" name="warehouses">
        <el-button type="success" style="margin-bottom: 12px" @click="whDialog = true">新增仓库</el-button>
        <el-table :data="warehouses" border stripe>
          <el-table-column prop="id" label="ID" width="80" />
          <el-table-column prop="code" label="仓库编码" width="140" />
          <el-table-column prop="name" label="仓库名称" />
          <el-table-column label="状态" width="100">
            <template #default="{ row }">
              <el-tag :type="row.status === 'ACTIVE' ? 'success' : 'info'">{{ row.status }}</el-tag>
            </template>
          </el-table-column>
        </el-table>
      </el-tab-pane>

      <el-tab-pane label="库区" name="zones">
        <el-button type="success" style="margin-bottom: 12px" @click="zoneDialog = true">新增库区</el-button>
        <el-table :data="zones" border stripe>
          <el-table-column prop="id" label="ID" width="80" />
          <el-table-column prop="code" label="库区编码" width="140" />
          <el-table-column prop="name" label="库区名称" />
          <el-table-column label="类型" width="120">
            <template #default="{ row }">
              <el-tag :type="row.zoneType === 'GOODS' ? 'success' : 'warning'">
                {{ row.zoneType === 'GOODS' ? '正品区' : '残次品区' }}
              </el-tag>
            </template>
          </el-table-column>
          <el-table-column prop="warehouseId" label="所属仓库ID" width="120" />
        </el-table>
      </el-tab-pane>

      <el-tab-pane label="库位" name="locations">
        <el-button type="success" style="margin-bottom: 12px" @click="locDialog = true">新增库位</el-button>
        <el-table :data="locations" border stripe>
          <el-table-column prop="id" label="ID" width="80" />
          <el-table-column prop="code" label="库位编码" width="160" />
          <el-table-column prop="warehouseId" label="仓库ID" width="100" />
          <el-table-column prop="zoneId" label="库区ID" width="100" />
          <el-table-column prop="priority" label="优先级" width="100" />
          <el-table-column label="状态" width="100">
            <template #default="{ row }">
              <el-tag :type="row.status === 'FREE' ? 'success' : 'warning'">{{ row.status }}</el-tag>
            </template>
          </el-table-column>
        </el-table>
      </el-tab-pane>
    </el-tabs>

    <!-- 新增仓库 -->
    <el-dialog v-model="whDialog" title="新增仓库" width="420px">
      <el-form :model="whForm" label-width="80px">
        <el-form-item label="编码"><el-input v-model="whForm.code" placeholder="如 WH-C" /></el-form-item>
        <el-form-item label="名称"><el-input v-model="whForm.name" /></el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="whDialog = false">取消</el-button>
        <el-button type="primary" @click="submitWarehouse">确定</el-button>
      </template>
    </el-dialog>

    <!-- 新增库区 -->
    <el-dialog v-model="zoneDialog" title="新增库区" width="440px">
      <el-form :model="zoneForm" label-width="80px">
        <el-form-item label="所属仓库">
          <el-select v-model="zoneForm.warehouseId" placeholder="选择仓库" style="width: 100%">
            <el-option v-for="w in warehouses" :key="w.id" :label="`${w.code} ${w.name}`" :value="w.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="编码"><el-input v-model="zoneForm.code" placeholder="如 A-GOODS" /></el-form-item>
        <el-form-item label="名称"><el-input v-model="zoneForm.name" /></el-form-item>
        <el-form-item label="类型">
          <el-radio-group v-model="zoneForm.zoneType">
            <el-radio value="GOODS">正品区</el-radio>
            <el-radio value="DEFECT">残次品区</el-radio>
          </el-radio-group>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="zoneDialog = false">取消</el-button>
        <el-button type="primary" @click="submitZone">确定</el-button>
      </template>
    </el-dialog>

    <!-- 新增库位 -->
    <el-dialog v-model="locDialog" title="新增库位" width="440px">
      <el-form :model="locForm" label-width="80px">
        <el-form-item label="所属仓库">
          <el-select v-model="locForm.warehouseId" placeholder="选择仓库" style="width: 100%" @change="locForm.zoneId = 0">
            <el-option v-for="w in warehouses" :key="w.id" :label="`${w.code} ${w.name}`" :value="w.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="所属库区">
          <el-select v-model="locForm.zoneId" placeholder="先选仓库" style="width: 100%">
            <el-option v-for="z in zones.filter(z => z.warehouseId === locForm.warehouseId)" :key="z.id"
              :label="z.name" :value="z.id" />
          </el-select>
        </el-form-item>
        <el-form-item label="编码"><el-input v-model="locForm.code" placeholder="如 A-03-01" /></el-form-item>
        <el-form-item label="优先级">
          <el-input-number v-model="locForm.priority" :min="0" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="locDialog = false">取消</el-button>
        <el-button type="primary" @click="submitLocation">确定</el-button>
      </template>
    </el-dialog>
  </div>
</template>
