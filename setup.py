from setuptools import setup, find_packages


def find_install_requires():
    return [line for line in open('requirements/base.txt').read().split("\n")
            if not line.startswith('-e')]

setup(
    name="django-fitbit",
    version=__import__("fitapp").__version__,
    author="orcas",
    author_email="",
    packages=find_packages(),
    install_requires=["setuptools"] + find_install_requires(),
    dependency_links=[
        "git+ssh://git@github.com/orcasgit/python-fitbit.git@oauth2-support-only#egg=fitbit"
    ],
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
        "Programming Language :: Python",
        "Programming Language :: Python :: 2",
        "Programming Language :: Python :: 2.6",
        "Programming Language :: Python :: 2.7",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.3",
        "Programming Language :: Python :: 3.4",
        "Programming Language :: Python :: 3.5",
        "Programming Language :: Python :: Implementation",
        "Programming Language :: Python :: Implementation :: PyPy"
    ],
    test_suite="runtests.runtests"
)
