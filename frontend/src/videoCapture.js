let globalState = {
  userVideoMounted: {
    value: false,
    warningToast: "videoNotMountedWarning",
  },
  userVideoSending: {
    value: false,
  },
  webSocketConnection: {
    socket: undefined
  }
};

// https://www.tutorialspoint.com/how-to-open-a-webcam-using-javascript
function openCam() {
  let allMediaDevices = navigator.mediaDevices;
  if (!allMediaDevices || !allMediaDevices.getUserMedia) {
    console.log("getUserMedia() not supported."); // handle error here
    return;
  }

  // attempt to access the video stream
  allMediaDevices.getUserMedia({
    audio: false,
    video: true,
  })
    .then((vidStream) => {
      let video = document.getElementById("video-cam");
      if ("srcObject" in video) {
        video.srcObject = vidStream;
      } else {
        video.src = window.URL.createObjectURL(vidStream);
      }
      video.onloadedmetadata = () => {
        video.play();
        globalState.userVideoMounted.value = true;
      };
    })
    .catch(function (e) {
      console.log(e.name + ": " + e.message);
    });
}

function sendFrames(ws, video, canvas, ctx) {
  
  ctx.drawImage(video, 0, 0, canvas.width, canvas.height);
  img = canvas.toDataURL("image/png").split(";base64,")[1];
  ws.send(JSON.stringify({
    type: "frame", data: img
  }));

  if (!globalState.userVideoSending.value) {
    return;
  }

  setTimeout(() => {
    sendFrames(ws, video, canvas, ctx)
  }, 100); // about ten images per second
}

function startVideoReceiving() {
  if (!globalState.userVideoMounted.value || !globalState.webSocketConnection.socket || globalState.userVideoSending.value) {
    createToast(globalState.userVideoMounted.warningToast);
    return;
  }
  globalState.userVideoSending.value = true;

  const video = document.getElementById("video-cam");
  const canvas = document.getElementById("video-canvas")
  const ctx = canvas.getContext('2d');

  canvas.width = video.clientWidth;
  canvas.height = video.clientHeight;
  sendFrames(globalState.webSocketConnection.socket, video, canvas, ctx);
}

function endVideoReceiving() {
  if (!globalState.userVideoSending.value) {
    return;
  }

  globalState.userVideoSending.value = false;
  globalState.webSocketConnection.socket.send(JSON.stringify({
    type: "finish"
  }));
}

document.addEventListener("DOMContentLoaded", () => {
  const ws = new WebSocket("ws://localhost:8080/");
  ws.addEventListener("message", (data) => {
    const dataObj = JSON.parse(data);
    switch (dataObj.type) {
      case "cv_finish":
        console.log(dataObj.cube);
        break;
    }
  });
  globalState.webSocketConnection.socket = ws;
  setTimeout(() => {
    ws.send(JSON.stringify({
      type: "init",
      size: 3
    }));
  }, 1000);
  openCam();
});
