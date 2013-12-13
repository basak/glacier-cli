from setuptools import setup


setup(
    name='counsyl-glacier-cli',
    version='0.1.0',
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
        'boto',
        'iso8601',
        'sqlalchemy',
        'python-gnupg',
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
