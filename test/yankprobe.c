#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include "yankmem.h"

static int failures;
static char chunk[257];

static void check(int ok)
{
    if (!ok)
        failures++;
}

static unsigned char pattern(unsigned i)
{
    return (unsigned char)((i * 13U + i / 251U) & 255U);
}

int main(int argc, char **argv)
{
    char *source;
    unsigned i, offset, count;
    FILE *f;
    int initialized = vi_yank_init();

    if (argc > 1 && !strcmp(argv[1], "REJECT")) {
        if (initialized) {
            vi_yank_close();
            return 1;
        }
        puts("VI YANK INIT REJECTED");
        return 0;
    }
    if (!initialized) {
        puts("VI YANK INIT FAILED");
        return 1;
    }
    check(vi_yank_init());
    source = malloc(VI_YANK_CAPACITY);
    if (source == NULL) {
        vi_yank_close();
        puts("VI YANK NEAR ALLOCATION FAILED");
        return 1;
    }
    for (i = 0; i < VI_YANK_CAPACITY; i++)
        source[i] = pattern(i);
    check(vi_yank_store(source, VI_YANK_CAPACITY));
    memset(source, 0, VI_YANK_CAPACITY);
    for (offset = 0; offset < VI_YANK_CAPACITY; offset += count) {
        count = VI_YANK_CAPACITY - offset;
        if (count > 256)
            count = 256;
        chunk[256] = 77;
        check(vi_yank_load(offset, chunk, count));
        check(chunk[256] == 77);
        for (i = 0; i < count; i++)
            check((unsigned char)chunk[i] == pattern(offset + i));
    }
    for (i = 0; i < VI_YANK_CAPACITY; i++)
        check(source[i] == 0);
    check(!vi_yank_store(source, VI_YANK_CAPACITY + 1U));
    check(!vi_yank_store(NULL, 1));
    check(!vi_yank_load(VI_YANK_CAPACITY, chunk, 1));
    check(vi_yank_load(VI_YANK_CAPACITY - 1U, chunk, 1));
    check((unsigned char)chunk[0] == pattern(VI_YANK_CAPACITY - 1U));
    check(vi_yank_store(NULL, 0));
    check(vi_yank_load(0, NULL, 0));
    check(!vi_yank_load(0, chunk, 1));
    free(source);
    vi_yank_close();
    vi_yank_close();
    check(!vi_yank_store(chunk, 1));
    check(vi_yank_init());
    check(vi_yank_store("again", 5));
    check(vi_yank_load(0, chunk, 5) && !memcmp(chunk, "again", 5));
    vi_yank_close();
    printf("VI YANK PASS: %d failures\n", failures);
    f = fopen("RESULT.TXT", "w");
    if (f == NULL)
        return 1;
    fprintf(f, "VI YANK PASS: %d failures\n", failures);
    if (fclose(f))
        return 1;
    return failures != 0;
}
