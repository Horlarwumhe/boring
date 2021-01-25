import setuptools

setuptools.setup(name="boring",
                 version="0.0.1",
                 author="Horlarwumhe",
                 author_email="amachiever4real@gmail.com",
                 description="A small HTTP web server for wsgi compatible app",
                 long_description='',
                 long_description_content_type="text/markdown",
                 url="https://github.com/horlarwumhe/boring",
                 packages=setuptools.find_packages(),
                 classifiers=[
                     "Programming Language :: Python :: 3",
                     "License :: OSI Approved :: MIT License",
                     "Operating System :: OS Independent",
                 ],
                 python_requires='>=3.7',
                 entry_points='''
                 [console_scripts]
                 boring = boring.cli:main''')
