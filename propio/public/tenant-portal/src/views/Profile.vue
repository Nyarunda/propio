<template>
  <section class="space-y-6">
    <div class="rounded-xl border border-slate-200 bg-white p-6 shadow-sm dark:border-slate-800 dark:bg-slate-900">
      <h1 class="text-xl font-semibold text-slate-900 dark:text-white">Profile</h1>
      <p class="mt-2 text-sm text-slate-600 dark:text-slate-300">
        Update your account password for tenant portal access.
      </p>
    </div>

    <div class="rounded-xl border border-slate-200 bg-white p-6 shadow-sm dark:border-slate-800 dark:bg-slate-900">
      <h2 class="mb-4 text-lg font-semibold text-slate-900 dark:text-white">Change Password</h2>

      <form class="max-w-md space-y-4" @submit.prevent="handleChangePassword">
        <div>
          <label class="block text-sm font-medium text-slate-700 dark:text-slate-200">Current Password</label>
          <input
            v-model="passwordForm.current"
            type="password"
            required
            class="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm outline-none focus:border-propio-500 focus:ring-1 focus:ring-propio-500 dark:border-slate-700 dark:bg-slate-800"
          />
        </div>

        <div>
          <label class="block text-sm font-medium text-slate-700 dark:text-slate-200">New Password</label>
          <input
            v-model="passwordForm.new"
            type="password"
            required
            class="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm outline-none focus:border-propio-500 focus:ring-1 focus:ring-propio-500 dark:border-slate-700 dark:bg-slate-800"
          />
        </div>

        <div>
          <label class="block text-sm font-medium text-slate-700 dark:text-slate-200">Confirm New Password</label>
          <input
            v-model="passwordForm.confirm"
            type="password"
            required
            class="mt-1 w-full rounded-lg border border-slate-300 px-3 py-2 text-sm outline-none focus:border-propio-500 focus:ring-1 focus:ring-propio-500 dark:border-slate-700 dark:bg-slate-800"
          />
        </div>

        <button
          type="submit"
          :disabled="changingPassword"
          class="rounded-lg bg-propio-600 px-4 py-2 text-sm font-medium text-white transition hover:bg-propio-700 disabled:cursor-not-allowed disabled:opacity-50"
        >
          {{ changingPassword ? "Updating..." : "Update Password" }}
        </button>

        <p v-if="passwordMessage" class="text-sm" :class="passwordMessageType">
          {{ passwordMessage }}
        </p>
      </form>
    </div>
  </section>
</template>

<script setup lang="ts">
import axios from "axios"
import { ref } from "vue"

const changingPassword = ref(false)
const passwordMessage = ref("")
const passwordMessageType = ref("")
const passwordForm = ref({
  current: "",
  new: "",
  confirm: "",
})

async function handleChangePassword() {
  if (passwordForm.value.new !== passwordForm.value.confirm) {
    passwordMessage.value = "New passwords do not match."
    passwordMessageType.value = "text-rose-600"
    return
  }

  if (passwordForm.value.new.length < 6) {
    passwordMessage.value = "Password must be at least 6 characters."
    passwordMessageType.value = "text-rose-600"
    return
  }

  changingPassword.value = true
  passwordMessage.value = ""

  try {
    const { data } = await axios.post("/api/method/propio.portal_utils.auth.change_password", {
      current_password: passwordForm.value.current,
      new_password: passwordForm.value.new,
      confirm_password: passwordForm.value.confirm,
    })

    const payload = data?.message || data
    if (payload?.success) {
      passwordMessage.value = payload.message || "Password changed successfully."
      passwordMessageType.value = "text-emerald-600"
      passwordForm.value = { current: "", new: "", confirm: "" }
    } else {
      passwordMessage.value = payload?.message || "Failed to change password."
      passwordMessageType.value = "text-rose-600"
    }
  } catch (err: any) {
    passwordMessage.value = err?.response?.data?.message || "Failed to change password."
    passwordMessageType.value = "text-rose-600"
  } finally {
    changingPassword.value = false
  }
}
</script>
