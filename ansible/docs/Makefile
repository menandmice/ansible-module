#
# The Makefile
#
SHELL         := /bin/bash
.DEFAULT_GOAL := all
TOPDOC        := README
INCLUDES      := $(sort $(wildcard *.adoc))
THEMES        := $(sort $(wildcard resources/themes/*.yml))
#
DEPS          := $(THEMES)

$(TOPDOC).pdf: $(TOPDOC).adoc $(INCLUDES) $(DEPS)
	@asciidoctor-pdf				\
		--doctype=book				\
		--require='asciidoctor-diagram'		\
		--trace					\
		--timings				\
		$<

all: $(TOPDOC).pdf

clean:
	@rm -f $(TOPDOC).pdf
