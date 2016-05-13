@echo off
echo Upgrading PIP
pause
python -m pip install --upgrade pip
python -m pip install --upgrade pip
python -m pip install --upgrade pip
echo .
echo Done
echo .

echo Preparing to install ndscheduler
pause
pushd data\ndscheduler
python setup.py install
popd
echo .
echo Done
echo .

echo Preparing to install pymssql 2.1.2
pause
pip install data\pymssql-2.1.2-cp27-cp27m-win_amd64.whl
echo .
echo Done
echo .

echo Preparing to install additonal required software
pause
pip install -r data\requirements.txt
echo .
echo Done
echo .
pause

echo Fixing file permissions on new modules
pause
D:
cd \Python
chmod -R a+rx .
echo .
echo Done
echo .
pause
