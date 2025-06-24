<template>
  <div class="upload-form-container">
    <h1>BioDiversity Tracker</h1>
    <h2>Contribute to Biodiversity Research</h2>

    <div class="form-tabs">
      <router-link to="/auth/login" class="tab-link">Login</router-link>
      <router-link to="/auth/register" class="tab-link active">Register</router-link>
    </div>


    <div v-if="showTermsModal" class="modal-overlay">
      <div class="modal-content">
        <h3>Terms and Conditions</h3>
        <p>
          By registering, you agree that the platform admins can block or delete your account at any time.
          If an account is deleted (by you or by admins), your data (like comments or uploads) may remain but will be anonymized.
          Comments cannot be edited or removed after submission. Your data helps scientific research.
        </p>
        <p>
          This is in line with personal data protection rule, and your continued use of the platform is considered acceptance.
        </p>
        <div class="modal-buttons">
        <button @click="acceptTerms">I Understand & Accept</button>
        <button @click="declineTerms" class="cancel-btn">Cancel</button>
        </div>
      </div>
    </div>

    <form class="upload-form" @submit.prevent="handleRegister">
      <div class="form-group">
        <label>Full Name</label>
        <input
          v-model="fullName"
          type="text"
          required
          placeholder="Enter your full name"
        />
      </div>

      <div class="form-group">
        <label>Username</label>
        <input
          v-model="username"
          type="text"
          required
          placeholder="Choose a username"
        />
      </div>

      <div class="form-group">
        <label>Email Address</label>
        <input
          v-model="email"
          type="email"
          required
          placeholder="Enter your email address"
        />
      </div>

      <div class="form-group">
        <label>Password</label>
          <input
            v-model="password"
            :type="showPassword ? 'text' : 'password'"
            required
            placeholder="Create a password (min. 8 characters)"
            minlength="8"
          />
        </div>

      <div class="form-group">
        <label>Confirm Password</label>
          <input
            v-model="confirmPassword"
            :type="showConfirmPassword ? 'text' : 'password'"
            required
            placeholder="Confirm your password"
          />
      </div>

      <div class="form-group terms-group">
        <label>
          <input
            type="checkbox"
            :checked="acceptedTerms"
            @click.prevent="handleTermsCheckboxClick"
          />
          I accept the
          <a href="#" @click.prevent="showTerms" style="text-decoration: underline;">
            Terms and Conditions
          </a>
        </label>
        <p v-if="showTermsMessage" class="terms-warning">Please read and accept the Terms and Conditions first.</p>
      </div>

      <div class="form-actions">
        <button type="submit">
          Register
        </button>
      </div>

      <div class="form-footer">
        <span>Already have an account?</span>
        <router-link to="/auth/login">Sign In</router-link>
      </div>

      <SuccessBanner :visible="showBanner" />

    </form>
  </div>
</template>

<script setup lang="ts">
import { ref } from 'vue'
import { Eye, EyeOff } from 'lucide-vue-next'
import SuccessBanner from '@/components/SuccessBanner.vue'
import axios from 'axios'

const fullName = ref('')
const username = ref('')
const email = ref('')
const password = ref('')
const confirmPassword = ref('')
const showPassword = ref(false)
const showConfirmPassword = ref(false)
const showBanner = ref(false)
const acceptedTerms = ref(false)
const showTermsModal = ref(false)
const showTermsMessage = ref(false)

// Handles the terms checkbox click - shows warning if not accepted
const handleTermsCheckboxClick = () => {
  if (!acceptedTerms.value) {
    showTermsMessage.value = true
    setTimeout(() => {
      showTermsMessage.value = false
    }, 2200) 
  }
}

// Shows the terms modal dialog
const showTerms = () => {
  showTermsModal.value = true
}

// User accepted terms - closes modal and marks as accepted
const acceptTerms = () => {
  acceptedTerms.value = true
  showTermsModal.value = false
}

// User declined terms - just closes the modal
const declineTerms = () => {
  showTermsModal.value = false
}

// Main registration handler
const handleRegister = async () => {

  // Validate terms acceptance first
  if (!acceptedTerms.value) {
    alert("Please accept the Terms and Conditions to continue.")
    return
  }

  // Basic password match validation
  if (password.value !== confirmPassword.value) {
    alert('Passwords do not match')
    return
  }

  try {
    await axios.post('http://localhost:8000/api/auth/register/', {
      full_name: fullName.value,
      username: username.value,
      email: email.value,
      password: password.value
    })

    // Show success banner on successful registration
    showBanner.value = true
  } catch (err: any) {
    console.error(err.response?.data || err.message)
    alert(err.response?.data?.detail || 'Registration failed.')
  }
}
</script>

<style scoped>

.terms-warning {
  color: var(--color-danger, #d9534f); /* Fallback if --color-danger not defined */
  font-size: var(--font-size-sm);
  margin-top: 0.25rem;
  animation: fadeInOut 3s ease forwards;
}

@keyframes fadeInOut {
  0% { opacity: 0; }
  10% { opacity: 1; }
  90% { opacity: 1; }
  100% { opacity: 0; }
}

.modal-overlay {
  position: fixed;
  top: 0;
  left: 0;
  width: 100%;
  height: 100%;
  background: rgba(0,0,0,0.6);
  display: flex;
  align-items: center;
  justify-content: center;
  z-index: 1000;
}

.modal-content {
  background: white;
  padding: 2rem;
  border-radius: var(--radius-md);
  width: 90%;
  max-width: 500px;
  box-shadow: var(--shadow-md);
  text-align: center;
}

.modal-content h3 {
  margin-bottom: 1rem;
}

.modal-content button {
  margin-top: 1rem;
  background-color: var(--color-primary-600);
  color: white;
  padding: 0.5rem 1.25rem;
  border: none;
  border-radius: var(--radius-sm);
  cursor: pointer;
}

.modal-content .modal-buttons {
  display: flex;
  justify-content: center;
  gap: 1rem;
  margin-top: 1.5rem;
  flex-wrap: wrap;
}

.modal-content .modal-buttons button {
  background-color: var(--color-primary-600);
  color: white;
  padding: 0.5rem 1.25rem;
  border: none;
  border-radius: var(--radius-sm);
  cursor: pointer;
  transition: background-color 0.2s ease;
}

.modal-content .modal-buttons button:hover {
  background-color: var(--color-primary-700);
}

.modal-content .modal-buttons .cancel-btn {
  background-color: var(--color-neutral-300);
  color: var(--color-neutral-800);
}

.modal-content .modal-buttons .cancel-btn:hover {
  background-color: var(--color-neutral-400);
}

.terms-group label {
  font-size: var(--font-size-sm);
  color: var(--color-neutral-700);
}

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