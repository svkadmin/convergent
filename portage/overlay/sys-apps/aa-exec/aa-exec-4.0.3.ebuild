# Convergent: AppArmor's aa-exec alone, for Incus (DECISIONS 41); apparmor-utils brings Python.
EAPI=8

inherit toolchain-funcs

DESCRIPTION="aa-exec from AppArmor's binutils"
HOMEPAGE="https://gitlab.com/apparmor/apparmor"
SRC_URI="https://launchpad.net/apparmor/$(ver_cut 1-2)/${PV}/+download/apparmor-${PV}.tar.gz"
S=${WORKDIR}/apparmor-${PV}/binutils

LICENSE="GPL-2"
SLOT="0"
KEYWORDS="amd64"

DEPEND="~sys-libs/libapparmor-${PV}"
RDEPEND="${DEPEND}"

src_prepare() {
	default
	sed -i -e 's/Bstatic/Bdynamic/g' Makefile || die
}

src_compile() {
	emake CC="$(tc-getCC)" EXTRA_CFLAGS="${CFLAGS}" USE_SYSTEM=1 aa-exec
}

src_install() {
	dobin aa-exec
}
