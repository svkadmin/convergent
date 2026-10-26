# Pinned prebuilt static assets; no Debian maintainer scripts or Node build.
EAPI=8

inherit unpacker

DESCRIPTION="Incus web management interface (Zabbly prebuilt assets)"
HOMEPAGE="https://github.com/zabbly/incus-ui-canonical"
SRC_URI="https://pkgs.zabbly.com/incus/lts-7.0/pool/main/i/incus/incus-ui-canonical_7.0.1-debian12-202609250207_amd64.deb"
S="${WORKDIR}"
LICENSE="AGPL-3"
SLOT="0"
KEYWORDS="amd64"
BDEPEND="$(unpacker_src_uri_depends)"

src_unpack() {
	unpack_deb ${A}
}

src_prepare() {
	default
	[[ -f opt/incus/ui/index.html ]] || die "missing prebuilt UI"
	[[ -z $(find opt/incus/ui -type l -print -quit) ]] || die "unexpected UI symlink"
}

src_configure() { :; }
src_compile() { :; }

src_install() {
	insinto /usr/share/incus-ui
	doins -r opt/incus/ui/.
}
