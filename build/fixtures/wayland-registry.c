/* Registry round-trip on the ordinary and security-context sockets. */
#include <stdio.h>
#include <stdint.h>
#include <wayland-client.h>

static void global(void *data, struct wl_registry *registry, uint32_t name,
		const char *interface, uint32_t version) {
	(void)data; (void)registry; (void)name; (void)version;
	puts(interface);
}

static void removed(void *data, struct wl_registry *registry, uint32_t name) {
	(void)data; (void)registry; (void)name;
}

int main(int argc, char **argv) {
	const struct wl_registry_listener listener = {global, removed};
	if (argc != 2) return 1;
	struct wl_display *display = wl_display_connect(argv[1]);
	if (!display) return 1;
	struct wl_registry *registry = wl_display_get_registry(display);
	if (!registry) return 1;
	if (wl_registry_add_listener(registry, &listener, NULL) < 0) return 1;
	int result = wl_display_roundtrip(display);
	wl_registry_destroy(registry);
	wl_display_disconnect(display);
	return result < 0 || fflush(stdout) != 0;
}
