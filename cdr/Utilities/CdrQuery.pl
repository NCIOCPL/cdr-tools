#----------------------------------------------------------------------
#
# $Id: CdrQuery.pl,v 1.1 2001-06-04 14:11:57 bkline Exp $
#
# Creates CDR command set for XQL query against the repository.
#
# Usage: perl CdrQuery uid pwd cond
# where: uid ::= CDR user account name
#        pwd ::= password for CDR user account
#       cond ::= predicate expression (without '[' ']') for XQL query
#
# Example: perl CdrQuery rmk BLAHBLAHBLAH "CdrAttr/Term/TermPrimaryType = 'gene'"
#
# $Log: not supported by cvs2svn $
#----------------------------------------------------------------------

# Check command-line arguments.
die "usage: CdrQuery.pl uid pwd search-conditions" unless $#ARGV == 2;

# Emit the command set document.
print qq(<CdrCommandSet>
 <CdrCommand>
  <CdrLogon>
   <UserName>$ARGV[0]</UserName>
   <Password>$ARGV[1]</Password>
  </CdrLogon>
 </CdrCommand>
 <CdrCommand>
  <CdrSearch>
   <Query>//CdrDoc[$ARGV[2]]/CdrCtl/DocId</Query>
  </CdrSearch>
 </CdrCommand>
 <CdrCommand>
   <CdrLogoff/>
 </CdrCommand>
</CdrCommandSet>
);
