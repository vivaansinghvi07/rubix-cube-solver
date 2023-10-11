import pycubing
from setuptools import setup, find_packages

with open("README.md", "r") as f:
    description = f.read()

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
    # project_urls={
    #     "Documentation": "https://pynterface.readthedocs.io/en/latest/"
    # }
)
