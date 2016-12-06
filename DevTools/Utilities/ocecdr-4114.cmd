SETLOCAL
D:
cd D:\home\bkline\sandboxes\ocecdr-4114
copy Inetpub\wwwroot\cgi-bin\cdr\EditFilter.py \Inetpub\wwwroot\cgi-bin\cdr\ /Y
copy Inetpub\wwwroot\cgi-bin\cdr\GetCdrImage.py \Inetpub\wwwroot\cgi-bin\cdr\ /Y
copy Inetpub\wwwroot\cgi-bin\cdr\ResizeImage.py \Inetpub\wwwroot\cgi-bin\cdr\ /Y
copy Inetpub\wwwroot\cgi-bin\cdr\TestPythonUpgrade.py \Inetpub\wwwroot\cgi-bin\cdr\ /Y
copy Inetpub\wwwroot\cgi-bin\cdr\UpdatePreMedlineCitations.py \Inetpub\wwwroot\cgi-bin\cdr\ /Y
copy Inetpub\wwwroot\cgi-bin\cdr\cdr-menus.py \Inetpub\wwwroot\cgi-bin\cdr\ /Y
copy Inetpub\wwwroot\cgi-bin\cdr\check-cdr-tier-settings.py \Inetpub\wwwroot\cgi-bin\cdr\ /Y
copy Inetpub\wwwroot\cgi-bin\cdr\ocecdr-3588.py \Inetpub\wwwroot\cgi-bin\cdr\ /Y
copy Inetpub\wwwroot\cgi-bin\cdr\ocecdr-3734.py \Inetpub\wwwroot\cgi-bin\cdr\ /Y
copy Inetpub\wwwroot\cgi-bin\cdr\proxy.py \Inetpub\wwwroot\cgi-bin\cdr\ /Y
copy Mailers\GPMailers.py \cdr\Mailers\ /Y
copy Mailers\cdrlatexlib.py \cdr\Mailers\ /Y
copy Utilities\DownloadCTGovProtocols.py \cdr\Utilities\ /Y
copy Utilities\GetRecentCTGovProtocols.py \cdr\Utilities\ /Y
copy Utilities\UpdateEmailerTrackingInfo.py \cdr\Utilities\ /Y
copy lib\Python\CdrLongReports.py \cdr\lib\Python\ /Y
copy lib\Python\NCIThes.py \cdr\lib\Python /Y
cd \
zip ocecdr-4114.zip Inetpub/wwwroot/cgi-bin/cdr/EditFilter.py Inetpub/wwwroot/cgi-bin/cdr/GetCdrImage.py Inetpub/wwwroot/cgi-bin/cdr/ResizeImage.py Inetpub/wwwroot/cgi-bin/cdr/TestPythonUpgrade.py Inetpub/wwwroot/cgi-bin/cdr/UpdatePreMedlineCitations.py Inetpub/wwwroot/cgi-bin/cdr/cdr-menus.py Inetpub/wwwroot/cgi-bin/cdr/check-cdr-tier-settings.py Inetpub/wwwroot/cgi-bin/cdr/ocecdr-3588.py Inetpub/wwwroot/cgi-bin/cdr/ocecdr-3734.py Inetpub/wwwroot/cgi-bin/cdr/proxy.py cdr/Mailers/GPMailers.py cdr/Mailers/cdrlatexlib.py cdr/Utilities/DownloadCTGovProtocols.py cdr/Utilities/GetRecentCTGovProtocols.py cdr/Utilities/UpdateEmailerTrackingInfo.py cdr/lib/Python/CdrLongReports.py cdr/lib/Python/NCIThes.py
ENDLOCAL
