from setuptools import setup, find_packages

packages = find_packages()

setup(
    name='streetget',
    version='0.0.1',
    url='https://www.rocq.inria.fr/cluster-willow/gronat/streetget/',
    author='petr',
    author_email='',
    description='',
    platforms='any',
    license='MIT',
    packages=packages,
    install_requires=['docopt',
                      'Pillow',
                      'numpy',
                      'matplotlib',
                      'requests'
                      ],
    entry_points={
        'console_scripts': [
            'streetget = streetget.streetget:main',
        ],
    },
)

print packages
