VERSION  = 0.1.0
# These are needed for the RPM build target:
BASEDIR         = $(PWD)
BASENAME       := $(notdir $(PWD))
SRC_TAR         = ssh-key-retriever.tar
PKG_NAME        = ssh-key-retriever

SRCDIR          = .
BINDIR          = bin
GOPATH          = $(shell pwd)/GOPATH
GO              = go
#GO_BUILD_PARAMS = -ldflags -buildid\ fuckRPM
GO_BUILD_PARAMS = -ldflags -B\ 0x2323232323232323232323232323232323232323

INSTALL_PATH ?=/usr
MAN_PATH     ?=/usr/share/man
CONFIG_PATH  ?=/etc

# FILES:
SSH_KEY_RETRIEVER = ssh-key-retriever
CONFIG = ssh-key-retriever.json.conf

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
	@tar cf $(SRC_TAR) Makefile README.md Changelog $(SSH_KEY_RETRIEVER) $(CONFIG).example $(PKG_NAME).go   --transform='s_^_$(PKG_NAME)-$(VERSION)/_'

.PHONY: build
build:
	@echo $(GOPATH)
	$(GO) get gopkg.in/alecthomas/kingpin.v2
	$(GO) build $(GO_BUILD_PARAMS)

.PHONY: install
install:
	@install -D $(SSH_KEY_RETRIEVER) $(INSTALL_PATH)/bin/$(SSH_KEY_RETRIEVER)
	@install -m 644 -D $(CONFIG).example $(CONFIG_PATH)/$(CONFIG)
	@install -d $(INSTALL_PATH)/share/doc/ssh-key-retriever/
	@install -m 644 -D README.md $(INSTALL_PATH)/share/doc/ssh-key-retriever/
	@install -m 644 -D Changelog $(INSTALL_PATH)/share/doc/ssh-key-retriever/
	@echo "Installation complete!"


.PHONY: rpm
rpm: build srctar 
	@mkdir -p rpm/rpmbuild/SOURCES
	#@cp -af src Makefile  rpm/rpmbuild/SOURCES
	@mv $(SRC_TAR) rpm/rpmbuild/SOURCES/
	rpmbuild --define "_topdir $(BASEDIR)/rpm/rpmbuild" -bb  rpm/ssh-key-retriever.spec
	@mv rpm/rpmbuild/RPMS/*/*rpm ..
	@echo "Success: RPMs are in parent directory"
