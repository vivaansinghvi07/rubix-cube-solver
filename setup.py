import pycubing
from setuptools import setup, find_packages

with open("./README.md", "r") as f:
    description = f.read()

with open("./requirements.txt", 'r') as f:
    requirements = f.read()

setup(
    name="pycubing",
    version=pycubing.__version__,
    author=pycubing.__author__,
    author_email='singhvi.vivaan@gmail.com',
    description="A feature-rich package for dealing with Rubik's cubes of any size in Python",
    long_description=description,
    long_description_content_type="text/markdown",
    license='MIT',
    packages=find_packages(),
    python_requires='>=3.8',
    include_package_data=True,
    install_requires=requirements
)
