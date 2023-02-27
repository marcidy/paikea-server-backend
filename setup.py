import setuptools

with open("README.md", 'r') as fh:
    long_description = fh.read()


setuptools.setup(
    name="paikea-server-backend",
    version="0.1.0",
    author="Matthew Arcidy",
    author_email="marcidy@gmail.com",
    description="back end data warehouse and processing for Paikea",
    long_description=long_description,
    long_description_content_type="test/markdown",
    url="None",
    package=setuptools.find_packages(),
    classifiers=[
        "Programming Language :: Python :: 3",
    ],
    python_requires='>=3.7',
)
