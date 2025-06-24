<template>
  <div class="upload-form-container">
    <h1>BioDiversity Tracker</h1>
    <h2>Contribute to Biodiversity Research</h2>

    <div class="form-tabs">
      <router-link to="/auth/login" class="tab-link active">Login</router-link>
      <router-link to="/auth/register" class="tab-link">Register</router-link>
    </div>

    <form class="upload-form" @submit.prevent="handleLogin">
      <div class="form-group">
        <label>Email or Username</label>
        <input
          v-model="email"
          type="text"
          required
          placeholder="Enter your email or username"
        />
      </div>

      <div class="form-group">
        <label>Password</label>
          <input
            v-model="password"
            :type="showPassword ? 'text' : 'password'"
            required
            placeholder="Enter your password"
          />
      </div>

      <div class="form-footer">
        <router-link to="/auth/forgot-password">Forgot Password?</router-link>
      </div>

      <div class="form-actions">
        <button type="submit">
          Sign In
        </button>
      </div>
    </form>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { Eye, EyeOff } from 'lucide-vue-next'

const email = ref('')
const password = ref('')
const showPassword = ref(false)

// Handles the login submission
const handleLogin = async () => {
  try {
    const response = await fetch('http://localhost:8000/api/auth/login/', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json'
      },
      body: JSON.stringify({
        username_or_email: email.value,
        password: password.value
      })
    });

    if (!response.ok) {
      const error = await response.json();
      alert(error.error || 'Login failed.');
      return;
    }

    const data = await response.json();

    // Stores auth data
    localStorage.setItem('token', data.token);
    localStorage.setItem('user', JSON.stringify({
      username: data.username,
      roles: data.roles,
      isAdmin: data.isAdmin
    }));

    console.log('Login successful!');
    console.log('Token:', data.token);
    console.log('User:', {
      username: data.username,
      roles: data.roles,
      isAdmin: data.isAdmin
    });

    // Redirects after login to home
    window.location.href = "/";
  } catch (err) {
    console.error(err);
    alert('An error occurred during login.');
  }
}

</script>

<style scoped>
.upload-form-container {
  width: 60vw;
  margin: 2rem auto;
  padding: 2rem;
  background: white;
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-sm);
  border: 1px solid var(--color-neutral-100);
}

h1 {
  font-size: var(--font-size-3xl);
  color: var(--color-primary-900);
  margin-bottom: 1rem;
  font-weight: 600;
  text-align: center;
}

h2 {
  font-size: var(--font-size-lg);
  color: var(--color-neutral-600);
  margin-bottom: 2rem;
  text-align: center;
}

.form-tabs {
  display: flex;
  justify-content: center;
  margin-bottom: 2rem;
  border-bottom: 1px solid var(--color-neutral-200);
}

.tab-link {
  padding: 0.5rem 1rem;
  margin: 0 0.5rem;
  color: var(--color-neutral-500);
  font-weight: 500;
  border-bottom: 2px solid transparent;
}

.tab-link.active {
  color: var(--color-primary-600);
  border-bottom-color: var(--color-primary-600);
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