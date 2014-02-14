from setuptools import setup
from pip.req import parse_requirements

setup(
    name='counsyl-glacier-cli',
    version='0.1.1.alpha',
    author='Counsyl',
    author_email='root@counsyl.com',
    maintainer='Counsyl',
    maintainer_email='root@counsyl.com',
    description='Command-line interface to Amazon Glacier',
    long_description=open('README.md', 'rt').read(),
    url='https://github.counsyl.com/dev/glacier-cli',

    py_modules=['glacier', 'gpg'],
    zip_safe=False,
    install_requires=[
        str(req.req) for req in parse_requirements('requirements.txt')
    ],
    tests_require=[
        str(req.req) for req in parse_requirements('requirements-dev.txt')
    ],
    classifiers=(
        "Development Status :: 3 - Alpha",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: BSD License",
        "Operating System :: OS Independent",
        "Programming Language :: Python :: 2.7",
        "Topic :: System :: Logging",
    ),
)
