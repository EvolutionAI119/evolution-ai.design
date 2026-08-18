import { defineStore } from 'pinia'
import { ref, computed } from 'vue'

export const useUiStore = defineStore('ui', () => {
  const sidebarCollapsed = ref(false)
  const theme = ref('light')
  const currentLocale = ref('zh')
  const snackbar = ref({
    show: false,
    message: '',
    type: 'info',
    duration: 3000
  })

  const isDark = computed(() => theme.value === 'dark')

  function toggleSidebar() {
    sidebarCollapsed.value = !sidebarCollapsed.value
  }

  function setSidebarCollapsed(collapsed) {
    sidebarCollapsed.value = collapsed
  }

  function toggleTheme() {
    theme.value = theme.value === 'light' ? 'dark' : 'light'
    document.documentElement.classList.toggle('dark', theme.value === 'dark')
  }

  function setTheme(newTheme) {
    theme.value = newTheme
    document.documentElement.classList.toggle('dark', theme.value === 'dark')
  }

  function setLocale(locale) {
    currentLocale.value = locale
  }

  function showSnackbar(message, type = 'info', duration = 3000) {
    snackbar.value = { show: true, message, type, duration }
    setTimeout(() => {
      snackbar.value.show = false
    }, duration)
  }

  function hideSnackbar() {
    snackbar.value.show = false
  }

  return {
    sidebarCollapsed,
    theme,
    currentLocale,
    snackbar,
    isDark,
    toggleSidebar,
    setSidebarCollapsed,
    toggleTheme,
    setTheme,
    setLocale,
    showSnackbar,
    hideSnackbar
  }
})