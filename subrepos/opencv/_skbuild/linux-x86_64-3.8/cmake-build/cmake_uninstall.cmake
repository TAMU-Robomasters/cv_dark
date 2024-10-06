# -----------------------------------------------
# File that provides "make uninstall" target
#  We use the file 'install_manifest.txt'
#
# Details: https://gitlab.kitware.com/cmake/community/-/wikis/FAQ#can-i-do-make-uninstall-with-cmake
# -----------------------------------------------

if(NOT EXISTS "/home/kestrel41x4/Desktop/Robomasters/cv_dark.git/subrepos/opencv/_skbuild/linux-x86_64-3.8/cmake-build/install_manifest.txt")
  message(FATAL_ERROR "Cannot find install manifest: \"/home/kestrel41x4/Desktop/Robomasters/cv_dark.git/subrepos/opencv/_skbuild/linux-x86_64-3.8/cmake-build/install_manifest.txt\"")
endif()

file(READ "/home/kestrel41x4/Desktop/Robomasters/cv_dark.git/subrepos/opencv/_skbuild/linux-x86_64-3.8/cmake-build/install_manifest.txt" files)
string(REGEX REPLACE "\n" ";" files "${files}")
foreach(file ${files})
  message(STATUS "Uninstalling $ENV{DESTDIR}${file}")
  if(IS_SYMLINK "$ENV{DESTDIR}${file}" OR EXISTS "$ENV{DESTDIR}${file}")
    exec_program(
        "/home/kestrel41x4/Desktop/Robomasters/cv_dark.git/settings/home/tmp.cleanable/pip-build-env-s8krhyc1/overlay/lib/python3.8/site-packages/cmake/data/bin/cmake" ARGS "-E remove \"$ENV{DESTDIR}${file}\""
        OUTPUT_VARIABLE rm_out
        RETURN_VALUE rm_retval
    )
    if(NOT "${rm_retval}" STREQUAL 0)
      message(FATAL_ERROR "Problem when removing $ENV{DESTDIR}${file}")
    endif()
  else(IS_SYMLINK "$ENV{DESTDIR}${file}" OR EXISTS "$ENV{DESTDIR}${file}")
    message(STATUS "File $ENV{DESTDIR}${file} does not exist.")
  endif()
endforeach()
