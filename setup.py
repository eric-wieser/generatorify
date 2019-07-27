from setuptools import setup

version = '0.1.0'

setup(
    name='generatorify',
    py_modules=['generatorify'],
    version=version,
    description='Convert between repeated callback and generators',
    author='Eric Wieser',
    author_email='wieser.eric+generatorify@gmail.com',
    url='https://github.com/eric-wieser/generatorify',
    download_url='https://github.com/eric-wieser/raven-client/tarball/v'+version,
    keywords=['generator', 'requests', 'raven'],
    classifiers=[
        'License :: OSI Approved :: MIT License',
        'Programming Language :: Python :: 3',
        'Software Development :: Libraries :: Python Modules',
        'Intended Audience :: Developers',
        "Operating System :: OS Independent",
    ],
)
