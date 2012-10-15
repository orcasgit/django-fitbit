from setuptools import setup, find_packages

required = [line for line in open('requirements.txt').read().split("\n")]

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
        'License :: OSI Approved :: Apache Software License',
        "Environment :: Web Environment",
        "Framework :: Django",
        "Intended Audience :: Developers",
        "Programming Language :: Python :: 2 :: Only"
    ]
)
