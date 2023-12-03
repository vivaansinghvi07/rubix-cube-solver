// https://dev.to/arafat4693/how-to-create-a-toast-notification-in-javascript-261d

function createErrorToast(text) {
  const toast = document.createElement("li")
  toast.className = `toast error`
  toast.innerHTML = `<div class="column">
                         <i class="fa-solid fa-triangle-exclamation"></i>
                         <span>${text}</span>
                      </div>
                      <i class="fa-solid fa-xmark" onclick="removeToast(this.parentElement)"></i>`
  document.querySelector(".notifications").appendChild(toast);
  setTimeout(() => removeToast(toast), 5000);
}

function removeToast(toast) {
  toast.classList.add("hide")
  setTimeout(() => { toast.remove(); }, 500)
}
