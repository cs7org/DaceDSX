from setuptools import setup, Extension
from Cython.Build import cythonize
import numpy as np
import bitarray

extensions = [Extension("rle_generation", ["rle_generation.pyx"],
                        include_dirs=[np.get_include()])]
#setup(
#    ext_modules = cythonize("rle_generation.pyx", compiler_directives={'language_level': 3})
#)
setup(name="rle_generation",
      ext_modules=cythonize(extensions, compiler_directives={'language_level': 3}))