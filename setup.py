from setuptools import Extension, setup

setup(name='orca', ext_modules=[Extension('orca.tfs._fastdag', ['orca/tfs/_fastdag.c'],
                                          extra_compile_args=['-O3'])])
