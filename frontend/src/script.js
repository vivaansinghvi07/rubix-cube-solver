// makeshift enums
const STATE = {
  VIDEO_STREAM: "video-stream",
  CUBE_EDIT: "cube-edit",
  HOME_PAGE: "home-page",
  CUBE_PLAY: "cube-play"
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

// stores global variables in a somewhat organized fashion
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
    simpleString: undefined
  },
  pageState: undefined,
  currentColor: {
    id: undefined,
    color: undefined
  }
};

// closes each track in a video stream
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
      
      // attach the webcam stream to the video element
      let video = document.querySelector("#video-cam");
      if ("srcObject" in video) {
        video.srcObject = vidStream;
      } else {
        video.src = window.URL.createObjectURL(vidStream);
      }

      // after video is successfully mounted
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

// procedurally send video frames to the websocket server
function sendFrames(canvas, ctx) {

  // if we are done, break, otherwise execute the same function again
  if (!globalState.userVideo.sending) {
    return;
  }
  
  // send one frame
  ctx.drawImage(globalState.userVideo.video, 0, 0, canvas.width, canvas.height);
  img = canvas.toDataURL("image/png").split(";base64,")[1];
  globalState.webSocketConnection.socket.send(JSON.stringify({
    type: "frame", data: img
  }));

  setTimeout(() => {
    sendFrames(canvas, ctx)
  }, 100); // about ten images per second
}

// setup variables and begins sending frames to the server
function startVideoReceiving() {

  // make sure: the video is up, the server is connected, and the video is not sending already
  if (!globalState.userVideo.mounted || !globalState.webSocketConnection.socket || globalState.userVideo.sending) {
    createErrorToast("Video not found. Wait or skip this part.");
    return;
  }
  globalState.userVideo.sending = true;

  // setup canvas and begin sending frames
  const canvas = document.querySelector("#video-canvas")
  const ctx = canvas.getContext('2d');
  canvas.width = globalState.userVideo.video.clientWidth;
  canvas.height = globalState.userVideo.video.clientHeight;
  sendFrames(canvas, ctx);
}

// exit the video streaming, and tell the socket server that it is done
function endVideoReceiving() {
  if (globalState.userVideo.sending) {
    globalState.userVideo.sending = false;
    globalState.webSocketConnection.socket.send(JSON.stringify({
      type: "finish"  // sending this message prompts a response from the server with the read cube
    }));
  }
  toggleCubeEditState(true);  // go to the next part of the process
}

// toggles the state for video receiving
function toggleVideoReceivingState(on) {
  const page = document.querySelector("#video-stream-page");
  if (on) {

    // disable all the other states, begin webcam streaming
    globalState.pageState = STATE.VIDEO_STREAM;
    turnAllStatesOffExcept(STATE.VIDEO_STREAM);
    page.removeAttribute("hidden");
    page.style.display = "flex";
    openWebcam();
  } else {

    // close the webcam stream
    if (globalState.userVideo.video) {
      globalState.userVideo.video.pause();
      closeVidStream(globalState.userVideo.stream)
    }
    page.setAttribute("hidden", "hidden");
    page.style.display = "none"; // TODO: APPLY THIS LOGIC FOR EVERYTHING ELSE 

    // unset variables
    globalState.userVideo.sending = false;
    globalState.userVideo.mounted = false;
    globalState.userVideo.video = undefined;
    globalState.userVideo.stream = undefined;
  }
}

// toggles the cube editing state
function toggleCubeEditState(on) {  // uses visibility because it acts weird
  const page = document.querySelector("#cube-edit-page");
  if (on) {
    globalState.pageState = STATE.CUBE_EDIT;
    turnAllStatesOffExcept(STATE.CUBE_EDIT);
    page.style.display = "flex"; 
    page.removeAttribute("hidden")
    generateCubeFaces();
  } else {
    page.style.display = "none";
    page.setAttribute("hidden", "hidden")
  }
}

// toggles the home page state
function toggleHomePageState(on) {
  const page = document.querySelector("#home-page");
  if (on) {
    globalState.pageState = STATE.HOME_PAGE;
    turnAllStatesOffExcept(STATE.HOME_PAGE);
    page.style.display = "flex";
    page.removeAttribute("hidden");
  } else {
    page.style.display = "none";
    page.setAttribute("hidden", "hidden")
  }
}

// toggles the state with playing with the cube 
function toggleCubePlayState(on) {
  const page = document.querySelector("#cube-play-page");
  if (on) {
    globalState.pageState = STATE.CUBE_PLAY;
    turnAllStatesOffExcept(STATE.CUBE_PLAY);
    page.style.display = "flex";
    page.removeAttribute("hidden");
    generateInteractiveCube();
  } else {
    page.style.display = "none";
    page.setAttribute("hidden", "hidden")
  }
}

// starts the process, managing input from the home page 
function submitHomePageBegin() {
  
  // determine cube size
  const N = parseInt(document.querySelector("#home-page-size-input").value);
  if (N <= 0) {
    createErrorToast("Cube size must be at least 1.");
    return;
  } 

  // initialize the websocket server with the cube size 
  try {
    globalState.webSocketConnection.socket.send(JSON.stringify({
      type: "init", size: N
    }));
    globalState.cubeObject.N = N;
  } catch {
    createToast("Server not connected. Try again in a bit.");
    return;
  }

  // set cube size and go to the next thing
  toggleVideoReceivingState(true);
}

// get id of a square in the cube edit stage given a position in the simple string
function getSquareID(position) {
  return `cube-square-${position}`;
}

// generate the image of the cube which is edited by the user
function generateCubeFaces() {
  
  // setup, setting variables 
  const N = globalState.cubeObject.N;
  if (!globalState.cubeObject.simpleString) {
    globalState.cubeObject.simpleString = " ".repeat(N * N * 6);
  }
  const squareArray = Array.from(globalState.cubeObject.simpleString);
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
        let color = COLORS[colorChar];
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

// turns the simple string into the form that TTk can work with
function transformSimpleString(simpleString, N) {
  
  // helper function to flip a face vertically (across a horizontal axis)
  const flipFaceVertically = (faceString) => {
    
    // initialize variables
    const faceStringArray = Array.from(faceString);
    const newFaceString = new Array(faceStringArray.length);
    
    // map the vertical flipping
    for (let col = 0; col < N; col++) {
      for (let row = 0; row < Math.ceil(N / 2); row++) {
        newFaceString[row * N + col] = faceStringArray[(N - row - 1) * N + col];
        newFaceString[(N - row - 1) * N + col] = faceStringArray[row * N + col];
      }
    }
    return newFaceString.join("");
  }

  // construct the new string representation of the cube
  let newSimpleString = "";
  const ssFaceToTTk = [5, 3, 0, 4, 1, 2];
  for (const faceIndex of ssFaceToTTk) {
    let faceString = simpleString.substring(N * N * faceIndex, N * N * (faceIndex + 1));
    if (faceIndex !== 5)
      faceString = flipFaceVertically(faceString);
    newSimpleString += faceString;
  }
  return newSimpleString;
}

function generateInteractiveCube() {
  const { N, simpleString } = globalState.cubeObject;
  adjustedSimpleString = transformSimpleString(simpleString, N);
  TTk.AlgorithmPuzzle(N).fc(adjustedSimpleString).movePeriod(50).alg("R U R' U' R U R' U' R U R' U' R U R' U' R U R' U' R U R' U' R U R' U' R U R' U' R U R' U' R U R' U' R U R' U' R U R' U'")("#interactive-cube").movePeriod(5);
}

// reconstruct a "simple string" representation of the cube after the user is done editing
function finishCubeEditing() {
  
  const simpleStringLength = globalState.cubeObject.N * globalState.cubeObject.N * 6;
  const simpleStringArray = new Array(simpleStringLength);

  // build for each position
  for (let i = 0; i < simpleStringLength; i++) {
    let targetElement = document.getElementById(getSquareID(i));
    let color = targetElement.style.backgroundColor;   // I'm pretty sure this is the HEX value
    let [r, g, b] = Array.from(color.matchAll(/[0-9]+/g)).map(n => parseInt(n[0]));
    let colorHex = "#" + (1 << 24 | r << 16 | g << 8 | b).toString(16).slice(1);  // https://stackoverflow.com/a/5624139/22164400
    if (!(colorHex in COLORS)) {
      createErrorToast("Cube incomplete. Fill in the black squares.");
      return;
    }
    simpleStringArray[i] = COLORS[colorHex];  
  }
  const newSimpleString = simpleStringArray.join("");
  globalState.cubeObject.simpleString = newSimpleString;

  // go on to the next state, where the user interacts with the built cube
  toggleCubePlayState(true);
}

// turn off every state except for the given one
function turnAllStatesOffExcept(state) { 
  if (state !== STATE.CUBE_EDIT)
    toggleCubeEditState(false);
  if (state !== STATE.VIDEO_STREAM)
    toggleVideoReceivingState(false);
  if (state !== STATE.HOME_PAGE)
    toggleHomePageState(false);
  if (state !== STATE.CUBE_PLAY)
    toggleCubePlayState(false);
}

document.addEventListener("DOMContentLoaded", () => {
  const ws = new WebSocket("ws://localhost:8090/");
  
  // handle websocket messages coming FROM the server 
  ws.addEventListener("message", (data) => {
    const dataObj = JSON.parse(data);
    switch (dataObj.type) {
      case "cv_finish":
        globalState.cubeObject.simpleString = dataObj.cube;
        toggleCubeEditState(true);
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
  globalState.cubeObject.N = 5;
  globalState.cubeObject.simpleString = "wygryyywoboygwbogwrrrowwbworbrrgywgogogywybggrwrwgybogoobrywgbbywybrrbwrybborwyoogrbgwgrbryooogywbgobrgwgyywwryowggooywbgbybbwybggrrowwbrybooroboyyrgr"
  
  toggleCubeEditState(true);
});
