# NOTE: I'm not sure how the "fkzvetmy" was generated
# but I got this path from the failed-to-build error message
__where_numpy_should_be="$HOME/tmp.cleanable/pip-build-env-fkzvetmy/overlay/lib/python3.8/site-packages/numpy/core/include"
__build_success_indicator="$HOME/tmp.cleanable/opencv_was_built"
# check if file exists
if ! [ -f "$__build_success_indicator" ]
then
    mkdir -p "$(dirname "$__where_numpy_should_be")"
    ln -s "$(tools nix lib_path_for python38Packages.numpy)/python3.8/site-packages/numpy/core/include" "$(dirname "$__where_numpy_should_be")"
    cd "$FORNIX_FOLDER/subrepos/opencv"
    pip wheel . --verbose && echo "true" > "$__build_success_indicator"
    cd -
fi
unset __where_numpy_should_be