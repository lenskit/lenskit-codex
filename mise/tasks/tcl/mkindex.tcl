#!/usr/bin/env tclsh
#MISE description="Make Tcl package index."

pkg_mkIndex -verbose src/tcl */*.tcl
