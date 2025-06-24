<script setup lang="ts">
import { ref, computed, nextTick } from 'vue'
import axios from 'axios'

// Component props - expects an observation ID and existing comments array
const props = defineProps<{
  observationId: number
  comments: any[]
}>()

// Emits events to parent component
const emit = defineEmits(['comment-added'])

// Form state
const newComment = ref('')
const replyingTo = ref<{ id: string; username: string } | null>(null)
const submitting = ref(false)
const error = ref('')
const maxLength = 300

const commentInputRef = ref<HTMLTextAreaElement | null>(null)

/**
 * Handles posting a new comment or reply
 * Validates input, checks auth, then submits to API
 */
const postComment = async () => {
  if (!newComment.value.trim()) return

  // Checks if user is logged in
  const token = localStorage.getItem('token')
  if (!token) {
    error.value = 'You must be logged in to post a comment.'
    return
  }

  submitting.value = true
  error.value = ''

  try {

    // Differents payloads for replies vs top-level comments
    if (replyingTo.value) {
      await axios.post(`http://localhost:8000/api/observations/${props.observationId}/`, {
        comment_text: newComment.value,
        parent_comment_id: replyingTo.value.id
        },
        {
          headers: {
            Authorization: `Bearer ${token}`
          }
        }
      )
    } else {
      // Regular comment without parents
      await axios.post(`http://localhost:8000/api/observations/${props.observationId}/`, {
        comment_text: newComment.value
        },
        {
          headers: {
            Authorization: `Bearer ${token}`
          }
        }
      )
    }

    // Resets form after successful post
    newComment.value = ''
    replyingTo.value = null
    emit('comment-added')
  } catch (err) {
    console.error('Failed to post comment/reply', err)
    error.value = 'Failed to post your message. Please try again.'
  } finally {
    submitting.value = false
  }
}

/**
 * Sets up the form to reply to a specific comment
 * @param commentId - ID of comment being replied to
 * @param username - Username of comment author (for display)
 */
const handleReplyClick = (commentId: string, username: string) => {
  replyingTo.value = { id: commentId, username }
  nextTick(() => {
    commentInputRef.value?.focus()
  })
}

const cancelReply = () => {
  replyingTo.value = null
}

/**
 * Formats a date string into a more readable relative time
 * @param dateString - ISO date string from API
 * @returns Formatted date string
 */
const formatDate = (dateString: string) => {
  if (!dateString) return ''
  
  const date = new Date(dateString)
  const now = new Date()
  const diffMs = now.getTime() - date.getTime()
  const diffDays = Math.floor(diffMs / (1000 * 60 * 60 * 24))
  
  // Returns relative time for recent dates
  if (diffDays < 1) return 'Today'
  if (diffDays === 1) return 'Yesterday'
  if (diffDays < 30) return `${diffDays} days ago`
  
  return date.toLocaleDateString()
}

const remainingChars = computed(() => maxLength - newComment.value.length)
</script>

<template>
  <div class="comments-wrapper">
    <div v-if="comments && comments.length > 0" class="comment-list">
      <div 
        v-for="(comment, index) in comments" 
        :key="index"
        class="comment-item"
      >
        <div class="comment-header">
          <div class="comment-user">
            <div class="user-avatar">
              <img 
                v-if="comment.user_profile_picture" 
                :src="comment.user_profile_picture" 
                alt="User avatar" 
                class="avatar-img"
              />
              <span v-else>👤</span>
            </div>
            <span class="user-name">{{ comment.user_name || 'Anonymous' }}</span>
          </div>
          <span class="comment-date">{{ formatDate(comment.timestamp) }}</span>
        </div>
        
        <div class="comment-body">
          {{ comment.comment_text }}
        </div>

        <!-- 💬 Reply Button -->
        <button class="reply-button" @click="handleReplyClick(comment._id, comment.user_name)">
          💬 Reply
        </button>

        <!-- Replies (nested under parent) -->
        <div 
          v-if="comment.replies && comment.replies.length" 
          class="replies-wrapper"
        >
          <div 
            v-for="reply in comment.replies" 
            :key="reply.id" 
            class="reply-item"
          >
            <div class="comment-header">
              <div class="comment-user">
                <div class="user-avatar">
                  <img 
                    v-if="reply.user_profile_picture" 
                    :src="reply.user_profile_picture" 
                    alt="User avatar" 
                    class="avatar-img"
                  />
                  <span v-else>👤</span>
                </div>
                <span class="user-name">{{ reply.user_name || 'Anonymous' }}</span>
              </div>
              <span class="comment-date">{{ formatDate(reply.timestamp) }}</span>
            </div>

            <div class="comment-body">
              {{ reply.comment_text }}
            </div>

            <button class="reply-button" @click="handleReplyClick(reply._id, reply.user_name)">
              💬 Reply
            </button>
          </div>
        </div>
      </div>
    </div>
    
    <div v-else class="no-comments">
      <p>No comments yet. Be the first to comment!</p>
    </div>
    
    <div class="comment-form">
      <h3 v-if="!replyingTo">Add a comment</h3>
      <h3 v-else>
        Replying to <strong>@{{ replyingTo.username }}</strong>
        <button @click="cancelReply" class="cancel-reply">Cancel</button>
      </h3>
      
      <textarea 
        ref="commentInputRef"
        v-model="newComment"
        :maxlength="maxLength"
        placeholder="Share your insights about this observation..."
        rows="4"
        class="comment-textarea"
        autofocus
      ></textarea>
      
      <div class="form-footer">
        <span class="char-counter" :class="{ 'warning': remainingChars < 20 }">
          {{ remainingChars }} characters remaining
        </span>
        
        <button 
          @click="postComment" 
          :disabled="submitting || !newComment.trim()"
          class="post-button"
        >
          {{ submitting ? 'Posting...' : (replyingTo ? 'Post Reply' : 'Post Comment') }}
        </button>
      </div>
      
      <p v-if="error" class="error-message">{{ error }}</p>
    </div>
  </div>
</template>

<style scoped>
.comments-wrapper {
  background: white;
  border-radius: var(--radius-lg);
  overflow: hidden;
  box-shadow: var(--shadow-md);
}

.comment-list {
  padding: var(--space-2);
}

.comment-item {
  padding: var(--space-2);
  margin-bottom: var(--space-2);
  border-bottom: 1px solid var(--color-neutral-200);
  animation: fadeIn 0.3s ease-in-out;
}

.comment-item:last-child {
  margin-bottom: 0;
  border-bottom: none;
}

.comment-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: var(--space-1);
}

.comment-user {
  display: flex;
  align-items: center;
  gap: var(--space-1);
}

.user-avatar {
  width: 30px;
  height: 30px;
  display: flex;
  align-items: center;
  justify-content: center;
  background-color: var(--color-primary-100);
  border-radius: 50%;
  color: var(--color-primary-700);
  overflow: hidden;
}

.avatar-img {
  width: 100%;
  height: 100%;
  border-radius: 50%;
  object-fit: cover;
}

.user-name {
  font-weight: 600;
  color: var(--color-primary-700);
}

.comment-date {
  font-size: var(--font-size-sm);
  color: var(--color-neutral-500);
}

.comment-body {
  color: var(--color-neutral-800);
  line-height: 1.5;
}

.reply-button {
  background: none;
  border: none;
  color: #007bff;
  cursor: pointer;
  margin-top: 0.5rem;
  font-size: 0.9rem;
}
.reply-button:hover {
  text-decoration: underline;
}

.replies-wrapper {
  margin-top: 0.5rem;
  margin-left: 2rem;
  border-left: 2px solid var(--color-neutral-200);
  padding-left: 1rem;
}

.reply-item {
  padding-top: var(--space-2);
  padding-bottom: var(--space-2);
  border-bottom: 1px dashed var(--color-neutral-200);
}

.no-comments {
  padding: var(--space-3);
  text-align: center;
  color: var(--color-neutral-600);
}

.comment-form {
  background-color: var(--color-neutral-50);
  padding: var(--space-3);
  border-top: 1px solid var(--color-neutral-200);
}

.comment-form h3 {
  margin-bottom: var(--space-2);
  color: var(--color-primary-700);
}

.cancel-reply {
  background: none;
  border: none;
  color: red;
  margin-left: 1rem;
  font-size: 0.85rem;
  cursor: pointer;
}

.comment-textarea {
  width: 100%;
  padding: var(--space-2);
  border: 1px solid var(--color-neutral-300);
  border-radius: var(--radius-md);
  font-family: inherit;
  font-size: var(--font-size-md);
  line-height: 1.5;
  resize: vertical;
  transition: border-color var(--transition-fast);
}

.comment-textarea:focus {
  outline: none;
  border-color: var(--color-primary-500);
}

.form-footer {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-top: var(--space-1);
}

.char-counter {
  font-size: var(--font-size-sm);
  color: var(--color-neutral-600);
}

.char-counter.warning {
  color: var(--color-warning-500);
}

.post-button {
  background-color: var(--color-primary-600);
  color: white;
  border: none;
  padding: var(--space-1) var(--space-2);
  border-radius: var(--radius-md);
  cursor: pointer;
  transition: background-color var(--transition-fast);
}

.post-button:hover:not(:disabled) {
  background-color: var(--color-primary-700);
}

.post-button:disabled {
  background-color: var(--color-neutral-400);
  cursor: not-allowed;
}

.error-message {
  color: var(--color-error-500);
  margin-top: var(--space-2);
  text-align: center;
}

@keyframes fadeIn {
  from { opacity: 0; transform: translateY(5px); }
  to { opacity: 1; transform: translateY(0); }
}
</style>