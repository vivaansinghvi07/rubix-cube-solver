// https://dev.to/arafat4693/how-to-create-a-toast-notification-in-javascript-261d

toastDetails = {
   videoNotMountedWarning: {
    label: "error",
    text: "Video not found. Wait or skip this part.",
    icon: "fa-triangle-exclamation"
  },
  cubeEditIncomplete: {
    label: "error",
    text: "Cube incomplete. Fill in the black squares.",
    icon: "fa-triangle-exclamation"
  }
}

function createToast(id) {
  const { label, icon, text } = toastDetails[id];
  const toast = document.createElement("li")
  toast.className = `toast ${label}`
  toast.innerHTML = `<div class="column">
                         <i class="fa-solid ${icon}"></i>
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
