from distutils.core import setup
from distutils.extension import Extension
from Cython.Build import cythonize


ext_modules = Extension("recorder",
              sources=["recorder.pyx"],
              include_dirs=[],
              library_dirs=[],
              libraries=["m", "avformat", "avcodec","avdevice","avutil","avfilter","swscale", "swresample"])

compiler_directives=dict(
            c_string_type="unicode",
            c_string_encoding="default",
            embedsignature=True,
            language_level=3,
        )


ext_modules = cythonize([ext_modules], compiler_directives=compiler_directives, annotate=True, build_dir="src")
setup(name="Demo", ext_modules=ext_modules)