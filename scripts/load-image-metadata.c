// Import OCI content through Apple's imageLoad route without the CLI's eager
// full-rootfs unpack. Protocol: apple/container 1.2.2 ClientImage and
// ImagesServiceHarness (https://github.com/apple/container/tree/1.2.2).
#include <xpc/xpc.h>
#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>

int main(int argc, char **argv) {
    if (argc != 2 || argv[1][0] != '/') {
        fprintf(stderr, "Usage: load-image-metadata /absolute/path/image.oci.tar\n");
        return 2;
    }
    alarm(300);
    xpc_connection_t connection = xpc_connection_create_mach_service(
        "com.apple.container.core.container-core-images", NULL, 0);
    xpc_connection_set_event_handler(connection, ^(xpc_object_t event) { (void)event; });
    xpc_connection_activate(connection);
    xpc_object_t request = xpc_dictionary_create_empty();
    xpc_dictionary_set_string(request, "com.apple.container.xpc.route", "imageLoad");
    xpc_dictionary_set_string(request, "filePath", argv[1]);
    xpc_dictionary_set_bool(request, "forceLoad", false);
    xpc_object_t reply = xpc_connection_send_message_with_reply_sync(connection, request);
    int result = 0;
    if (!reply || xpc_get_type(reply) != XPC_TYPE_DICTIONARY) {
        char *message = reply ? xpc_copy_description(reply) : NULL;
        fprintf(stderr, "Apple image service did not accept the import: %s\n", message ? message : "no reply");
        free(message); result = 1;
    } else {
        size_t size = 0;
        const void *error = xpc_dictionary_get_data(reply, "com.apple.container.xpc.error", &size);
        if (error) { fwrite(error, 1, size, stderr); fputc('\n', stderr); result = 1; }
        else {
            const void *images = xpc_dictionary_get_data(reply, "imageDescriptions", &size);
            if (!images || !size) { fprintf(stderr, "Image service returned no image descriptions\n"); result = 1; }
            else { fwrite(images, 1, size, stdout); fputc('\n', stdout); }
        }
    }
    if (reply) xpc_release(reply);
    xpc_release(request);
    xpc_connection_cancel(connection);
    xpc_release(connection);
    return result;
}
