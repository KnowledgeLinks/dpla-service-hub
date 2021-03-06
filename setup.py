from setuptools import setup, find_packages

VERSION = "0.9.9"

setup(
    "dpla_service_hub",
    version=VERSION,
    packages=find_packages(),
    include_package_data=True,
    install_requires=[
        'Click',
        'rdflib',
        'requests'
    ],
    entry_points='''
        [console_scripts]
        profile=dpla_service_hub.profile:cli
    ''',
)
    
