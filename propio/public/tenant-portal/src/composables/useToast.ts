import { ref } from 'vue'

export type ToastType = 'success' | 'error' | 'info' | 'warning'

export interface ToastItem {
  id: number
  title: string
  text?: string
  type: ToastType
}

const toasts = ref<ToastItem[]>([])
let nextId = 1

export function useToast() {
  const remove = (id: number) => {
    toasts.value = toasts.value.filter((t) => t.id !== id)
  }

  const push = (payload: Omit<ToastItem, 'id'>, ttl = 3500) => {
    const toast = { id: nextId++, ...payload }
    toasts.value.push(toast)
    window.setTimeout(() => remove(toast.id), ttl)
  }

  return { toasts, push, remove }
}
