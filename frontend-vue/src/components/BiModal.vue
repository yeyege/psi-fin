<script setup lang="ts">
/**
 * BI 通用下钻弹窗：Teleport 到 body，根节点带 .bi-scope 复用局部主题。
 * 支持点击遮罩 / 右上角 X / ESC 三种关闭方式；既可 @close 也可 v-model:visible。
 */
import { onMounted, onBeforeUnmount } from 'vue'

const props = defineProps<{ visible: boolean; title: string }>()
const emit = defineEmits<{ (e: 'close'): void; (e: 'update:visible', v: boolean): void }>()

const close = () => {
  emit('close')
  emit('update:visible', false)
}

const onKey = (ev: KeyboardEvent) => {
  if (ev.key === 'Escape' && props.visible) close()
}
onMounted(() => window.addEventListener('keydown', onKey))
onBeforeUnmount(() => window.removeEventListener('keydown', onKey))
</script>

<template>
  <Teleport to="body">
    <div v-if="visible" class="bi-scope bi-modal-root">
      <div class="bi-modal-mask" @click="close"></div>
      <div class="bi-modal-box">
        <div class="bi-modal-head">
          <h4>{{ title }}</h4>
          <button class="bi-modal-close" aria-label="关闭" @click="close">×</button>
        </div>
        <slot />
      </div>
    </div>
  </Teleport>
</template>
