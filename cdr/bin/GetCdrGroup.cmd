@python -c "import cdr, string; print cdr.sendCommands(cdr.wrapCommand('<CdrGetGrp><GrpName>%%s</GrpName></CdrGetGrp>' %% string.strip('%*'), ('rmk','***REDACTED***')))"
