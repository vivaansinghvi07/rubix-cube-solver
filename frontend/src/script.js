// makeshift enums
const STATE = {
  VIDEO_STREAM: "video-stream",
  CUBE_EDIT: "cube-edit",
  HOME_PAGE: "home-page"
}
const COLORS = {
  'r': "#ff0000",
  'b': "#0000ff",
  'g': "#00ff00",
  'o': "#ff9900",
  'y': "#ffee00",
  'w': "#ffffff",
  ' ': "#000000",
  "#ff0000": 'r',
  "#0000ff": 'b',
  "#00ff00": 'g',
  "#ff9900": 'o',
  "#ffee00": 'y',
  "#ffffff": 'w',
}
const BORDER_WIDTH = 3;

let globalState = {
  userVideo: {
    mounted: false,
    sending: false,
    stream: undefined,
    video: undefined
  },
  webSocketConnection: {
    socket: undefined
  },
  cubeObject: {
    N: undefined,
    simple_string: undefined
  },
  pageState: undefined,
  currentColor: {
    id: undefined,
    color: undefined
  }
};

function closeVidStream(stream) {
  for (const track of stream.getTracks()) {
    track.stop();
  }
}

// https://www.tutorialspoint.com/how-to-open-a-webcam-using-javascript
function openWebcam() {
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

      let video = document.querySelector("#video-cam");
      if ("srcObject" in video) {
        video.srcObject = vidStream;
      } else {
        video.src = window.URL.createObjectURL(vidStream);
      }
      video.onloadedmetadata = () => {
        
        if (globalState.pageState === STATE.VIDEO_STREAM) {
          video.play();
          globalState.userVideo.mounted = true;
          globalState.userVideo.video = video;
          globalState.userVideo.stream = vidStream;
        } else {
          closeVidStream(vidStream);
        }
      };
    })
    .catch(function (e) {
      console.log(e.name + ": " + e.message);
    });
}

function sendFrames(canvas, ctx) {
  
  ctx.drawImage(globalState.userVideo.video, 0, 0, canvas.width, canvas.height);
  img = canvas.toDataURL("image/png").split(";base64,")[1];
  globalState.webSocketConnection.socket.send(JSON.stringify({
    type: "frame", data: img
  }));

  if (!globalState.userVideo.sending) {
    return;
  }
  
  setTimeout(() => {
    sendFrames(canvas, ctx)
  }, 100); // about ten images per second
}

function startVideoReceiving() {
  if (!globalState.userVideo.mounted || !globalState.webSocketConnection.socket || globalState.userVideo.sending) {
    createToast("videoNotMountedWarning");
    return;
  }
  globalState.userVideo.sending = true;

  const canvas = document.querySelector("#video-canvas")
  const ctx = canvas.getContext('2d');

  canvas.width = video.clientWidth;
  canvas.height = video.clientHeight;
  sendFrames(canvas, ctx);
}

function endVideoReceiving() {
  if (globalState.userVideo.sending) {
    globalState.userVideo.sending = false;
    globalState.webSocketConnection.socket.send(JSON.stringify({
      type: "finish"
    }));
  }
  toggleCubeModState(true);
}

function toggleVideoReceivingState(on) {
  if (on) {
    globalState.pageState = STATE.VIDEO_STREAM;
    allStatesOffExcept(STATE.VIDEO_STREAM);
    document.querySelector("#video-stream-page").removeAttribute("hidden");
    openWebcam();
  } else {
    if (globalState.userVideo.video) {
      globalState.userVideo.video.pause();
      closeVidStream(globalState.userVideo.stream)
    }
    document.querySelector("#video-stream-page").setAttribute("hidden", "hidden");
    globalState.userVideo.sending = false;
    globalState.userVideo.mounted = false;
  }
}

function toggleCubeModState(on) {  // uses visibility because it acts weird
  if (on) {
    globalState.pageState = STATE.CUBE_EDIT;
    allStatesOffExcept(STATE.CUBE_EDIT);
    document.querySelector("#cube-edit-page").style.visibility = "visible"; 
    generateCubeFaces();
  } else {
    document.querySelector("#cube-edit-page").style.visibility = "hidden";
  }
}

function toggleHomePageState(on) {
  if (on) {
    globalState.pageState = STATE.HOME_PAGE;
    allStatesOffExcept(STATE.HOME_PAGE);
    document.querySelector("#home-page").removeAttribute("hidden");
  } else {
    document.querySelector("#home-page").setAttribute("hidden", "hidden");
  }
}

function getSquareColor(colorChar) {
  if (colorChar in COLORS) {
    return COLORS[colorChar];
  }
}

function getSquareID(position) {
  return `cube-square-${position}`;
}

function generateCubeFaces() {
  const N = globalState.cubeObject.N;
  if (!globalState.cubeObject.simple_string) {
    globalState.cubeObject.simple_string = " ".repeat(N * N * 6);
  }
  const squareArray = Array.from(globalState.cubeObject.simple_string);
  const container = document.querySelector("#cube-edit-container");
  const squareWidth = Math.round(container.clientWidth / (4 * N));

  // place offsets to help the borders look better
  container.innerHTML = `<div style="position: absolute; background-color: black;` +
                                     `height: ${squareWidth * N + BORDER_WIDTH * 2}px;` + 
                                     `left: -${BORDER_WIDTH}px;` + 
                                     `width: ${squareWidth * N * 4 + BORDER_WIDTH * 2}px;` + 
                                     `top: ${squareWidth * N - BORDER_WIDTH}px;"></div>`;
  container.innerHTML += `<div style="position: absolute; background-color: black;` +
                                     `height: ${squareWidth * N * 3 + BORDER_WIDTH * 2}px;` + 
                                     `top: -${BORDER_WIDTH}px;` + 
                                     `width: ${squareWidth * N + BORDER_WIDTH * 2}px;` + 
                                     `left: ${squareWidth * N - BORDER_WIDTH}px;"></div>`;

  // build each face
  for (let face = 0; face < 6; ++face) {

    // determine what to offset each face by
    let leftOffset, topOffset;
    if (face < 4) { // front, left, back, right
      topOffset = N;
      leftOffset = ((5 - face) % 4) * N;
    } else { // top or bottom
      leftOffset = N;
      if (face === 5) {
        topOffset = 2 * N;
      } else {
        topOffset = 0;
      }
    }

    // build each square
    for (let y = 0; y < N; ++y) {
      for (let x = 0; x < N; ++x) {

        // apply stylings based on location
        let width = squareWidth;
        let left = squareWidth * (x + leftOffset);
        let top = squareWidth * ((face === 5 ? N - y - 1 : y) + topOffset);

        // determine what position it is on the array
        let position = face * N * N + y * N + x;
        let id = getSquareID(position);

        // put the face onto display
        let colorChar = squareArray[position];
        let color = getSquareColor(colorChar);
        container.innerHTML += `<div class="cube-square" id="${id}"` + 
                                    `style="width: ${width}px; left: ${left}px; ` +
                                           `top: ${top}px; background-color: ${color}; ` + 
                                           `width: ${width}"></div>`
      }
    }
  }

  // build event listeners for each square to change color
  Array.from(document.querySelectorAll(".cube-square")).forEach((ele) => {
    ele.addEventListener('click', () => {
      ele.style.backgroundColor = globalState.currentColor.color;
    });
  });
}

function finishCubeEditing() {

  // build a new "simple string" representation of the cube using current colors
  const simpleStringLength = globalState.cubeObject.N * globalState.cubeObject.N * 6;
  const simpleStringArray = new Array(simpleStringLength);
  for (let i = 0; i < simpleStringLength; i++) {
    let targetElement = document.getElementById(getSquareID(i));
    let color = targetElement.style.backgroundColor;   // I'm pretty sure this is the HEX value
    let [r, g, b] = Array.from(color.matchAll(/[0-9]+/g)).map(n => parseInt(n[0]));
    let colorHex = "#" + (1 << 24 | r << 16 | g << 8 | b).toString(16).slice(1);  // https://stackoverflow.com/a/5624139/22164400
    if (!(colorHex in COLORS)) {
      createToast("cubeEditIncomplete");
      return;
    }
    simpleStringArray[i] = COLORS[colorHex];  
  }
  const newSimpleString = simpleStringArray.join("");
  
  toggleCubePlayState(true);
  console.log(newSimpleString);
}

function allStatesOffExcept(state) { 
  if (state !== STATE.CUBE_EDIT)
    toggleCubeModState(false);
  if (state !== STATE.VIDEO_STREAM)
    toggleVideoReceivingState(false);
  if (state !== STATE.HOME_PAGE)
    toggleHomePageState(false);
}

document.addEventListener("DOMContentLoaded", () => {
  const ws = new WebSocket("ws://localhost:8080/");
  
  // handle websocket messages coming FROM the server 
  ws.addEventListener("message", (data) => {
    const dataObj = JSON.parse(data);
    switch (dataObj.type) {
      case "cv_finish":
        globalState.cubeObject.simple_string = dataObj.cube;
        toggleCubeModState(true);
        break;
    }
  });

  // for the color pickers, they handle their own clicks
  const colorPickers = Array.from(document.querySelectorAll(".color-picker"))
  colorPickers.forEach((ele) => {
    ele.addEventListener("click", () => {
      colorPickers.forEach((secondEle) => {
        secondEle.classList.remove("selected");
      });
      ele.classList.add("selected");
      globalState.currentColor = {
        id: ele.id, color: ele.style.backgroundColor
      }
    });
  });

  globalState.webSocketConnection.socket = ws;
  setTimeout(() => {
    ws.send(JSON.stringify({
      type: "init",
      size: 3
    }));
  }, 1000);
  globalState.cubeObject.N = 5;
  globalState.cubeObject.simple_string = "wygryyywoboygwbogwrrrowwbworbrrgywgogogywybggrwrwgybogoobrywgbbywybrrbwrybborwyoogrbgwgrbryooogywbgobrgwgyywwryowggooywbgbybbwybggrrowwbrybooroboyyrgr"
  
  toggleCubeModState(true);

});
