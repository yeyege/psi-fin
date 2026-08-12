<script lang="ts">
/**
 * 通用多维度汇总 KPI 卡（渐变风格）
 * 配色取自数据看板统计卡，深度一致；支持跨页面复用。
 */
import type { Component } from 'vue'

export interface SummaryCard {
  label: string
  value: number | string
  unit?: string
  icon: Component
  gradient: { background: string; shadow: string }
}

// 看板同款渐变色板（背景 + 同色系投影）
export const GRADIENTS = {
  cyan:   { background: 'linear-gradient(135deg, #1a6a8a 0%, #3a9ec0 100%)', shadow: '0 6px 18px rgba(58, 158, 192, 0.35)' },
  blue:   { background: 'linear-gradient(135deg, #1a5cb0 0%, #3a8de0 100%)', shadow: '0 6px 18px rgba(58, 141, 224, 0.35)' },
  indigo: { background: 'linear-gradient(135deg, #2d4a8e 0%, #5470c6 100%)', shadow: '0 6px 18px rgba(84, 112, 198, 0.35)' },
  green:  { background: 'linear-gradient(135deg, #3a7a3f 0%, #6ba84f 100%)', shadow: '0 6px 18px rgba(107, 168, 79, 0.35)' },
  amber:  { background: 'linear-gradient(135deg, #8a5a0e 0%, #c98a1e 100%)', shadow: '0 6px 18px rgba(201, 138, 30, 0.35)' },
  red:    { background: 'linear-gradient(135deg, #a82828 0%, #d44848 100%)', shadow: '0 6px 18px rgba(212, 72, 72, 0.35)' },
  purple: { background: 'linear-gradient(135deg, #5a3088 0%, #7a4aa8 100%)', shadow: '0 6px 18px rgba(122, 74, 168, 0.35)' },
  orange: { background: 'linear-gradient(135deg, #a04525 0%, #c96535 100%)', shadow: '0 6px 18px rgba(201, 101, 53, 0.35)' },
}
</script>

<script setup lang="ts">
defineProps<{ cards: SummaryCard[] }>()

const formatNumber = (v: number | string) =>
  typeof v === 'number' ? v.toLocaleString('zh-CN') : v
</script>

<template>
  <div class="sum-grid">
    <div
      v-for="(c, i) in cards"
      :key="i"
      class="sum-card"
      :style="{ background: c.gradient.background, boxShadow: c.gradient.shadow }"
    >
      <div class="sum-icon"><el-icon :size="20"><component :is="c.icon" /></el-icon></div>
      <div class="sum-info">
        <div class="sum-label">{{ c.label }}</div>
        <div class="sum-value">{{ formatNumber(c.value) }}<span v-if="c.unit" class="sum-unit">{{ c.unit }}</span></div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.sum-grid {
  display: grid;
  grid-template-columns: repeat(4, 1fr);
  gap: 16px;
  margin-bottom: 16px;
}
.sum-card {
  position: relative;
  border-radius: 12px;
  padding: 14px 16px;
  height: 72px;
  box-sizing: border-box;
  display: flex;
  align-items: center;
  gap: 12px;
  color: #fff;
  overflow: hidden;
  transition: transform 0.25s ease, box-shadow 0.25s ease;
}
.sum-card:hover {
  transform: translateY(-3px);
}
/* 装饰圆：固定在右下角，不遮挡内容 */
.sum-card::after {
  content: '';
  position: absolute;
  right: -18px;
  bottom: -18px;
  width: 48px;
  height: 48px;
  border-radius: 50%;
  background: rgba(255, 255, 255, 0.12);
  pointer-events: none;
}
.sum-icon {
  position: relative;
  z-index: 1;
  width: 38px;
  height: 38px;
  border-radius: 10px;
  background: rgba(255, 255, 255, 0.22);
  backdrop-filter: blur(4px);
  display: flex;
  align-items: center;
  justify-content: center;
  color: #fff;
  flex-shrink: 0;
}
.sum-info {
  position: relative;
  z-index: 1;
  min-width: 0;
}
.sum-label {
  font-size: 12px;
  opacity: 0.9;
  margin-bottom: 2px;
  letter-spacing: 0.3px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.sum-value {
  font-size: 22px;
  font-weight: 700;
  line-height: 1.2;
  font-family: 'DIN', -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;
  white-space: nowrap;
}
.sum-unit {
  font-size: 12px;
  font-weight: 500;
  opacity: 0.85;
  margin-left: 2px;
}
@media (max-width: 768px) {
  .sum-grid {
    grid-template-columns: repeat(2, 1fr);
  }
}
</style>
