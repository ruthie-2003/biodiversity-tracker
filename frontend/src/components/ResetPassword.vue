<script setup lang="ts">
import { ref, onMounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'

const route = useRoute()
const router = useRouter()
const token = ref('')
const newPassword = ref('')

// Gets token from URL query params when component mounts
onMounted(() => {
  token.value = route.query.token as string || ''
})

/**
 * Handles password reset submission
 * Sends token and new password to API, then redirects on success
 */
const handleReset = async () => {
  try {
    const response = await fetch("http://localhost:8000/api/auth/reset-password/", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ token: token.value, new_password: newPassword.value })
    })

    const data = await response.json()
    if (data.message) {
      // Success case - shows message and redirects to login
      alert(data.message)
      router.push('/auth/login') 
    } else {
      alert(data.error)
    }
  } catch (err) {
    console.error(err)
    alert("Something went wrong.")
  }
}
</script>

<template>
  <div class="upload-form-container">
    <h1>Reset Your Password</h1>
    <form class="upload-form" @submit.prevent="handleReset">
      <div class="form-group">
        <label>New Password</label>
        <input
          v-model="newPassword"
          type="password"
          required
          placeholder="Enter new password"
        />
      </div>
      <div class="form-actions">
        <button type="submit">Reset Password</button>
      </div>
    </form>
  </div>
</template>

<style scoped>
.upload-form-container {
  width: 60vw;
  max-width: 500px;
  margin: 4rem auto;
  padding: 2rem;
  background-color: white;
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-sm);
  border: 1px solid var(--color-neutral-100);
}

h1 {
  font-size: var(--font-size-3xl);
  color: var(--color-primary-900);
  margin-bottom: 1rem;
  font-weight: 700;
  text-align: center;
}

p {
  font-size: var(--font-size-md);
  color: var(--color-neutral-600);
  text-align: center;
  margin-bottom: 2rem;
}

.upload-form {
  display: flex;
  flex-direction: column;
  gap: 1.5rem;
}

.form-group {
  display: flex;
  flex-direction: column;
}

.form-group label {
  font-weight: 600;
  margin-bottom: 0.5rem;
  color: var(--color-primary-800);
}

.form-group input {
  padding: 0.5rem 0.75rem;
  font-size: var(--font-size-md);
  border: 1px solid var(--color-neutral-300);
  border-radius: var(--radius-sm);
  transition: border-color 0.2s ease;
}

.form-group input:focus {
  outline: none;
  border-color: var(--color-primary-500);
}

.form-actions {
  display: flex;
  justify-content: center;
}

.form-actions button {
  background-color: var(--color-primary-600);
  color: white;
  border: none;
  padding: 0.75rem 1.5rem;
  font-size: var(--font-size-md);
  font-weight: 600;
  border-radius: var(--radius-md);
  cursor: pointer;
  transition: background-color 0.2s ease;
}

.form-actions button:hover {
  background-color: var(--color-primary-700);
}

.form-footer {
  text-align: center;
  margin-top: -0.5rem;
}

.form-footer a {
  color: var(--color-primary-600);
  text-decoration: none;
  font-size: var(--font-size-sm);
}

.form-footer a:hover {
  text-decoration: underline;
}
</style>