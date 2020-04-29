from setuptools import setup, find_packages

setup(
    name='pydoni',
    version=open('version').read(),
    author='Andoni Sooklaris',
    author_email='andoni.sooklaris@gmail.com',
    install_requires=open('requirements.txt').read(),
    packages=find_packages('pydoni'),
    package_dir={'': 'pydoni'},
    include_package_data=True
)
