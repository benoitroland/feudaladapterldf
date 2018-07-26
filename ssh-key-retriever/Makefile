VERSION  = 0.0.2
# These are needed for the RPM build target:
BASEDIR   = $(PWD)
BASENAME := $(notdir $(PWD))
SRC_TAR   = ssh-key-retriever.tar
PKG_NAME  = ssh-key-retriever

SRCDIR   = .
BINDIR   = bin
GOPATH   = $(shell pwd)/GOPATH
#ifndef $(GOPATH)
#    #GOPATH=$(shell go env GOPATH)
#    GOPATH=$(shell pwd)/GOPATH
#    export GOPATH
#endif

rm       = rm -f

all: build

.PHONY: clean
clean:
	@$(rm) -r debian/.debhelper
	@$(rm) -r rpm/rpmbuild
	@$(rm) $(PKG_NAME)


distclean: clean
	@$(rm) -r $(BINDIR)
	@$(rm) -r $(MANDIR)
	@$(RM) -r $(GOPATH)


.PHONY: srctar
srctar:
	#@(cd ..; tar cf $(BASENAME)/$(SRC_TAR) $(BASENAME)/src $(BASENAME)/Makefile)
	@tar cf $(SRC_TAR) Makefile $(PKG_NAME) $(PKG_NAME).conf $(PKG_NAME).go   --transform='s_^_$(PKG_NAME)-$(VERSION)/_'

build:
	go get gopkg.in/alecthomas/kingpin.v2
	go build


.PHONY: rpm
rpm: srctar
	@mkdir -p rpm/rpmbuild/SOURCES
	#@cp -af src Makefile  rpm/rpmbuild/SOURCES
	@mv $(SRC_TAR) rpm/rpmbuild/SOURCES/
	rpmbuild --define "_topdir $(BASEDIR)/rpm/rpmbuild" -bb  rpm/ssh-key-retriever.spec
	@mv rpm/rpmbuild/RPMS/*/*rpm ..
	@echo "Success: RPMs are in parent directory"
