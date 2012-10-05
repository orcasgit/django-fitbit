from setuptools import setup, find_packages

# FIXME: Can't install python-fitbit from setup.py until it's on PyPI
# For now, use "pip install -r requirements.txt"
required = ["fitbit"] + \
           [line for line in open('requirements.txt').read().split("\n") if not line.startswith("git")]

setup(
    name="django-fitbit",
    version=__import__("fitapp").__version__,
    author="orcas",
    author_email="",
    packages=find_packages(),
    install_requires=["distribute"] + required,
    include_package_data=True,
    url="https://github.com/orcasgit/django-fitbit/",
    license="",
    description="Django integration for python-fitbit",
    long_description=open("README.md").read(),
    classifiers=[
        "Development Status :: 3 - Alpha",
        'License :: OSI Approved :: Apache 2.0',
        "Environment :: Web Environment",
        "Framework :: Django",
        "Intended Audience :: Developers",
        "Programming Language :: Python :: 2 :: Only"
    ]
)
