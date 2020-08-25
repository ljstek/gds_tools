from setuptools import setup, find_packages

setup(
    name='gds_tools',

    version = '0.1.2',

    install_requires=[
        'numpy',
        'gdspy',
        'recordclass'
    ],

    license = 'MIT',

    author='Lieuwe Stek',
    author_email='lieuwe.stek@gmail.com',

    description=("Package aiding scripted design of structures for nanofabrication of devices for condensed matter physics research."),

    packages=find_packages(),

    classifiers=[
        'Development Status :: 2 - Pre-Alpha',
        'Intended Audience :: Science/Research',
        'Programming Language :: Python :: 3.6'
        ],

    keywords='gds gdsii cad script scripting physics nanofabrication condensed matter',

    url='https://github.com/kouwenhovenlab/gds_tools'
)
