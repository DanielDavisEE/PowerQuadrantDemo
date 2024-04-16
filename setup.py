from setuptools import setup

with open("README.md", 'r') as f:
    long_description = f.read()

setup(
    name='power-quadrant-demo',
    version='0.1',
    author='Daniel Davis',
    description="A demo for showing the relationship between power, current, voltage and power factor.",
    long_description=long_description,
    url='https://github.com/DanielDavisEE/PowerQuadrantDemo',
    python_requires='>=3.10, <4',
    package_dir={'': 'src'},
    packages=['power_quadrant_demo'],
    install_requires=[
        'numpy',
        'matplotlib'
    ],
    package_data={
    },
    entry_points={
    }
)
