from setuptools import setup, find_packages

setup(
    name="zellular",
    version="0.1.8",
    author="Mahdi",
    author_email="mahdi@zellular.xyz",
    description="SDK package for zelluar sequencer",
    long_description=open('README.md').read(),
    long_description_content_type="text/markdown",
    url="https://github.com/zellular-xyz/zellular.py",
    py_modules=["zellular"],
    packages=find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
    ],
    python_requires='>=3.6',
    install_requires=[
        "eigensdk",
        "requests",
        "xxhash"
    ],
)
