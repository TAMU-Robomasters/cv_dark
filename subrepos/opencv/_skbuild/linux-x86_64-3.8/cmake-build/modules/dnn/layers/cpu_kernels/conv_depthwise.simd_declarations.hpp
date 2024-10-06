#define CV_CPU_SIMD_FILENAME "/home/kestrel41x4/Desktop/Robomasters/cv_dark.git/subrepos/opencv/opencv/modules/dnn/src/layers/cpu_kernels/conv_depthwise.simd.hpp"
#define CV_CPU_DISPATCH_MODE AVX
#include "opencv2/core/private/cv_cpu_include_simd_declarations.hpp"

#define CV_CPU_DISPATCH_MODE AVX2
#include "opencv2/core/private/cv_cpu_include_simd_declarations.hpp"

#define CV_CPU_DISPATCH_MODE RVV
#include "opencv2/core/private/cv_cpu_include_simd_declarations.hpp"

#define CV_CPU_DISPATCH_MODE LASX
#include "opencv2/core/private/cv_cpu_include_simd_declarations.hpp"

#define CV_CPU_DISPATCH_MODES_ALL LASX, RVV, AVX2, AVX, BASELINE

#undef CV_CPU_SIMD_FILENAME
