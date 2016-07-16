appveyor\\build.cmd %PYTHON%\\python.exe setup.py bdist_wheel
IF "%APPVEYOR_REPO_TAG%"=="true" (
    IF "%APPVEYOR_REPO_TAG_NAME:~0,4%"=="rel_" (
        %PYTHON%\\Scripts\\twine.exe upload -u %PYPI_USERNAME% -p %PYPI_PASSWORD% dist\*.whl
    )
)
