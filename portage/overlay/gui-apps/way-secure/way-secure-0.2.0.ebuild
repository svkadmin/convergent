# Convergent: sway security contexts for the browsers (ARCHITECTURE 3.5, DECISIONS 41).
EAPI=8

CRATES="
	bitflags@2.3.3
	cfg-if@1.0.0
	cfg_aliases@0.1.1
	lexopt@0.3.0
	libc@0.2.153
	memchr@2.5.0
	nix@0.28.0
	proc-macro2@1.0.63
	quick-xml@0.37.2
	quote@1.0.29
	syn@2.0.23
	unicode-ident@1.0.10
	wayrs-client@1.2.0
	wayrs-core@1.0.4
	wayrs-proto-parser@3.0.0
	wayrs-protocols@0.14.5+1.39
	wayrs-scanner@0.15.2
"

inherit cargo

DESCRIPTION="Run a Wayland client inside a restricted security context"
HOMEPAGE="https://git.sr.ht/~whynothugo/way-secure"
SRC_URI="https://git.sr.ht/~whynothugo/way-secure/archive/v${PV}.tar.gz -> ${P}.tar.gz
	${CARGO_CRATE_URIS}"
S=${WORKDIR}/${PN}-v${PV}

LICENSE="ISC"
# Dependent crate licenses
LICENSE+=" || ( Apache-2.0 MIT ) Unicode-DFS-2016"
SLOT="0"
KEYWORDS="amd64"

src_install() {
	dobin "$(cargo_target_dir)/${PN}"
}
