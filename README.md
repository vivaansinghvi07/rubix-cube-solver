# Rubik's Cube Solver

This is a project I made using my [pycubing](https://github.com/vivaansinghvi07/pycubing) library, which models a Rubik's cube in Python and contains functions for solving it somewhat like a human would. It uses comptuer vision techniques to "read" a cube from a video, and then provides a frontend for using solver functions to interact with a cube through the browser.

The `backend` and `frontend` folders contain code for the respective parts of the project. The `frontend` portion contains a simple website made of HTML/CSS/JS. The `backend` portion is a WebSockets server utilizing many computer vision functions defined in `cv.py`. For a step-by-step demonstration of these functions, view the [`cv_testing.ipynb`](https://github.com/vivaansinghvi07/rubix-cube-solver/blob/main/cv_testing.ipynb) file.

Since instructions are not yet on the website, view `media/example_video.mov` to see how to use the computer vision process in the website.

## Usage 

To use, you will need to host both the frontend and backend on your device. To do this, open two terminal windows, and on each of them, run the following commands:

For the backend, go into the `backend` directory, activate a virtual environment with the packages in `requirements.txt`, and run the `server.py` file. On UNIX, this would be: 

```
$ cd backend
$ python3 -m venv .venv
$ source .venv/bin/activate
$ pip install -r requirements.txt
$ python3 server.py 
```

For the frontend, simply host the website locally. An example of a way to do this would be to install `live-server` via `npm`, then use it on the frontend directory:

```
$ npm install -g live-server 
$ live-server frontend
```

This way is particularly useful if you want to edit code and have it update the website automatically.

## License

This software is released under the MIT License.

## Contributing

Contribute by opening a pull request or an issue, any help is appreciated!
